"""Target-bound Windows diagnostics. No launch, pairing, mount or input API.

Run in the dedicated host venv, never from the iSH client. Raw artifacts and
configuration stay outside Git; stdout contains only public_summary's fields.
"""
import argparse
import asyncio
import contextlib
import hashlib
import importlib.metadata
import json
import logging
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

from .capture import inspect_bytes
from .validation import MAX_IMAGE, ProbeError, json_object


PMD_VERSION = "11.55.1"
STAGES = ("host", "transport", "lockdown", "developer_mode", "ddi", "apps",
          "server", "capture", "geometry", "cleanup")
STATUSES = frozenset(("pass", "blocked", "fail", "not_run"))
REASONS = frozenset(("not_requested", "host_unavailable", "host_version", "config_invalid",
    "private_directory_invalid", "device_list_invalid", "target_missing", "transport_missing",
    "target_ambiguous", "target_changed", "pairing_required", "backend_error", "deadline",
    "cancelled", "cleanup_failed", "developer_mode_disabled", "developer_mode_unknown",
    "ddi_missing", "app_missing", "server_not_probed", "geometry_unverified",
    "capture_invalid", "capture_metadata_invalid", "artifact_conflict", "artifact_error"))
APP_IDS = {"loopctrl": "top.ebato.loopctrl", "game": "jp.co.spike-chunsoft.necrodancerjp",
           "ish": "app.ish.iSH", "sidestore": "com.SideStore.SideStore"}


class LabError(Exception):
    def __init__(self, code):
        self.code = code if code in REASONS else "backend_error"
        super().__init__(self.code)


def _outside_git(path):
    # Some managed workspaces expose an empty, protected .git placeholder.
    # A Git directory has HEAD; a worktree/submodule uses a .git file.
    return not any((p / ".git").is_file() or (p / ".git" / "HEAD").is_file()
                   for p in (path, *path.parents))


def _windows_acl_ok(state):
    if not isinstance(state, dict) or set(state) != {"owner", "user", "protected", "allowed"}:
        return False
    user = state["user"]
    if type(user) is not str or re.fullmatch(r"S-1-\d+(?:-\d+)+", user) is None:
        return False
    owners = {"S-1-5-18", "S-1-5-32-544", user}
    # Python 3.14's Windows mkdir(0o700) uses OWNER RIGHTS (OW). It is
    # private only after the actual owner has passed the separate check.
    readers = owners | {"S-1-3-4"}
    return (state["protected"] is True and type(state["owner"]) is str
            and state["owner"] in owners and isinstance(state["allowed"], list)
            and 0 < len(state["allowed"]) <= 256
            and all(type(sid) is str and sid in readers for sid in state["allowed"]))


def _windows_private_directory(path):
    command = ("$ErrorActionPreference='Stop'; $a=Get-Acl -LiteralPath "
        "$env:NECRO_LAB_PRIVATE_DIRECTORY; [pscustomobject]@{"
        "owner=$a.GetOwner([Security.Principal.SecurityIdentifier]).Value; "
        "user=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value; "
        "protected=$a.AreAccessRulesProtected; "
        "allowed=@($a.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier]) | "
        "Where-Object {$_.AccessControlType -eq 'Allow'} | "
        "ForEach-Object {$_.IdentityReference.Value})} | ConvertTo-Json -Compress -Depth 3")
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        env=dict(os.environ, NECRO_LAB_PRIVATE_DIRECTORY=str(path)), stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL, timeout=5, check=False)
    try:
        if result.returncode or not _windows_acl_ok(json_object(result.stdout, limit=16384)):
            raise LabError("private_directory_invalid")
    except ProbeError:
        raise LabError("private_directory_invalid") from None


def _private_root(value):
    if not isinstance(value, (str, Path)) or not Path(value).is_absolute():
        raise LabError("private_directory_invalid")
    try:
        path = Path(value).resolve(strict=True)
        if not path.is_dir() or not _outside_git(path):
            raise LabError("private_directory_invalid")
        if os.name == "nt":
            # ACL metadata is parsed internally and never enters the summary.
            # The path is passed through the environment, never shell source.
            _windows_private_directory(path)
        elif path.stat().st_mode & 0o077:
            raise LabError("private_directory_invalid")
        return path
    except (OSError, ValueError, subprocess.SubprocessError):
        raise LabError("private_directory_invalid") from None


def validate_config(config):
    if (not isinstance(config, dict) or set(config) != {"expected_udid", "transport", "private_dir"}
            or type(config.get("expected_udid")) is not str
            or re.fullmatch(r"[A-Za-z0-9_-]{8,128}", config["expected_udid"]) is None
            or config.get("transport") not in ("USB", "Network")):
        raise LabError("config_invalid")
    return dict(config, private_dir=_private_root(config["private_dir"]))


def load_config(path):
    try:
        path = Path(path).resolve(strict=True)
        if not path.is_file() or not _outside_git(path) or path.stat().st_size > 16384:
            raise LabError("config_invalid")
        return validate_config(json_object(path.read_bytes(), limit=16384))
    except (OSError, ValueError, ProbeError):
        raise LabError("config_invalid") from None


def select_device(devices, config):
    if not isinstance(devices, list) or len(devices) > 256:
        raise LabError("device_list_invalid")
    for row in devices:
        if (not isinstance(row, dict) or set(row) != {"udid", "transport", "device_id"}
                or type(row["udid"]) is not str or row["transport"] not in ("USB", "Network")
                or type(row["device_id"]) is not int or row["device_id"] < 0):
            raise LabError("device_list_invalid")
    target = [x for x in devices if x["udid"] == config["expected_udid"]]
    if not target:
        raise LabError("target_missing")
    selected = [x for x in target if x["transport"] == config["transport"]]
    if not selected:
        raise LabError("transport_missing")
    if len(selected) != 1:
        raise LabError("target_ambiguous")
    return dict(selected[0])


def _stage(record, name, status, reason=None):
    row = {"status": status}
    if reason:
        row["reason"] = reason
    record["stages"][name] = row


def public_summary(record):
    """Reconstruct a whitelist; never return backend payloads or exception text."""
    result = {"schema": "necro-device-lab-v1", "operation": record.get("operation")
              if record.get("operation") in ("check", "capture") else "check",
              "operation_status": record.get("operation_status")
              if type(record.get("operation_status")) is str and record["operation_status"] in STATUSES else "fail",
              "input_authorized": False, "automation_ready": False, "stages": {}}
    for name in STAGES:
        row = record.get("stages", {}).get(name, {})
        row = row if isinstance(row, dict) else {}
        safe = {"status": row.get("status") if type(row.get("status")) is str and row["status"] in STATUSES else "not_run"}
        if type(row.get("reason")) is str and row["reason"] in REASONS:
            safe["reason"] = row["reason"]
        result["stages"][name] = safe
    if record.get("transport") in ("USB", "Network"):
        result["transport"] = record["transport"]
    if type(record.get("run_id")) is str and re.fullmatch(r"[0-9a-f]{32}", record["run_id"]):
        result["run_id"] = record["run_id"]
    apps = record.get("apps")
    if isinstance(apps, dict) and set(apps) == set(APP_IDS) and all(type(v) is bool for v in apps.values()):
        result["app_presence"] = {k: apps[k] for k in APP_IDS}
    image = record.get("image", {})
    if (isinstance(image, dict) and image.get("format") in ("PNG", "JPEG")
            and all(type(image.get(k)) is int and 1 <= image[k] <= 4096
                    for k in ("pixel_width", "pixel_height"))
            and type(image.get("exif_orientation")) is int and 1 <= image["exif_orientation"] <= 8):
        result["image"] = {k: image[k] for k in ("format", "pixel_width", "pixel_height", "exif_orientation")}
        result["freshness_verified"] = False
    return result


class PmdBackend:
    """The only device adapter: allowlisted read APIs, lazily imported."""
    async def host_version(self):
        if sys.platform != "win32":
            raise LabError("host_unavailable")
        return importlib.metadata.version("pymobiledevice3")

    async def list_devices(self):
        from pymobiledevice3.usbmux import list_devices
        return [{"udid": d.serial, "transport": d.connection_type, "device_id": d.devid}
                for d in await list_devices()]

    async def connect(self, selected, config):
        from pymobiledevice3.lockdown import create_using_usbmux
        return await create_using_usbmux(serial=selected["udid"],
            connection_type=selected["transport"], autopair=False,
            pairing_records_cache_folder=config["private_dir"] / "pairing")

    async def info(self, session):
        values = await session.get_value()
        return {"udid": values.get("UniqueDeviceID"), "paired": session.paired}

    async def developer_mode(self, session):
        return await session.get_value(domain="com.apple.security.mac.amfi", key="DeveloperModeStatus")

    async def ddi(self, session):
        from pymobiledevice3.services.mobile_image_mounter import MobileImageMounterService
        async with MobileImageMounterService(session) as service:
            return await service.is_image_mounted("Developer")

    async def apps(self, session):
        from pymobiledevice3.services.installation_proxy import InstallationProxyService
        async with InstallationProxyService(session) as service:
            rows = await service.browse(options={"ApplicationType": "User"},
                attributes=["CFBundleIdentifier"])
        installed = {r.get("CFBundleIdentifier") for r in rows}
        # Signing suffixes establish presence only, never app/ABI identity.
        return {name: any(item == bundle or (name in ("sidestore", "loopctrl") and isinstance(item, str)
                and item.startswith(bundle + ".")) for item in installed)
                for name, bundle in APP_IDS.items()}

    async def screenshot(self, session):
        from pymobiledevice3.services.screenshot import ScreenshotService
        async with ScreenshotService(session) as service:
            return {"data": await service.take_screenshot(), "metadata": {}}

    async def close(self, session):
        await session.close()


async def run_lab(config, operation="check", *, backend=None, timeout=20):
    record = {"operation": operation, "operation_status": "blocked", "input_authorized": False,
              "automation_ready": False, "stages": {k: {"status": "not_run"} for k in STAGES}}
    current, session, store = "host", None, None
    backend = backend or PmdBackend()
    try:
        if operation not in ("check", "capture") or type(timeout) not in (int, float) or not math.isfinite(timeout) or not 0 < timeout <= 300:
            raise LabError("config_invalid")
        deadline = time.monotonic() + timeout
        config = validate_config(config)
        record["transport"] = config["transport"]

        async def steps():
            nonlocal current, session, store
            if await backend.host_version() != PMD_VERSION:
                raise LabError("host_version")
            _stage(record, "host", "pass")
            current = "transport"
            selected = select_device(await backend.list_devices(), config)
            _stage(record, "transport", "pass")
            current = "lockdown"
            session = await backend.connect(selected, config)
            info = await backend.info(session)
            if not isinstance(info, dict) or info.get("udid") != config["expected_udid"]:
                raise LabError("target_changed")
            if info.get("paired") is not True:
                raise LabError("pairing_required")
            _stage(record, "lockdown", "pass")
            for name, method in (("developer_mode", backend.developer_mode), ("ddi", backend.ddi), ("apps", backend.apps)):
                current = name
                try:
                    value = await method(session)
                    if name == "apps":
                        if not isinstance(value, dict) or set(value) != set(APP_IDS) or any(type(v) is not bool for v in value.values()):
                            raise LabError("backend_error")
                        passed = value["loopctrl"] and value["game"]
                        reason = "app_missing"
                        record["apps"] = value
                    else:
                        passed = value is True
                        reason = ("developer_mode_disabled" if value is False else "developer_mode_unknown") if name == "developer_mode" else "ddi_missing"
                    _stage(record, name, "pass" if passed else "blocked", None if passed else reason)
                except Exception:
                    _stage(record, name, "fail", "backend_error")
            _stage(record, "server", "not_run", "server_not_probed")
            _stage(record, "geometry", "blocked", "geometry_unverified")
            if operation == "check":
                return
            current = "capture"
            for name in ("developer_mode", "ddi"):
                prerequisite = record["stages"][name]
                if prerequisite["status"] != "pass":
                    _stage(record, "capture", "blocked", prerequisite["reason"])
                    return
            if select_device(await backend.list_devices(), config) != selected:
                raise LabError("target_changed")
            if (await backend.info(session)).get("udid") != config["expected_udid"]:
                raise LabError("target_changed")
            started = time.monotonic_ns()
            response = await backend.screenshot(session)
            ended = time.monotonic_ns()
            if not isinstance(response, dict) or set(response) != {"data", "metadata"}:
                raise LabError("capture_invalid")
            raw, metadata = response["data"], response["metadata"]
            if type(raw) is not bytes or not raw or len(raw) > MAX_IMAGE:
                raise LabError("capture_invalid")
            if select_device(await backend.list_devices(), config) != selected:
                raise LabError("target_changed")
            run_id = uuid.uuid4().hex
            candidate = config["private_dir"] / run_id
            try:
                candidate.mkdir(mode=0o700, exist_ok=False)
            except FileExistsError:
                raise LabError("artifact_conflict") from None
            store = _private_root(candidate)
            record["run_id"] = run_id
            with (store / "capture.bin").open("xb") as stream:
                stream.write(raw)
            record["artifact"] = {"file": "capture.bin", "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(), "source": "com.apple.mobile.screenshotr",
                "requested_transport": config["transport"], "actual_transport": selected["transport"],
                "clock_domain": "windows-host-monotonic", "request_start_ns": started,
                "response_end_ns": ended, "device_capture_time_ns": None, "freshness_verified": False}
            try:
                image = inspect_bytes(raw)
            except ProbeError:
                raise LabError("capture_invalid") from None
            if not isinstance(metadata, dict) or set(metadata) - {"pixel_width", "pixel_height", "exif_orientation"}:
                raise LabError("capture_metadata_invalid")
            if any(type(v) is not int or v != image[k] for k, v in metadata.items()):
                raise LabError("capture_metadata_invalid")
            if time.monotonic() >= deadline:
                raise LabError("deadline")
            record["image"] = {k: image[k] for k in ("format", "pixel_width", "pixel_height", "exif_orientation")}
            _stage(record, "capture", "pass")
            record["operation_status"] = "pass"

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise LabError("deadline")
        await asyncio.wait_for(steps(), timeout=remaining)
    except asyncio.TimeoutError:
        _stage(record, current, "blocked", "deadline")
    except asyncio.CancelledError:
        _stage(record, current, "blocked", "cancelled")
    except LabError as exc:
        failed = exc.code in ("capture_invalid", "capture_metadata_invalid", "device_list_invalid", "artifact_error")
        _stage(record, current, "fail" if failed else "blocked", exc.code)
        if failed:
            record["operation_status"] = "fail"
    except Exception:
        _stage(record, current, "fail", "backend_error")
        record["operation_status"] = "fail"
    finally:
        if session is not None:
            try:
                await asyncio.wait_for(backend.close(session), timeout=2)
                _stage(record, "cleanup", "pass")
            except (Exception, asyncio.CancelledError):
                _stage(record, "cleanup", "fail", "cleanup_failed")
                record["operation_status"] = "fail"
        if store is not None:
            try:
                private = dict(record, target_udid=config["expected_udid"])
                with (store / "manifest.json").open("x", encoding="utf-8") as stream:
                    json.dump(private, stream, ensure_ascii=True, allow_nan=False, indent=2)
                    stream.write("\n")
            except (OSError, ValueError):
                _stage(record, "capture", "fail", "artifact_error")
                record["operation_status"] = "fail"
    return public_summary(record)


class _Parser(argparse.ArgumentParser):
    def error(self, _message):
        raise LabError("config_invalid")


def main(argv=None, *, backend=None, runner=None):
    parser = _Parser(description="Target-bound, input-free device diagnostics")
    parser.add_argument("operation", choices=("check", "capture"))
    parser.add_argument("--config", required=True)
    parser.add_argument("--timeout", type=float, default=20)
    try:
        args = parser.parse_args(argv)
    except LabError:
        print(json.dumps(public_summary({"operation_status": "fail", "stages": {
            "host": {"status": "fail", "reason": "config_invalid"}}})))
        return 2
    previous_logging = logging.root.manager.disable
    previous_handlers = tuple(logging.root.handlers)
    try:
        logging.disable(logging.CRITICAL)
        with open(os.devnull, "w") as sink, contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            config = load_config(args.config)
            # The pinned adapter supplies the Windows selector event loop.
            if runner is None:
                from pymobiledevice3.utils import run_in_loop
                runner = run_in_loop
            result = runner(run_lab(config, args.operation, backend=backend, timeout=args.timeout))
    except (LabError, ImportError, KeyboardInterrupt) as exc:
        reason = exc.code if isinstance(exc, LabError) else "cancelled" if isinstance(exc, KeyboardInterrupt) else "host_unavailable"
        result = public_summary({"operation": args.operation, "operation_status": "fail",
            "stages": {"host": {"status": "fail", "reason": reason}}})
    except Exception:
        result = public_summary({"operation": args.operation, "operation_status": "fail",
            "stages": {"host": {"status": "fail", "reason": "backend_error"}}})
    finally:
        logging.disable(previous_logging)
        for handler in tuple(logging.root.handlers):
            if handler not in previous_handlers:
                logging.root.removeHandler(handler)
                handler.close()
    print(json.dumps(result, ensure_ascii=True, allow_nan=False, indent=2))
    return 0 if result["operation_status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
