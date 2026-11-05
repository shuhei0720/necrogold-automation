"""TEST-011の読み取り専用契約・停止・再読込の挙動試験。実機受入ではない。"""
from copy import deepcopy
import base64
import contextlib
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from necroprobe import input_path as probe
from necroprobe.crypto import Crypto
from necroprobe.protocol import Client, GAME, RpcReply
from necroprobe.validation import ProbeError
from input_path_support import AX, CAPABILITY, FakeClient, METHODS
from timer_support import TimerTestCase
from test_protocol import KEY, TOK, sealed_reply
from test_capture import picture

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "tests/fixtures/input_path_driver.py"


class InputClientTests(unittest.TestCase):
    def client(self):
        return probe.InputPathClient(None, crypto=Crypto(native=False))

    def test_only_exact_fixed_params_are_allowed(self):
        for method, params in (("device_info", {}), ("launch_app", {"bundle_id": GAME}),
                               ("screenshot", probe.CAPTURE_PARAMS), ("find_element", probe.FIND_PARAMS)):
            self.client()._validate(method, dict(params))
            for key in params:
                altered = dict(params)
                altered.pop(key)
                with self.subTest(method=method, key=key), self.assertRaises(ProbeError):
                    self.client()._validate(method, altered)
            for changed in (dict(params, unknown=True), [], None):
                with self.subTest(method=method, changed=changed), self.assertRaises(ProbeError):
                    self.client()._validate(method, changed)

    def test_other_bundles_matches_labels_scales_and_input_methods_are_refused(self):
        cases = [("find_element", dict(probe.FIND_PARAMS, **change)) for change in
                 ({"bundle_id": "com.apple.springboard"}, {"element_id": "続行"}, {"match": "contains"})]
        cases += [("screenshot", dict(probe.CAPTURE_PARAMS, **change)) for change in
                  ({"format": "png"}, {"scale": 2}, {"scale": True}, {"quality": 1}, {"geometry": "legacy"})]
        cases += [(name, {}) for name in ("tap", "tap_element", "scroll", "scroll_to_element", "run_steps",
                                         "rotate", "config", "page_source", "type_text")]
        cases += [("launch_app", {"bundle_id": "other"}), ("device_info", {"verbose": True})]
        for method, params in cases:
            with self.subTest(method=method, params=params), self.assertRaises(ProbeError):
                self.client()._validate(method, params)

    def test_find_allowance_is_consumed_before_sending_even_when_send_fails(self):
        client = self.client()
        with patch.object(Client, "call", side_effect=ProbeError("rpc_error")) as send:
            with self.assertRaises(ProbeError):
                client.call("find_element", dict(probe.FIND_PARAMS))
            with self.assertRaises(ProbeError):
                client.call("find_element", dict(probe.FIND_PARAMS))
        self.assertEqual(1, send.call_count)

    def test_launch_allowance_is_also_consumed_before_failed_send(self):
        client = self.client()
        with patch.object(Client, "call", side_effect=ProbeError("rpc_error")) as send:
            for _ in range(2):
                with self.assertRaises(ProbeError):
                    client.call("launch_app", {"bundle_id": GAME})
        self.assertEqual(1, send.call_count)


class InputCollectionTests(unittest.TestCase):
    def run_probe(self, client):
        with tempfile.TemporaryDirectory() as folder:
            report = probe.new_report(time.monotonic_ns())
            probe.collect(client, report, folder, time.monotonic_ns() + 10_000_000_000)
            saved = {p.name: p.read_bytes() for p in Path(folder).iterdir() if p.suffix == ".jpg"}
            self.assertEqual(report, probe.read_checkpoint(Path(folder) / "report.json"))
            return report, saved

    def test_success_uses_fixed_sequence_and_preserves_original_bytes(self):
        client = FakeClient()
        report, saved = self.run_probe(client)
        self.assertEqual(METHODS, [method for method, _ in client.calls])
        self.assertEqual([probe.FIND_PARAMS], [params for method, params in client.calls if method == "find_element"])
        self.assertEqual([probe.CAPTURE_PARAMS] * 2, [params for method, params in client.calls if method == "screenshot"])
        self.assertEqual("completed", report["status"])
        self.assertEqual("candidate_reference_observed", report["candidate_reference"])
        self.assertIs(False, report["input_authorized"])
        self.assertEqual("not_tested", report["device_acceptance"])
        self.assertEqual({"before.jpg": client.raws[0], "after.jpg": client.raws[1]}, saved)
        self.assertNotIn("PRIVATE", json.dumps(report))
        self.assertNotIn("el_123", json.dumps(report))

    def test_capability_is_exact_member_of_list(self):
        for caps in ([], CAPABILITY, {CAPABILITY: True}, [CAPABILITY + "0"], [[CAPABILITY]], [True]):
            with self.subTest(caps=caps):
                client = FakeClient(caps=caps)
                report, saved = self.run_probe(client)
                self.assertEqual(METHODS[:1], [method for method, _ in client.calls])
                self.assertEqual("source_geometry_capability_missing", report["stop_reason"])
                self.assertEqual({}, saved)

    def test_foreground_or_lock_failure_stops_before_any_later_rpc_or_image_save(self):
        for index in (3, 5, 7, 9):
            for system in ({}, {"foreground_app": "other", "screen_locked": False},
                           {"foreground_app": GAME}, {"foreground_app": GAME, "screen_locked": True},
                           {"foreground_app": GAME, "screen_locked": 0}):
                with self.subTest(index=index, system=system):
                    client = FakeClient(info_changes={index: {"system": system}})
                    report, saved = self.run_probe(client)
                    self.assertEqual(index, len(client.calls))
                    self.assertEqual("foreground_not_verified", report["stop_reason"])
                    self.assertEqual("unconfirmed", report["candidate_reference"])
                    self.assertEqual({"before.jpg"} if index >= 7 else set(), set(saved))

    def test_each_rpc_failure_is_terminal_without_retry_or_followup(self):
        for index in range(1, 10):
            with self.subTest(index=index):
                client = FakeClient(failure=index)
                report, _ = self.run_probe(client)
                self.assertEqual(index, len(client.calls))
                self.assertEqual("rpc_error", report["stop_reason"])
                self.assertEqual("unconfirmed", report["candidate_reference"])

    def test_invalid_image_contract_is_terminal_and_does_not_save_that_image(self):
        for image_index in (1, 2):
            for change in ({"geometry": "legacy"}, {"scale": 2}, {"pixel_width": 41}, {"data": "bad"}):
                with self.subTest(image_index=image_index, change=change):
                    client = FakeClient(image_change=lambda data, n: data.update(change) if n == image_index else None)
                    report, saved = self.run_probe(client)
                    self.assertEqual(4 if image_index == 1 else 8, len(client.calls))
                    self.assertEqual("source_geometry_invalid", report["stop_reason"])
                    self.assertEqual("unconfirmed", report["candidate_reference"])
                    self.assertEqual(set() if image_index == 1 else {"before.jpg"}, set(saved))

    def test_candidate_remains_unconfirmed_until_last_image_and_checkpoint_complete(self):
        observations = []
        real = probe.write_report
        def observe(folder, report):
            observations.append(deepcopy(report))
            return real(folder, report)
        with patch.object(probe, "write_report", side_effect=observe):
            report, _ = self.run_probe(FakeClient())
        self.assertEqual("candidate_reference_observed", report["candidate_reference"])
        for item in observations:
            if item["status"] != "completed":
                self.assertEqual("unconfirmed", item["candidate_reference"])

    def test_each_checkpoint_failure_stops_without_later_rpc(self):
        calls = []
        real = probe.write_report
        client = FakeClient()
        def record(folder, report):
            calls.append(len(client.calls))
            return real(folder, report)
        with patch.object(probe, "write_report", side_effect=record):
            self.run_probe(client)
        for failure, expected in enumerate(calls, 1):
            with self.subTest(checkpoint=failure), tempfile.TemporaryDirectory() as folder:
                client = FakeClient()
                report = probe.new_report(time.monotonic_ns())
                count = [0]
                def failing(folder, report):
                    count[0] += 1
                    if count[0] == failure:
                        raise OSError("PRIVATE")
                    return real(folder, report)
                with patch.object(probe, "write_report", side_effect=failing):
                    probe.collect(client, report, folder, time.monotonic_ns() + 10_000_000_000)
                self.assertEqual(expected, len(client.calls))
                self.assertEqual("stopped", report["status"])
                self.assertEqual("output_write_failed", report["stop_reason"])
                self.assertEqual("unconfirmed", report["candidate_reference"])

    def test_each_raw_save_failure_stops_without_later_rpc(self):
        for filename, expected in (("before.jpg", 5), ("after.jpg", 9)):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as folder:
                real = probe.atomic_write
                def failing(path, raw):
                    if Path(path).name == filename:
                        raise OSError("PRIVATE")
                    return real(path, raw)
                client = FakeClient()
                report = probe.new_report(time.monotonic_ns())
                with patch.object(probe, "atomic_write", side_effect=failing):
                    probe.collect(client, report, folder, time.monotonic_ns() + 10_000_000_000)
                self.assertEqual(expected, len(client.calls))
                self.assertEqual("output_write_failed", report["stop_reason"])
                self.assertEqual("unconfirmed", report["candidate_reference"])

    def test_unknown_exception_details_are_never_saved(self):
        client = FakeClient()
        client.call = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("PRIVATE"))
        report, _ = self.run_probe(client)
        self.assertEqual("internal_error", report["stop_reason"])
        self.assertNotIn("PRIVATE", json.dumps(report))

    def test_ax_invalid_fields_cannot_confirm_candidate(self):
        mutations = [{"ref": v} for v in (None, True, 1, {}, [], "el_bad", "el_1\n", "PRIVATE")]
        mutations += [{k: v} for k in ("exists", "hittable") for v in (None, 1, "true", False)]
        mutations += [{"label": v} for v in (None, True, "続行", "PRIVATE")]
        mutations += [{k: v} for k in ("x", "y", "width", "height") for v in (True, None, "1", float("inf"), float("nan"), 4097)]
        mutations += [{k: 0} for k in ("width", "height")]
        mutations += [{"x": -4097}, {"y": -4097}, {"width": -1}, {"height": -1}]
        mutations += [{"match_count": v} for v in (0, 2, True, "1", 1.0, None)]
        mutations += [{"alternatives": v} for v in ({}, "PRIVATE", None, [{}])]
        mutations += [{"element_type": "PRIVATE"}, {"visibility": "PRIVATE"}]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                report, _ = self.run_probe(FakeClient(ax=dict(AX, **mutation)))
                self.assertEqual("unconfirmed", report["candidate_reference"])
                self.assertIs(False, report["input_authorized"])
                self.assertNotIn("PRIVATE", json.dumps(report))

    def test_optional_scan_fields_absent_do_not_assert_uniqueness(self):
        ax = deepcopy(AX)
        for key in ("match_count", "alternatives", "visibility"):
            ax.pop(key)
        report, _ = self.run_probe(FakeClient(ax=ax))
        self.assertEqual("candidate_reference_observed", report["candidate_reference"])
        self.assertNotIn("unique", json.dumps(report))

    def test_dark_before_or_after_image_keeps_reference_unconfirmed(self):
        for image_index in (1, 2):
            with self.subTest(image_index=image_index):
                def change(payload, index):
                    if index == image_index:
                        payload["data"] = base64.b64encode(picture((40, 20), color="black", format="JPEG")).decode()
                report, saved = self.run_probe(FakeClient(image_change=change))
                self.assertEqual("completed", report["status"])
                self.assertEqual(2, len(saved))
                self.assertEqual("unconfirmed", report["candidate_reference"])


class InputReportTests(unittest.TestCase):
    def assert_rejected(self, report):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "report.json"
            path.write_text(json.dumps(report))
            with self.assertRaises(ValueError):
                probe.read_checkpoint(path)

    def test_initial_and_completed_reports_roundtrip(self):
        report = probe.new_report(1)
        with tempfile.TemporaryDirectory() as folder:
            probe.write_report(folder, report)
            self.assertEqual(report, probe.read_checkpoint(Path(folder) / "report.json"))

    def test_every_required_top_level_field_is_required(self):
        original = probe.new_report(1)
        for key in original:
            with self.subTest(key=key):
                report = deepcopy(original)
                report.pop(key)
                self.assert_rejected(report)

    def test_authorization_and_unknown_fields_are_strictly_rejected(self):
        for value in (True, 1, 0, None, "false"):
            report = probe.new_report(1)
            report["input_authorized"] = value
            self.assert_rejected(report)
        for change in ({"unknown": "PRIVATE"}, {"kind": "capture_probe"}, {"stage": "PRIVATE"},
                       {"candidate_reference": "candidate_reference_observed"}, {"stop_reason": "PRIVATE"},
                       {"start_ns": True}, {"start_ns": float("nan")}):
            self.assert_rejected(dict(probe.new_report(1), **change))

    def test_nested_secrets_and_authorization_are_rejected(self):
        report, _ = InputCollectionTests().run_probe(FakeClient())
        paths = [("ax",), ("images", "before"), ("images", "before", "reported_geometry"),
                 ("worker",), ("events", 0), ("events", 0, "observation")]
        for path in paths:
            with self.subTest(path=path):
                altered = deepcopy(report)
                target = altered
                for key in path:
                    target = target[key]
                target["ref"] = "el_PRIVATE"
                self.assert_rejected(altered)
        for path in (("images", "before", "input_authorized"),
                     ("images", "after", "reported_geometry", "input_geometry_verified")):
            for value in (True, 1, 0, None):
                altered = deepcopy(report)
                target = altered
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
                self.assert_rejected(altered)

    def test_corrupt_duplicate_nan_and_oversized_json_are_rejected(self):
        for raw in (b"{", b'{"kind":"TEST011","kind":"TEST011"}', b'{"x":NaN}', b" " * (probe.MAX_REPORT + 1)):
            with tempfile.TemporaryDirectory() as folder:
                path = Path(folder) / "report.json"
                path.write_bytes(raw)
                with self.assertRaises(ValueError):
                    probe.read_checkpoint(path)

    def test_huge_numeric_report_field_is_a_safe_read_rejection(self):
        report, _ = InputCollectionTests().run_probe(FakeClient())
        report["ax"]["frame"]["x"] = 10 ** 1000
        self.assert_rejected(report)

    def test_contradictory_ax_visibility_is_rejected_on_reload(self):
        report, _ = InputCollectionTests().run_probe(FakeClient())
        for visibility in ("partial", "offscreen"):
            with self.subTest(visibility=visibility):
                altered = deepcopy(report)
                altered["ax"]["visibility"] = visibility
                self.assert_rejected(altered)

    def test_confirmed_candidate_with_dark_image_is_rejected_on_reload(self):
        report, _ = InputCollectionTests().run_probe(FakeClient())
        for name in ("before", "after"):
            with self.subTest(image=name):
                altered = deepcopy(report)
                altered["images"][name]["image_status"] = "blank_or_dark"
                self.assert_rejected(altered)

    def test_image_status_must_agree_with_maximum_luma(self):
        report, _ = InputCollectionTests().run_probe(FakeClient())
        for status, maximum in (("decoded_nonblank", 12), ("blank_or_dark", 13)):
            with self.subTest(status=status):
                altered = deepcopy(report)
                altered["candidate_reference"] = "unconfirmed"
                altered["images"]["before"].update(image_status=status, max_luma=maximum, mean_luma=1)
                self.assert_rejected(altered)

    def test_parent_rejects_bad_checkpoint_and_keeps_safe_initial_report(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            args = probe.parser().parse_args(["--output", folder, "--python-crypto"])
            def corrupt(command, timeout, diagnostics):
                target = Path(command[command.index("--output") + 1]) / "report.json"
                target.write_text('{"ref":"PRIVATE", "input_authorized":true}')
                diagnostics.update(returncode=0, signal_number=None, signal_name=None)
                return None
            with patch.object(probe, "supervise", side_effect=corrupt):
                self.assertEqual(2, probe.run(args))
            report = probe.read_checkpoint(next(Path(folder).glob("input-path-*/report.json")))
            self.assertEqual("report_read_failed", report["stop_reason"])
            self.assertEqual("unconfirmed", report["candidate_reference"])
            self.assertIs(False, report["input_authorized"])
            self.assertNotIn("PRIVATE", json.dumps(report))


class InputStopTests(unittest.TestCase):
    def check_stop(self, phase, mode):
        with tempfile.TemporaryDirectory() as folder:
            process = subprocess.Popen([sys.executable, str(DRIVER), phase, folder, mode],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
            try:
                marker = Path(folder) / "blocked.json"
                until = time.monotonic() + 5
                while not marker.exists() and process.poll() is None and time.monotonic() < until:
                    time.sleep(.01)
                self.assertTrue(marker.exists(), "指定した段階に子が到達すること")
                worker = json.loads(marker.read_text())
                if mode == "term":
                    process.send_signal(signal.SIGTERM)
                out, err = process.communicate(timeout=8)
                self.assertEqual(2, process.returncode, out + err)
                report = probe.read_checkpoint(next(Path(folder).glob("input-path-*/report.json")))
                self.assertEqual("session_deadline" if mode == "deadline" else "user_interrupt", report["stop_reason"])
                self.assertEqual("unconfirmed", report["candidate_reference"])
                self.assertIs(False, report["input_authorized"])
                self.assertEqual(-signal.SIGKILL, report["worker"]["returncode"])
                with self.assertRaises(ProcessLookupError):
                    os.kill(worker["pid"], 0)
                calls_log = Path(folder) / "rpc-calls.jsonl"
                self.assertEqual(worker["calls"], len(calls_log.read_text().splitlines()))
                stopped_calls = calls_log.read_bytes()
                time.sleep(.05)
                self.assertEqual(stopped_calls, calls_log.read_bytes())
            finally:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.communicate(timeout=2)

    def test_deadline_during_rpc(self):
        self.check_stop("rpc", "deadline")

    def test_parent_sigterm_during_rpc(self):
        self.check_stop("rpc", "term")

    def test_parent_sigterm_during_decode(self):
        self.check_stop("decode", "term")

    def test_parent_sigterm_during_save(self):
        self.check_stop("save", "term")

    def check_spawn_stop(self, mode):
        with tempfile.TemporaryDirectory() as folder:
            process = subprocess.Popen([sys.executable, str(DRIVER), "spawn", folder, mode],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
            try:
                out, err = process.communicate(timeout=5)
                worker = json.loads(Path(folder, "blocked.json").read_text())
                self.assertEqual(2, process.returncode, out + err)
                report = probe.read_checkpoint(next(Path(folder).glob("input-path-*/report.json")))
                self.assertEqual("user_interrupt", report["stop_reason"])
                self.assertEqual("stopped", report["status"])
                self.assertIs(False, report["input_authorized"])
                self.assertIsNotNone(report["worker"]["returncode"])
                with self.assertRaises(ProcessLookupError):
                    os.kill(worker["pid"], 0)
            finally:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.communicate(timeout=2)

    def test_parent_sigterm_immediately_after_real_spawn_reaps_child(self):
        self.check_spawn_stop("term")

    def test_parent_sigint_immediately_after_real_spawn_reaps_child(self):
        self.check_spawn_stop("int")


class InputEncryptedProtocolTests(TimerTestCase):
    def test_fixed_find_reaches_encrypted_protocol_once_with_no_raw_ref_report(self):
        requests = []
        def transport(body, timeout):
            requests.append(body)
            return sealed_reply(body, result=AX)
        client = probe.InputPathClient(transport, KEY, TOK, crypto=Crypto(native=False), deadline_owner=self.timer)
        result = client.call("find_element", dict(probe.FIND_PARAMS)).result
        self.assertEqual("el_123", result["ref"])
        with self.assertRaises(ProbeError):
            client.call("find_element", dict(probe.FIND_PARAMS))
        self.assertEqual(1, len(requests))
        self.assertTrue(probe.sanitize_ax(result)["ref_present"])


class InputCleanupTests(unittest.TestCase):
    def failed_process(self, mode):
        class Process:
            returncode = None
            killed = False
            def poll(self):
                return self.returncode
            def terminate(self):
                if mode == "terminate":
                    raise OSError("PRIVATE")
            def kill(self):
                self.killed = True
                if mode == "kill":
                    raise OSError("PRIVATE")
                if mode != "wait":
                    self.returncode = -signal.SIGKILL
            def wait(self, timeout):
                if self.returncode is None:
                    raise subprocess.TimeoutExpired("PRIVATE_COMMAND", timeout)
                return self.returncode
        return Process()

    def test_terminate_failure_still_attempts_kill_and_reap(self):
        process = self.failed_process("terminate")
        diagnostics = {}
        with patch.object(probe.subprocess, "Popen", return_value=process):
            reason = probe.supervise(["PRIVATE_COMMAND"], 0, diagnostics)
        self.assertTrue(process.killed)
        self.assertEqual("worker_cleanup_failed", reason)
        self.assertTrue(diagnostics["exit_confirmed"])
        self.assertEqual(-signal.SIGKILL, diagnostics["returncode"])
        self.assertNotIn("PRIVATE", json.dumps(diagnostics))

    def test_failed_kill_or_reap_has_fixed_diagnostics_and_no_exception_text(self):
        for mode in ("kill", "wait"):
            with self.subTest(mode=mode):
                process = self.failed_process(mode)
                diagnostics = {}
                with patch.object(probe.subprocess, "Popen", return_value=process):
                    reason = probe.supervise(["PRIVATE_COMMAND"], 0, diagnostics)
                self.assertTrue(process.killed)
                self.assertEqual("worker_cleanup_failed", reason)
                self.assertFalse(diagnostics["exit_confirmed"])
                self.assertIsNone(diagnostics["returncode"])
                self.assertEqual("worker_cleanup_failed", diagnostics["cleanup_error"])
                self.assertNotIn("PRIVATE", json.dumps(diagnostics))

    def test_unreaped_child_cannot_overwrite_parent_final_result(self):
        with tempfile.TemporaryDirectory() as folder:
            args = probe.parser().parse_args(["--output", folder, "--python-crypto"])
            child_report = []
            def unfinished(command, timeout, diagnostics):
                path = Path(command[command.index("--output") + 1]) / "report.json"
                child_report.append(path)
                diagnostics.update(returncode=None, signal_number=None, signal_name=None,
                                   exit_confirmed=False, cleanup_error="worker_cleanup_failed")
                return "worker_cleanup_failed"
            output = io.StringIO()
            with patch.object(probe, "supervise", side_effect=unfinished), contextlib.redirect_stdout(output):
                self.assertEqual(2, probe.run(args))
            parent = child_report[0].with_name("parent-result.json")
            report = probe.read_checkpoint(parent)
            self.assertEqual("worker_cleanup_failed", report["stop_reason"])
            self.assertEqual("unconfirmed", report["candidate_reference"])
            self.assertIs(False, report["input_authorized"])
            self.assertIn("子プロセスの終了は未確認", output.getvalue())
            final = parent.read_bytes()
            self.assertEqual("running", probe.read_checkpoint(child_report[0])["status"])
            child_report[0].write_text('{"private":"PRIVATE"}')
            self.assertEqual(final, parent.read_bytes())
