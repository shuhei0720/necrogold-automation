#!/usr/bin/env python3
"""Bounded macOS GUI measurement; a successful measurement is not game E2E."""
from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
from datetime import datetime, timezone


SOURCE_FILES = (
    "tools/ci_game_capability_probe.py",
    "tools/ci_game_capability_probe.swift",
    ".github/workflows/ci-game-capability-probe.yml",
)
STAGES = ("compile", "runtime", "gui", "ownership", "capture", "input", "visual_change")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic_json(path, data):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def compiler_diagnostics(raw, source):
    """Normalize only diagnostics addressed to this one known source file."""
    pattern = re.compile(r"^(?:" + re.escape(str(source)) + "|" + re.escape(SOURCE_FILES[1])
                         + r"):(\d+):(\d+): (error|warning): (.*)$")
    diagnostics = []
    for line in raw.decode("utf-8", errors="replace").splitlines():
        match = pattern.fullmatch(line)
        if match:
            message = re.sub(r"(?<!\w)/(?:[^\s'\"<>]+)", "<path>", match[4])[:320]
            diagnostics.append({"source": SOURCE_FILES[1], "line": int(match[1]),
                                "column": int(match[2]), "severity": match[3], "message": message})
            if len(diagnostics) == 20:
                break
    return diagnostics


def clock_compatible(before_ns, swift_ns, after_ns):
    return type(swift_ns) is int and before_ns <= swift_ns <= after_ns


def assess(report):
    """Only independently agreeing positive evidence can produce a pass."""
    stages = report["stages"]
    sender = stages["input"].get("sender", {})
    receipts = stages["input"].get("receipts", {})
    images = stages["capture"].get("images", {})
    gui = stages["gui"]
    owner = stages["ownership"]
    before, after = images.get("before", {}), images.get("after", {})
    checks = {
        "source_commit_matches": report["lineage"].get("commit_matches") is True,
        "measurement_complete": report.get("measurement_complete") is True,
        "cleanup_complete": report.get("cleanup", {}).get("status") == "pass",
        "clock_compatible": report.get("clock", {}).get("status") == "pass",
        "stages_pass": all(stages[name]["status"] == "pass" for name in STAGES),
        "post_permission": report.get("capabilities", {}).get("post_event_preflight") is True,
        "own_frontmost_window": gui.get("frontmost_matches") is True
        and gui.get("is_key_window") is True and owner.get("nonce_matches") is True
        and owner.get("window_owner_matches") is True,
        "sender_ownership": sender.get("ownership_before", {}).get("owned") is True
        and sender.get("ownership_before", {}).get("frontmost_matches") is True
        and sender.get("ownership_after_down", {}).get("owned") is True,
        "sender_pair": sender.get("status") == "posted"
        and sender.get("key_down_posted") is True and sender.get("key_up_posted") is True
        and sender.get("pending_cleared") is True,
        "receipt_pair": receipts.get("key_down_delta") == 1 and receipts.get("key_up_delta") == 1,
        "draw_receipt": receipts.get("draw_delta", 0) > 0
        and receipts.get("before_color") == "red" and receipts.get("after_color") == "blue",
        "images_valid_and_fresh": all(
            images.get(name, {}).get("valid") is True
            and images.get(name, {}).get("fresh") is True
            and bool(images.get(name, {}).get("sha256")) for name in ("before", "after")
        ),
        "images_match_owned_window": all(
            images.get(name, {}).get("owner_pid") == gui.get("pid")
            and images.get(name, {}).get("window_id") == gui.get("window_id")
            and images.get(name, {}).get("owner_before") is True
            and images.get(name, {}).get("owner_after") is True for name in ("before", "after")
        ),
        "pixel_evidence": before.get("red_ratio", 0) >= 0.9 and before.get("blue_ratio", 1) <= 0.1
        and after.get("blue_ratio", 0) >= 0.9 and after.get("red_ratio", 1) <= 0.1
        and before.get("width_px") == after.get("width_px")
        and before.get("height_px") == after.get("height_px")
        and before.get("sha256") != after.get("sha256"),
        "red_to_blue": stages["visual_change"].get("red_to_blue") is True,
        "uninterrupted": report.get("interrupted") is False,
    }
    passed = all(checks.values())
    if passed:
        status = "pass"
    elif (all(checks[name] for name in ("source_commit_matches", "measurement_complete", "cleanup_complete",
                                       "clock_compatible", "post_permission", "own_frontmost_window",
                                       "sender_ownership", "images_valid_and_fresh", "images_match_owned_window",
                                       "sender_pair", "uninterrupted"))
          and all(stages[name]["status"] == "pass" for name in ("compile", "runtime", "gui", "ownership", "capture"))
          and (stages["input"]["status"] == "fail" or stages["visual_change"]["status"] == "fail"
               or not checks["receipt_pair"] or not checks["draw_receipt"] or not checks["pixel_evidence"])):
        status = "pipeline_fail"
    else:
        status = "unknown_or_blocked"
    return {"capability_pass": passed, "capability_status": status, "checks": checks,
            "game_e2e": False, "metal_command_execution_tested": False}


def self_test():
    good = {
        "lineage": {"commit_matches": True}, "interrupted": False, "measurement_complete": True,
        "cleanup": {"status": "pass"}, "clock": {"status": "pass"},
        "capabilities": {"post_event_preflight": True},
        "stages": {name: {"status": "pass"} for name in STAGES},
    }
    good["stages"]["input"].update(
        sender={"status": "posted", "key_down_posted": True, "key_up_posted": True, "pending_cleared": True,
                "ownership_before": {"owned": True, "frontmost_matches": True},
                "ownership_after_down": {"owned": True}},
        receipts={"key_down_delta": 1, "key_up_delta": 1, "draw_delta": 1,
                  "before_color": "red", "after_color": "blue"},
    )
    good["stages"]["capture"]["images"] = {
        name: {"valid": True, "fresh": True, "sha256": name, "width_px": 400, "height_px": 268,
               "owner_pid": 42, "window_id": 43, "owner_before": True, "owner_after": True,
               "red_ratio": 1 if name == "before" else 0,
               "blue_ratio": 1 if name == "after" else 0} for name in ("before", "after")}
    good["stages"]["gui"].update(pid=42, window_id=43, frontmost_matches=True, is_key_window=True)
    good["stages"]["ownership"].update(nonce_matches=True, window_owner_matches=True)
    good["stages"]["visual_change"]["red_to_blue"] = True
    assert assess(good)["capability_pass"] is True
    count = 1
    for name in STAGES:
        for state in ("unknown", "fail", "blocked", "timeout", "not_run"):
            case = copy.deepcopy(good)
            case["stages"][name]["status"] = state
            assert assess(case)["capability_pass"] is False, (name, state)
            count += 1
    mutations = (
        ("permission_blocked", lambda r: r["capabilities"].update(post_event_preflight=False)),
        ("stale_png", lambda r: r["stages"]["capture"]["images"]["before"].update(fresh=False)),
        ("corrupt_png", lambda r: r["stages"]["capture"]["images"]["after"].update(valid=False)),
        ("missing_png", lambda r: r["stages"]["capture"]["images"].pop("after")),
        ("wrong_source", lambda r: r["lineage"].update(commit_matches=False)),
        ("wrong_owner", lambda r: r["stages"]["ownership"].update(window_owner_matches=False)),
        ("wrong_nonce", lambda r: r["stages"]["ownership"].update(nonce_matches=False)),
        ("wrong_frontmost", lambda r: r["stages"]["gui"].update(frontmost_matches=False)),
        ("wrong_image_owner", lambda r: r["stages"]["capture"]["images"]["after"].update(owner_pid=99)),
        ("wrong_image_window", lambda r: r["stages"]["capture"]["images"]["after"].update(window_id=99)),
        ("false_visual_flag", lambda r: r["stages"]["capture"]["images"]["after"].update(blue_ratio=0)),
        ("sender_owner_lost", lambda r: r["stages"]["input"]["sender"]["ownership_after_down"].update(owned=False)),
        ("missing_key_up", lambda r: r["stages"]["input"]["sender"].update(key_up_posted=False)),
        ("pending_not_cleared", lambda r: r["stages"]["input"]["sender"].update(pending_cleared=False)),
        ("no_key_receipt", lambda r: r["stages"]["input"]["receipts"].update(key_down_delta=0)),
        ("no_draw", lambda r: r["stages"]["input"]["receipts"].update(draw_delta=0)),
        ("internal_vs_png", lambda r: r["stages"]["visual_change"].update(red_to_blue=False)),
        ("interrupted", lambda r: r.update(interrupted=True)),
        ("incomplete", lambda r: r.update(measurement_complete=False)),
        ("cleanup_failed", lambda r: r["cleanup"].update(status="fail")),
        ("clock_unknown", lambda r: r["clock"].update(status="unknown")),
    )
    for name, mutation in mutations:
        case = copy.deepcopy(good)
        mutation(case)
        assert assess(case)["capability_pass"] is False, name
        if name in ("wrong_source", "incomplete", "cleanup_failed", "clock_unknown"):
            assert assess(case)["capability_status"] == "unknown_or_blocked", name
        count += 1
    unchanged = copy.deepcopy(good)
    unchanged["stages"]["visual_change"].update(status="fail", red_to_blue=False)
    assert assess(unchanged)["capability_status"] == "pipeline_fail"
    count += 1
    diagnostics = compiler_diagnostics(
        b"/known/ci_game_capability_probe.swift:4:5: error: cannot load '/Users/private/SDK'\n"
        b"  source echo must not appear\n/unknown.swift:1:2: error: ignored\n", "/known/ci_game_capability_probe.swift")
    assert len(diagnostics) == 1 and diagnostics[0]["source"] == SOURCE_FILES[1]
    assert "/Users" not in diagnostics[0]["message"] and "source echo" not in json.dumps(diagnostics)
    assert compiler_diagnostics(b"raw account and environment dump", "/known/source") == []
    count += 3
    assert clock_compatible(100, 100, 200) and clock_compatible(100, 200, 200)
    assert not clock_compatible(100, 99, 200)
    assert not clock_compatible(100, 201, 200)
    assert not clock_compatible(100, None, 200)
    count += 4
    count += lifecycle_self_test()
    print(json.dumps({"self_test": "pass", "assertion_cases": count,
                      "scope": "fixed decision matrix and lifecycle faults; not environmental Red or game E2E"}))


class ProbeInterrupted(Exception):
    pass


def handle_interrupt(probe, number):
    was_interrupted = probe.report["interrupted"]
    probe.mark_interrupted("deadline" if number == signal.SIGALRM else "terminated")
    signal.alarm(0)
    if not probe.cleaning_up and not was_interrupted:
        raise ProbeInterrupted(probe.report["interruption_reason"])


class Probe:
    def __init__(self, args):
        self.args = args
        self.root = Path(__file__).resolve().parents[1]
        self.output = Path(args.output_dir).resolve()
        self.output.mkdir(parents=True, mode=0o700, exist_ok=False)
        # Reserve the final ten seconds of the 300-second bound for owned-child cleanup.
        self.deadline = time.monotonic() + 290
        self.children = set()
        self.app = None
        self.binary = None
        self.state_path = None
        self.pending_path = None
        self.cleaning_up = False
        self.cleanup_deadline = None
        self.nonce = secrets.token_hex(16)
        self.report = {
            "schema_version": 1, "scope": "self_owned_appkit_gui_only", "started_at_utc": utc_now(),
            "measurement_complete": False, "interrupted": False,
            "lineage": {"expected_commit": args.source_commit, "checkout_commit": None,
                        "commit_matches": False, "workflow_run_id": args.run_id,
                        "workflow_run_attempt": args.run_attempt, "runner_label": "macos-26",
                        "source_sha256": {name: sha256(self.root / name) for name in SOURCE_FILES}},
            "capabilities": {}, "permissions": {"status": "not_run"},
            "stages": {name: {"status": "not_run"} for name in STAGES},
        }
        self.save()

    def save(self):
        self.report["summary"] = assess(self.report)
        self.report["updated_at_utc"] = utc_now()
        atomic_json(self.output / "summary.json", self.report)

    def stage(self, name, status, **details):
        self.report["stages"][name] = {"status": status, **details}
        self.save()

    def terminate(self, child):
        # Only the session/process group created by this helper is targeted.
        for signum in (signal.SIGTERM, signal.SIGKILL):
            if child.poll() is not None:
                break
            if self.cleaning_up and time.monotonic() >= self.cleanup_deadline:
                break
            try:
                os.killpg(child.pid, signum)
            except ProcessLookupError:
                pass
            try:
                timeout = min(1, max(0.001, self.cleanup_deadline - time.monotonic())) if self.cleaning_up else 1
                child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                pass
        if child.poll() is not None:
            self.children.discard(child)

    def command(self, arguments, seconds=10, cleanup=False, diagnostic_source=None):
        remaining = (self.cleanup_deadline if cleanup else self.deadline) - time.monotonic()
        if remaining <= 0:
            raise ProbeInterrupted("deadline")
        child = subprocess.Popen(arguments, cwd=self.root, stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE if diagnostic_source else subprocess.DEVNULL,
                                 start_new_session=True)
        self.children.add(child)
        try:
            output, errors = child.communicate(timeout=min(seconds, remaining))
            return {"status": "pass" if child.returncode == 0 else "fail",
                    "returncode": child.returncode, "output": output,
                    "diagnostics": compiler_diagnostics(errors or b"", diagnostic_source) if diagnostic_source else []}
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "returncode": None, "output": b"", "diagnostics": []}
        finally:
            self.terminate(child)

    def swift(self, mode, *arguments, cleanup=False):
        result = self.command([str(self.binary), mode, *map(str, arguments)],
                              seconds=2 if cleanup else 10, cleanup=cleanup)
        if result["status"] != "pass":
            return result["status"], {}
        try:
            value = json.loads(result["output"])
            return ("pass", value) if isinstance(value, dict) else ("fail", {})
        except (ValueError, UnicodeError):
            return "fail", {}

    def state(self):
        if self.app is None or self.app.poll() is not None:
            return None
        try:
            value = json.loads(self.state_path.read_text())
            if (value["pid"] == self.app.pid and value["nonce"] == self.nonce
                    and value["window_id"] > 0 and -1 <= time.time() - value["updated_unix"] <= 3):
                return value
        except (OSError, ValueError, KeyError, TypeError):
            pass
        return None

    def target_args(self, state):
        return ["--pid", self.app.pid, "--window-id", state["window_id"],
                "--state", self.state_path, "--nonce", self.nonce]

    def owner(self, state):
        if self.state() is None:
            return False
        status, result = self.swift("capabilities", *self.target_args(state))
        return status == "pass" and result.get("ownership", {}).get("owned") is True

    def wait_state(self, predicate, seconds):
        limit = min(self.deadline, time.monotonic() + seconds)
        while time.monotonic() < limit:
            state = self.state()
            if state is not None and predicate(state):
                return state
            if self.app.poll() is not None:
                break
            time.sleep(0.1)
        return None

    def capture(self, label, state, private):
        result = {"valid": False, "fresh": False, "status": "blocked"}
        if not self.owner(state):
            result["reason"] = "window_owner_unverified"
            return result
        result.update(owner_before=True, owner_pid=self.app.pid, window_id=state["window_id"])
        path = private / (label + ".png")
        started = time.time()
        result["started_at_utc"] = utc_now()
        captured = self.command(["/usr/sbin/screencapture", "-x", "-o", "-l",
                                 str(state["window_id"]), str(path)])
        result["status"] = captured["status"]
        if captured["status"] != "pass":
            result["reason"] = "window_capture_did_not_complete"
            return result
        if not self.owner(state):
            result.update(status="blocked", reason="window_owner_changed")
            return result
        result["owner_after"] = True
        try:
            from PIL import Image
            # The untouched original PNG is saved. Cropping below is analysis in memory only.
            with Image.open(path) as image:
                if image.format != "PNG" or not (200 <= image.width <= 2000 and 120 <= image.height <= 1500):
                    raise ValueError("unexpected_window_image")
                image.load()
                width, height = image.size
                region = (width // 5, height // 4, width * 4 // 5, height * 3 // 4)
                pixels = list(image.convert("RGB").crop(region).getdata())
            red = sum(r >= 220 and g <= 45 and b <= 45 for r, g, b in pixels) / len(pixels)
            blue = sum(b >= 220 and g <= 45 and r <= 45 for r, g, b in pixels) / len(pixels)
            fresh = path.stat().st_mtime >= started - 1
            result.update(valid=True, fresh=fresh, sha256=sha256(path), width_px=width, height_px=height,
                          analysis_region_px=region, red_ratio=red, blue_ratio=blue,
                          status="pass" if fresh else "fail", completed_at_utc=utc_now())
            shutil.copyfile(path, self.output / (label + ".png"))
        except ImportError:
            result.update(status="blocked", reason="pillow_unavailable")
        except (OSError, ValueError):
            result.update(status="fail", reason="invalid_or_missing_png")
        return result

    def measure(self, private):
        lineage = self.command(["git", "rev-parse", "HEAD"])
        actual = lineage["output"].decode("ascii", errors="ignore").strip()
        self.report["lineage"].update(checkout_commit=actual,
                                      commit_matches=lineage["status"] == "pass" and actual == self.args.source_commit)
        self.save()
        if platform.system() != "Darwin":
            self.stage("runtime", "blocked", reason="macos_required")
            return
        self.binary = private / "ci-game-probe"
        self.state_path = private / "state.json"
        self.pending_path = private / "pending-key.json"
        compiled = self.command(["xcrun", "swiftc", "-swift-version", "5",
                                 str(self.root / SOURCE_FILES[1]), "-o", str(self.binary),
                                 "-framework", "AppKit", "-framework", "CoreGraphics", "-framework", "Metal"], 180,
                                diagnostic_source=self.root / SOURCE_FILES[1])
        self.stage("compile", compiled["status"], returncode=compiled["returncode"],
                   source_diagnostics=compiled["diagnostics"])
        if compiled["status"] != "pass":
            return
        clock_start = time.monotonic_ns()
        status, capabilities = self.swift("capabilities")
        clock_end = time.monotonic_ns()
        self.stage("runtime", status)
        if status != "pass":
            return
        swift_clock = capabilities.get("monotonic_ns")
        clock_ok = clock_compatible(clock_start, swift_clock, clock_end)
        self.report["clock"] = {"status": "pass" if clock_ok else "unknown",
                                "python_before_ns": clock_start, "swift_ns": swift_clock,
                                "python_after_ns": clock_end}
        # Explicit allowlist: no raw runtime, exception, environment, or window-list dump.
        names = ("architecture", "macos_version", "metal_device_count", "metal_device_names",
                 "metal_command_execution_tested", "screen_count", "screen_capture_preflight",
                 "post_event_preflight", "app_store_present")
        self.report["capabilities"] = {name: capabilities.get(name) for name in names}
        self.report["permissions"] = {
            "status": "observed", "screen_capture_preflight": capabilities.get("screen_capture_preflight"),
            "post_event_preflight": capabilities.get("post_event_preflight"),
            "screen_preflight_scope": "probe_binary_only; screencapture_is_measured_separately",
            "permission_request_apis_used": False,
        }
        self.save()
        self.app = subprocess.Popen([str(self.binary), "app", "--state", str(self.state_path),
                                     "--nonce", self.nonce], cwd=self.root, stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL, start_new_session=True)
        self.children.add(self.app)
        before = self.wait_state(lambda s: s["draw_count"] > 0 and s["frontmost_matches"]
                                 and s["is_key_window"], 20)
        if before is None:
            self.stage("gui", "blocked", reason="own_key_window_not_ready_within_20_seconds")
            return
        self.stage("gui", "pass", pid=self.app.pid, window_id=before["window_id"],
                   content_size_pt=[400, 240], frontmost_matches=True, is_key_window=True)
        if not self.owner(before):
            self.stage("ownership", "blocked", reason="window_owner_unverified")
            return
        self.stage("ownership", "pass", nonce_matches=True, window_owner_matches=True)
        before_image = self.capture("before", before, private)
        self.stage("capture", "unknown", images={"before": before_image})
        if not clock_ok:
            self.stage("input", "unknown", reason="cross_process_monotonic_clock_unverified")
            return
        # Input is a separate observation, even if capture is unavailable.
        if self.state() is None or not self.owner(before):
            self.stage("ownership", "blocked", reason="target_changed_before_input")
            return
        status, sender = self.swift("send", *self.target_args(before), "--pending", self.pending_path,
                                    "--deadline-ns", int(self.deadline * 1_000_000_000))
        sender_names = ("status", "reason", "method", "key_down_posted", "key_up_posted",
                        "ownership_before", "ownership_after_down", "pending_cleared", "mode")
        sender = {name: sender[name] for name in sender_names if name in sender}
        self.stage("input", "unknown" if status == "pass" else status, sender=sender)
        if sender.get("status") == "posted":
            after = self.wait_state(lambda s: s["key_down_count"] > before["key_down_count"]
                                    and s["key_up_count"] > before["key_up_count"]
                                    and s["draw_count"] > before["draw_count"], 10)
        else:
            after = self.state()
        if after is None:
            after = self.state()
        receipts = {}
        if after is not None:
            receipts = {"key_down_delta": after["key_down_count"] - before["key_down_count"],
                        "key_up_delta": after["key_up_count"] - before["key_up_count"],
                        "draw_delta": after["draw_count"] - before["draw_count"],
                        "before_color": before["last_draw_color"], "after_color": after["last_draw_color"]}
        input_pass = (sender.get("status") == "posted" and sender.get("key_down_posted") is True
                      and sender.get("key_up_posted") is True and receipts.get("key_down_delta") == 1
                      and receipts.get("key_up_delta") == 1)
        input_status = "pass" if input_pass else ("fail" if sender.get("status") == "posted" else "blocked")
        if status != "pass":
            input_status = status
        self.stage("input", input_status, sender=sender, receipts=receipts)
        after_image = self.capture("after", after, private) if after else {
            "status": "blocked", "valid": False, "fresh": False, "reason": "own_app_state_unavailable"}
        images = {"before": before_image, "after": after_image}
        capture_pass = all(image.get("status") == "pass" and image.get("valid") is True
                           and image.get("fresh") is True for image in images.values())
        capture_status = "pass" if capture_pass else (
            "timeout" if any(i["status"] == "timeout" for i in images.values()) else
            "fail" if any(i["status"] == "fail" for i in images.values()) else "blocked")
        self.stage("capture", capture_status, images=images)
        if any(image.get("reason") in ("window_owner_changed", "window_owner_unverified") for image in images.values()):
            self.stage("ownership", "blocked", reason="capture_ownership_unverified")
        if capture_pass:
            same_size = ((before_image["width_px"], before_image["height_px"])
                         == (after_image["width_px"], after_image["height_px"]))
            changed = (same_size and before_image["red_ratio"] >= 0.9 and before_image["blue_ratio"] <= 0.1
                       and after_image["blue_ratio"] >= 0.9 and after_image["red_ratio"] <= 0.1
                       and before_image["sha256"] != after_image["sha256"])
            self.stage("visual_change", "pass" if changed else "fail", red_to_blue=changed,
                       same_dimensions=same_size, minimum_color_ratio=0.9)
        else:
            self.stage("visual_change", "unknown", reason="two_valid_external_pngs_required")

    def mark_interrupted(self, reason):
        self.report.update(interrupted=True, measurement_complete=False, interruption_reason=reason)

    def recover_key_up(self):
        if self.pending_path is None or self.app is None or self.app.poll() is not None:
            return {"status": "not_needed"}
        try:
            pending = json.loads(self.pending_path.read_text())
        except (OSError, ValueError):
            return {"status": "not_needed"}
        if pending.get("pending_key_up") is not True:
            return {"status": "not_needed"}
        state = self.state()
        if (state is None or pending.get("nonce") != self.nonce or pending.get("pid") != self.app.pid
                or pending.get("window_id") != state["window_id"]):
            return {"status": "blocked", "reason": "pending_owner_unverified"}
        status, result = self.swift(
            "send", *self.target_args(state), "--pending", self.pending_path,
            "--deadline-ns", int(self.cleanup_deadline * 1_000_000_000), "--key-up-only", cleanup=True)
        return {"status": "released" if status == "pass" and result.get("status") == "released" else "blocked",
                "key_up_posted": result.get("key_up_posted") is True,
                "reason": result.get("reason", "release_attempt_completed")}

    def cleanup(self):
        # Signal handlers flag interruptions from here onward; they do not unwind cleanup.
        self.cleaning_up = True
        self.cleanup_deadline = min(time.monotonic() + 10, self.deadline + 10)
        signal.alarm(0)

        def reap(child):
            for _ in range(2):
                if child not in self.children or time.monotonic() >= self.cleanup_deadline:
                    break
                try:
                    self.terminate(child)
                except ProbeInterrupted:
                    self.mark_interrupted("terminated_during_cleanup")
                except OSError:
                    self.report["cleanup_error_class"] = "OSError"

        # Stop any sender first; keep the original application alive for a pending release.
        for child in tuple(self.children):
            if child is not self.app:
                reap(child)
        try:
            recovery = self.recover_key_up()
        except ProbeInterrupted:
            self.mark_interrupted("terminated_during_cleanup")
            recovery = {"status": "blocked", "reason": "cleanup_interrupted"}
        except (OSError, ValueError, KeyError, TypeError):
            recovery = {"status": "blocked", "reason": "cleanup_owner_unverified"}
        for child in tuple(self.children):
            reap(child)
        self.report["cleanup"] = {"status": "pass" if not self.children else "fail",
                                  "owned_processes_remaining": len(self.children), "pending_key_up": recovery}
        if self.children:
            self.mark_interrupted("owned_process_cleanup_incomplete")

    def run(self):
        try:
            with tempfile.TemporaryDirectory(prefix="ci-game-probe-") as directory:
                try:
                    try:
                        self.measure(Path(directory))
                        self.report["measurement_complete"] = True
                    except ProbeInterrupted as error:
                        self.mark_interrupted(str(error))
                    except (OSError, ValueError, KeyError, TypeError) as error:
                        # Keep a fixed class name; raw exceptions may contain private paths.
                        self.report["internal_error_class"] = type(error).__name__
                    finally:
                        self.cleaning_up = True
                finally:
                    self.cleanup()
        except ProbeInterrupted:
            self.mark_interrupted("terminated_at_cleanup_boundary")
        finally:
            self.report["completed_at_utc"] = utc_now()
            self.save()
            manifest = {
                "schema_version": 1, "lineage": self.report["lineage"],
                "files": {path.name: {"sha256": sha256(path), "bytes": path.stat().st_size}
                          for path in sorted(self.output.iterdir()) if path.suffix in (".json", ".png")
                          and path.name != "manifest.json"},
            }
            atomic_json(self.output / "manifest.json", manifest)
            print(json.dumps({"measurement_complete": self.report["measurement_complete"],
                              **self.report["summary"]}, sort_keys=True))
        return 1 if self.report["interrupted"] or "internal_error_class" in self.report else 0


def lifecycle_self_test():
    """Exercise orchestration faults separately from environmental capabilities."""
    class InterruptedCleanup(Probe):
        def measure(self, private):
            pass

        def terminate(self, child):
            self.calls += 1
            if self.calls == 1:
                raise ProbeInterrupted("terminated")
            self.children.discard(child)

    with tempfile.TemporaryDirectory(prefix="ci-probe-self-test-") as directory:
        args = SimpleNamespace(output_dir=directory + "/out", source_commit="", run_id="", run_attempt="")
        probe = InterruptedCleanup(args)
        probe.calls = 0
        probe.children.add(object())
        with contextlib.redirect_stdout(io.StringIO()):
            code = probe.run()
        assert code == 1 and probe.report["measurement_complete"] is False
        assert not probe.children and probe.report["cleanup"]["status"] == "pass"
        assert probe.report["summary"]["capability_pass"] is False
        # A real handler invocation during cleanup flags the signal without unwinding it.
        handle_interrupt(probe, signal.SIGTERM)
        assert probe.report["interrupted"] is True and probe.cleaning_up is True
        probe.deadline = time.monotonic() - 1
        try:
            probe.command(["must-not-launch-after-deadline"])
            raise AssertionError("expired work must not launch")
        except ProbeInterrupted:
            pass
        probe.app = SimpleNamespace(pid=42, poll=lambda: None)
        probe.pending_path = Path(directory) / "pending.json"
        probe.state_path = Path(directory) / "state.json"
        probe.state = lambda: {"window_id": 43}
        atomic_json(probe.pending_path, {"pid": 42, "window_id": 43,
                                        "nonce": probe.nonce, "pending_key_up": True})
        calls = []

        def release_only(mode, *arguments, cleanup=False):
            calls.append((mode, arguments, cleanup))
            assert mode == "send" and "--key-up-only" in arguments and cleanup is True
            return "pass", {"status": "released", "key_up_posted": True}

        probe.swift = release_only
        assert probe.recover_key_up()["status"] == "released" and len(calls) == 1
        atomic_json(probe.pending_path, {"pid": 99, "window_id": 43,
                                        "nonce": probe.nonce, "pending_key_up": True})
        assert probe.recover_key_up()["status"] == "blocked" and len(calls) == 1
        atomic_json(probe.pending_path, {"pid": 42, "window_id": 43,
                                        "nonce": "wrong", "pending_key_up": True})
        assert probe.recover_key_up()["status"] == "blocked" and len(calls) == 1
        probe.app.poll = lambda: 0
        assert probe.recover_key_up()["status"] == "not_needed" and len(calls) == 1

        class EntryProbe(Probe):
            def measure(self, private):
                pass

            def terminate(self, child):
                self.children.discard(child)

        args.output_dir = directory + "/entry-out"
        entry = EntryProbe(args)
        entry.children.add(object())
        entry.deadline = time.monotonic() - 2
        injected = False

        def at_first_cleanup_line(frame, event, _argument):
            nonlocal injected
            if frame.f_code is Probe.cleanup.__code__ and event == "line" and not injected:
                injected = True
                assert entry.cleaning_up is True
                handle_interrupt(entry, signal.SIGTERM)
            return at_first_cleanup_line

        previous_trace = sys.gettrace()
        sys.settrace(at_first_cleanup_line)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                code = entry.run()
        finally:
            sys.settrace(previous_trace)
        assert injected and code == 1 and entry.report["measurement_complete"] is False
        assert not entry.children and entry.report["cleanup"]["status"] == "pass"
        assert entry.cleanup_deadline <= entry.deadline + 10

        class BoundaryProbe(Probe):
            def measure(self, private):
                self.children.add(object())
                if self.mode == "interrupt":
                    raise ProbeInterrupted("injected_measurement_interrupt")
                if self.mode == "oserror":
                    raise OSError("injected_measurement_failure")

            def terminate(self, child):
                self.children.discard(child)

        boundary_assertions = 0
        for mode in ("normal", "interrupt", "oserror"):
            args.output_dir = directory + "/collect-" + mode
            collector = BoundaryProbe(args)
            collector.mode = mode
            boundaries = set()

            def collect(frame, event, _argument):
                if frame.f_code is Probe.run.__code__ and event == "line" and collector.children:
                    boundaries.add(frame.f_lineno)
                return collect

            sys.settrace(collect)
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    collector.run()
            finally:
                sys.settrace(previous_trace)
            for boundary in sorted(boundaries):
                args.output_dir = directory + "/boundary-" + mode + "-" + str(boundary)
                candidate = BoundaryProbe(args)
                candidate.mode = mode
                fired = False

                def inject(frame, event, _argument):
                    nonlocal fired
                    if (frame.f_code is Probe.run.__code__ and event == "line"
                            and frame.f_lineno == boundary and candidate.children and not fired):
                        fired = True
                        handle_interrupt(candidate, signal.SIGTERM)
                    return inject

                sys.settrace(inject)
                try:
                    with contextlib.redirect_stdout(io.StringIO()):
                        code = candidate.run()
                finally:
                    sys.settrace(previous_trace)
                assert fired and code == 1 and candidate.report["measurement_complete"] is False
                assert not candidate.children and candidate.report["cleanup"]["status"] == "pass"
                boundary_assertions += 2
    return 13 + boundary_assertions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output-dir")
    parser.add_argument("--source-commit", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--run-attempt", default="")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.output_dir:
        parser.error("--output-dir is required")
    os.umask(0o077)
    probe = Probe(args)

    def interrupted(number, _frame):
        handle_interrupt(probe, number)

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    signal.signal(signal.SIGALRM, interrupted)
    signal.alarm(290)
    try:
        return probe.run()
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    sys.exit(main())
