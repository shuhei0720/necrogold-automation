import contextlib
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from necroprobe.protocol import RpcReply
from necroprobe.session import write_report, collect, durations, finish, new_report, safe_info, stats, summarize, VARIANTS
from necroprobe.validation import ProbeError
from test_capture import picture, payload


class FakeClient:
    timeout = 1
    allow_launch = False
    def __init__(self, mode="ok", raw=None):
        self.raw = raw
        self.mode = mode
        self.calls = []
    def call(self, method, params=None, timeout=None):
        self.calls.append((method, params))
        now = time.monotonic_ns()
        if method == "device_info":
            return RpcReply({"private": "DO_NOT_LOG", "system": {"foreground_app": "com.other.private"}}, {})
        if self.mode == "jpeg_bad" and params["format"] == "jpeg":
            raise ProbeError("rpc_error")
        if self.mode == "connection":
            raise ProbeError("connection_error")
        if self.mode == "fatal":
            raise ProbeError("response_mac_mismatch")
        if self.mode == "interrupt":
            raise KeyboardInterrupt()
        raw = self.raw if self.raw is not None else picture(color=(0, 0, 0) if self.mode == "black" else (255, 255, 255))
        return RpcReply(payload(raw), {"request_start_ns": now, "response_end_ns": time.monotonic_ns(), "crypto_engine": "test"})


class SessionTests(unittest.TestCase):
    def run_probe(self, client, count=12):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            report = new_report(count, time.monotonic_ns())
            collect(client, report, folder, time.monotonic_ns() + 5_000_000_000)
            files = list(Path(folder).glob("*.png"))
            saved = json.loads((Path(folder) / "report.json").read_text())
            self.assertEqual(report, saved)
            return report, len(files)

    def test_failures_and_unstarted_trials_stay_in_denominator(self):
        rows = [{"status": "complete", "variant": "jpeg_scale1"},
                {"status": "error", "variant": "jpeg_scale2"},
                {"status": "not_started", "variant": "png_scale1"}]
        result = summarize(rows, 3_000_000_000)
        self.assertAlmostEqual(1 / 3, result["completion_fraction"])
        self.assertEqual(1, result["not_started"])
        self.assertIsNone(result["fresh_observations_hz"])

    def test_interleaving_all_conditions_and_raw_files_per_condition(self):
        client = FakeClient()
        report, images = self.run_probe(client)
        self.assertEqual([VARIANTS[i % 3][1] for i in range(12)], [p for m, p in client.calls if m == "screenshot"])
        self.assertEqual(3, images)
        self.assertEqual(12, report["summary"]["complete"])
        self.assertEqual("not_passed", report["gate"]["P1"])
        self.assertFalse(report["input_authorized"])
        self.assertNotIn("DO_NOT_LOG", json.dumps(report))
        self.assertNotIn("com.other.private", json.dumps(report))

    def test_identical_frames_are_not_declared_stale(self):
        report, _ = self.run_probe(FakeClient())
        self.assertTrue(report["rows"][1]["image"]["same_bytes_as_previous"])
        self.assertFalse(report["rows"][1]["image"]["freshness_verified"])
        self.assertEqual("complete", report["rows"][1]["status"])

    def test_black_frames_complete_diagnostics_without_becoming_game_frames(self):
        report, images = self.run_probe(FakeClient("black"))
        self.assertEqual(12, report["summary"]["complete"])
        self.assertEqual(3, images)
        self.assertTrue(all(row["image"]["image_status"] == "blank_or_dark" for row in report["rows"]))

    def test_jpeg_failure_does_not_prevent_png_observation(self):
        report, _ = self.run_probe(FakeClient("jpeg_bad"), 18)
        self.assertEqual(6, report["summary"]["complete"])
        self.assertEqual(6, report["summary"]["errors"])
        self.assertEqual(6, report["summary"]["not_started"])
        self.assertEqual(6, report["summary"]["groups"]["png_scale1"]["counts"]["complete"])

    def test_authenticated_failure_stops_without_retry(self):
        client = FakeClient("fatal")
        report, _ = self.run_probe(client)
        self.assertEqual(1, len([m for m, _ in client.calls if m == "screenshot"]))
        self.assertEqual("response_mac_mismatch", report["stop_reason"])
        self.assertEqual(11, report["summary"]["not_started"])

    def test_ctrl_c_preserves_partial_report(self):
        report, _ = self.run_probe(FakeClient("interrupt"))
        self.assertEqual("user_interrupt", report["stop_reason"])
        self.assertEqual(1, report["summary"]["interrupted"])
        self.assertEqual(11, report["summary"]["not_started"])

    def test_expired_session_makes_no_network_calls(self):
        client = FakeClient()
        with tempfile.TemporaryDirectory() as folder:
            report = new_report(3, 0)
            collect(client, report, folder, 1, clock=lambda: 1)
        self.assertEqual([], client.calls)
        self.assertEqual("session_deadline", report["stop_reason"])

    def test_fixed_timestamp_durations_do_not_overlap_save_and_decode(self):
        row = {"timings": {"request_start_ns": 0, "http_start_ns": 1_000_000,
                            "http_end_ns": 11_000_000, "decrypt_start_ns": 13_000_000,
                            "decrypt_end_ns": 16_000_000, "decode_start_ns": 20_000_000,
                            "decode_end_ns": 24_000_000, "inspect_end_ns": 26_000_000,
                            "save_start_ns": 26_000_000, "save_end_ns": 32_000_000}}
        result = durations(row)
        self.assertEqual(10, result["http_roundtrip"])
        self.assertEqual(4, result["image_decode"])
        self.assertEqual(6, result["raw_save"])
        self.assertEqual(26, result["capture_to_inspected"])

    def test_p95_small_samples_and_missing_values(self):
        self.assertEqual(10, stats([1, 2, 10])["p95_ms"])
        self.assertEqual(2, stats([1, 2, 10])["median_ms"])
        self.assertIsNone(stats([])["p95_ms"])

    def test_killed_worker_marks_inflight_interrupted(self):
        report = new_report(3, 0)
        report["rows"][0]["status"] = "in_progress"
        finish(report, 10, "session_deadline")
        self.assertEqual(1, report["summary"]["interrupted"])
        self.assertEqual(2, report["summary"]["not_started"])

    def test_three_connection_errors_stop_all_conditions(self):
        client = FakeClient("connection")
        report, _ = self.run_probe(client)
        self.assertEqual(3, len([m for m, _ in client.calls if m == "screenshot"]))
        self.assertEqual("connection_failure_limit", report["stop_reason"])

    def test_stale_temporary_report_does_not_prevent_finalization(self):
        with tempfile.TemporaryDirectory() as folder:
            report = new_report(3, 0)
            write_report(folder, report)
            (Path(folder) / "report.json.tmp").write_text("left by terminated worker")
            finish(report, 10, "session_deadline")
            write_report(folder, report)
            saved = json.loads((Path(folder) / "report.json").read_text())
            self.assertEqual("session_deadline", saved["stop_reason"])

    def test_save_failure_preserves_original_fatal_reason(self):
        with tempfile.TemporaryDirectory() as folder:
            report = new_report(3, time.monotonic_ns())
            failed = []
            def fail_once_after_error(destination, current):
                if current["rows"][0].get("error") == "response_mac_mismatch" and not failed:
                    failed.append(True)
                    raise OSError("synthetic disk failure")
                return write_report(destination, current)
            with patch("necroprobe.session.write_report", side_effect=fail_once_after_error):
                collect(FakeClient("fatal"), report, folder, time.monotonic_ns() + 5_000_000_000)
            saved = json.loads((Path(folder) / "report.json").read_text())
            self.assertEqual("response_mac_mismatch", saved["stop_reason"])
            self.assertEqual("output_write_failed", saved["output_error"])

    def test_raw_files_are_exact_received_bytes(self):
        expected = (Path(__file__).resolve().parents[1] / "analysis/manual-video-2/frames/002000-pause.jpg").read_bytes()
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            report = new_report(3, time.monotonic_ns())
            collect(FakeClient(raw=expected), report, folder, time.monotonic_ns() + 5_000_000_000)
            for row in report["rows"]:
                self.assertEqual(expected, (Path(folder) / row["raw_file"]).read_bytes())

    def test_supervisor_reason_does_not_overwrite_primary_failure(self):
        report = new_report(3, 0)
        report.update(status="stopped", stop_reason="response_mac_mismatch", output_error="output_write_failed")
        finish(report, 10, "worker_failed")
        self.assertEqual("response_mac_mismatch", report["stop_reason"])
        self.assertEqual("worker_failed", report["termination_reason"])
        self.assertEqual("output_write_failed", report["output_error"])

    def test_save_failure_after_interrupt_keeps_interrupt_reason(self):
        with tempfile.TemporaryDirectory() as folder:
            report = new_report(3, time.monotonic_ns())
            failed = []
            def fail_once(destination, current):
                if current.get("stop_reason") == "user_interrupt" and not failed:
                    failed.append(True)
                    raise OSError("synthetic disk failure")
                write_report(destination, current)
            with patch("necroprobe.session.write_report", side_effect=fail_once):
                collect(FakeClient("interrupt"), report, folder, time.monotonic_ns() + 5_000_000_000)
            self.assertEqual("user_interrupt", report["stop_reason"])
            self.assertEqual("output_write_failed", report["output_error"])
