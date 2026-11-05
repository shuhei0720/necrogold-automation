"""TEST-011: 続行対象の候補参照を一度照会する。ゲーム内入力APIは許可しない。"""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
import uuid

from . import VERSION
from .capture import inspect_payload, validate_source_geometry
from .crypto import Crypto
from .deadlines import OwnedRpcTimer
from .protocol import Client, GAME, HttpTransport, load_pairing
from .session import atomic_write, safe_info
from .validation import MAX_IMAGE, ProbeError, json_object

CAPABILITY = "screenshot_image_geometry_v1"
FIND_PARAMS = {"bundle_id": GAME, "element_id": "ゲームを続行", "match": "exact"}
CAPTURE_PARAMS = {"format": "jpeg", "quality": .6, "scale": 1, "geometry": "image_size_v1"}
MAX_REPORT = 65536
SESSION_SECONDS = 50
WORKER_REPORT_READ_EXIT = 74
STEPS = ("initial_info", "launch", "pre_info", "before_capture", "before_info", "before_save",
         "find", "after_info", "after_capture", "final_info", "after_save")
STAGES = ("spawn_requested", "pairing_load", "crypto_initialize", "timer_initialize") + STEPS + ("complete",)
INFO_STEPS = ("initial_info", "pre_info", "before_info", "after_info", "final_info")
TYPES = frozenset(("Any", "Application", "Window", "Button", "StaticText", "TextField", "SecureTextField",
                   "TextView", "SearchField", "Image", "Icon", "Cell", "Table", "CollectionView", "ScrollView",
                   "Switch", "Slider", "Link", "NavigationBar", "TabBar", "Toolbar", "Alert", "Sheet", "Keyboard",
                   "Key", "Picker", "PickerWheel", "SegmentedControl", "Map", "WebView", "Other", "Group"))
VISIBILITY = ("in_view", "partial", "offscreen")
ERRORS = frozenset(("source_geometry_capability_missing", "foreground_not_verified", "source_geometry_invalid",
                   "rpc_error", "rpc_deadline", "connection_error", "response_mac_mismatch", "response_id_mismatch",
                   "invalid_response_tag", "rpc_result_type", "http_body_limit", "http_body_truncated",
                   "pairing_missing", "pairing_ambiguous", "invalid_pairing_record", "posix_timer_required",
                   "timer_already_in_use", "timer_setup_failed", "timer_cleanup_failed", "timer_owner_required",
                   "timer_unusable", "timer_handler_in_use", "session_deadline", "user_interrupt",
                   "output_write_failed", "internal_error", "worker_start_failed", "worker_failed",
                   "worker_cleanup_failed",
                   "report_read_failed", "worker_report_read_failed", "invalid_params", "method_not_allowed",
                   "json_size", "json_depth", "json_nodes", "invalid_json", "duplicate_json_key", "nonfinite_json",
                   "json_object_required", "base64_size_or_type", "invalid_base64"))
IMAGE_FIELDS = ("image_status", "format", "pixel_width", "pixel_height", "exif_orientation", "raw_bytes",
                "max_luma", "mean_luma", "sha256", "game_state", "input_authorized", "geometry_applied",
                "capture_time_ns", "source_sequence", "frame_age_ms", "freshness_verified", "reported_geometry",
                "metadata_issues")
GEOMETRY_FIELDS = ("geometry", "input_geometry_verified", "source_orientation", "scope", "source_scale",
                   "device_scale", "scale", "requested_scale", "source_width", "source_pixel_width",
                   "image_point_width", "point_width", "pixel_width", "source_height", "source_pixel_height",
                   "image_point_height", "point_height", "pixel_height")
_cancel_requested = False


def supervise(command, timeout, diagnostics=None):
    """spawn中の停止もフラグで受け、取得した子の終了・回収を期限付きで試みる。"""
    details = diagnostics if diagnostics is not None else {}
    details.update(returncode=None, signal_number=None, signal_name=None,
                   exit_confirmed=None, cleanup_error=None)
    process = None
    reason = None
    expires = time.monotonic() + timeout
    try:
        if _cancel_requested:
            return "user_interrupt"
        try:
            process = subprocess.Popen(command, stderr=subprocess.DEVNULL)
        except OSError as exc:
            details["spawn_errno"] = exc.errno if type(exc.errno) is int else None
            return "worker_start_failed"
        while True:
            if _cancel_requested:
                reason = "user_interrupt"
                break
            remaining = expires - time.monotonic()
            if remaining <= 0:
                reason = "session_deadline"
                break
            try:
                process.wait(timeout=min(.1, remaining))
                break
            except subprocess.TimeoutExpired:
                continue
    except KeyboardInterrupt:
        # main以外からの呼出しでも既存の停止契約を保つ。
        reason = "user_interrupt"
    except OSError:
        details["cleanup_error"] = "worker_cleanup_failed"
    finally:
        if process is not None:
            if process.returncode is None:
                needs_kill = False
                try:
                    process.terminate()
                except (OSError, KeyboardInterrupt):
                    details["cleanup_error"] = "worker_cleanup_failed"
                    needs_kill = True
                if not needs_kill:
                    try:
                        process.wait(timeout=.3)
                    except subprocess.TimeoutExpired:
                        needs_kill = True
                    except (OSError, KeyboardInterrupt):
                        details["cleanup_error"] = "worker_cleanup_failed"
                        needs_kill = True
                if needs_kill:
                    try:
                        process.kill()
                    except (OSError, KeyboardInterrupt):
                        details["cleanup_error"] = "worker_cleanup_failed"
                    # killの成否だけでは終了を断定しない。失敗時も一度だけ回収を試みる。
                    try:
                        process.wait(timeout=1)
                    except (OSError, subprocess.TimeoutExpired, KeyboardInterrupt):
                        details["cleanup_error"] = "worker_cleanup_failed"
            details["returncode"] = process.returncode
            details["exit_confirmed"] = process.returncode is not None
            if not details["exit_confirmed"]:
                details["cleanup_error"] = "worker_cleanup_failed"
            if process.returncode is not None and process.returncode < 0:
                details["signal_number"] = -process.returncode
                try:
                    details["signal_name"] = signal.Signals(-process.returncode).name
                except ValueError:
                    details["signal_name"] = "UNKNOWN_SIGNAL"
    if details["cleanup_error"]:
        return "worker_cleanup_failed"
    if _cancel_requested:
        return "user_interrupt"
    if reason:
        return reason
    return None if process is not None and process.returncode == 0 else "worker_failed"


class InputPathClient(Client):
    """固定の読取要求とゲーム起動1回のみ。失敗した送信も回数に含める。"""

    def __init__(self, *args, **kwargs):
        kwargs.update(allow_launch=True, source_geometry=True)
        super().__init__(*args, **kwargs)
        self.find_sent = self.launch_sent = False

    def _validate(self, method, params):
        expected = {"device_info": {}, "launch_app": {"bundle_id": GAME},
                    "screenshot": CAPTURE_PARAMS, "find_element": FIND_PARAMS}.get(method)
        if (type(params) is not dict or expected is None or set(params) != set(expected)
                or any(type(params[key]) is not type(value) or params[key] != value
                       for key, value in expected.items())):
            raise ProbeError("method_not_allowed")

    def call(self, method, params=None, *, timeout=None):
        params = {} if params is None else params
        self._validate(method, params)
        if method in ("find_element", "launch_app"):
            field = "find_sent" if method == "find_element" else "launch_sent"
            if getattr(self, field):
                raise ProbeError("method_not_allowed")
            # 親の暗号化・通信・タイマーが失敗しても照会を再送しない。
            setattr(self, field, True)
        return super().call(method, params, timeout=timeout)


def finite(value, low, high):
    return type(value) in (int, float) and low <= value <= high and math.isfinite(value)


def sanitize_ax(result):
    """本文・value・hint・生refを持ち越さず、固定型だけを抽出する。"""
    output = {"label_exact": result.get("label") == FIND_PARAMS["element_id"],
              "ref_present": isinstance(result.get("ref"), str)
              and re.fullmatch(r"el_[0-9]{1,20}", result["ref"]) is not None,
              "exists": result.get("exists") if type(result.get("exists")) is bool else None,
              "hittable": result.get("hittable") if type(result.get("hittable")) is bool else None,
              "frame": None, "element_type": None, "visibility": None,
              "match_count": None, "alternatives_count": None,
              "ambiguity": "not_reported", "response_valid": True}
    coords = {name: result.get(name) for name in ("x", "y", "width", "height")}
    if (all(finite(coords[name], -4096, 4096) for name in ("x", "y"))
            and all(finite(coords[name], 0, 4096) and coords[name] > 0 for name in ("width", "height"))):
        output["frame"] = coords
    for key, allowed in (("element_type", TYPES), ("visibility", VISIBILITY)):
        if key in result:
            value = result[key]
            if isinstance(value, str) and value in allowed:
                output[key] = value
            else:
                output["response_valid"] = False
    if "match_count" in result:
        count = result["match_count"]
        if type(count) is int and 1 <= count <= 100000:
            output["match_count"] = count
        else:
            output["ambiguity"] = "invalid"
    if "alternatives" in result:
        alternatives = result["alternatives"]
        if type(alternatives) is list and len(alternatives) <= 10000:
            output["alternatives_count"] = len(alternatives)
        else:
            output["ambiguity"] = "invalid"
    count, alternatives = output["match_count"], output["alternatives_count"]
    if count is not None and alternatives is not None and alternatives >= count:
        output["ambiguity"] = "invalid"
    if output["ambiguity"] != "invalid" and ((count is not None and count > 1) or alternatives):
        output["ambiguity"] = "reported"
    if output["visibility"] in ("partial", "offscreen") and output["hittable"] is True:
        output["response_valid"] = False
    return output


def candidate_ax(ax):
    return (ax is not None and ax["label_exact"] is True and ax["ref_present"] is True
            and ax["exists"] is True and ax["hittable"] is True and ax["frame"] is not None
            and ax["ambiguity"] == "not_reported" and ax["response_valid"] is True)


def candidate_evidence(report):
    # 非黒はゲーム認識の証明ではないが、暗い診断画像では確認を確定しない。
    return candidate_ax(report["ax"]) and all(
        image is not None and image["image_status"] == "decoded_nonblank"
        for image in report["images"].values())


def new_report(start_ns):
    return {"version": VERSION, "kind": "input_path_probe", "test_id": "TEST-011",
            "device_acceptance": "not_tested", "input_authorized": False, "input_geometry_verified": False,
            "device_input_cancel_verified": False, "start_ns": start_ns, "end_ns": None,
            "status": "running", "stage": "spawn_requested", "stop_reason": None,
            "candidate_reference": "unconfirmed", "ax": None, "images": {"before": None, "after": None},
            "events": [{"stage": stage, "status": "not_started", "start_ns": None, "end_ns": None,
                        "observation": None} for stage in STEPS],
            "crypto_engine": None, "timer": None,
            "worker": {"returncode": None, "signal_number": None, "signal_name": None,
                       "spawn_errno": None, "report_read_ok": None, "exit_confirmed": None,
                       "cleanup_error": None}}


def write_report(folder, report):
    atomic_write(Path(folder) / "report.json", json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False).encode())


def write_parent_result(folder, report):
    # 子が残った場合でも後書きされない、親だけが保存する終了結果。
    atomic_write(Path(folder) / "parent-result.json", json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False).encode())


def stop(report, reason):
    # 外部例外の文字列をそのままreportへ入れない。
    if reason not in ERRORS and not (isinstance(reason, str) and re.fullmatch(r"http_status_[1-5][0-9]{2}", reason)):
        reason = "internal_error"
    report.update(status="stopped", candidate_reference="unconfirmed", stop_reason=reason)
    for event in report["events"]:
        if event["status"] == "in_progress":
            event["status"] = "error"


def collect(client, report, folder, stop_ns, clock=time.monotonic_ns):
    """各境界で保存し、どの失敗からも後続RPCへ進まない。"""
    def begin(stage):
        report["stage"] = stage
        event = report["events"][STEPS.index(stage)]
        event.update(status="in_progress", start_ns=clock())
        write_report(folder, report)
        return event

    def complete(event):
        event.update(status="complete", end_ns=clock())
        write_report(folder, report)

    def rpc(stage, method, params=None):
        event = begin(stage)
        remaining = (stop_ns - clock()) / 1e9
        if remaining < .001:
            raise ProbeError("session_deadline")
        result = client.call(method, params, timeout=min(client.timeout, remaining)).result
        if not isinstance(result, dict):
            raise ProbeError("rpc_result_type")
        if method == "device_info":
            event["observation"] = safe_info(result)
            if stage == "initial_info":
                caps = result.get("capabilities")
                if not isinstance(caps, list) or CAPABILITY not in caps:
                    raise ProbeError("source_geometry_capability_missing")
            elif event["observation"]["foreground"] != "game" or event["observation"]["screen_locked"] is not False:
                raise ProbeError("foreground_not_verified")
        if method == "find_element":
            report["ax"] = sanitize_ax(result)
        if method == "screenshot":
            try:
                raw, image = inspect_payload(result)
                validate_source_geometry(result, image, CAPTURE_PARAMS)
            except ProbeError:
                raise ProbeError("source_geometry_invalid") from None
            result = (raw, {key: image[key] for key in IMAGE_FIELDS})
        complete(event)
        return result

    def save(name, captured):
        event = begin(name + "_save")
        raw, image = captured
        atomic_write(Path(folder) / (name + ".jpg"), raw)
        report["images"][name] = dict(image, raw_file=name + ".jpg")
        complete(event)

    try:
        rpc("initial_info", "device_info")
        rpc("launch", "launch_app", {"bundle_id": GAME})
        rpc("pre_info", "device_info")
        before = rpc("before_capture", "screenshot", dict(CAPTURE_PARAMS))
        rpc("before_info", "device_info")
        save("before", before)
        rpc("find", "find_element", dict(FIND_PARAMS))
        rpc("after_info", "device_info")
        after = rpc("after_capture", "screenshot", dict(CAPTURE_PARAMS))
        rpc("final_info", "device_info")
        save("after", after)
        report.update(status="completed", stage="complete", end_ns=clock())
        if candidate_evidence(report):
            report["candidate_reference"] = "candidate_reference_observed"
        write_report(folder, report)
    except ProbeError as exc:
        stop(report, exc.code)
    except KeyboardInterrupt:
        stop(report, "user_interrupt")
    except OSError:
        stop(report, "output_write_failed")
    except Exception:
        stop(report, "internal_error")
    if report["status"] == "stopped":
        report["end_ns"] = clock()
        try:
            write_report(folder, report)
        except OSError:
            stop(report, "output_write_failed")
    return report


def require(condition):
    if not condition:
        raise ValueError("report_read_failed")


def keys(value, expected):
    require(type(value) is dict and set(value) == set(expected))


def ns(value, optional=False):
    require((optional and value is None) or (type(value) is int and 0 <= value < 2 ** 64))


def validate_info(info):
    keys(info, ("foreground", "screen_locked", "advertised_known_capabilities", "execution_deadline_verified",
                "foreground_generation_verified", "input_cancel_verified"))
    require(info["foreground"] in ("game", "springboard", "other", "unknown"))
    require(info["screen_locked"] is None or type(info["screen_locked"]) is bool)
    allowed = ("run_steps", "wait_for", "screenshot_stream", CAPABILITY)
    caps = info["advertised_known_capabilities"]
    require(type(caps) is list and len(caps) <= len(allowed))
    require(all(type(value) is str and value in allowed for value in caps) and len(set(caps)) == len(caps))
    for key in ("execution_deadline_verified", "foreground_generation_verified", "input_cancel_verified"):
        require(info[key] is False)


def validate_ax(ax):
    keys(ax, ("label_exact", "ref_present", "exists", "hittable", "frame", "element_type", "visibility",
              "match_count", "alternatives_count", "ambiguity", "response_valid"))
    for key in ("label_exact", "ref_present", "response_valid"):
        require(type(ax[key]) is bool)
    for key in ("exists", "hittable"):
        require(ax[key] is None or type(ax[key]) is bool)
    if ax["frame"] is not None:
        keys(ax["frame"], ("x", "y", "width", "height"))
        for key, value in ax["frame"].items():
            require(finite(value, -4096 if key in ("x", "y") else 0, 4096))
            if key in ("width", "height"):
                require(value > 0)
    require(ax["element_type"] is None or (type(ax["element_type"]) is str and ax["element_type"] in TYPES))
    require(ax["visibility"] is None or ax["visibility"] in VISIBILITY)
    if ax["visibility"] in ("partial", "offscreen") and ax["hittable"] is True:
        require(ax["response_valid"] is False)
    for key, low, high in (("match_count", 1, 100000), ("alternatives_count", 0, 10000)):
        require(ax[key] is None or (type(ax[key]) is int and low <= ax[key] <= high))
    require(ax["ambiguity"] in ("not_reported", "reported", "invalid"))
    if ax["ambiguity"] == "not_reported":
        require(ax["match_count"] in (None, 1) and ax["alternatives_count"] in (None, 0))


def validate_image(image, name):
    keys(image, IMAGE_FIELDS + ("raw_file",))
    require(image["raw_file"] == name + ".jpg" and image["format"] == "JPEG")
    require(image["image_status"] in ("blank_or_dark", "decoded_nonblank"))
    for key, low, high in (("pixel_width", 1, 4096), ("pixel_height", 1, 4096), ("raw_bytes", 1, MAX_IMAGE),
                           ("max_luma", 0, 255), ("exif_orientation", 1, 1)):
        require(type(image[key]) is int and low <= image[key] <= high)
    require(finite(image["mean_luma"], 0, 255))
    require(image["mean_luma"] <= image["max_luma"])
    require(image["image_status"] == ("blank_or_dark" if image["max_luma"] <= 12 else "decoded_nonblank"))
    require(type(image["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", image["sha256"]) is not None)
    for key in ("input_authorized", "freshness_verified"):
        require(image[key] is False)
    for key in ("capture_time_ns", "source_sequence", "frame_age_ms"):
        require(image[key] is None)
    require(image["game_state"] == "not_classified" and image["geometry_applied"] == "none")
    require(image["metadata_issues"] == [])
    geometry = image["reported_geometry"]
    keys(geometry, GEOMETRY_FIELDS)
    # 既存の契約検査をそのまま使い、保存JSONの幾何矛盾も拒否する。
    payload = dict(geometry, format="jpeg")
    validate_source_geometry(payload, dict(image), CAPTURE_PARAMS)


def validate_report(report):
    template = new_report(0)
    keys(report, template)
    for key in ("version", "kind", "test_id", "device_acceptance"):
        require(report[key] == template[key])
    for key in ("input_authorized", "input_geometry_verified", "device_input_cancel_verified"):
        require(report[key] is False)
    ns(report["start_ns"])
    ns(report["end_ns"], True)
    require(report["status"] in ("running", "stopped", "completed"))
    require(report["stage"] in STAGES)
    reason = report["stop_reason"]
    require(reason is None or (type(reason) is str and (reason in ERRORS or re.fullmatch(r"http_status_[1-5][0-9]{2}", reason))))
    require((report["status"] == "stopped") == (reason is not None))
    require(report["candidate_reference"] in ("unconfirmed", "candidate_reference_observed"))
    require(report["crypto_engine"] in (None, "python", "native_i386"))
    keys(report["images"], ("before", "after"))
    for name, image in report["images"].items():
        if image is not None:
            validate_image(image, name)
    if report["ax"] is not None:
        validate_ax(report["ax"])
    events = report["events"]
    require(type(events) is list and len(events) == len(STEPS))
    unfinished = False
    for index, event in enumerate(events):
        keys(event, ("stage", "status", "start_ns", "end_ns", "observation"))
        require(event["stage"] == STEPS[index])
        require(event["status"] in ("not_started", "in_progress", "complete", "error"))
        ns(event["start_ns"], True)
        ns(event["end_ns"], True)
        if unfinished:
            require(event["status"] == "not_started")
        if event["status"] != "complete":
            unfinished = True
        if event["status"] == "not_started":
            require(event["start_ns"] is None and event["end_ns"] is None and event["observation"] is None)
        else:
            require(event["start_ns"] is not None)
        if event["status"] == "complete":
            require(event["end_ns"] is not None)
        if event["observation"] is not None:
            require(event["stage"] in INFO_STEPS)
            validate_info(event["observation"])
        if event["status"] == "complete" and event["stage"] in INFO_STEPS:
            require(event["observation"] is not None)
            if event["stage"] == "initial_info":
                require(CAPABILITY in event["observation"]["advertised_known_capabilities"])
            else:
                require(event["observation"]["foreground"] == "game" and event["observation"]["screen_locked"] is False)
    if report["status"] == "completed":
        require(not unfinished and report["stage"] == "complete" and report["end_ns"] is not None)
        require(all(report["images"].values()) and report["ax"] is not None)
    if report["candidate_reference"] == "candidate_reference_observed":
        require(report["status"] == "completed" and candidate_evidence(report))
    worker = report["worker"]
    keys(worker, template["worker"])
    for key, low, high in (("returncode", -255, 255), ("signal_number", 1, 255), ("spawn_errno", 0, 4096)):
        require(worker[key] is None or (type(worker[key]) is int and low <= worker[key] <= high))
    require(worker["signal_name"] is None or worker["signal_name"] in {value.name for value in signal.Signals} | {"UNKNOWN_SIGNAL"})
    require(worker["report_read_ok"] is None or type(worker["report_read_ok"]) is bool)
    require(worker["exit_confirmed"] is None or type(worker["exit_confirmed"]) is bool)
    require(worker["cleanup_error"] in (None, "worker_cleanup_failed"))
    if worker["exit_confirmed"] is not None:
        require(worker["exit_confirmed"] == (worker["returncode"] is not None))
    if worker["exit_confirmed"] is False or worker["cleanup_error"] is not None:
        require(report["status"] == "stopped" and report["candidate_reference"] == "unconfirmed")
    if report["timer"] is not None:
        timer = report["timer"]
        keys(timer, ("backend", "poisoned", "closed", "cleanup_error"))
        require(timer["backend"] == "owned_itimer_real" and type(timer["poisoned"]) is bool and type(timer["closed"]) is bool)
        require(timer["cleanup_error"] in (None, "timer_cleanup_failed"))


def read_checkpoint(path):
    """capture用schemaは使わず、未知キー・文字列・偽boolを階層ごとに拒否する。"""
    try:
        with Path(path).open("rb") as stream:
            raw = stream.read(MAX_REPORT + 1)
        report = json_object(raw, MAX_REPORT)
        validate_report(report)
        return report
    except (OSError, ValueError, TypeError, KeyError, RecursionError, ProbeError):
        raise ValueError("report_read_failed") from None


def parser():
    ap = argparse.ArgumentParser(description="TEST-011: 続行対象の参照を1回照会。ゲーム内入力は0回。")
    ap.add_argument("--output", default="runtime/test-011")
    ap.add_argument("--token-store", default=str(Path.home() / ".loopctrl/token.json"))
    ap.add_argument("--store-key", default=None)
    ap.add_argument("--python-crypto", action="store_true")
    ap.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--stop-ns", type=int, default=0, help=argparse.SUPPRESS)
    return ap


def worker(args):
    folder = Path(args.output)
    try:
        report = read_checkpoint(folder / "report.json")
    except ValueError:
        return WORKER_REPORT_READ_EXIT
    timer = None
    def stage(name):
        report["stage"] = name
        write_report(folder, report)
    try:
        stage("pairing_load")
        key, tok = load_pairing(args.token_store, args.store_key)
        stage("crypto_initialize")
        crypto = Crypto(native=not args.python_crypto)
        report["crypto_engine"] = crypto.engine
        stage("timer_initialize")
        timer = OwnedRpcTimer()
        with timer:
            client = InputPathClient(HttpTransport(), key, tok, timeout=8, crypto=crypto, deadline_owner=timer)
            collect(client, report, folder, args.stop_ns)
    except ProbeError as exc:
        stop(report, exc.code)
    except KeyboardInterrupt:
        stop(report, "user_interrupt")
    except OSError:
        stop(report, "output_write_failed")
    except Exception:
        stop(report, "internal_error")
    finally:
        if timer is not None:
            report["timer"] = timer.diagnostics()
    report["end_ns"] = time.monotonic_ns()
    try:
        write_report(folder, report)
    except OSError:
        return 2
    return 0


def run(args):
    if os.name != "posix" or not hasattr(signal, "setitimer"):
        raise ProbeError("posix_timer_required")
    if args.worker:
        return worker(args)
    base = Path(args.output).resolve()
    base.mkdir(parents=True, exist_ok=True)
    folder = base / ("input-path-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    folder.mkdir(mode=0o700)
    start = time.monotonic_ns()
    report = new_report(start)
    write_report(folder, report)
    command = [sys.executable, "-m", "necroprobe.input_path", "--worker", "--output", str(folder),
               "--token-store", args.token_store, "--stop-ns", str(start + SESSION_SECONDS * 1_000_000_000)]
    if args.store_key is not None:
        command.extend(["--store-key", args.store_key])
    if args.python_crypto:
        command.append("--python-crypto")
    diagnostics = {}
    print("TEST-011: ゲームを1回開き、続行対象を照会します。ゲーム内入力0回。", flush=True)
    reason = supervise(command, max(.001, SESSION_SECONDS - (time.monotonic_ns() - start) / 1e9), diagnostics)
    if reason == "worker_failed" and diagnostics.get("returncode") == WORKER_REPORT_READ_EXIT:
        reason = "worker_report_read_failed"
    try:
        report = read_checkpoint(folder / "report.json")
        report["worker"]["report_read_ok"] = True
    except ValueError:
        reason = reason or "report_read_failed"
        report["worker"]["report_read_ok"] = False
    for key in ("returncode", "signal_number", "signal_name", "spawn_errno", "exit_confirmed", "cleanup_error"):
        report["worker"][key] = diagnostics.get(key)
    if diagnostics.get("exit_confirmed") is False or diagnostics.get("cleanup_error") is not None:
        reason = "worker_cleanup_failed"
    if reason:
        stop(report, reason)
    elif report["status"] == "running":
        stop(report, "worker_failed")
    report["end_ns"] = time.monotonic_ns()
    # 終了未確認なら子のcheckpointへ上書きせず、親専用結果だけを確定する。
    write_parent_result(folder, report)
    if report["worker"]["exit_confirmed"] is not False:
        write_report(folder, report)
    print("続行対象の候補参照を確認" if report["candidate_reference"] == "candidate_reference_observed" else "候補参照は未確認", flush=True)
    print("ゲーム内入力0回 / 終了理由: " + (report["stop_reason"] or "completed"), flush=True)
    print("保存先: " + str(folder), flush=True)
    print("子終了コード: %s / シグナル: %s" % (report["worker"]["returncode"], report["worker"]["signal_name"]), flush=True)
    if report["worker"]["exit_confirmed"] is False:
        print("子プロセスの終了は未確認です。parent-result.json保存後にiSHを終了してください。", flush=True)
    print("最終結果: parent-result.json", flush=True)
    return 0 if report["status"] == "completed" else 2


def main(argv=None):
    global _cancel_requested
    args = parser().parse_args(argv)
    previous = {}
    if not args.worker:
        # Popenが子を返す前に例外を投げると子の所有権を失うため、フラグだけ変更する。
        _cancel_requested = False
        def interrupted(_signum, _frame):
            global _cancel_requested
            _cancel_requested = True
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.getsignal(signum)
            signal.signal(signum, interrupted)
    try:
        return run(args)
    except ProbeError as exc:
        print("TEST-011停止: " + (exc.code if exc.code in ERRORS else "internal_error"), file=sys.stderr)
        return 2
    except OSError:
        print("TEST-011: 結果を保存できませんでした。", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("TEST-011: 中断しました。", file=sys.stderr)
        return 130
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


if __name__ == "__main__":
    raise SystemExit(main())
