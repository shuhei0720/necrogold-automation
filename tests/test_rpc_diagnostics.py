"""TEST-012の認証済み遠隔エラー診断。合成応答であり実機受入ではない。"""
from copy import deepcopy
import base64
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch

from necroprobe import input_path as probe
from necroprobe.crypto import Crypto, mac, python_xor
from necroprobe.protocol import Client, GAME
from necroprobe.validation import ProbeError
from input_path_support import FakeClient, METHODS
from test_protocol import KEY, TOK
from timer_support import TimerTestCase

ROOT = Path(__file__).resolve().parents[1]
REVISION = "rpc-diagnostics-v1"
BASE = "No element matching label/id 'ゲームを続行'"
NO_MATCH = BASE + ". It may be off-screen (page{direction}, then find_element again), or the label differs from on-screen text — check page_source. Try match:'contains'."
WEB = (BASE + ". ⚠️ The foreground app is a BROWSER: web page content is NOT exposed to the "
       "accessibility tree, so find_element/page_source can never see links, buttons or text in the page "
       "(page_source returns only browser chrome). Do NOT retry with scroll_to_element or match:'contains' — "
       "they cannot help here. Next: call screenshot, read the target's position off the image, convert "
       "pixel→point by dividing by the `scale` field in that same screenshot response, then tap{x,y}.")
PREFIXES = (
    (-32602, NO_MATCH, "no_matching_element"),
    (-32602, BASE + ": a system alert ", "system_alert_reported"),
    (-32602, WEB, "webview_context_reported"),
    (-32004, "Can't find 'ゲームを続行': app '" + GAME + "' is not running (", "app_not_running"),
    (-32004, "Can't find 'ゲームを続行': app '" + GAME + "' is in the background, so it has no snapshottable window.", "app_background"),
    (-32000, GAME + "'s accessibility isn't answering right now, so 'ゲームを続行' can't be looked up.", "ax_unresponsive"),
    (-32000, GAME + "'s accessibility isn't answering right now (the tree read failed after 12s), so 'ゲームを続行' couldn't be looked up.", "ax_unresponsive"),
    (-32000, "find_element has NOT run yet: it is queued behind ", "server_queued"),
    (-32000, "find_element exceeded 6s and may still be running on the device.", "server_timeout"),
)


def decode_request(body):
    envelope = json.loads(body)
    nonce = bytes.fromhex(envelope["nonce"])
    request = json.loads(python_xor(mac(KEY, b"loopctrl-v1|enc-req" + nonce), nonce,
                                  base64.b64decode(envelope["ct"])))
    return nonce, request


def seal(body, fields, *, wrong_id=False, corrupt_mac=False, plain=None):
    nonce, request = decode_request(body)
    response = dict(jsonrpc="2.0", id=request["id"] + 1 if wrong_id else request["id"])
    response.update(fields)
    raw = json.dumps(response, ensure_ascii=False).encode() if plain is None else plain
    cipher = python_xor(mac(KEY, b"loopctrl-v1|enc-resp" + nonce), nonce, raw)
    tag = mac(mac(KEY, b"loopctrl-v1|mac" + nonce), b"resp" + nonce + cipher).hex()
    return json.dumps({"ct": base64.b64encode(cipher).decode(), "tag": "00" * 32 if corrupt_mac else tag}).encode()


class RpcDiagnosticTests(TimerTestCase):
    def error(self, error, *, fields=None, method="find_element", params=None, **options):
        transport = lambda body, timeout: seal(body, dict({"error": error}, **(fields or {})), **options)
        client = probe.InputPathClient(transport, KEY, TOK, crypto=Crypto(native=False), deadline_owner=self.timer)
        with self.assertRaises(ProbeError) as caught:
            client.call(method, dict(probe.FIND_PARAMS) if params is None and method == "find_element" else params)
        return caught.exception

    def test_known_source_prefixes_are_classified_without_retaining_remote_text(self):
        for code, message, category in PREFIXES:
            with self.subTest(category=category, message=message):
                exc = self.error({"code": code, "message": message + " PRIVATE_SECRET", "data": {"token": "PRIVATE_SECRET"}})
                self.assertEqual("rpc_error", exc.code)
                self.assertEqual(code, getattr(exc, "rpc_code", None))
                self.assertEqual(category, getattr(exc, "category", None))
                self.assertIs(True, getattr(exc, "error_shape_valid", None))
                self.assertIsNot(type(exc), ProbeError)
                self.assertEqual("rpc_error", str(exc))
                self.assertNotIn("PRIVATE_SECRET", repr(vars(exc)) + repr(exc.args) + repr(exc))

    def test_code_alone_and_unknown_or_embedded_prefix_are_unclassified(self):
        for code, message in ((-32602, "PRIVATE_SECRET"), (-32602, "prefix " + NO_MATCH),
                              (-32000, NO_MATCH), (-32603, NO_MATCH), (2147483647, NO_MATCH),
                              (-2147483648, NO_MATCH), (-32602, BASE + ". unknown")):
            with self.subTest(code=code, message=message):
                exc = self.error({"code": code, "message": message})
                self.assertEqual("unclassified", getattr(exc, "category", None))
                self.assertEqual(code, getattr(exc, "rpc_code", None))

    def test_free_text_suffix_cannot_change_category(self):
        for code, message, category in PREFIXES:
            suffix = " PRIVATE " + " ".join(other for _, other, _ in PREFIXES)
            with self.subTest(category=category):
                self.assertEqual(category, getattr(self.error({"code": code, "message": message + suffix}), "category", None))

    def test_oversized_message_is_unclassified_but_shape_valid(self):
        for size, expected in ((8192, "no_matching_element"), (8193, "unclassified")):
            exc = self.error({"code": -32602, "message": NO_MATCH + "x" * (size - len(NO_MATCH))})
            self.assertEqual(expected, getattr(exc, "category", None))
            self.assertIs(True, getattr(exc, "error_shape_valid", None))

    def test_ax_duration_grammar_accepts_only_one_to_three_decimal_digits(self):
        for duration, expected in (("0", "ax_unresponsive"), ("999", "ax_unresponsive"),
                                   ("1000", "unclassified"), ("1.5", "unclassified"),
                                   ("-1", "unclassified"), ("１２", "unclassified")):
            message = GAME + "'s accessibility isn't answering right now (the tree read failed after " + duration + "s), so 'ゲームを続行' couldn't be looked up."
            self.assertEqual(expected, getattr(self.error({"code": -32000, "message": message}), "category", None))

    def test_invalid_error_schema_has_fixed_category_and_sanitized_optional_code(self):
        errors = [None, [], "PRIVATE", True, {}, {"message": NO_MATCH}]
        errors += [{"code": code, "message": NO_MATCH} for code in (True, False, 1.0, "-32602", None, 2147483648, -2147483649)]
        errors += [{"code": -32602, "message": message} for message in (None, True, 1, [], {})]
        errors += [{"code": -32602}]
        for error in errors:
            with self.subTest(error=error):
                exc = self.error(error)
                expected = -32602 if type(error) is dict and type(error.get("code")) is int and error["code"] == -32602 else None
                self.assertEqual("malformed_remote_error", getattr(exc, "category", None))
                self.assertEqual(expected, getattr(exc, "rpc_code", None))
                self.assertIs(False, getattr(exc, "error_shape_valid", None))

    def test_result_and_error_coexistence_is_malformed_even_with_valid_code(self):
        exc = self.error({"code": -32602, "message": NO_MATCH}, fields={"result": {"exists": True}})
        self.assertEqual("malformed_remote_error", getattr(exc, "category", None))
        self.assertEqual(-32602, getattr(exc, "rpc_code", None))
        self.assertIs(False, getattr(exc, "error_shape_valid", None))

    def test_non_find_rpc_never_gets_specific_find_category(self):
        for method, params in (("device_info", {}), ("launch_app", {"bundle_id": GAME}), ("screenshot", dict(probe.CAPTURE_PARAMS))):
            with self.subTest(method=method):
                exc = self.error({"code": -32602, "message": NO_MATCH}, method=method, params=params)
                self.assertEqual("unclassified", getattr(exc, "category", None))

    def test_non_fixed_find_params_never_get_specific_category(self):
        for change in ({"bundle_id": "other"}, {"match": "contains"}, {"element_id": "other"}, {"extra": True}):
            transport = lambda body, timeout: seal(body, {"error": {"code": -32602, "message": NO_MATCH}})
            client = self.client(transport, KEY, TOK, crypto=Crypto(native=False))
            with patch.object(client, "_validate"), self.assertRaises(ProbeError) as caught:
                client.call("find_element", dict(probe.FIND_PARAMS, **change))
            self.assertEqual("unclassified", getattr(caught.exception, "category", None))

    def test_bad_mac_and_wrong_id_remain_transport_errors_with_no_remote_detail(self):
        for options, expected in (({"corrupt_mac": True}, "response_mac_mismatch"), ({"wrong_id": True}, "response_id_mismatch")):
            exc = self.error({"code": -32602, "message": NO_MATCH}, **options)
            self.assertEqual(expected, exc.code)
            self.assertFalse(hasattr(exc, "rpc_code"))
            self.assertFalse(hasattr(exc, "category"))

    def test_invalid_json_and_http_failure_are_not_remote_errors(self):
        exc = self.error({}, plain=b"not json PRIVATE")
        self.assertEqual("invalid_json", exc.code)
        self.assertFalse(hasattr(exc, "rpc_code"))
        def failed(*_):
            raise ProbeError("http_status_503")
        client = self.client(failed, KEY, TOK, crypto=Crypto(native=False))
        with self.assertRaises(ProbeError) as caught:
            client.call("device_info")
        self.assertEqual("http_status_503", caught.exception.code)
        self.assertFalse(hasattr(caught.exception, "rpc_code"))

    def test_success_dictionary_and_invalid_result_contract_remain_unchanged(self):
        for result in ({"ok": True}, None, [], "PRIVATE", True):
            client = self.client(lambda body, timeout: seal(body, {"result": result}), KEY, TOK, crypto=Crypto(native=False))
            if type(result) is dict:
                reply = client.call("device_info")
                self.assertEqual(result, reply.result)
                self.assertIn("response_end_ns", reply.timings)
            else:
                with self.assertRaises(ProbeError) as caught:
                    client.call("device_info")
                self.assertEqual("rpc_result_type", caught.exception.code)


class DiagnosticReportTests(TimerTestCase):
    def encrypted_collect(self, folder, *, failure=6, test_id="TEST-011", error=None):
        fake = FakeClient()
        requests = []
        error = {"code": -32602, "message": NO_MATCH + " PRIVATE_SECRET", "data": "PRIVATE_SECRET"} if error is None else error
        def transport(body, timeout):
            _, request = decode_request(body)
            requests.append(request)
            if len(requests) == failure:
                return seal(body, {"error": error})
            return seal(body, {"result": fake.call(request["method"], request["params"]).result})
        client = probe.InputPathClient(transport, KEY, TOK, crypto=Crypto(native=False), deadline_owner=self.timer)
        report = probe.new_report(time.monotonic_ns())
        report["test_id"] = test_id
        probe.collect(client, report, folder, time.monotonic_ns() + 10_000_000_000)
        return report, requests, fake

    def fixture(self, folder):
        report, _, _ = self.encrypted_collect(folder)
        # The contract fixture makes rejection tests meaningful before feature implementation.
        report.update(diagnostic_revision=REVISION, rpc_error_detail={"stage": "find", "rpc_code": -32602,
                      "category": "no_matching_element", "error_shape_valid": True})
        report["events"][6]["end_ns"] = report["end_ns"]
        return report

    def assert_read(self, report, folder, *, valid):
        probe.write_report(folder, report)
        if valid:
            self.assertEqual(report, probe.read_checkpoint(Path(folder) / "report.json"))
        else:
            with self.assertRaises(ValueError):
                probe.read_checkpoint(Path(folder) / "report.json")

    def test_encrypted_failure_collect_save_read_keeps_sanitized_detail_and_host_stage_end(self):
        with tempfile.TemporaryDirectory() as folder:
            report, requests, fake = self.encrypted_collect(folder)
            self.assertEqual(REVISION, report.get("diagnostic_revision"))
            self.assertEqual({"stage": "find", "rpc_code": -32602, "category": "no_matching_element", "error_shape_valid": True}, report.get("rpc_error_detail"))
            self.assertEqual(METHODS[:6], [request["method"] for request in requests])
            event = report["events"][6]
            self.assertIsInstance(event["end_ns"], int)
            self.assertLessEqual(event["start_ns"], event["end_ns"])
            self.assertLessEqual(event["end_ns"], report["end_ns"])
            self.assertEqual(["not_started"] * 4, [item["status"] for item in report["events"][7:]])
            self.assertEqual(fake.raws[0], Path(folder, "before.jpg").read_bytes())
            self.assertFalse(Path(folder, "after.jpg").exists())
            self.assertEqual("rpc_error", report["stop_reason"])
            self.assertEqual("unconfirmed", report["candidate_reference"])
            self.assertNotIn("PRIVATE_SECRET", Path(folder, "report.json").read_text())
            self.assert_read(report, folder, valid=True)

    def test_every_rpc_failure_is_terminal_and_other_stages_are_unclassified(self):
        for failure in range(1, 10):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as folder:
                report, requests, _ = self.encrypted_collect(folder, failure=failure)
                self.assertEqual(failure, len(requests))
                detail = report.get("rpc_error_detail")
                self.assertIsInstance(detail, dict)
                self.assertEqual("no_matching_element" if failure == 6 else "unclassified", detail["category"])
                self.assertEqual(report["stage"], detail["stage"])
                self.assert_read(report, folder, valid=True)

    def test_report_roundtrips_malformed_and_unknown_remote_errors(self):
        for error, category in (({"code": True, "message": NO_MATCH}, "malformed_remote_error"),
                                ({"code": -32602, "message": []}, "malformed_remote_error"),
                                ({"code": 0, "message": "PRIVATE"}, "unclassified")):
            with tempfile.TemporaryDirectory() as folder:
                report, _, _ = self.encrypted_collect(folder, error=error)
                self.assertIsInstance(report.get("rpc_error_detail"), dict)
                self.assertEqual(category, report["rpc_error_detail"]["category"])
                self.assert_read(report, folder, valid=True)

    def test_success_has_null_detail_and_same_safe_candidate_contract(self):
        with tempfile.TemporaryDirectory() as folder:
            report, requests, _ = self.encrypted_collect(folder, failure=99)
            self.assertIn("rpc_error_detail", report)
            self.assertIsNone(report["rpc_error_detail"])
            self.assertEqual("completed", report["status"])
            self.assertEqual("candidate_reference_observed", report["candidate_reference"])
            self.assertEqual(METHODS, [request["method"] for request in requests])
            self.assert_read(report, folder, valid=True)

    def test_stage_timing_includes_checkpoint_io_before_send(self):
        with tempfile.TemporaryDirectory() as folder:
            clock = [1000]
            report = probe.new_report(clock[0])
            fake = FakeClient()
            original = probe.write_report
            def writing(folder, report):
                clock[0] += 10
                original(folder, report)
            with patch.object(probe, "write_report", side_effect=writing):
                probe.collect(fake, report, folder, 1000000000, clock=lambda: clock[0])
            self.assertEqual(10, report["events"][0]["end_ns"] - report["events"][0]["start_ns"])

    def test_valid_diagnostic_schema_roundtrips(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assert_read(self.fixture(folder), folder, valid=True)

    def test_malformed_diagnostic_fields_unknown_keys_and_invalid_code_category_pairs_are_rejected(self):
        mutations = [{"rpc_code": value} for value in (True, 1.0, "-32602", 2147483648, -2147483649, None, -32000)]
        mutations += [{"category": value} for value in ("PRIVATE", None, True, "malformed_remote_error")]
        mutations += [{"error_shape_valid": value} for value in (False, 1, "true", None)]
        mutations += [{"stage": value} for value in ("before_save", "initial_info", "PRIVATE", None)]
        mutations += [{"data": "PRIVATE"}, {"message": "PRIVATE"}]
        with tempfile.TemporaryDirectory() as folder:
            original = self.fixture(folder)
            for mutation in mutations:
                with self.subTest(mutation=mutation):
                    report = deepcopy(original)
                    report["rpc_error_detail"].update(mutation)
                    self.assert_read(report, folder, valid=False)
            for missing in original["rpc_error_detail"]:
                report = deepcopy(original)
                report["rpc_error_detail"].pop(missing)
                self.assert_read(report, folder, valid=False)
            for value in (True, [], "PRIVATE"):
                self.assert_read(dict(original, rpc_error_detail=value), folder, valid=False)

    def test_completed_success_pending_and_inconsistent_event_injections_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            original = self.fixture(folder)
            mutations = [lambda r: r.update(status="completed", stop_reason=None),
                         lambda r: r.update(candidate_reference="candidate_reference_observed"),
                         lambda r: r.update(stage="after_info"),
                         lambda r: r.update(input_authorized=True),
                         lambda r: r["events"][6].update(status="complete"),
                         lambda r: r["events"][6].update(status="in_progress"),
                         lambda r: r["events"][6].update(end_ns=None),
                         lambda r: r["events"][6].update(end_ns=r["events"][6]["start_ns"] - 1),
                         lambda r: r["events"][6].update(end_ns=r["end_ns"] + 1),
                         lambda r: r["events"][7].update(status="error", start_ns=r["end_ns"], end_ns=r["end_ns"]),
                         lambda r: r.update(end_ns=r["start_ns"] - 1),
                         lambda r: r["events"][0].update(start_ns=r["start_ns"] - 1),
                         lambda r: r.update(stop_reason="foreground_not_verified")]
            for index, mutation in enumerate(mutations):
                with self.subTest(index=index):
                    report = deepcopy(original)
                    mutation(report)
                    self.assert_read(report, folder, valid=False)
            success, _, _ = self.encrypted_collect(folder, failure=99)
            success["rpc_error_detail"] = original["rpc_error_detail"]
            self.assert_read(success, folder, valid=False)

    def test_allowed_parent_and_cleanup_overrides_keep_prior_detail_and_unconfirmed_candidate(self):
        with tempfile.TemporaryDirectory() as folder:
            original = self.fixture(folder)
            for reason in ("user_interrupt", "session_deadline", "worker_failed", "worker_cleanup_failed",
                           "output_write_failed", "timer_cleanup_failed"):
                with self.subTest(reason=reason):
                    report = deepcopy(original)
                    probe.stop(report, reason)
                    self.assertEqual(original["rpc_error_detail"], report["rpc_error_detail"])
                    self.assertEqual("unconfirmed", report["candidate_reference"])
                    self.assert_read(report, folder, valid=True)


class DiagnosticRunTests(unittest.TestCase):
    def test_cli_default_and_explicit_ids_and_invalid_id(self):
        self.assertEqual("TEST-011", getattr(probe.parser().parse_args([]), "test_id", None))
        for test_id in ("TEST-011", "TEST-012"):
            self.assertEqual(test_id, probe.parser().parse_args(["--test-id", test_id]).test_id)
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            probe.parser().parse_args(["--test-id", "PRIVATE"])

    def test_test012_parent_passes_and_displays_id_start_and_revision(self):
        with tempfile.TemporaryDirectory() as folder:
            args = probe.parser().parse_args(["--test-id", "TEST-012", "--output", folder])
            seen = []
            def supervise(command, timeout, diagnostics):
                path = Path(command[command.index("--output") + 1])
                report = json.loads((path / "report.json").read_text())
                seen.append(command)
                self.assertEqual("TEST-012", command[command.index("--test-id") + 1])
                self.assertEqual(str(report["start_ns"]), command[command.index("--start-ns") + 1])
                self.assertEqual(REVISION, report["diagnostic_revision"])
                probe.collect(FakeClient(), report, path, time.monotonic_ns() + 10000000000)
                diagnostics.update(returncode=0, exit_confirmed=True)
                return None
            out = io.StringIO()
            with patch.object(probe, "supervise", side_effect=supervise), contextlib.redirect_stdout(out):
                self.assertEqual(0, probe.run(args))
            self.assertEqual(1, len(seen))
            self.assertIn("TEST-012", out.getvalue())
            self.assertNotIn("TEST-011", out.getvalue())
            saved = json.loads(next(Path(folder).glob("input-path-*/parent-result.json")).read_text())
            self.assertEqual("TEST-012", saved["test_id"])

    def test_parent_rejects_checkpoint_swapped_to_other_run_identity_or_revision(self):
        for field, value in (("test_id", "TEST-012"), ("start_ns", 1), ("diagnostic_revision", "old")):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as folder:
                args = probe.parser().parse_args(["--output", folder])
                def swap(command, timeout, diagnostics):
                    path = Path(command[command.index("--output") + 1])
                    report = json.loads((path / "report.json").read_text())
                    probe.collect(FakeClient(), report, path, time.monotonic_ns() + 10000000000)
                    report[field] = value
                    probe.write_report(path, report)
                    diagnostics.update(returncode=0, exit_confirmed=True)
                    return None
                with patch.object(probe, "supervise", side_effect=swap), contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(2, probe.run(args))
                saved = json.loads(next(Path(folder).glob("input-path-*/parent-result.json")).read_text())
                self.assertEqual("report_read_failed", saved["stop_reason"])
                self.assertEqual("unconfirmed", saved["candidate_reference"])
                self.assertEqual("TEST-011", saved["test_id"])

    def test_worker_rejects_mismatch_before_pairing_or_network(self):
        for field, value in (("test_id", "TEST-012"), ("start_ns", 2), ("diagnostic_revision", "old")):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as folder:
                report = probe.new_report(1)
                report[field] = value
                probe.write_report(folder, report)
                args = probe.parser().parse_args(["--worker", "--output", folder])
                args.test_id, args.start_ns = "TEST-011", 1
                with patch.object(probe, "load_pairing", side_effect=AssertionError("must not load")) as pairing, patch.object(probe, "HttpTransport") as transport:
                    self.assertEqual(probe.WORKER_REPORT_READ_EXIT, probe.worker(args))
                pairing.assert_not_called()
                transport.assert_not_called()

    def test_worker_requires_expected_start_before_any_pairing(self):
        with tempfile.TemporaryDirectory() as folder:
            probe.write_report(folder, probe.new_report(1))
            args = probe.parser().parse_args(["--worker", "--output", folder])
            with patch.object(probe, "load_pairing", side_effect=AssertionError("must not load")) as pairing:
                self.assertEqual(probe.WORKER_REPORT_READ_EXIT, probe.worker(args))
            pairing.assert_not_called()

    def test_parent_override_retains_prior_rpc_observation_and_prints_separately(self):
        with tempfile.TemporaryDirectory() as folder:
            args = probe.parser().parse_args(["--output", folder])
            def stopped(command, timeout, diagnostics):
                path = Path(command[command.index("--output") + 1])
                report = json.loads((path / "report.json").read_text())
                probe.collect(FakeClient(failure=6), report, path, time.monotonic_ns() + 10000000000)
                report.update(diagnostic_revision=REVISION, rpc_error_detail={"stage": "find", "rpc_code": -32602,
                              "category": "no_matching_element", "error_shape_valid": True})
                report["events"][6]["end_ns"] = report["end_ns"]
                probe.write_report(path, report)
                diagnostics.update(returncode=-15, exit_confirmed=True)
                return "session_deadline"
            out = io.StringIO()
            with patch.object(probe, "supervise", side_effect=stopped), contextlib.redirect_stdout(out):
                self.assertEqual(2, probe.run(args))
            saved = json.loads(next(Path(folder).glob("input-path-*/parent-result.json")).read_text())
            self.assertEqual("session_deadline", saved["stop_reason"])
            self.assertEqual("no_matching_element", (saved.get("rpc_error_detail") or {}).get("category"))
            self.assertEqual("unconfirmed", saved["candidate_reference"])
            self.assertIn("no_matching_element", out.getvalue())
            self.assertIn("session_deadline", out.getvalue())

    def test_old_schema_is_rejected_without_rewriting_original(self):
        with tempfile.TemporaryDirectory() as folder:
            report = probe.new_report(1)
            report.pop("diagnostic_revision", None)
            report.pop("rpc_error_detail", None)
            probe.write_report(folder, report)
            path = Path(folder, "report.json")
            raw = path.read_bytes()
            with self.assertRaises(ValueError):
                probe.read_checkpoint(path)
            self.assertEqual(raw, path.read_bytes())

    def test_wrapper_rejects_overrides_before_python_keeper_or_network(self):
        wrapper = ROOT / "test_012.sh"
        self.assertTrue(wrapper.exists(), "TEST-012 wrapper is required")
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder, "called")
            for name in ("python3", "cat", "sleep"):
                path = Path(folder, name)
                path.write_text('#!/bin/sh\nprintf touched >> "$DIAGNOSTIC_MARKER"\nexit 9\n')
                path.chmod(0o755)
            for args in (("--output", "PRIVATE"), ("--test-id", "TEST-011"), ("--worker",),
                         ("--python-crypto", "--python-crypto"), ("--help",), ("--",)):
                with self.subTest(args=args):
                    result = subprocess.run(["/bin/sh", str(wrapper), *args], env=dict(os.environ, PATH=folder, DIAGNOSTIC_MARKER=str(marker)), capture_output=True, text=True)
                    self.assertNotEqual(0, result.returncode)
                    self.assertIn("TEST-012", result.stderr)
                    self.assertFalse(marker.exists())

    def test_wrapper_accepts_only_no_args_or_sole_python_crypto_at_preflight(self):
        wrapper = ROOT / "test_012.sh"
        self.assertTrue(wrapper.exists(), "TEST-012 wrapper is required")
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder, "called")
            python = Path(folder, "python3")
            python.write_text('#!/bin/sh\nprintf called >> "$DIAGNOSTIC_MARKER"\nexit 9\n')
            python.chmod(0o755)
            for args in ((), ("--python-crypto",)):
                result = subprocess.run(["/bin/sh", str(wrapper), *args], env=dict(os.environ, PATH=folder, DIAGNOSTIC_MARKER=str(marker)), capture_output=True, text=True)
                self.assertNotEqual(0, result.returncode)
                self.assertTrue(marker.exists(), "accepted args must reach version preflight")
                marker.unlink()
            source = wrapper.read_text()
            self.assertIn("--test-id TEST-012", source)
            self.assertIn("--output runtime/test-012", source)


if __name__ == "__main__":
    unittest.main()
