"""Return codes and checkpoints must survive failures outside Python exceptions."""
import errno
import contextlib
import io
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from necroprobe import __main__ as cli
from necroprobe.__main__ import supervise
from necroprobe.session import new_report, write_report

ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT / "tests/fixtures/worker_failure_driver.py"


class WorkerDiagnosticsTests(unittest.TestCase):
    def test_nonzero_exit_keeps_exact_code_without_logging_stderr(self):
        info = {}
        reason = supervise([sys.executable, "-c", "import sys; sys.stderr.write('PRIVATE_TEST_SECRET'); sys.exit(23)"], 3, info)
        self.assertEqual("worker_failed", reason)
        self.assertEqual(23, info.get("returncode"))
        self.assertIsNone(info["signal_number"])
        self.assertNotIn("PRIVATE_TEST_SECRET", json.dumps(info))

    def test_success_keeps_zero_returncode(self):
        info = {}
        self.assertIsNone(supervise([sys.executable, "-c", "pass"], 3, info))
        self.assertEqual(0, info.get("returncode"))
        self.assertIsNone(info["signal_number"])

    def test_signal_exit_keeps_number_and_name(self):
        info = {}
        code = "import os,signal; os.kill(os.getpid(),signal.SIGTERM)"
        self.assertEqual("worker_failed", supervise([sys.executable, "-c", code], 3, info))
        self.assertEqual(-signal.SIGTERM, info.get("returncode"))
        self.assertEqual(signal.SIGTERM, info["signal_number"])
        self.assertEqual("SIGTERM", info["signal_name"])

    def test_spawn_failure_is_not_misreported_as_output_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            info = {}
            reason = supervise([str(Path(folder) / "missing-executable")], 3, info)
        self.assertEqual("worker_start_failed", reason)
        self.assertEqual(errno.ENOENT, info["spawn_errno"])
        self.assertIsNone(info["returncode"])

    def run_child_failure(self, mode):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, str(DRIVER), mode, folder],
                                    capture_output=True, text=True, timeout=8)
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            report = json.loads(next(Path(folder).glob("probe-*/report.json")).read_text())
            self.assertEqual("crypto_initialize", report.get("worker", {}).get("stage"))
            self.assertEqual(0, report["summary"]["complete"])
            self.assertEqual(3, report["summary"]["not_started"])
            self.assertFalse(report["input_authorized"])
            self.assertEqual("not_passed", report["gate"]["P1"])
            self.assertNotIn("PRIVATE_FIXTURE_SECRET", result.stdout + result.stderr + json.dumps(report))
            return report

    def test_native_style_crash_keeps_last_checkpoint_in_final_report(self):
        report = self.run_child_failure("signal")
        self.assertEqual("worker_failed", report["stop_reason"])
        self.assertEqual(-signal.SIGSEGV, report["worker"]["process"]["returncode"])
        self.assertEqual("SIGSEGV", report["worker"]["process"]["signal_name"])

    def test_python_failure_keeps_safe_type_and_primary_reason(self):
        report = self.run_child_failure("exception")
        self.assertEqual("internal_error", report["stop_reason"])
        self.assertEqual("ValueError", report["worker"]["exception_type"])
        self.assertEqual(0, report["worker"]["process"]["returncode"])

    def test_unknown_exception_class_is_not_exposed(self):
        report = self.run_child_failure("custom")
        self.assertEqual("Exception", report["worker"]["exception_type"])

    def test_oserror_in_initialization_is_not_output_error(self):
        report = self.run_child_failure("oserror")
        self.assertEqual("internal_error", report["stop_reason"])
        self.assertEqual("OSError", report["worker"]["exception_type"])
        self.assertNotIn("output_error", report)

    def test_unreadable_report_and_nonzero_exit_are_both_recorded(self):
        with tempfile.TemporaryDirectory() as folder:
            result = subprocess.run([sys.executable, str(DRIVER), "corrupt_report", folder],
                                    capture_output=True, text=True, timeout=8)
            self.assertEqual(2, result.returncode)
            report = json.loads(next(Path(folder).glob("probe-*/report.json")).read_text())
            self.assertEqual("worker_failed", report["stop_reason"])
            self.assertEqual(23, report["worker"]["process"]["returncode"])
            self.assertFalse(report["worker"]["report_read_ok"])
            self.assertEqual("report_read_failed", report["worker"]["report_read_error"])
            self.assertIn("件数は開始時の予定", result.stdout)
            self.assertNotIn("PRIVATE_FIXTURE_SECRET", result.stdout + result.stderr + json.dumps(report))

    def test_child_initial_report_failure_has_reserved_code_and_safe_message(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / "report.json").write_text("PRIVATE_FIXTURE_SECRET")
            args = cli.parser().parse_args(["capture", "--worker", "--output", folder])
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = cli.worker(args)
            self.assertEqual(cli.WORKER_REPORT_READ_EXIT, code)
            self.assertIn("worker_report_read_failed", output.getvalue())
            self.assertNotIn("PRIVATE_FIXTURE_SECRET", output.getvalue())

    def test_structurally_invalid_parent_report_keeps_process_result(self):
        for index in range(4):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as folder:
                result = subprocess.run([sys.executable, str(DRIVER), "invalid_structure_" + str(index), folder],
                                        capture_output=True, text=True, timeout=8)
                self.assertEqual(2, result.returncode, result.stdout + result.stderr)
                report = json.loads(next(Path(folder).glob("probe-*/report.json")).read_text())
                self.assertEqual(23, report["worker"]["process"]["returncode"])
                self.assertFalse(report["worker"]["report_read_ok"])
                self.assertEqual("report_read_failed", report["worker"]["report_read_error"])

    def test_structurally_invalid_child_report_uses_reserved_code(self):
        bad_fields = [{}, {"rows": []}, {"worker": []}, {"start_ns": "bad"},
                      {"rows": [None]}, {"events": [None]}, {"status": "PRIVATE_FIXTURE_SECRET"}]
        for update in bad_fields:
            with self.subTest(update=update), tempfile.TemporaryDirectory() as folder:
                report = new_report(3, 0)
                report["worker"] = {"stage": "spawn_requested"}
                if update:
                    report.update(update)
                else:
                    report = {}
                (Path(folder) / "report.json").write_text(json.dumps(report))
                args = cli.parser().parse_args(["capture", "--worker", "--output", folder, "--samples", "3"])
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = cli.worker(args)
                self.assertEqual(cli.WORKER_REPORT_READ_EXIT, code)
                self.assertNotIn("PRIVATE_FIXTURE_SECRET", output.getvalue())

    def test_each_checkpoint_failure_prevents_the_next_operation(self):
        phases = ["pairing_load", "crypto_initialize", "timer_initialize", "capture_collection"]
        previous = ["spawn_requested", "pairing_load", "crypto_initialize", "timer_initialize"]
        for index, phase in enumerate(phases):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as folder:
                report = new_report(3, 0)
                report["worker"] = {"stage": "spawn_requested"}
                write_report(folder, report)
                def fail_at_stage(destination, current):
                    if current["worker"]["stage"] == phase:
                        raise OSError("PRIVATE_FIXTURE_SECRET_SAVE")
                    write_report(destination, current)
                args = cli.parser().parse_args(["capture", "--worker", "--output", folder, "--samples", "3"])
                with patch.object(cli, "write_report", side_effect=fail_at_stage), \
                     patch.object(cli, "load_pairing", return_value=(b"key", "tok")) as pairing, \
                     patch.object(cli, "Crypto") as crypto, \
                     patch.object(cli, "Client") as client, \
                     patch.object(cli, "collect") as collect:
                    crypto.return_value.engine = "test"
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        cli.worker(args)
                saved = json.loads((Path(folder) / "report.json").read_text())
                self.assertEqual("output_write_failed", saved["stop_reason"])
                self.assertEqual(previous[index], saved["worker"]["stage"])
                self.assertEqual(phase, saved["worker"]["checkpoint_error"])
                self.assertEqual(3, saved["summary"]["not_started"])
                self.assertEqual(index > 0, pairing.called)
                self.assertEqual(index > 1, crypto.called)
                self.assertFalse(collect.called)
                self.assertNotIn("PRIVATE_FIXTURE_SECRET", output.getvalue() + json.dumps(saved))

