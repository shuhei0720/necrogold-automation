"""TEST-013の限定6群。合成応答の合格は実機の続行成功を表さない。"""
from copy import deepcopy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from necroprobe import resume_once as probe
from necroprobe.crypto import Crypto
from necroprobe.protocol import Client, GAME, RpcReply
from necroprobe.validation import ProbeError
from test_source_geometry import geometry_payload

GOOD = {"completed": 2, "failed_step": None, "not_sent": [], "steps": [
    {"i": 0, "method": "wait_for", "ok": True, "result": {"met": True, "foreground": GAME, "message": "PRIVATE"}},
    {"i": 1, "method": "tap", "ok": True, "result": {"message": "PRIVATE", "hit": {"label": "PRIVATE"}}}],
    "hint": "PRIVATE", "elapsed_ms": 1}
LABEL = {"matched": True, "pixel_diff": 0, "white_pixels": 253}
METHODS = ["device_info", "launch_app", "device_info", "screenshot", "device_info", "run_steps", "device_info", "screenshot", "device_info"]


class FakeClient:
    timeout = 8

    def __init__(self, *, batch=None, failure=None, info=None, image=None):
        self.batch, self.failure, self.info, self.image = deepcopy(GOOD if batch is None else batch), failure, info or {}, image
        self.calls, self.raws = [], []

    def call(self, method, params=None, timeout=None):
        self.calls.append((method, deepcopy(params)))
        i = len(self.calls)
        if self.failure == i:
            raise ProbeError("rpc_deadline")
        result = {}
        if method == "device_info":
            result = {"capabilities": list(probe.CAPABILITIES), "system": {"foreground_app": GAME, "screen_locked": False}, "private": "PRIVATE"}
            result.update(deepcopy(self.info.get(i, {})))
        elif method == "screenshot":
            raw, result = geometry_payload(params, size=(1792, 828))
            result["source_orientation"] = 2
            if self.image:
                self.image(result)
            self.raws.append(raw)
        elif method == "run_steps":
            result = deepcopy(self.batch)
        elif method != "launch_app":
            raise AssertionError("Unexpected method")
        now = time.monotonic_ns()
        return RpcReply(result, {"request_start_ns": now, "response_end_ns": now})


class ResumeOnceTests(unittest.TestCase):
    def run_probe(self, client, *, label=LABEL, clock=time.monotonic_ns):
        with tempfile.TemporaryDirectory() as folder:
            report = probe.new_report(time.monotonic_ns(), "a" * 32)
            with patch.object(probe, "label_evidence", return_value=deepcopy(label)):
                probe.collect(client, report, folder, time.monotonic_ns() + 45_000_000_000, clock=clock)
            saved = {p.name: p.read_bytes() for p in Path(folder).glob("*.jpg")}
            self.assertEqual(report, probe.read_checkpoint(Path(folder) / "report.json", expected_run_id="a" * 32, expected_start_ns=report["start_ns"]))
            return report, saved

    def test_01_normal_one_batch_and_original_bytes(self):
        client = FakeClient()
        report, saved = self.run_probe(client)
        self.assertEqual(METHODS, [m for m, _ in client.calls])
        self.assertEqual([probe.BATCH_PARAMS], [p for m, p in client.calls if m == "run_steps"])
        self.assertEqual(1, report["batch_attempts"])
        self.assertEqual("acknowledged", report["tap_outcome"])
        self.assertEqual("completed", report["status"])
        self.assertFalse(report["resume_verified"])
        self.assertFalse(report["input_geometry_verified"])
        self.assertEqual({"before.jpg": client.raws[0], "after.jpg": client.raws[1]}, saved)
        self.assertNotIn("PRIVATE", json.dumps(report))

    def test_02_preconditions_reject_without_batch(self):
        cases = [FakeClient(info={i: {"system": system}}) for i in (3, 5) for system in
                 ({}, {"foreground_app": "other", "screen_locked": False}, {"foreground_app": GAME, "screen_locked": True}, {"foreground_app": GAME, "screen_locked": 0})]
        cases += [FakeClient(info={1: {"capabilities": caps}}) for caps in ([], "run_steps", ["run_steps", "wait_for"], [True])]
        cases += [FakeClient(image=lambda p, k=k, v=v: p.update({k: v})) for k, v in
                  (("source_orientation", 3), ("point_width", 896), ("point_height", 414), ("source_scale", 2))]
        for client in cases:
            with self.subTest(calls=len(cases)):
                report, _ = self.run_probe(client)
                self.assertEqual(0, report["batch_attempts"])
                self.assertEqual("not_requested", report["tap_outcome"])
                self.assertNotIn("run_steps", [m for m, _ in client.calls])
        report, _ = self.run_probe(FakeClient(), label={"matched": False, "pixel_diff": 33, "white_pixels": 253})
        self.assertEqual(0, report["batch_attempts"])
        for delay in (1_100_000_000, 3_100_000_000):
            now = time.monotonic_ns()
            def late_clock():
                nonlocal now
                now += delay
                return now
            report, _ = self.run_probe(FakeClient(), clock=late_clock)
            self.assertEqual(0, report["batch_attempts"])

    def test_03_changed_batch_and_types_rejected(self):
        client = probe.ResumeOnceClient(None, crypto=Crypto(native=False))
        client._validate("run_steps", deepcopy(probe.BATCH_PARAMS))
        changes = []
        for key, value in (("x", 298), ("x", 297.0), ("y", True), ("fast", 1), ("settle", 0)):
            item = deepcopy(probe.BATCH_PARAMS); item["steps"][1]["params"][key] = value; changes.append(item)
        for key, value in (("foreground", "other"), ("timeout", 1), ("timeout", True)):
            item = deepcopy(probe.BATCH_PARAMS); item["steps"][0]["params"][key] = value; changes.append(item)
        changes += [dict(deepcopy(probe.BATCH_PARAMS), observe="visible"), {}, [], None]
        item = deepcopy(probe.BATCH_PARAMS); item["steps"].reverse(); changes.append(item)
        for item in changes:
            with self.subTest(params=item), self.assertRaises(ProbeError):
                client._validate("run_steps", item)
        for method in ("tap", "find_element", "page_source", "reset"):
            with self.assertRaises(ProbeError):
                client._validate(method, {})

    def test_04_failed_send_consumes_permission_and_never_retries(self):
        for method, params in (("run_steps", probe.BATCH_PARAMS), ("launch_app", {"bundle_id": GAME})):
            client = probe.ResumeOnceClient(None, crypto=Crypto(native=False))
            with patch.object(Client, "call", side_effect=ProbeError("rpc_deadline")) as send:
                for _ in range(2):
                    with self.assertRaises(ProbeError):
                        client.call(method, deepcopy(params))
            self.assertEqual(1, send.call_count)
        client = FakeClient(failure=6)
        report, _ = self.run_probe(client)
        self.assertEqual(1, report["batch_attempts"])
        self.assertEqual("unknown", report["tap_outcome"])
        self.assertEqual(1, [m for m, _ in client.calls].count("run_steps"))

    def test_05_nested_batch_reply_and_privacy(self):
        wait_error = {"i": 0, "method": "wait_for", "ok": False, "error": {"code": -32000, "message": "PRIVATE"}}
        rejected = {"completed": 0, "failed_step": 0, "not_sent": [1], "steps": [wait_error], "hint": "PRIVATE"}
        report, _ = self.run_probe(FakeClient(batch=rejected))
        self.assertEqual("not_sent", report["tap_outcome"])
        self.assertNotIn("PRIVATE", json.dumps(report))
        failed = deepcopy(GOOD); failed.update(completed=1, failed_step=1)
        failed["steps"][1] = {"i": 1, "method": "tap", "ok": False, "error": {"code": -32000, "message": "PRIVATE"}}
        malformed = [failed, {}, dict(GOOD, completed=True), dict(GOOD, failed_step=False), dict(GOOD, not_sent=[True])]
        wrong_wait = deepcopy(GOOD); wrong_wait["steps"][0]["result"]["met"] = False; malformed.append(wrong_wait)
        bad_ok = deepcopy(GOOD); bad_ok["steps"][1]["ok"] = 1; malformed.append(bad_ok)
        for reply in malformed:
            with self.subTest(reply=reply):
                report, _ = self.run_probe(FakeClient(batch=reply))
                self.assertEqual("unknown", report["tap_outcome"])
                self.assertNotIn("PRIVATE", json.dumps(report))
        report, _ = self.run_probe(FakeClient())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "report.json"
            alterations = [dict(report, run_id="b" * 32), dict(report, unknown="PRIVATE"), dict(report, batch_attempts=False)]
            for route in (("images", "before"), ("events", 0), ("batch_result",), ("worker",), ("label",)):
                changed = deepcopy(report); target = changed
                for key in route: target = target[key]
                target["private"] = "PRIVATE"; alterations.append(changed)
            for changed in alterations:
                path.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):
                    probe.read_checkpoint(path, expected_run_id="a" * 32, expected_start_ns=report["start_ns"])
            for raw in (b"{", b'{"x":1,"x":2}', b'{"x":NaN}', b" " * (probe.MAX_REPORT + 1)):
                path.write_bytes(raw)
                with self.assertRaises(ValueError): probe.read_checkpoint(path)

    def test_06_after_failure_and_parent_read_failure_preserve_uncertainty(self):
        for index in (7, 8, 9):
            report, _ = self.run_probe(FakeClient(failure=index))
            self.assertEqual(1, report["batch_attempts"])
            self.assertEqual("acknowledged", report["tap_outcome"])
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            def corrupt(command, timeout, diagnostics):
                output = Path(command[command.index("--output") + 1])
                (output / "report.json").write_text('{"private":"PRIVATE"}')
                diagnostics.update(returncode=0, signal_number=None, signal_name=None, exit_confirmed=True, cleanup_error=None)
                return None
            with patch.object(probe.supervisor, "supervise", side_effect=corrupt):
                self.assertEqual(2, probe.run(probe.parser().parse_args(["--output", folder])))
            report = probe.read_checkpoint(next(Path(folder).glob("resume-once-*/parent-result.json")))
            self.assertIsNone(report["batch_attempts"])
            self.assertEqual("unknown", report["tap_outcome"])
            self.assertNotIn("PRIVATE", json.dumps(report))
        for already_sent in (False, True):
            with self.subTest(already_sent=already_sent), tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
                def unfinished(command, timeout, diagnostics):
                    output = Path(command[command.index("--output") + 1])
                    if already_sent:
                        checkpoint = probe.read_checkpoint(output / "report.json")
                        with patch.object(probe, "label_evidence", return_value=deepcopy(LABEL)):
                            probe.collect(FakeClient(), checkpoint, output, time.monotonic_ns() + 45_000_000_000)
                    diagnostics.update(returncode=None, signal_number=None, signal_name=None,
                                       exit_confirmed=False, cleanup_error="worker_cleanup_failed")
                    return "worker_cleanup_failed"
                with patch.object(probe.supervisor, "supervise", side_effect=unfinished):
                    self.assertEqual(2, probe.run(probe.parser().parse_args(["--output", folder])))
                report = probe.read_checkpoint(next(Path(folder).glob("resume-once-*/parent-result.json")))
                self.assertEqual(1 if already_sent else None, report["batch_attempts"])
                self.assertEqual("acknowledged" if already_sent else "unknown", report["tap_outcome"])
                self.assertFalse(report["worker"]["exit_confirmed"])
