"""Owned worker timer contract; host fault injection is not device acceptance."""
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
import threading
import time
import unittest
from unittest.mock import patch

from necroprobe.crypto import Crypto, mac, python_xor
from necroprobe.deadlines import OwnedRpcTimer
from necroprobe.protocol import Client, GAME, HttpTransport
from necroprobe.session import collect, new_report
from necroprobe.validation import ProbeError
from test_capture import picture, payload
from test_http_and_cli import LocalServer
from test_protocol import KEY, TOK, sealed_reply
from test_session import FakeClient
from timer_support import TimerTestCase

ROOT = Path(__file__).resolve().parents[1]


class TimerCompatibilityTests(TimerTestCase):
    def test_getitimer_sigsys_fault_does_not_kill_rpc_child(self):
        result = subprocess.run([sys.executable, str(ROOT / "tests/fixtures/ish_timer_driver.py")],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(0, result.returncode)
        self.assertIn("authenticated_reply_received", result.stdout)

    def run_http_sequence(self):
        methods, params_seen = [], []
        images = {f: picture(color=(80, 90, 100), format=f.upper()) for f in ("jpeg", "png")}
        def respond(handler, body):
            envelope = json.loads(body)
            nonce = bytes.fromhex(envelope["nonce"])
            request = json.loads(python_xor(mac(KEY, b"loopctrl-v1|enc-req" + nonce), nonce,
                                           base64.b64decode(envelope["ct"])))
            methods.append(request["method"])
            params_seen.append(request["params"])
            result = payload(images[request["params"]["format"]]) if request["method"] == "screenshot" else {}
            response = sealed_reply(body, result=result)
            handler.send_response(200)
            handler.send_header("Content-Length", str(len(response)))
            handler.end_headers()
            handler.wfile.write(response)
        output = io.StringIO()
        with LocalServer(respond) as port, tempfile.TemporaryDirectory() as folder:
            client = self.client(HttpTransport(port), KEY, TOK, allow_launch=True, crypto=Crypto(native=False))
            report = new_report(12, time.monotonic_ns())
            with patch("signal.getitimer", side_effect=AssertionError("unsupported syscall")), contextlib.redirect_stdout(output):
                collect(client, report, folder, time.monotonic_ns() + 5_000_000_000)
            self.assertEqual(["device_info", "launch_app"] + ["screenshot"] * 12 + ["device_info"], methods)
            self.assertEqual({"bundle_id": GAME}, params_seen[1])
            self.assertEqual(12, report["summary"]["complete"])
            self.assertFalse(report["events"][1]["game_visible_verified"])
            self.assertFalse(report["input_authorized"])
            self.assertEqual("not_passed", report["gate"]["P1"])
            saved = [row for row in report["rows"] if "raw_file" in row]
            self.assertEqual(3, len(saved))
            self.assertEqual({"jpeg_scale1", "jpeg_scale2", "png_scale1"}, {row["variant"] for row in saved})
            for row in saved:
                self.assertEqual(images[row["image"]["format"].lower()], (Path(folder) / row["raw_file"]).read_bytes())
            self.assertEqual(report, json.loads((Path(folder) / "report.json").read_text()))
        self.assertIn("ゲームの起動要求を送ります", output.getvalue())
        self.assertIn("表示の成功は未確認", output.getvalue())

    def test_real_http_launch_capture_sequence_without_getitimer(self):
        self.run_http_sequence()

    def test_rpc_sequence_ignores_all_timer_return_values(self):
        real = signal.setitimer
        class UnreadableOldValue:
            def __ne__(self, _):
                raise AssertionError("OS timer old value must not be interpreted")
            def __eq__(self, _):
                raise AssertionError("OS timer old value must not be interpreted")
            def __iter__(self):
                raise AssertionError("OS timer old value must not be restored")
            def __bool__(self):
                raise AssertionError("OS timer old value must not be tested")
        for returned in (UnreadableOldValue(), (-1000000, 0), (2147483647, 123), (float("nan"), float("inf"))):
            def bad_return(*args):
                real(*args)
                return returned
            with self.subTest(return_type=type(returned).__name__), patch("signal.setitimer", side_effect=bad_return):
                self.run_http_sequence()

    def test_no_owner_rejects_before_crypto_timer_or_http(self):
        crypto = Crypto(native=False)
        with patch.object(crypto, "xor") as xor, patch("signal.setitimer") as setter:
            with self.assertRaisesRegex(ProbeError, "timer_owner_required"):
                Client(lambda *_: self.fail("network"), KEY, TOK, crypto=crypto).call("device_info")
        xor.assert_not_called()
        setter.assert_not_called()

    def test_unstarted_and_closed_owner_are_rejected(self):
        for owner in (OwnedRpcTimer(), self.timer):
            if owner is self.timer:
                owner.close()
            with self.subTest(started=owner is self.timer), patch("signal.setitimer") as setter:
                with self.assertRaisesRegex(ProbeError, "timer_unusable"):
                    Client(lambda *_: self.fail("network"), KEY, TOK, deadline_owner=owner).call("device_info")
                setter.assert_not_called()

    def test_duplicate_owner_and_reentry_refused_without_touching_timer(self):
        with patch("signal.setitimer") as setter:
            for owner in (self.timer, OwnedRpcTimer()):
                with self.assertRaisesRegex(ProbeError, "timer_already_in_use"):
                    owner.__enter__()
            setter.assert_not_called()

    def test_nested_rpc_does_not_modify_outer_deadline(self):
        started = time.monotonic()
        with self.assertRaisesRegex(ProbeError, "rpc_deadline"):
            with self.timer.deadline(.15):
                with patch("signal.setitimer") as setter:
                    with self.assertRaisesRegex(ProbeError, "timer_already_in_use"):
                        with self.timer.deadline(1):
                            self.fail("nested entered")
                    setter.assert_not_called()
                time.sleep(.5)
        self.assertLess(time.monotonic() - started, .4)

    def test_wrong_pid_or_thread_rejected_without_timer_changes(self):
        with patch("necroprobe.deadlines.os.getpid", return_value=-1), patch("signal.setitimer") as setter:
            with self.assertRaisesRegex(ProbeError, "timer_unusable"):
                with self.timer.deadline(.1):
                    self.fail("wrong pid")
            setter.assert_not_called()
        errors = []
        def other_thread():
            try:
                with self.timer.deadline(.1):
                    errors.append("entered")
            except ProbeError as exc:
                errors.append(exc.code)
        with patch("signal.setitimer") as setter:
            thread = threading.Thread(target=other_thread)
            thread.start()
            thread.join(2)
            self.assertFalse(thread.is_alive())
            setter.assert_not_called()
        self.assertEqual(["timer_unusable"], errors)

    def test_late_signals_outside_or_before_deadline_are_ignored(self):
        signal.raise_signal(signal.SIGALRM)
        with self.timer.deadline(.5):
            signal.raise_signal(signal.SIGALRM)
        signal.raise_signal(signal.SIGALRM)
        self.timer.close()
        signal.raise_signal(signal.SIGALRM)

    def test_pending_alarm_between_rpcs_and_after_close_does_not_kill_child(self):
        result = subprocess.run([sys.executable, str(ROOT / "tests/fixtures/owned_timer_driver.py"), "pending"],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("pending_survived", result.stdout)

    def test_delayed_signal_cannot_make_overdue_result_successful(self):
        with patch("signal.setitimer", return_value=(123, 123)):
            with self.assertRaisesRegex(ProbeError, "rpc_deadline"):
                with self.timer.deadline(.02):
                    time.sleep(.05)

    def test_early_one_shot_delivery_rearms_remaining_deadline(self):
        real = signal.setitimer
        arms = []
        def early(which, seconds, interval=0):
            if seconds:
                arms.append(seconds)
            return real(which, .01 if seconds and len(arms) == 1 else seconds, interval)
        started = time.monotonic()
        with patch("signal.setitimer", side_effect=early):
            with self.assertRaisesRegex(ProbeError, "rpc_deadline"):
                with self.timer.deadline(.08):
                    time.sleep(.5)
        self.assertLess(time.monotonic() - started, .3)
        self.assertGreaterEqual(len(arms), 2)
        self.assertLess(arms[1], arms[0])

    def test_early_signal_rearm_failure_poison_prevents_reuse(self):
        with self.assertRaisesRegex(ProbeError, "timer_setup_failed"):
            with self.timer.deadline(1):
                with patch("signal.setitimer", side_effect=OSError("PRIVATE_REARM_ERROR")):
                    signal.raise_signal(signal.SIGALRM)
        self.assertTrue(self.timer.diagnostics()["poisoned"])
        with self.assertRaisesRegex(ProbeError, "timer_unusable"):
            self.client(lambda *_: self.fail("network"), KEY, TOK).call("device_info")

    def test_outer_handled_exception_does_not_hide_cleanup_failure(self):
        real = signal.setitimer
        def fail_disarm(which, seconds, interval=0):
            real(which, seconds, interval)
            if seconds == 0:
                raise OSError("PRIVATE_CLEANUP_ERROR")
        try:
            raise ValueError("already handled")
        except ValueError:
            with patch("signal.setitimer", side_effect=fail_disarm):
                with self.assertRaisesRegex(ProbeError, "timer_cleanup_failed"):
                    self.client(lambda body, timeout: sealed_reply(body), KEY, TOK).call("device_info")

    def test_timer_failures_stop_session_without_later_rpc(self):
        for code in ("timer_setup_failed", "timer_cleanup_failed", "timer_unusable",
                     "timer_owner_required", "timer_handler_in_use", "timer_already_in_use"):
            for failing_method in ("device_info", "screenshot"):
                client = FakeClient()
                client.allow_launch = True
                original = client.call
                def failing(method, params=None, timeout=None):
                    if method == failing_method:
                        client.calls.append((method, params))
                        raise ProbeError(code)
                    return original(method, params, timeout)
                client.call = failing
                with self.subTest(code=code, method=failing_method), tempfile.TemporaryDirectory() as folder:
                    report = new_report(3, time.monotonic_ns())
                    with contextlib.redirect_stdout(io.StringIO()):
                        collect(client, report, folder, time.monotonic_ns() + 5_000_000_000)
                    expected = ["device_info"] if failing_method == "device_info" else ["device_info", "launch_app", "screenshot"]
                    self.assertEqual(expected, [method for method, _ in client.calls])
                    self.assertEqual(code, report["stop_reason"])

    def test_arm_failure_poison_prevents_reuse(self):
        real = signal.setitimer
        def fail_arm(which, seconds, interval=0):
            if seconds:
                raise OSError("PRIVATE_TIMER_ERROR")
            return real(which, seconds, interval)
        with patch("signal.setitimer", side_effect=fail_arm):
            with self.assertRaisesRegex(ProbeError, "timer_setup_failed"):
                with self.timer.deadline(.1):
                    self.fail("entered")
        self.assertTrue(self.timer.diagnostics()["poisoned"])
        with self.assertRaisesRegex(ProbeError, "timer_unusable"):
            self.client(lambda *_: self.fail("network"), KEY, TOK).call("device_info")

    def test_cleanup_failure_poison_preserves_primary_interrupt(self):
        for primary in (KeyboardInterrupt, ValueError):
            with self.subTest(primary=primary.__name__):
                if self.timer.diagnostics()["poisoned"]:
                    self.timer.close()
                    self.timer = OwnedRpcTimer().__enter__()
                real = signal.setitimer
                def fail_cleanup(which, seconds, interval=0):
                    if seconds == 0:
                        raise OSError("PRIVATE_CLEANUP_ERROR")
                    return real(which, seconds, interval)
                with patch("signal.setitimer", side_effect=fail_cleanup):
                    with self.assertRaises(primary):
                        with self.timer.deadline(5):
                            raise primary()
                self.assertEqual("timer_cleanup_failed", self.timer.diagnostics()["cleanup_error"])
                self.assertTrue(self.timer.diagnostics()["poisoned"])
                with self.assertRaisesRegex(ProbeError, "timer_unusable"):
                    self.client(lambda *_: self.fail("network"), KEY, TOK).call("device_info")
                real(signal.ITIMER_REAL, 0)

    def test_cleanup_failure_after_success_is_fatal(self):
        real = signal.setitimer
        def fail_cleanup(which, seconds, interval=0):
            result = real(which, seconds, interval)
            if seconds == 0:
                raise OSError("PRIVATE_CLEANUP_ERROR")
            return result
        with patch("signal.setitimer", side_effect=fail_cleanup):
            with self.assertRaisesRegex(ProbeError, "timer_cleanup_failed"):
                self.client(lambda body, timeout: sealed_reply(body), KEY, TOK).call("device_info")
        with self.assertRaisesRegex(ProbeError, "timer_unusable"):
            self.client(lambda *_: self.fail("network"), KEY, TOK).call("device_info")

    def test_slow_headers_obey_total_deadline(self):
        def respond(handler, _body):
            for byte in b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n{}":
                handler.wfile.write(bytes([byte])); handler.wfile.flush(); time.sleep(.02)
        with LocalServer(respond) as port:
            started = time.monotonic()
            with self.assertRaisesRegex(ProbeError, "rpc_deadline"):
                self.client(HttpTransport(port), KEY, TOK, timeout=.15).call("device_info")
            self.assertLess(time.monotonic() - started, 1)

    def test_slow_crypto_times_out_before_network(self):
        crypto = Crypto(native=False)
        with patch.object(crypto, "xor", side_effect=lambda *_: time.sleep(.5)):
            with self.assertRaisesRegex(ProbeError, "rpc_deadline"):
                self.client(lambda *_: self.fail("network"), KEY, TOK, timeout=.15, crypto=crypto).call("device_info")

    def test_combined_crypto_transport_and_decrypt_share_one_deadline(self):
        crypto = Crypto(native=False)
        original = crypto.xor
        stages = []
        simulated = [100.0]
        def advance():
            # 同じ総期限を使う契約を、ホスト負荷や暗号処理の実行時間と分けて検査する。
            # 実SIGALRMの配送・低速HTTPの中断は隣接する実時間試験で扱う。
            simulated[0] += .08
            signal.getsignal(signal.SIGALRM)(signal.SIGALRM, None)
        def slow_xor(*args):
            stages.append("crypto"); advance(); return original(*args)
        def slow_transport(body, _timeout):
            stages.append("http"); advance(); return sealed_reply(body)
        with patch.object(crypto, "xor", side_effect=slow_xor), \
                patch("necroprobe.deadlines.time.monotonic", side_effect=lambda: simulated[0]), \
                patch("necroprobe.deadlines.signal.setitimer"):
            with self.assertRaisesRegex(ProbeError, "rpc_deadline"):
                self.client(slow_transport, KEY, TOK, crypto=crypto, timeout=.2).call("device_info")
        self.assertEqual(["crypto", "http", "crypto"], stages)

    def test_cli_identifies_no_web_ui_or_taps(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, "-m", "necroprobe", "capture", "--launch-game",
                                     "--python-crypto", "--token-store", folder + "/absent", "--output", folder,
                                     "--samples", "3", "--seconds", "5"], capture_output=True, text=True, timeout=8)
        self.assertEqual(2, result.returncode)
        self.assertIn("操作サイトは起動しません", result.stdout)
        self.assertIn("ゲームを続行", result.stdout)
        self.assertIn("押しません", result.stdout)


class TimerStartupTests(unittest.TestCase):
    def setUp(self):
        self.before = signal.getsignal(signal.SIGALRM)
        self.addCleanup(signal.signal, signal.SIGALRM, self.before)
        self.addCleanup(signal.setitimer, signal.ITIMER_REAL, 0)

    def test_foreign_or_unknown_handler_rejected_before_any_timer_change(self):
        for handler in (lambda *_: None, None):
            with self.subTest(handler=handler), patch("signal.getsignal", return_value=handler), patch("signal.setitimer") as setter:
                with self.assertRaisesRegex(ProbeError, "timer_handler_in_use"):
                    OwnedRpcTimer().__enter__()
                setter.assert_not_called()

    def test_owner_initialization_ignores_arbitrary_old_values(self):
        real = signal.setitimer
        with patch("signal.setitimer", side_effect=lambda *a: (real(*a), object())[1]):
            with OwnedRpcTimer() as owner:
                with owner.deadline(.1):
                    pass
        self.assertEqual(signal.SIG_IGN, signal.getsignal(signal.SIGALRM))

    def test_initial_disarm_failure_is_fixed_error(self):
        owner = OwnedRpcTimer()
        with patch("signal.setitimer", side_effect=OSError("PRIVATE_INIT_ERROR")):
            with self.assertRaisesRegex(ProbeError, "timer_setup_failed"):
                owner.__enter__()
        self.assertTrue(owner.diagnostics()["poisoned"])
        self.assertEqual(signal.SIG_IGN, signal.getsignal(signal.SIGALRM))

    def test_interrupt_during_initialization_closes_owner_and_preserves_reason(self):
        owner = OwnedRpcTimer()
        real = signal.signal
        def interrupted(signum, handler):
            result = real(signum, handler)
            if callable(handler):
                raise KeyboardInterrupt()
            return result
        try:
            with patch("signal.signal", side_effect=interrupted):
                with self.assertRaises(KeyboardInterrupt):
                    owner.__enter__()
            self.assertTrue(owner.diagnostics()["closed"])
            self.assertTrue(owner.diagnostics()["poisoned"])
            self.assertEqual(signal.SIG_IGN, signal.getsignal(signal.SIGALRM))
        finally:
            owner.close()

    def test_handler_setup_failure_is_fixed_error(self):
        owner = OwnedRpcTimer()
        with patch("signal.signal", side_effect=ValueError("PRIVATE_HANDLER_ERROR")):
            with self.assertRaisesRegex(ProbeError, "timer_setup_failed"):
                owner.__enter__()
        self.assertTrue(owner.diagnostics()["poisoned"])

    def test_close_handler_failure_is_fatal_and_poisoned(self):
        owner = OwnedRpcTimer().__enter__()
        with patch("signal.signal", side_effect=ValueError("PRIVATE_CLOSE_ERROR")):
            with self.assertRaisesRegex(ProbeError, "timer_cleanup_failed"):
                owner.close()
        self.assertTrue(owner.diagnostics()["poisoned"])
        self.assertEqual("timer_cleanup_failed", owner.diagnostics()["cleanup_error"])
