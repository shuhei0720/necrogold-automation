"""試行を先に登録し、成功・失敗・未実施をすべて残す。"""
from collections import Counter
import json
import math
import os
from pathlib import Path
import statistics
import tempfile
import time

from . import VERSION
from .capture import inspect_payload, validate_source_geometry
from .protocol import GAME
from .validation import ProbeError

VARIANTS = (
    ("jpeg_scale1", {"format": "jpeg", "quality": .6, "scale": 1}),
    ("jpeg_scale2", {"format": "jpeg", "quality": .6, "scale": 2}),
    ("png_scale1", {"format": "png", "scale": 1}),
)
FATAL = {"response_mac_mismatch", "response_id_mismatch", "http_status_401", "http_status_403",
         "invalid_response_tag", "pairing_missing", "posix_timer_required", "timer_already_in_use",
         "timer_setup_failed", "timer_cleanup_failed", "timer_owner_required", "timer_unusable", "timer_handler_in_use",
         "source_geometry_invalid"}


def atomic_write(path, raw):
    path = Path(path)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as file:
            file.write(raw)
        os.replace(str(temporary), str(path))
    finally:
        if temporary.exists():
            temporary.unlink()


def write_report(folder, report):
    atomic_write(Path(folder) / "report.json", json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False).encode())


def stop_report(report, reason):
    report["status"] = "stopped"
    report.setdefault("stop_reason", reason)


def output_failed(report):
    report["output_error"] = "output_write_failed"
    stop_report(report, "output_write_failed")


def stats(values):
    if not values:
        return {"n": 0, "median_ms": None, "p95_ms": None}
    ordered = sorted(values)
    return {"n": len(values), "median_ms": round(statistics.median(values), 3),
            "p95_ms": round(ordered[math.ceil(.95 * len(ordered)) - 1], 3)}


def durations(row):
    times = row.get("timings", {})
    spans = {
        "request_prepare": ("request_start_ns", "http_start_ns"),
        "http_roundtrip": ("http_start_ns", "http_end_ns"),
        "envelope_auth": ("http_end_ns", "decrypt_start_ns"),
        "decrypt": ("decrypt_start_ns", "decrypt_end_ns"),
        "response_json": ("decrypt_end_ns", "response_end_ns"),
        "image_base64": ("base64_start_ns", "base64_end_ns"),
        "image_decode": ("decode_start_ns", "decode_end_ns"),
        "image_inspect": ("decode_end_ns", "inspect_end_ns"),
        "capture_to_inspected": ("request_start_ns", "inspect_end_ns"),
        "raw_save": ("save_start_ns", "save_end_ns"),
        "trial_total": ("trial_start_ns", "trial_end_ns"),
    }
    return {name: (times[end] - times[start]) / 1e6 for name, (start, end) in spans.items()
            if start in times and end in times}


def summarize(rows, elapsed_ns):
    complete = [row for row in rows if row["status"] == "complete"]
    summary = {
        "planned": len(rows), "started": sum(row["status"] != "not_started" for row in rows),
        "complete": len(complete), "errors": sum(row["status"] == "error" for row in rows),
        "interrupted": sum(row["status"] == "interrupted" for row in rows),
        "not_started": sum(row["status"] == "not_started" for row in rows),
        "completion_fraction": len(complete) / len(rows) if rows else 0,
        "elapsed_ms": elapsed_ns / 1e6,
        "captures_completed_per_second": len(complete) * 1e9 / elapsed_ns if elapsed_ns > 0 else None,
        "fresh_observations_hz": None, "frame_age_ms": None,
        "p95_method": "nearest_rank", "warmup_excluded": 0,
        "groups": {},
    }
    for variant, _ in VARIANTS:
        group = [row for row in rows if row["variant"] == variant]
        timings = {}
        for row in group:
            if row["status"] == "complete":
                for key, value in durations(row).items():
                    timings.setdefault(key, []).append(value)
        summary["groups"][variant] = {
            "planned": len(group), "counts": dict(Counter(row["status"] for row in group)),
            "image_counts": dict(Counter(row.get("image", {}).get("image_status") for row in group if row["status"] == "complete")),
            "saved": sum("raw_file" in row for row in group),
            "success_only_timings": {key: stats(values) for key, values in timings.items()},
        }
    return summary


def safe_info(result):
    system = result.get("system")
    system = system if isinstance(system, dict) else {}
    front = system.get("foreground_app")
    front = "game" if front == GAME else "springboard" if front == "com.apple.springboard" else "other" if isinstance(front, str) and front else "unknown"
    caps = result.get("capabilities", [])
    caps = caps if isinstance(caps, list) else []
    # Presence is informational, not proof of semantics or device execution.
    return {"foreground": front, "screen_locked": system.get("screen_locked") if type(system.get("screen_locked")) is bool else None,
            "advertised_known_capabilities": [name for name in ("run_steps", "wait_for", "screenshot_stream", "screenshot_image_geometry_v1") if name in caps],
            "execution_deadline_verified": False, "foreground_generation_verified": False,
            "input_cancel_verified": False}


def new_report(samples, start_ns):
    return {"version": VERSION, "kind": "capture_probe", "device_acceptance": "not_tested",
            "input_authorized": False, "start_ns": start_ns, "status": "running", "events": [],
            "rows": [{"trial": index + 1, "variant": VARIANTS[index % 3][0], "status": "not_started"}
                     for index in range(samples)]}


def collect(client, report, folder, stop_ns, clock=time.monotonic_ns):
    """Parent supervises the entire worker, including native code and file IO."""
    source_geometry = getattr(client, "source_geometry", False) is True
    if source_geometry:
        report["requested_geometry"] = "image_size_v1"
    failures = {name: 0 for name, _ in VARIANTS}
    saved = set()
    last_hash = None
    connection_failures = 0

    def checkpoint():
        try:
            write_report(folder, report)
        except OSError:
            output_failed(report)
            raise

    def call(method, params=None):
        remaining = (stop_ns - clock()) / 1e9
        if remaining < .001:
            raise ProbeError("session_deadline")
        return client.call(method, params, timeout=min(client.timeout, remaining))

    def event(method, params=None, *, required=False):
        entry = {"method": method, "start_ns": clock()}
        report["events"].append(entry)
        checkpoint()
        try:
            if method == "launch_app":
                print("ゲームの起動要求を送ります。", flush=True)
            reply = call(method, params)
            entry.update(status="complete", timings=reply.timings)
            if method == "device_info":
                entry["observation"] = safe_info(reply.result)
            else:
                entry["launch_acknowledged"] = True
                entry["game_visible_verified"] = False
                print("ゲーム起動の応答を受け取りました。表示の成功は未確認です。画像を取得します。", flush=True)
            return reply.result
        except ProbeError as exc:
            entry.update(status="error", error=exc.code)
            if required or exc.code in FATAL or exc.code == "session_deadline" or method == "launch_app":
                stop_report(report, exc.code)
                raise
        except KeyboardInterrupt:
            stop_report(report, "user_interrupt")
            raise
        finally:
            entry["end_ns"] = clock()
            checkpoint()

    try:
        initial_info = event("device_info", required=source_geometry)
        if source_geometry:
            caps = initial_info.get("capabilities")
            if not isinstance(caps, list) or "screenshot_image_geometry_v1" not in caps:
                raise ProbeError("source_geometry_capability_missing")
        if client.allow_launch:
            event("launch_app", {"bundle_id": GAME})
        for row in report["rows"]:
            if clock() >= stop_ns:
                raise ProbeError("session_deadline")
            name, params = VARIANTS[(row["trial"] - 1) % 3]
            if source_geometry:
                params = dict(params, geometry="image_size_v1")
            if failures[name] >= 3:
                row["not_started_reason"] = "condition_failure_limit"
                continue
            row["status"] = "in_progress"
            row["timings"] = {"trial_start_ns": clock()}
            checkpoint()
            try:
                reply = call("screenshot", params)
                connection_failures = 0
                row["timings"].update(reply.timings)
                try:
                    raw, image = inspect_payload(reply.result)
                    if source_geometry:
                        validate_source_geometry(reply.result, image, params)
                except ProbeError:
                    if source_geometry:
                        raise ProbeError("source_geometry_invalid") from None
                    raise
                for key in list(image):
                    if key.endswith("_ns") and key != "capture_time_ns":
                        row["timings"][key] = image.pop(key)
                image["same_bytes_as_previous"] = image["sha256"] == last_hash
                last_hash = image["sha256"]
                row["image"] = image
                slot = (name, image["image_status"])
                if slot not in saved:
                    suffix = "jpg" if image["format"] == "JPEG" else "png"
                    filename = "%03d-%s-%s.%s" % (row["trial"], name, image["image_status"], suffix)
                    row["timings"]["save_start_ns"] = clock()
                    atomic_write(Path(folder) / filename, raw)
                    row["timings"]["save_end_ns"] = clock()
                    row["raw_file"] = filename
                    saved.add(slot)
                row["status"] = "complete"
                failures[name] = 0
            except ProbeError as exc:
                row.update(status="error", error=exc.code)
                failures[name] += 1
                if exc.code in ("connection_error", "rpc_deadline"):
                    connection_failures += 1
                else:
                    connection_failures = 0
                if connection_failures >= 3:
                    stop_report(report, "connection_failure_limit")
                    raise ProbeError("connection_failure_limit")
                if exc.code in FATAL or exc.code == "session_deadline":
                    stop_report(report, exc.code)
                    raise
            except KeyboardInterrupt:
                stop_report(report, "user_interrupt")
                raise
            except OSError:
                row.update(status="error", error="output_write_failed")
                output_failed(report)
                raise
            finally:
                row["timings"]["trial_end_ns"] = clock()
                checkpoint()
            outcome = row.get("image", {}).get("image_status", row.get("error", row["status"]))
            if source_geometry and row["status"] == "complete":
                outcome += " %dx%d" % (row["image"]["pixel_width"], row["image"]["pixel_height"])
            print("%d/%d %s: %s" % (row["trial"], len(report["rows"]), name, outcome), flush=True)
            if all(value >= 3 for value in failures.values()):
                raise ProbeError("all_conditions_failed")
        event("device_info")
        report["status"] = "completed"
    except ProbeError as exc:
        stop_report(report, exc.code)
    except KeyboardInterrupt:
        stop_report(report, "user_interrupt")
    except OSError:
        output_failed(report)
    finally:
        finish(report, clock())
        checkpoint()
    return report


def finish(report, now, reason=None):
    if reason:
        report["termination_reason"] = reason
        stop_report(report, reason)
    for row in report["rows"]:
        if row["status"] == "in_progress":
            row["status"] = "interrupted"
    for event in report["events"]:
        if "status" not in event:
            event["status"] = "interrupted"
    report["end_ns"] = now
    report["summary"] = summarize(report["rows"], max(0, now - report["start_ns"]))
    report["gate"] = {
        "P1": "not_passed", "capture_freshness": "not_measured",
        "input_geometry": "not_measured", "device_input_cancel": "not_measured",
        "reason": "Capture diagnostics alone do not authorize gameplay input.",
    }
