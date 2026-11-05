"""Real processes and authenticated local HTTP; not iPhone/game acceptance."""
import base64
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from necroprobe.crypto import mac, python_xor
from necroprobe.protocol import GAME
from test_capture import picture, payload
from test_http_and_cli import LocalServer
from test_protocol import KEY, sealed_reply

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "tests/fixtures/owned_timer_driver.py"


class OwnedWorkerTests(unittest.TestCase):
    def run_worker(self, mode):
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
        with LocalServer(respond) as port, tempfile.TemporaryDirectory() as folder:
            process = subprocess.run([sys.executable, str(DRIVER), mode, str(port), folder],
                                     capture_output=True, text=True, timeout=15)
            report_file = next(Path(folder).glob("probe-*/report.json"))
            report = json.loads(report_file.read_text())
            self.assertNotIn("PRIVATE_TIMER_ERROR", process.stdout + process.stderr + json.dumps(report))
            self.assertFalse(report["input_authorized"])
            self.assertEqual("not_passed", report["gate"]["P1"])
            self.assertTrue(report["worker"]["report_read_ok"])
            self.assertEqual(0, report["worker"]["process"]["returncode"])
            self.assertEqual("owned_itimer_real", report["timer"]["backend"])
            self.assertTrue(report["timer"]["closed"])
            if mode == "success":
                self.assertEqual(0, process.returncode, process.stdout + process.stderr)
                self.assertEqual(["device_info", "launch_app"] + ["screenshot"] * 12 + ["device_info"], methods)
                self.assertEqual({"bundle_id": GAME}, params_seen[1])
                self.assertEqual(12, report["summary"]["complete"])
                self.assertFalse(report["timer"]["poisoned"])
                self.assertIsNone(report["timer"]["cleanup_error"])
                saved = [row for row in report["rows"] if "raw_file" in row]
                self.assertEqual(3, len(saved))
                for row in saved:
                    self.assertEqual(images[row["image"]["format"].lower()],
                                     (report_file.parent / row["raw_file"]).read_bytes())
                self.assertFalse(report["events"][1]["game_visible_verified"])
            else:
                self.assertEqual(2, process.returncode, process.stdout + process.stderr)
                self.assertEqual([], methods)
                self.assertEqual(12, report["summary"]["not_started"])
                self.assertTrue(report["timer"]["poisoned"])
                self.assertEqual("timer_cleanup_failed", report["timer"]["cleanup_error"])
            return report

    def test_real_parent_child_12_captures_with_unreadable_old_values(self):
        self.run_worker("success")

    def test_initialization_failure_is_recorded_before_any_http(self):
        report = self.run_worker("init_failure")
        self.assertEqual("timer_initialize", report["worker"]["stage"])
        self.assertEqual("timer_setup_failed", report["stop_reason"])

    def test_interrupt_remains_primary_when_cleanup_also_fails(self):
        report = self.run_worker("interrupt_cleanup")
        self.assertEqual("capture_collection", report["worker"]["stage"])
        self.assertEqual("user_interrupt", report["stop_reason"])
