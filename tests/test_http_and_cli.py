import contextlib
import io
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest

from necroprobe.__main__ import supervise
from necroprobe.crypto import Crypto
from necroprobe.protocol import HttpTransport
from necroprobe.validation import MAX_HTTP, ProbeError
from test_protocol import KEY, TOK, sealed_reply
from timer_support import TimerTestCase


class LocalServer:
    def __init__(self, behavior):
        self.behavior = behavior
    def __enter__(self):
        behavior = self.behavior
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass
            def do_POST(self):
                data = self.rfile.read(int(self.headers["Content-Length"]))
                try:
                    behavior(self, data)
                except (BrokenPipeError, ConnectionResetError):
                    pass
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=.01), daemon=True)
        self.thread.start()
        return self.server.server_port
    def __exit__(self, *_):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=1)


class HttpTests(TimerTestCase):
    def test_real_local_http_encrypted_exchange(self):
        def respond(handler, body):
            raw = sealed_reply(body, result={"local_test": True})
            handler.send_response(200)
            handler.send_header("Content-Length", str(len(raw)))
            handler.end_headers()
            handler.wfile.write(raw)
        with LocalServer(respond) as port:
            reply = self.client(HttpTransport(port), KEY, TOK, crypto=Crypto(native=False)).call("device_info")
            self.assertTrue(reply.result["local_test"])

    def test_redirect_and_oversized_content_length_rejected(self):
        for status in (302, 200):
            def respond(handler, body):
                handler.send_response(status)
                handler.send_header("Location", "http://127.0.0.1:1/never")
                handler.send_header("Content-Length", str(MAX_HTTP + 1))
                handler.end_headers()
            with self.subTest(status=status), LocalServer(respond) as port:
                with self.assertRaises(ProbeError):
                    self.client(HttpTransport(port), KEY, TOK).call("device_info")

    def test_slow_drip_has_total_deadline_not_just_read_timeout(self):
        def respond(handler, body):
            handler.send_response(200)
            handler.send_header("Content-Length", "100")
            handler.end_headers()
            for _ in range(100):
                handler.wfile.write(b"x")
                handler.wfile.flush()
                time.sleep(.02)
        with LocalServer(respond) as port:
            started = time.monotonic()
            with self.assertRaisesRegex(ProbeError, "rpc_deadline"):
                self.client(HttpTransport(port), KEY, TOK, timeout=.15).call("device_info")
            self.assertLess(time.monotonic() - started, 1)

    def test_owned_handler_remains_after_rpc_timeout(self):
        before = signal.getsignal(signal.SIGALRM)
        with self.assertRaisesRegex(ProbeError, "rpc_deadline"):
            with self.timer.deadline(.01):
                time.sleep(.1)
        self.assertEqual(before, signal.getsignal(signal.SIGALRM))
        self.assertEqual((0, 0), signal.getitimer(signal.ITIMER_REAL))

    def test_worker_deadline_kills_process_ignoring_term(self):
        code = "import signal,time; signal.signal(signal.SIGTERM,signal.SIG_IGN); time.sleep(10)"
        start = time.monotonic()
        reason = supervise([sys.executable, "-c", code], .15)
        self.assertEqual("session_deadline", reason)
        self.assertLess(time.monotonic() - start, 2)

    def test_missing_pairing_returns_report_and_nonzero_without_network(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, "-m", "necroprobe", "capture", "--token-store", str(Path(folder) / "absent"),
                                     "--output", folder, "--samples", "3", "--seconds", "5"], capture_output=True, text=True, timeout=8)
            self.assertEqual(2, result.returncode)
            report = json.loads(next(Path(folder).glob("probe-*/report.json")).read_text())
            self.assertEqual("pairing_missing", report["stop_reason"])
            self.assertEqual(3, report["summary"]["not_started"])
            self.assertFalse(report["input_authorized"])
