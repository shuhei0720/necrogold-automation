"""Real parent+worker lifecycle with test-only blocking adapters, no iPhone claims."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "tests/fixtures/stop_driver.py"


class StopIntegrationTests(unittest.TestCase):
    def check_stop(self, phase, mode):
        with tempfile.TemporaryDirectory() as folder:
            seconds = "3" if mode == "deadline" else "15"
            process = subprocess.Popen([sys.executable, str(DRIVER), phase, folder, seconds],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                       start_new_session=True)
            try:
                marker = Path(folder) / "blocked.json"
                until = time.monotonic() + 5
                while not marker.exists() and process.poll() is None and time.monotonic() < until:
                    time.sleep(.01)
                self.assertTrue(marker.exists(), "Worker must reach the selected stage before testing stop")
                worker = json.loads(marker.read_text())
                if mode == "interrupt":
                    process.send_signal(signal.SIGINT)
                output, error = process.communicate(timeout=8)
                self.assertEqual(2, process.returncode, output + error)
                report = json.loads(next(Path(folder).glob("probe-*/report.json")).read_text())
                self.assertEqual("stopped", report["status"])
                self.assertEqual("session_deadline" if mode == "deadline" else "user_interrupt", report["stop_reason"])
                self.assertEqual(1, report["summary"]["complete"])
                self.assertEqual(1, report["summary"]["interrupted"])
                self.assertEqual(4, report["summary"]["not_started"])
                self.assertEqual(6, report["summary"]["planned"])
                self.assertFalse(report["input_authorized"])
                self.assertEqual("not_passed", report["gate"]["P1"])
                with self.assertRaises(ProcessLookupError):
                    os.kill(worker["pid"], 0)
            finally:
                # Cleanup covers the fixture's grandchildren even on assertion failure.
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.communicate(timeout=2)

    def test_deadline_during_rpc(self):
        self.check_stop("rpc", "deadline")

    def test_deadline_during_decode(self):
        self.check_stop("decode", "deadline")

    def test_deadline_during_save(self):
        self.check_stop("save", "deadline")

    def test_ctrl_c_during_rpc(self):
        self.check_stop("rpc", "interrupt")

    def test_ctrl_c_during_decode(self):
        self.check_stop("decode", "interrupt")

    def test_ctrl_c_during_save(self):
        self.check_stop("save", "interrupt")
