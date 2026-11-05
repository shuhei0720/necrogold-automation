"""iSH syscall compatibility regressions. Host tests, never device acceptance."""
import base64
import contextlib
import io
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from necroprobe.crypto import Crypto, mac, python_xor
from necroprobe.protocol import Client, GAME, HttpTransport, deadline
from necroprobe.session import collect, new_report
from necroprobe.validation import ProbeError
from test_capture import picture, payload
from test_http_and_cli import LocalServer
from test_protocol import KEY, TOK, sealed_reply
from test_session import FakeClient

ROOT = Path(__file__).resolve().parents[1]


class TimerCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.old_handler = signal.getsignal(signal.SIGALRM)
        self.old_timer = signal.setitimer(signal.ITIMER_REAL, 0)

    def tearDown(self):
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, self.old_handler)
        signal.setitimer(signal.ITIMER_REAL, *self.old_timer)

    def test_getitimer_sigsys_fault_does_not_kill_rpc_child(self):
        result = subprocess.run([sys.executable, str(ROOT / "tests/fixtures/ish_timer_driver.py")],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(0, result.returncode, "getitimer caused child signal/exit: " + str(result.returncode))
        self.assertIn("authenticated_reply_received", result.stdout)

    def test_real_http_launch_capture_sequence_without_getitimer(self):
        methods = []
        params_seen = []
        raw = picture(color=(80, 90, 100))
        def respond(handler, body):
            envelope = json.loads(body)
            nonce = bytes.fromhex(envelope["nonce"])
            request = json.loads(python_xor(mac(KEY, b"loopctrl-v1|enc-req" + nonce), nonce,
                                           base64.b64decode(envelope["ct"])))
            methods.append(request["method"])
            params_seen.append(request["params"])
            result = payload(raw) if request["method"] == "screenshot" else {}
            response = sealed_reply(body, result=result)
            handler.send_response(200)
            handler.send_header("Content-Length", str(len(response)))
            handler.end_headers()
            handler.wfile.write(response)
        output = io.StringIO()
        with LocalServer(respond) as port, tempfile.TemporaryDirectory() as folder:
            client = Client(HttpTransport(port), KEY, TOK, allow_launch=True, crypto=Crypto(native=False))
            report = new_report(12, time.monotonic_ns())
            with patch("signal.getitimer", side_effect=AssertionError("unsupported syscall")), contextlib.redirect_stdout(output):
                collect(client, report, folder, time.monotonic_ns() + 5_000_000_000)
            self.assertEqual(["device_info", "launch_app"] + ["screenshot"] * 12 + ["device_info"], methods)
            self.assertEqual({"bundle_id": GAME}, params_seen[1])
            self.assertEqual(12, report["summary"]["complete"])
            self.assertFalse(report["events"][1]["game_visible_verified"])
            self.assertFalse(report["input_authorized"])
            self.assertEqual("not_passed", report["gate"]["P1"])
            saved_rows = [row for row in report["rows"] if "raw_file" in row]
            self.assertEqual(3, len(saved_rows))
            self.assertEqual({"jpeg_scale1", "jpeg_scale2", "png_scale1"}, {row["variant"] for row in saved_rows})
            for row in report["rows"]:
                if "raw_file" in row:
                    self.assertEqual(raw, (Path(folder) / row["raw_file"]).read_bytes())
            self.assertEqual(report, json.loads((Path(folder) / "report.json").read_text()))
        self.assertIn("ゲームの起動要求を送ります", output.getvalue())
        self.assertIn("表示の成功は未確認", output.getvalue())

    def test_arm_failure_restores_handler_and_does_not_enter_body(self):
        real = signal.setitimer
        def fail_arm(which, seconds, interval=0):
            if seconds:
                raise OSError("timer unsupported")
            return real(which, seconds, interval)
        with patch("signal.setitimer", side_effect=fail_arm):
            with self.assertRaises(ProbeError) as caught:
                with deadline(.2):
                    self.fail("must not proceed without deadline")
        self.assertEqual("timer_setup_failed", caught.exception.code)
        self.assertEqual(self.old_handler, signal.getsignal(signal.SIGALRM))
        self.assertEqual((0, 0), signal.setitimer(signal.ITIMER_REAL, 0))

    def test_cleanup_failure_still_restores_handler(self):
        real = signal.setitimer
        armed = []
        def fail_cleanup(which, seconds, interval=0):
            result = real(which, seconds, interval)
            if seconds:
                armed.append(True)
            elif armed:
                raise OSError("synthetic cleanup failure after disarm")
            return result
        with patch("signal.setitimer", side_effect=fail_cleanup):
            with self.assertRaises(ProbeError) as caught:
                with deadline(.2):
                    pass
        self.assertEqual("timer_cleanup_failed", caught.exception.code)
        self.assertEqual(self.old_handler, signal.getsignal(signal.SIGALRM))

    def test_existing_periodic_timer_restored_and_rpc_refused(self):
        calls = []
        signal.signal(signal.SIGALRM, signal.SIG_IGN)
        signal.setitimer(signal.ITIMER_REAL, 5, 2)
        try:
            client = Client(lambda *args: calls.append(args), KEY, TOK, crypto=Crypto(native=False))
            with patch("signal.getitimer", side_effect=AssertionError("unsupported syscall")):
                with self.assertRaisesRegex(ProbeError, "timer_already_in_use"):
                    client.call("device_info")
            remaining, interval = signal.setitimer(signal.ITIMER_REAL, 0)
            self.assertGreater(remaining, 4)
            self.assertLessEqual(remaining, 5)
            self.assertEqual(2, interval)
            self.assertEqual(signal.SIG_IGN, signal.getsignal(signal.SIGALRM))
            self.assertEqual([], calls)
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)

    def test_nested_deadline_refused_without_disabling_outer_timeout(self):
        start = time.monotonic()
        with self.assertRaisesRegex(ProbeError, "rpc_deadline"):
            with deadline(.15):
                with self.assertRaisesRegex(ProbeError, "timer_already_in_use"):
                    with deadline(1):
                        self.fail("nested deadline must not enter")
                time.sleep(.5)
        self.assertLess(time.monotonic() - start, .4)
        self.assertEqual(self.old_handler, signal.getsignal(signal.SIGALRM))

    def test_existing_timer_restoration_subtracts_elapsed_time_and_never_disarms_due_timer(self):
        for delay, expected in ((1.0, .75), (.1, .000001)):
            with self.subTest(delay=delay), patch("signal.setitimer", side_effect=[(delay, 2.0), (0, 0)]) as timer:
                with patch("necroprobe.protocol.time.monotonic", side_effect=[100.0, 100.25]):
                    with self.assertRaisesRegex(ProbeError, "timer_already_in_use"):
                        with deadline(1):
                            self.fail("must refuse existing timer")
                self.assertEqual(2, timer.call_count)
                self.assertEqual((signal.ITIMER_REAL, expected, 2.0), timer.call_args.args)

    def test_slow_headers_obey_total_deadline(self):
        def respond(handler, _body):
            for byte in b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\n{}":
                handler.wfile.write(bytes([byte]))
                handler.wfile.flush()
                time.sleep(.02)
        with LocalServer(respond) as port:
            start = time.monotonic()
            with self.assertRaisesRegex(ProbeError, "rpc_deadline"):
                Client(HttpTransport(port), KEY, TOK, timeout=.15, crypto=Crypto(native=False)).call("device_info")
            self.assertLess(time.monotonic() - start, 1)

    def test_slow_crypto_times_out_before_network(self):
        crypto = Crypto(native=False)
        calls = []
        with patch.object(crypto, "xor", side_effect=lambda *_: time.sleep(.5)):
            start = time.monotonic()
            with self.assertRaisesRegex(ProbeError, "rpc_deadline"):
                Client(lambda *args: calls.append(args), KEY, TOK, timeout=.15, crypto=crypto).call("device_info")
            self.assertLess(time.monotonic() - start, .4)
        self.assertEqual([], calls)

    def test_body_exception_clears_timer_and_restores_handler(self):
        with self.assertRaisesRegex(ValueError, "synthetic"):
            with deadline(.5):
                raise ValueError("synthetic")
        self.assertEqual((0, 0), signal.setitimer(signal.ITIMER_REAL, 0))
        self.assertEqual(self.old_handler, signal.getsignal(signal.SIGALRM))

    def test_initial_timer_query_failure_is_safe_and_sends_nothing(self):
        calls = []
        with patch("signal.setitimer", side_effect=OSError("PRIVATE_TIMER_ERROR")):
            with self.assertRaisesRegex(ProbeError, "timer_setup_failed"):
                Client(lambda *args: calls.append(args), KEY, TOK, crypto=Crypto(native=False)).call("device_info")
        self.assertEqual([], calls)
        self.assertEqual(self.old_handler, signal.getsignal(signal.SIGALRM))

    def test_existing_timer_restore_failure_is_fatal_and_sends_nothing(self):
        calls = []
        with patch("signal.setitimer", side_effect=[(2.0, 1.0), OSError("PRIVATE_RESTORE_ERROR")]):
            with self.assertRaisesRegex(ProbeError, "timer_restore_failed"):
                Client(lambda *args: calls.append(args), KEY, TOK, crypto=Crypto(native=False)).call("device_info")
        self.assertEqual([], calls)
        self.assertEqual(self.old_handler, signal.getsignal(signal.SIGALRM))

    def test_handler_restore_failure_cannot_report_success(self):
        real = signal.signal
        count = []
        def fail_restore(sig, handler):
            count.append(handler)
            if len(count) == 2:
                raise OSError("PRIVATE_HANDLER_ERROR")
            return real(sig, handler)
        with patch("signal.signal", side_effect=fail_restore):
            with self.assertRaisesRegex(ProbeError, "timer_cleanup_failed"):
                with deadline(.5):
                    pass
        self.assertEqual((0, 0), signal.setitimer(signal.ITIMER_REAL, 0))

    def test_unknown_handler_refuses_before_timer_or_transport(self):
        calls = []
        with patch("signal.getsignal", return_value=None), patch("signal.setitimer") as timer:
            with self.assertRaisesRegex(ProbeError, "timer_handler_unknown"):
                Client(lambda *args: calls.append(args), KEY, TOK, crypto=Crypto(native=False)).call("device_info")
        timer.assert_not_called()
        self.assertEqual([], calls)

    def test_handler_install_failure_refuses_before_transport(self):
        calls = []
        with patch("signal.signal", side_effect=ValueError("PRIVATE_HANDLER_ERROR")):
            with self.assertRaisesRegex(ProbeError, "timer_setup_failed"):
                Client(lambda *args: calls.append(args), KEY, TOK, crypto=Crypto(native=False)).call("device_info")
        self.assertEqual([], calls)
        self.assertEqual((0, 0), signal.setitimer(signal.ITIMER_REAL, 0))

    def test_cleanup_failing_before_disarm_stops_after_one_rpc(self):
        real = signal.setitimer
        armed = []
        calls = []
        output = io.StringIO()
        signal.signal(signal.SIGALRM, signal.SIG_IGN)
        def fail_cleanup(which, seconds, interval=0):
            if seconds:
                armed.append(True)
            elif armed:
                raise OSError("PRIVATE_BEFORE_DISARM_ERROR")
            return real(which, seconds, interval)
        def respond(body, _timeout):
            calls.append(body)
            return sealed_reply(body)
        with tempfile.TemporaryDirectory() as folder:
            client = Client(respond, KEY, TOK, timeout=5, allow_launch=True, crypto=Crypto(native=False))
            report = new_report(3, time.monotonic_ns())
            with patch("signal.setitimer", side_effect=fail_cleanup), contextlib.redirect_stdout(output):
                collect(client, report, folder, time.monotonic_ns() + 5_000_000_000)
            self.assertEqual(signal.SIG_IGN, signal.getsignal(signal.SIGALRM))
            self.assertGreater(real(signal.ITIMER_REAL, 0)[0], 0)
            self.assertEqual(1, len(calls))
            self.assertEqual("timer_cleanup_failed", report["stop_reason"])
            self.assertEqual(3, report["summary"]["not_started"])
            self.assertNotIn("PRIVATE_BEFORE_DISARM_ERROR", json.dumps(report) + output.getvalue())

    def test_timer_failures_stop_session_before_launch_or_more_captures(self):
        for code in ("timer_setup_failed", "timer_restore_failed", "timer_cleanup_failed", "timer_handler_unknown"):
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

    def test_keyboard_interrupt_clears_timer_and_restores_handler(self):
        with self.assertRaises(KeyboardInterrupt):
            with deadline(.5):
                raise KeyboardInterrupt()
        self.assertEqual((0, 0), signal.setitimer(signal.ITIMER_REAL, 0))
        self.assertEqual(self.old_handler, signal.getsignal(signal.SIGALRM))

    def test_combined_crypto_and_transport_share_one_deadline(self):
        crypto = Crypto(native=False)
        original = crypto.xor
        stages = []
        def slow_xor(*args):
            stages.append("crypto")
            time.sleep(.08)
            return original(*args)
        def slow_transport(body, _timeout):
            stages.append("http")
            time.sleep(.08)
            return sealed_reply(body)
        with patch.object(crypto, "xor", side_effect=slow_xor):
            with self.assertRaisesRegex(ProbeError, "rpc_deadline"):
                Client(slow_transport, KEY, TOK, crypto=crypto, timeout=.2).call("device_info")
        self.assertEqual(["crypto", "http", "crypto"], stages)

    def test_cli_explicitly_identifies_no_web_ui_or_taps(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, "-m", "necroprobe", "capture", "--launch-game",
                                     "--python-crypto", "--token-store", folder + "/absent", "--output", folder,
                                     "--samples", "3", "--seconds", "5"],
                                    capture_output=True, text=True, timeout=8)
        self.assertEqual(2, result.returncode)
        self.assertIn("操作サイトは起動しません", result.stdout)
        self.assertIn("ゲームを続行", result.stdout)
        self.assertIn("押しません", result.stdout)
