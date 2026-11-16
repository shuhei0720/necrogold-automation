import asyncio
import builtins
import contextlib
import hashlib
import io
import json
import logging
import os
import sys
import time
from pathlib import Path
from types import ModuleType, SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from necroprobe import device_lab as lab


TARGET = "PRIVATE_TARGET_UDID"
OTHER = "PRIVATE_OTHER_UDID"
SECRET = "PRIVATE_PAIRING_SENTINEL_DO_NOT_PUBLISH"


def picture(size=(750, 1334)):
    with io.BytesIO() as stream:
        Image.new("RGB", size, (30, 70, 120)).save(stream, "PNG")
        return stream.getvalue()


def device(udid=TARGET, transport="USB", device_id=1):
    return {"udid": udid, "transport": transport, "device_id": device_id}


class FakeBackend:
    def __init__(self, devices=None):
        self.devices = [device()] if devices is None else devices
        self.list_sequence = None
        self.connections = []
        self.calls = []
        self.closed = 0
        self.active = 0
        self.actual_udid = TARGET
        self.paired = True
        self.dev_mode = True
        self.mounted = True
        self.installed = {name: True for name in lab.APP_IDS}
        self.response = None
        self.wait_capture = False
        self.capture_started = asyncio.Event()
        self.close_error = False

    async def host_version(self):
        return lab.PMD_VERSION

    async def list_devices(self):
        self.calls.append("list_devices")
        if self.list_sequence is not None:
            if len(self.list_sequence) > 1:
                return self.list_sequence.pop(0)
            return self.list_sequence[0]
        return self.devices

    async def connect(self, selected, config):
        self.connections.append(selected)
        self.calls.append("connect")
        self.active += 1
        return object()

    async def info(self, session):
        self.calls.append("info")
        return {"udid": self.actual_udid, "paired": self.paired, "untrusted": SECRET}

    async def developer_mode(self, session):
        self.calls.append("developer_mode")
        return self.dev_mode

    async def ddi(self, session):
        self.calls.append("ddi")
        return self.mounted

    async def apps(self, session):
        self.calls.append("apps")
        return self.installed

    async def screenshot(self, session):
        self.calls.append("screenshot")
        self.capture_started.set()
        if self.wait_capture:
            await asyncio.Event().wait()
        return self.response if self.response is not None else {"data": picture(), "metadata": {}}

    async def close(self, session):
        self.closed += 1
        if self.close_error:
            raise RuntimeError(SECRET)
        self.active -= 1


class DeviceSelectionTests(unittest.TestCase):
    def test_unqualified_device_never_connects(self):
        cases = [[], [device(OTHER)], [device(transport="Network")],
                 [device(), device(device_id=2)]]
        for devices in cases:
            with self.subTest(devices=devices), tempfile.TemporaryDirectory() as folder:
                backend = FakeBackend(devices)
                result = asyncio.run(lab.run_lab({"expected_udid": TARGET, "transport": "USB",
                                        "private_dir": folder}, backend=backend))
                self.assertEqual([], backend.connections,
                                 "Absent/wrong/ambiguous transport must stop before connecting")
                self.assertEqual("pass", result["stages"]["host"]["status"])
                self.assertEqual("blocked", result["stages"]["transport"]["status"])

    def test_exact_target_among_other_phones_and_explicit_network(self):
        with tempfile.TemporaryDirectory() as folder:
            backend = FakeBackend([device(OTHER), device(transport="Network")])
            result = asyncio.run(lab.run_lab({"expected_udid": TARGET, "transport": "Network",
                "private_dir": folder}, backend=backend))
            self.assertEqual([device(transport="Network")], backend.connections)
            self.assertEqual("pass", result["stages"]["lockdown"]["status"])
            self.assertEqual(1, backend.closed)
            self.assertEqual(0, backend.active)
            self.assertNotIn("screenshot", backend.calls)


class DeviceLabTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.config = {"expected_udid": TARGET, "transport": "USB", "private_dir": str(self.root)}

    async def test_missing_transport_invalid_config_and_git_paths_never_connect(self):
        for config in ({"expected_udid": TARGET, "private_dir": str(self.root)},
                       dict(self.config, transport="Any"), dict(self.config, expected_udid="")):
            backend = FakeBackend()
            result = await lab.run_lab(config, backend=backend)
            self.assertEqual([], backend.connections)
            self.assertEqual("config_invalid", result["stages"]["host"]["reason"])
        (self.root / ".git").mkdir()
        (self.root / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
        backend = FakeBackend()
        result = await lab.run_lab(self.config, backend=backend)
        self.assertEqual([], backend.connections)
        self.assertEqual("private_directory_invalid", result["stages"]["host"]["reason"])

    async def test_other_users_readable_directory_is_rejected(self):
        if os.name == "nt":
            # Exercise the ACL reader's reject result without editing host ACLs.
            with patch.object(lab.subprocess, "run", return_value=SimpleNamespace(returncode=4)):
                backend = FakeBackend()
                result = await lab.run_lab(self.config, backend=backend)
        else:
            os.chmod(self.root, 0o755)
            backend = FakeBackend()
            result = await lab.run_lab(self.config, backend=backend)
        self.assertEqual([], backend.connections)
        self.assertEqual("private_directory_invalid", result["stages"]["host"]["reason"])

    async def test_malformed_device_list_does_not_connect(self):
        for row in (device(device_id=True), device(transport="Unknown"), {"udid": TARGET}):
            backend = FakeBackend([row])
            result = await lab.run_lab(self.config, backend=backend)
            self.assertEqual([], backend.connections)
            self.assertEqual("device_list_invalid", result["stages"]["transport"]["reason"])

    async def test_connected_identity_must_match_and_pairing_is_never_created(self):
        for actual, paired, reason in ((OTHER, True, "target_changed"), (TARGET, False, "pairing_required")):
            backend = FakeBackend()
            backend.actual_udid, backend.paired = actual, paired
            result = await lab.run_lab(self.config, "capture", backend=backend)
            self.assertEqual(reason, result["stages"]["lockdown"]["reason"])
            self.assertEqual(["list_devices", "connect", "info"], backend.calls)
            self.assertEqual(1, backend.closed)

    async def test_identity_is_rechecked_immediately_before_and_after_capture(self):
        for sequence, expected_captures in (([[device()], [device(OTHER)]], 0),
            ([[device()], [device()], []], 1),
            ([[device()], [device(device_id=2)]], 0)):
            backend = FakeBackend()
            backend.list_sequence = sequence
            result = await lab.run_lab(self.config, "capture", backend=backend)
            self.assertEqual(expected_captures, backend.calls.count("screenshot"))
            self.assertNotEqual("pass", result["operation_status"])
            self.assertEqual(1, backend.closed)
            self.assertEqual([], list(self.root.iterdir()))

    async def test_capture_preserves_bytes_and_never_grants_geometry_or_input(self):
        backend = FakeBackend()
        raw = picture()
        backend.response = {"data": raw, "metadata": {"pixel_width": 750, "pixel_height": 1334}}
        result = await lab.run_lab(self.config, "capture", backend=backend)
        self.assertEqual("pass", result["operation_status"])
        self.assertEqual("pass", result["stages"]["capture"]["status"])
        self.assertEqual("blocked", result["stages"]["geometry"]["status"])
        self.assertFalse(result["input_authorized"])
        self.assertFalse(result["automation_ready"])
        self.assertFalse(result["freshness_verified"])
        self.assertEqual((750, 1334), (result["image"]["pixel_width"], result["image"]["pixel_height"]))
        saved = self.root / result["run_id"]
        self.assertEqual(raw, (saved / "capture.bin").read_bytes())
        manifest = json.loads((saved / "manifest.json").read_text())
        self.assertEqual(hashlib.sha256(raw).hexdigest(), manifest["artifact"]["sha256"])
        self.assertEqual(TARGET, manifest["target_udid"])
        self.assertIsNone(manifest["artifact"]["device_capture_time_ns"])
        self.assertNotIn(TARGET, json.dumps(result))
        self.assertNotIn(str(self.root), json.dumps(result))
        self.assertEqual(1, backend.closed)
        self.assertEqual(0, backend.active)

    async def test_unknown_devmode_ddi_and_absent_app_are_separate_blockers(self):
        backend = FakeBackend()
        backend.dev_mode, backend.mounted = None, False
        backend.installed["loopctrl"] = False
        result = await lab.run_lab(self.config, "capture", backend=backend)
        self.assertEqual("developer_mode_unknown", result["stages"]["developer_mode"]["reason"])
        self.assertEqual("ddi_missing", result["stages"]["ddi"]["reason"])
        self.assertEqual("app_missing", result["stages"]["apps"]["reason"])
        self.assertEqual("not_run", result["stages"]["server"]["status"])
        self.assertNotIn("screenshot", backend.calls)

    async def test_capture_reports_the_failed_prerequisite_instead_of_assuming_ddi_missing(self):
        cases = ((False, True, None, "developer_mode_disabled"),
                 (None, True, None, "developer_mode_unknown"),
                 (True, True, "developer_mode", "backend_error"),
                 (True, False, None, "ddi_missing"),
                 (True, True, "ddi", "backend_error"),
                 (None, False, None, "developer_mode_unknown"))
        for dev_mode, mounted, failing, reason in cases:
            with self.subTest(dev_mode=dev_mode, mounted=mounted, failing=failing), contextlib.ExitStack() as stack:
                backend = FakeBackend()
                backend.dev_mode, backend.mounted = dev_mode, mounted
                if failing is not None:
                    stack.enter_context(patch.object(backend, failing, side_effect=RuntimeError(SECRET)))
                result = await lab.run_lab(self.config, "capture", backend=backend)
                self.assertEqual({"status": "blocked", "reason": reason}, result["stages"]["capture"])
                self.assertEqual("blocked", result["operation_status"])
                self.assertNotIn("screenshot", backend.calls)
                self.assertEqual([], list(self.root.iterdir()))
                self.assertEqual((1, 0), (backend.closed, backend.active))
                self.assertFalse(result["input_authorized"])
                self.assertNotIn(SECRET, json.dumps(result))

    async def test_bad_image_metadata_and_bytes_never_pass(self):
        cases = ({"data": b"invalid", "metadata": {}},
                 {"data": picture(), "metadata": {"pixel_width": 1334}},
                 {"data": picture(), "metadata": {"pixel_width": True}},
                 {"data": b"x" * (lab.MAX_IMAGE + 1), "metadata": {}},
                 {"data": picture(), "metadata": {SECRET: SECRET}})
        for response in cases:
            with self.subTest(case=len(response["data"])):
                backend = FakeBackend()
                backend.response = response
                result = await lab.run_lab(self.config, "capture", backend=backend)
                self.assertEqual("fail", result["stages"]["capture"]["status"])
                self.assertNotEqual("pass", result["operation_status"])
                self.assertFalse(result["input_authorized"])
                self.assertNotIn(SECRET, json.dumps(result))
                if "run_id" in result:
                    self.assertEqual(response["data"], (self.root / result["run_id"] / "capture.bin").read_bytes())

    async def test_existing_run_is_never_modified_even_when_uuid_collides(self):
        run_id = "a" * 32
        original = self.root / run_id
        original.mkdir(mode=0o700)
        (original / "capture.bin").write_bytes(b"ORIGINAL")
        with patch.object(lab.uuid, "uuid4", return_value=SimpleNamespace(hex=run_id)):
            result = await lab.run_lab(self.config, "capture", backend=FakeBackend())
        self.assertEqual("artifact_conflict", result["stages"]["capture"]["reason"])
        self.assertEqual(b"ORIGINAL", (original / "capture.bin").read_bytes())
        self.assertEqual(["capture.bin"], [x.name for x in original.iterdir()])

    async def test_timeout_closes_the_owned_session(self):
        backend = FakeBackend()
        backend.wait_capture = True
        result = await lab.run_lab(self.config, "capture", backend=backend, timeout=.02)
        self.assertEqual("deadline", result["stages"]["capture"]["reason"])
        self.assertEqual((1, 0), (backend.closed, backend.active))

    async def test_sync_decode_past_deadline_cannot_report_capture_success(self):
        backend = FakeBackend()
        backend.response = {"data": picture(), "metadata": {}}
        inspect = lab.inspect_bytes
        def slow_inspect(raw):
            time.sleep(.04)
            return inspect(raw)
        with patch.object(lab, "inspect_bytes", side_effect=slow_inspect):
            result = await lab.run_lab(self.config, "capture", backend=backend, timeout=.02)
        self.assertEqual("blocked", result["stages"]["capture"]["status"])
        self.assertEqual("deadline", result["stages"]["capture"]["reason"])
        self.assertEqual((1, 0), (backend.closed, backend.active))

    async def test_cancellation_closes_the_owned_session(self):
        backend = FakeBackend()
        backend.wait_capture = True
        task = asyncio.create_task(lab.run_lab(self.config, "capture", backend=backend))
        await asyncio.wait_for(backend.capture_started.wait(), timeout=1)
        task.cancel()
        result = await task
        self.assertEqual("cancelled", result["stages"]["capture"]["reason"])
        self.assertEqual((1, 0), (backend.closed, backend.active))

    async def test_cleanup_failure_cannot_be_a_success_and_never_leaks_exception(self):
        backend = FakeBackend()
        backend.close_error = True
        result = await lab.run_lab(self.config, "capture", backend=backend)
        self.assertEqual("fail", result["operation_status"])
        self.assertEqual("cleanup_failed", result["stages"]["cleanup"]["reason"])
        self.assertNotIn(SECRET, json.dumps(result))


class DeviceLabCliTests(unittest.TestCase):
    def test_windows_python314_owner_rights_acl_is_private_only_for_trusted_owner(self):
        # CPython v3.14.2 mkdir(0o700): SY/BA/OW full, protected DACL.
        user = "S-1-5-21-1-2-3-1001"
        state = {"owner": user, "user": user, "protected": True,
                 "allowed": ["S-1-5-18", "S-1-5-32-544", "S-1-3-4"]}
        self.assertTrue(lab._windows_acl_ok(state))
        for changed in (dict(state, owner="S-1-3-4"), dict(state, owner="S-1-1-0"),
                        dict(state, allowed=state["allowed"] + ["S-1-1-0"]),
                        dict(state, protected=False), dict(state, allowed=[])):
            self.assertFalse(lab._windows_acl_ok(changed))
        with patch.object(lab.subprocess, "run", return_value=SimpleNamespace(
                returncode=0, stdout=json.dumps(state).encode())):
            lab._windows_private_directory(Path("/synthetic-private"))

    def test_missing_host_dependency_is_not_reported_as_bad_private_config(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "private.json"
            path.write_text(json.dumps({"expected_udid": TARGET, "transport": "USB", "private_dir": folder}))
            original_import = builtins.__import__
            def importing(name, *args, **kwargs):
                if name == "pymobiledevice3.utils":
                    raise ModuleNotFoundError(SECRET)
                return original_import(name, *args, **kwargs)
            with patch.object(builtins, "__import__", side_effect=importing), contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(2, lab.main(["check", "--config", str(path)]))
                result = json.loads(out.getvalue())
                self.assertEqual("host_unavailable", result["stages"]["host"]["reason"])
                self.assertNotIn(SECRET, out.getvalue())

    def test_config_loader_rejects_duplicate_keys_oversize_and_git_config(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "private.json"
            for raw in (b'{"expected_udid":"a","expected_udid":"b"}', b"x" * 16385):
                path.write_bytes(raw)
                with self.assertRaises(lab.LabError):
                    lab.load_config(path)
            (root / ".git").mkdir()
            (root / ".git" / "HEAD").write_text("ref: refs/heads/main\n")
            path.write_text("{}")
            with self.assertRaises(lab.LabError):
                lab.load_config(path)

    def test_unknown_actions_flags_and_private_paths_are_not_echoed(self):
        for args in ([SECRET, "--config", SECRET], ["capture", "--config", SECRET, "--tap", SECRET],
                     ["check", "--config", "/missing/" + SECRET]):
            with self.subTest(args=args), contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
                self.assertEqual(2, lab.main(args, runner=asyncio.run))
                result = json.loads(out.getvalue())
                self.assertFalse(result["input_authorized"])
                self.assertNotIn(SECRET, out.getvalue() + err.getvalue())

    def test_public_summary_reconstructs_whitelist_and_cli_discards_backend_output(self):
        raw = {"operation_status": "pass", "input_authorized": True, "automation_ready": True,
               "udid": SECRET, "pair_record": SECRET,
               "stages": {"host": {"status": "pass", "reason": SECRET, "details": SECRET}}}
        safe = lab.public_summary(raw)
        self.assertNotIn(SECRET, json.dumps(safe))
        self.assertFalse(safe["input_authorized"])
        self.assertFalse(safe["automation_ready"])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "private.json"
            path.write_text(json.dumps({"expected_udid": TARGET, "transport": "USB", "private_dir": folder}))
            backend = FakeBackend()
            async def noisy():
                print(SECRET)
                logging.error(SECRET)
                raise RuntimeError(SECRET)
            backend.host_version = noisy
            handlers = tuple(logging.root.handlers)
            with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as err:
                self.assertEqual(2, lab.main(["check", "--config", str(path)], backend=backend, runner=asyncio.run))
                self.assertNotIn(SECRET, out.getvalue() + err.getvalue())
                self.assertEqual("fail", json.loads(out.getvalue())["stages"]["host"]["status"])
            self.assertEqual(handlers, tuple(logging.root.handlers))


class PmdAdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_signed_loopctrl_presence_is_not_identity_or_input_authority(self):
        rows = [{"CFBundleIdentifier": "top.ebato.loopctrlevil.PRIVATE_SUFFIX"}]
        class Service:
            def __init__(self, session):
                pass
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            async def browse(self, **kwargs):
                return rows
        parent = ModuleType("pymobiledevice3")
        parent.__path__ = []
        services = ModuleType("pymobiledevice3.services")
        services.__path__ = []
        module = ModuleType("pymobiledevice3.services.installation_proxy")
        module.InstallationProxyService = Service
        with patch.dict(sys.modules, {"pymobiledevice3": parent, "pymobiledevice3.services": services,
                "pymobiledevice3.services.installation_proxy": module}):
            self.assertFalse((await lab.PmdBackend().apps("selected-session"))["loopctrl"])
            rows.append({"CFBundleIdentifier": "top.ebato.loopctrl.PRIVATE_SIGNING_SUFFIX"})
            presence = await lab.PmdBackend().apps("selected-session")
        self.assertTrue(presence["loopctrl"])
        summary = lab.public_summary({"apps": presence, "input_authorized": True, "automation_ready": True})
        self.assertFalse(summary["input_authorized"])
        self.assertFalse(summary["automation_ready"])
        self.assertEqual("not_run", summary["stages"]["server"]["status"])

    async def test_app_presence_uses_observed_ish_id_and_signed_sidestore_prefix(self):
        calls = []
        class Service:
            def __init__(self, session):
                pass
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                pass
            async def browse(self, **kwargs):
                calls.append(kwargs)
                return [{"CFBundleIdentifier": "app.ish.iSH"},
                    {"CFBundleIdentifier": "com.SideStore.SideStore.PRIVATE_SIGNING_SUFFIX"},
                    {"CFBundleIdentifier": "jp.co.spike-chunsoft.necrodancerjp"}]
        parent = ModuleType("pymobiledevice3")
        parent.__path__ = []
        services = ModuleType("pymobiledevice3.services")
        services.__path__ = []
        module = ModuleType("pymobiledevice3.services.installation_proxy")
        module.InstallationProxyService = Service
        with patch.dict(sys.modules, {"pymobiledevice3": parent, "pymobiledevice3.services": services,
                "pymobiledevice3.services.installation_proxy": module}):
            result = await lab.PmdBackend().apps("selected-session")
        self.assertTrue(result["ish"])
        self.assertTrue(result["sidestore"])
        self.assertTrue(result["game"])
        self.assertFalse(result["loopctrl"])
        self.assertEqual([{"options": {"ApplicationType": "User"}, "attributes": ["CFBundleIdentifier"]}], calls)

    async def test_pinned_create_arguments_cannot_autopair_or_choose_first_phone(self):
        calls = []
        async def create(**kwargs):
            calls.append(kwargs)
            return "test-session"
        parent = ModuleType("pymobiledevice3")
        parent.__path__ = []
        module = ModuleType("pymobiledevice3.lockdown")
        module.create_using_usbmux = create
        config = {"private_dir": Path("/synthetic-private"), "expected_udid": TARGET, "transport": "USB"}
        with patch.dict(sys.modules, {"pymobiledevice3": parent, "pymobiledevice3.lockdown": module}):
            result = await lab.PmdBackend().connect(device(), config)
        self.assertEqual("test-session", result)
        self.assertEqual([{"serial": TARGET, "connection_type": "USB", "autopair": False,
            "pairing_records_cache_folder": config["private_dir"] / "pairing"}], calls)

    async def test_screenshot_owns_and_closes_its_service_without_other_actions(self):
        events = []
        raw = picture((30, 40))
        class Service:
            def __init__(self, session):
                events.append(("create", session))
            async def __aenter__(self):
                events.append("enter")
                return self
            async def __aexit__(self, *args):
                events.append("close")
            async def take_screenshot(self):
                events.append("take_screenshot")
                return raw
        parent = ModuleType("pymobiledevice3")
        parent.__path__ = []
        services = ModuleType("pymobiledevice3.services")
        services.__path__ = []
        module = ModuleType("pymobiledevice3.services.screenshot")
        module.ScreenshotService = Service
        with patch.dict(sys.modules, {"pymobiledevice3": parent, "pymobiledevice3.services": services,
                "pymobiledevice3.services.screenshot": module}):
            result = await lab.PmdBackend().screenshot("selected-session")
        self.assertEqual({"data": raw, "metadata": {}}, result)
        self.assertEqual([("create", "selected-session"), "enter", "take_screenshot", "close"], events)


if __name__ == "__main__":
    unittest.main()
