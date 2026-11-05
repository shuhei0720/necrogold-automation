"""TEST-013: 固定した続行候補点の実機試験。一般校正・自動周回ではない。"""
import argparse
import base64
from copy import deepcopy
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import re
import signal
import sys
import time
import uuid

from PIL import Image
from . import VERSION
from . import input_path as supervisor
from .capture import inspect_payload, validate_source_geometry
from .crypto import Crypto
from .deadlines import OwnedRpcTimer
from .protocol import Client, GAME, HttpTransport, load_pairing
from .session import atomic_write, safe_info
from .validation import ProbeError, json_object

REVISION = "resume-once-v1"
CAPABILITIES = ("run_steps", "wait_for", "screenshot_image_geometry_v1")
CAPTURE_PARAMS = {"format": "jpeg", "quality": .6, "scale": 1, "geometry": "image_size_v1"}
BATCH_PARAMS = {"steps": [
    {"method": "wait_for", "params": {"foreground": GAME, "timeout": .5}},
    {"method": "tap", "params": {"x": 297, "y": 448, "fast": True, "settle": False}},
], "observe": "none"}
MAX_REPORT = 65536
SESSION_SECONDS = 50
STEPS = ("initial_info", "launch", "pre_info", "before_capture", "before_save", "before_info",
         "batch", "after_info", "after_capture", "final_info", "after_save")
STAGES = ("spawn_requested", "pairing_load", "crypto_initialize", "timer_initialize") + STEPS + ("complete",)
ERRORS = supervisor.ERRORS | {"capabilities_missing", "pause_label_not_matched", "host_observation_expired",
                             "batch_reply_invalid", "batch_step_failed"}
# TEST-012 before.jpg、未加工896x414。crop=(384,104,512,132)、L>=180、MSB first。
TEMPLATE_SOURCE_SHA256 = "7d1249d356c71d3689b16ebed960d193b7508a7151fc4191e6c0748fccda1b06"
TEMPLATE_MASK_B64 = (
    "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABAAAAAAAAAAACAAAAAAAICEAAAAgAAQACAgCH8AAACAAAAAAIAAEAAAYAgAAAAAgCAAAACAABAAh/4QAAAAAIAAAAAAgAP/wQAgQAAAAADAAAAAAIAAYAEAYAAAAAAA//AAAACAAEAB4f4AAAAAAQIAQAABAAB4ACAACf/AAAACAAAAAQAAAAAAAAAGAAAEAgAf/AECAIJgh/4QAgAAAAIAAAABAgIPAfwCcAIAAAAAAAAAAAICBgBgADACAAAABAAAAAQCAhIAIJAQAgAAAAQAAAAEPIBCASCQEAIAAAAAAAAABgCAQAEgEBACAAAAMAAAAD+AgEABIRIQAgAAAYAAAAAAAIAfwDweED4AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="
)


def exact(value, expected):
    """再帰的な型の一致。Trueと1、座標intとfloatも区別する。"""
    if type(value) is not type(expected):
        return False
    if type(expected) is dict:
        return set(value) == set(expected) and all(exact(value[k], v) for k, v in expected.items())
    if type(expected) is list:
        return len(value) == len(expected) and all(exact(a, b) for a, b in zip(value, expected))
    return value == expected


class ResumeOnceClient(Client):
    """固定APIのみ。暗号化・通信の成否によらず一度の権利を消費する。"""
    def __init__(self, *args, **kwargs):
        kwargs.update(allow_launch=True, source_geometry=True)
        super().__init__(*args, **kwargs)
        self.batch_sent = self.launch_sent = False

    def _validate(self, method, params):
        expected = {"device_info": {}, "launch_app": {"bundle_id": GAME},
                    "screenshot": CAPTURE_PARAMS, "run_steps": BATCH_PARAMS}.get(method)
        if expected is None or not exact(params, expected):
            raise ProbeError("method_not_allowed")

    def call(self, method, params=None, *, timeout=None):
        params = {} if params is None else params
        self._validate(method, params)
        if method in ("run_steps", "launch_app"):
            field = "batch_sent" if method == "run_steps" else "launch_sent"
            if getattr(self, field):
                raise ProbeError("method_not_allowed")
            setattr(self, field, True)
        return super().call(method, params, timeout=timeout)


def label_evidence(raw):
    """現在の固定領域だけを比較。入力座標の正しさやゲーム状態を確定しない。"""
    template = base64.b64decode(TEMPLATE_MASK_B64, validate=True)
    with Image.open(io.BytesIO(raw)) as source:
        with source.crop((384, 104, 512, 132)).convert("L") as gray:
            pixels = gray.tobytes()
    bits = [value >= 180 for value in pixels]
    diff = sum(value != bool(template[i // 8] & (128 >> (i % 8))) for i, value in enumerate(bits))
    white = sum(bits)
    return {"matched": diff <= 32 and 200 <= white <= 310, "pixel_diff": diff, "white_pixels": white}


def new_report(start_ns, run_id):
    return {"version": VERSION, "kind": "resume_once_probe", "test_id": "TEST-013", "revision": REVISION,
            "run_id": run_id, "start_ns": start_ns, "end_ns": None, "status": "running", "stage": "spawn_requested",
            "stop_reason": None, "batch_attempts": 0, "tap_outcome": "not_requested", "batch_result": None,
            "resume_verified": False, "input_geometry_verified": False, "input_cancel_verified": False,
            "execution_deadline_verified": False, "device_acceptance": "not_tested", "label": None,
            "images": {"before": None, "after": None}, "image_bytes_changed": None,
            "timings": {"capture_request_ns": None, "foreground_reply_ns": None, "batch_invoked_ns": None},
            "events": [{"stage": stage, "status": "not_started", "start_ns": None, "end_ns": None,
                        "observation": None} for stage in STEPS], "crypto_engine": None, "timer": None,
            "worker": {"returncode": None, "signal_number": None, "signal_name": None, "spawn_errno": None,
                       "report_read_ok": None, "exit_confirmed": None, "cleanup_error": None}}


def write_report(folder, report, name="report.json"):
    atomic_write(Path(folder) / name, json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False).encode())


def safe_code(reason):
    return reason if type(reason) is str and (reason in ERRORS or re.fullmatch(r"http_status_[1-5][0-9]{2}", reason)) else "internal_error"


def stop(report, reason, now=None):
    report.update(status="stopped", stop_reason=safe_code(reason), end_ns=time.monotonic_ns() if now is None else now)
    for event in report["events"]:
        if event["status"] == "running":
            event.update(status="error", end_ns=report["end_ns"])


def batch_evidence(result):
    """実装元のcompleted/failed_step/not_sent/stepsを検査し、生ラベル等を破棄。"""
    summary = {"shape_valid": False, "completed": None, "failed_step": None,
               "wait_met": None, "tap_ok": None, "error_code": None}
    try:
        require = supervisor.require
        require(type(result) is dict)
        completed, failed, pending, steps = (result[k] for k in ("completed", "failed_step", "not_sent", "steps"))
        require(type(completed) is int and completed in (0, 1, 2))
        require(failed is None or (type(failed) is int and failed in (0, 1)))
        require(type(pending) is list and all(type(i) is int for i in pending))
        require(type(steps) is list and len(steps) == (2 if failed is None else failed + 1))
        require(completed == (2 if failed is None else failed))
        require(pending == ([1] if failed == 0 else []))
        for i, step in enumerate(steps):
            require(type(step) is dict and type(step.get("i")) is int and step["i"] == i)
            require(step.get("method") == ("wait_for" if i == 0 else "tap"))
            require(type(step.get("ok")) is bool and step["ok"] == (i != failed))
            if step["ok"]:
                require("error" not in step and type(step.get("result")) is dict)
                if i == 0:
                    require(step["result"].get("met") is True and step["result"].get("foreground") == GAME)
            else:
                error = step.get("error")
                require("result" not in step and type(error) is dict and type(error.get("code")) is int
                        and -(2 ** 31) <= error["code"] < 2 ** 31 and type(error.get("message")) is str)
                summary["error_code"] = error["code"]
        summary.update(shape_valid=True, completed=completed, failed_step=failed,
                       wait_met=failed != 0, tap_ok=None if failed == 0 else failed is None)
        return ("not_sent" if failed == 0 else "unknown" if failed == 1 else "acknowledged"), summary
    except (ValueError, TypeError, KeyError):
        return "unknown", {key: False if key == "shape_valid" else None for key in summary}


def collect(client, report, folder, stop_ns, clock=time.monotonic_ns):
    def begin(stage):
        report["stage"] = stage
        event = report["events"][STEPS.index(stage)]
        event.update(status="running", start_ns=clock())
        write_report(folder, report)
        return event

    def finish(event):
        event.update(status="complete", end_ns=clock())
        write_report(folder, report)

    def remaining():
        seconds = (stop_ns - clock()) / 1e9
        if seconds < .001:
            raise ProbeError("session_deadline")
        return min(client.timeout, seconds)

    def rpc(stage, method, params=None):
        event = begin(stage)
        started = clock()
        reply = client.call(method, params, timeout=remaining())
        replied = clock()
        result = reply.result
        if type(result) is not dict:
            raise ProbeError("rpc_result_type")
        if method == "device_info":
            info = safe_info(result)
            event["observation"] = info
            if not all(cap in info["advertised_known_capabilities"] for cap in CAPABILITIES):
                raise ProbeError("capabilities_missing")
            if stage != "initial_info" and (info["foreground"] != "game" or info["screen_locked"] is not False):
                raise ProbeError("foreground_not_verified")
            if stage == "before_info":
                report["timings"]["foreground_reply_ns"] = replied
        if method == "screenshot":
            if stage == "before_capture":
                # Host elapsed-time origin only; it does not bound the source frame's age.
                report["timings"]["capture_request_ns"] = started
            try:
                raw, image = inspect_payload(result)
                validate_source_geometry(result, image, CAPTURE_PARAMS)
                geometry = image["reported_geometry"]
                if (image["pixel_width"], image["pixel_height"], geometry["source_orientation"],
                    geometry["point_width"], geometry["point_height"]) != (896, 414, 2, 414, 896):
                    raise ProbeError("source_geometry_invalid")
            except ProbeError:
                raise ProbeError("source_geometry_invalid") from None
            result = raw, {key: image[key] for key in supervisor.IMAGE_FIELDS}
        finish(event)
        return result

    def save(name, captured):
        event = begin(name + "_save")
        raw, image = captured
        atomic_write(Path(folder) / (name + ".jpg"), raw)
        report["images"][name] = dict(image, raw_file=name + ".jpg")
        finish(event)

    def recent(now):
        times = report["timings"]
        if not (0 <= now - times["capture_request_ns"] <= 3_000_000_000
                and 0 <= now - times["foreground_reply_ns"] <= 1_000_000_000):
            raise ProbeError("host_observation_expired")

    try:
        rpc("initial_info", "device_info")
        rpc("launch", "launch_app", {"bundle_id": GAME})
        rpc("pre_info", "device_info")
        before = rpc("before_capture", "screenshot", dict(CAPTURE_PARAMS))
        report["label"] = label_evidence(before[0])
        save("before", before)
        if not report["label"]["matched"]:
            raise ProbeError("pause_label_not_matched")
        rpc("before_info", "device_info")
        event = begin("batch")
        recent(clock())
        # Write intent BEFORE encryption/transport; a killed worker cannot leave a false zero.
        report.update(batch_attempts=1, tap_outcome="unknown")
        write_report(folder, report)
        try:
            budget = remaining()
            invoked = clock()
            recent(invoked)
        except ProbeError:
            report.update(batch_attempts=0, tap_outcome="not_requested")
            raise
        report["timings"]["batch_invoked_ns"] = invoked
        reply = client.call("run_steps", deepcopy(BATCH_PARAMS), timeout=budget)
        report["tap_outcome"], report["batch_result"] = batch_evidence(reply.result)
        finish(event)
        if report["tap_outcome"] != "acknowledged":
            raise ProbeError("batch_step_failed" if report["batch_result"]["shape_valid"] else "batch_reply_invalid")
        rpc("after_info", "device_info")
        after = rpc("after_capture", "screenshot", dict(CAPTURE_PARAMS))
        rpc("final_info", "device_info")
        save("after", after)
        report["image_bytes_changed"] = report["images"]["before"]["sha256"] != report["images"]["after"]["sha256"]
        report.update(status="completed", stage="complete", end_ns=clock())
    except ProbeError as exc:
        stop(report, exc.code, clock())
    except KeyboardInterrupt:
        stop(report, "user_interrupt", clock())
    except OSError:
        stop(report, "output_write_failed", clock())
    except Exception:
        stop(report, "internal_error", clock())
    try:
        write_report(folder, report)
    except OSError:
        stop(report, "output_write_failed", clock())
    return report


def validate_report(report, expected_run_id=None, expected_start_ns=None):
    """この試験専用の有界schema。親が子の任意文字列を再保存しない。"""
    require, keys, ns = supervisor.require, supervisor.keys, supervisor.ns
    keys(report, new_report(0, ""))
    for key, value in (("version", VERSION), ("kind", "resume_once_probe"), ("test_id", "TEST-013"),
                       ("revision", REVISION), ("device_acceptance", "not_tested")):
        require(report[key] == value)
    require(type(report["run_id"]) is str and re.fullmatch(r"[0-9a-f]{32}", report["run_id"]) is not None)
    require(expected_run_id is None or report["run_id"] == expected_run_id)
    ns(report["start_ns"]); ns(report["end_ns"], optional=True)
    require(expected_start_ns is None or report["start_ns"] == expected_start_ns)
    require(report["status"] in ("running", "completed", "stopped") and report["stage"] in STAGES)
    require(report["stop_reason"] is None or safe_code(report["stop_reason"]) == report["stop_reason"])
    require((report["status"] == "stopped") == (report["stop_reason"] is not None))
    require(report["status"] == "running" or report["end_ns"] is not None)
    require(report["end_ns"] is None or report["end_ns"] >= report["start_ns"])
    for key in ("resume_verified", "input_geometry_verified", "input_cancel_verified", "execution_deadline_verified"):
        require(report[key] is False)
    attempts, outcome = report["batch_attempts"], report["tap_outcome"]
    require(attempts is None or (type(attempts) is int and attempts in (0, 1)))
    require(type(outcome) is str and outcome in ("not_requested", "not_sent", "acknowledged", "unknown"))
    require((attempts == 0) == (outcome == "not_requested"))
    require(attempts is not None or outcome == "unknown")
    if report["batch_result"] is not None:
        detail = report["batch_result"]
        keys(detail, ("shape_valid", "completed", "failed_step", "wait_met", "tap_ok", "error_code"))
        require(type(detail["shape_valid"]) is bool and attempts == 1)
        for key, allowed in (("completed", (0, 1, 2)), ("failed_step", (0, 1))):
            require(detail[key] is None or (type(detail[key]) is int and detail[key] in allowed))
        for key in ("wait_met", "tap_ok"):
            require(detail[key] is None or type(detail[key]) is bool)
        code = detail["error_code"]
        require(code is None or (type(code) is int and -(2 ** 31) <= code < 2 ** 31))
        if detail["shape_valid"]:
            failed = detail["failed_step"]
            require(detail["completed"] == (2 if failed is None else failed))
            require(detail["wait_met"] is (failed != 0))
            require(detail["tap_ok"] is (None if failed == 0 else failed is None))
            require((code is None) == (failed is None))
            require(outcome == ("acknowledged" if failed is None else "not_sent" if failed == 0 else "unknown"))
        else:
            require(all(v is None for k, v in detail.items() if k != "shape_valid") and outcome == "unknown")
    else:
        require(outcome in ("not_requested", "unknown"))
    label = report["label"]
    if label is not None:
        keys(label, ("matched", "pixel_diff", "white_pixels"))
        require(type(label["matched"]) is bool)
        for key in ("pixel_diff", "white_pixels"):
            require(type(label[key]) is int and 0 <= label[key] <= 3584)
        require(label["matched"] == (label["pixel_diff"] <= 32 and 200 <= label["white_pixels"] <= 310))
    keys(report["images"], ("before", "after"))
    for name, image in report["images"].items():
        if image is not None:
            supervisor.validate_image(image, name)
            require(image["pixel_width"] == 896 and image["pixel_height"] == 414)
            geometry = image["reported_geometry"]
            require(geometry["source_orientation"] == 2 and geometry["point_width"] == 414 and geometry["point_height"] == 896)
    require(report["image_bytes_changed"] is None or type(report["image_bytes_changed"]) is bool)
    if report["image_bytes_changed"] is not None:
        require(all(report["images"].values()))
        require(report["image_bytes_changed"] == (report["images"]["before"]["sha256"] != report["images"]["after"]["sha256"]))
    keys(report["timings"], ("capture_request_ns", "foreground_reply_ns", "batch_invoked_ns"))
    for value in report["timings"].values(): ns(value, optional=True)
    require(type(report["events"]) is list and len(report["events"]) == len(STEPS))
    for stage, event in zip(STEPS, report["events"]):
        keys(event, ("stage", "status", "start_ns", "end_ns", "observation"))
        require(event["stage"] == stage and event["status"] in ("not_started", "running", "complete", "error"))
        ns(event["start_ns"], optional=True); ns(event["end_ns"], optional=True)
        require((event["start_ns"] is None) == (event["status"] == "not_started"))
        require((event["end_ns"] is not None) == (event["status"] in ("complete", "error")))
        require(event["end_ns"] is None or event["end_ns"] >= event["start_ns"])
        if event["observation"] is not None:
            require(stage.endswith("info")); supervisor.validate_info(event["observation"])
    require(report["crypto_engine"] in (None, "python", "native_i386"))
    if report["timer"] is not None:
        timer = report["timer"]
        keys(timer, ("backend", "poisoned", "closed", "cleanup_error"))
        require(timer["backend"] == "owned_itimer_real" and type(timer["poisoned"]) is bool and type(timer["closed"]) is bool)
        require(timer["cleanup_error"] in (None, "timer_cleanup_failed"))
    worker = report["worker"]
    keys(worker, new_report(0, "")["worker"])
    for key, low, high in (("returncode", -255, 255), ("signal_number", 1, 255), ("spawn_errno", 1, 4096)):
        require(worker[key] is None or (type(worker[key]) is int and low <= worker[key] <= high))
    for key in ("report_read_ok", "exit_confirmed"):
        require(worker[key] is None or type(worker[key]) is bool)
    require(worker["signal_name"] is None or worker["signal_name"] in {v.name for v in signal.Signals} | {"UNKNOWN_SIGNAL"})
    require(worker["cleanup_error"] in (None, "worker_cleanup_failed"))
    if worker["exit_confirmed"] is not None:
        require(worker["exit_confirmed"] == (worker["returncode"] is not None))
    if report["status"] == "completed":
        require(report["stage"] == "complete" and outcome == "acknowledged" and all(report["images"].values()))
        require(all(e["status"] == "complete" for e in report["events"]))


def read_checkpoint(path, *, expected_run_id=None, expected_start_ns=None):
    try:
        with Path(path).open("rb") as stream:
            report = json_object(stream.read(MAX_REPORT + 1), MAX_REPORT)
        validate_report(report, expected_run_id, expected_start_ns)
        return report
    except (OSError, ValueError, TypeError, KeyError, OverflowError, RecursionError, ProbeError):
        raise ValueError("report_read_failed") from None


def parser():
    ap = argparse.ArgumentParser(description="TEST-013: 続行の固定候補点を最大1回試す。自動周回なし。")
    ap.add_argument("--output", default="runtime/test-013")
    ap.add_argument("--token-store", default=str(Path.home() / ".loopctrl/token.json"))
    ap.add_argument("--store-key", default=None)
    ap.add_argument("--python-crypto", action="store_true")
    ap.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    ap.add_argument("--stop-ns", type=int, default=0, help=argparse.SUPPRESS)
    ap.add_argument("--start-ns", type=int, default=None, help=argparse.SUPPRESS)
    ap.add_argument("--run-id", default=None, help=argparse.SUPPRESS)
    return ap


def worker(args):
    folder = Path(args.output)
    try:
        supervisor.ns(args.start_ns)
        report = read_checkpoint(folder / "report.json", expected_run_id=args.run_id, expected_start_ns=args.start_ns)
        supervisor.require(report["status"] == "running" and report["stage"] == "spawn_requested" and report["batch_attempts"] == 0)
    except ValueError:
        return supervisor.WORKER_REPORT_READ_EXIT
    timer = None
    def stage(name):
        report["stage"] = name
        write_report(folder, report)
    try:
        stage("pairing_load")
        key, tok = load_pairing(args.token_store, args.store_key)
        stage("crypto_initialize")
        crypto = Crypto(native=not args.python_crypto)
        report["crypto_engine"] = crypto.engine
        stage("timer_initialize")
        timer = OwnedRpcTimer()
        with timer:
            client = ResumeOnceClient(HttpTransport(), key, tok, timeout=8, crypto=crypto, deadline_owner=timer)
            collect(client, report, folder, args.stop_ns)
    except ProbeError as exc:
        stop(report, exc.code)
    except KeyboardInterrupt:
        stop(report, "user_interrupt")
    except OSError:
        stop(report, "output_write_failed")
    except Exception:
        stop(report, "internal_error")
    finally:
        if timer is not None:
            report["timer"] = timer.diagnostics()
    report["end_ns"] = time.monotonic_ns()
    try:
        write_report(folder, report)
    except OSError:
        return 2
    return 0


def run(args):
    if os.name != "posix" or not hasattr(signal, "setitimer"):
        raise ProbeError("posix_timer_required")
    if args.worker:
        return worker(args)
    base = Path(args.output).resolve()
    base.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex
    folder = base / ("resume-once-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + run_id[:8])
    folder.mkdir(mode=0o700)
    start = time.monotonic_ns()
    report = new_report(start, run_id)
    write_report(folder, report)
    command = [sys.executable, "-m", "necroprobe.resume_once", "--worker", "--output", str(folder),
               "--start-ns", str(start), "--run-id", run_id, "--token-store", args.token_store,
               "--stop-ns", str(start + SESSION_SECONDS * 1_000_000_000)]
    if args.store_key is not None: command.extend(["--store-key", args.store_key])
    if args.python_crypto: command.append("--python-crypto")
    diagnostics = {}
    print("TEST-013: ゲームを開き、続行候補点を最大1回試します。ゲームを表示したまま待ってください。", flush=True)
    reason = supervisor.supervise(command, max(.001, SESSION_SECONDS - (time.monotonic_ns() - start) / 1e9), diagnostics)
    try:
        report = read_checkpoint(folder / "report.json", expected_run_id=run_id, expected_start_ns=start)
        report["worker"]["report_read_ok"] = True
    except ValueError:
        # A worker may already have sent input. An unreadable checkpoint is not evidence of zero.
        report.update(batch_attempts=None, tap_outcome="unknown")
        report["worker"]["report_read_ok"] = False
        reason = reason or "report_read_failed"
    for key in ("returncode", "signal_number", "signal_name", "spawn_errno", "exit_confirmed", "cleanup_error"):
        report["worker"][key] = diagnostics.get(key)
    if diagnostics.get("exit_confirmed") is False and report["batch_attempts"] == 0:
        # A still-running child could send after this checkpoint was read.
        report.update(batch_attempts=None, tap_outcome="unknown")
    if diagnostics.get("exit_confirmed") is False or diagnostics.get("cleanup_error") is not None:
        reason = "worker_cleanup_failed"
    if reason:
        stop(report, reason)
    elif report["status"] == "running":
        stop(report, "worker_failed")
    report["end_ns"] = time.monotonic_ns()
    write_report(folder, report, "parent-result.json")
    if report["worker"]["exit_confirmed"] is not False:
        write_report(folder, report)
    count = "不明" if report["batch_attempts"] is None else str(report["batch_attempts"])
    print("batch試行: " + count + " / tap結果: " + report["tap_outcome"] + " / 終了理由: " + (report["stop_reason"] or "completed"), flush=True)
    print("続行成功・一般入力座標・端末側取消は未確認。終了後は手動でポーズしてください。", flush=True)
    print("保存先: " + str(folder) + " / 最終結果: parent-result.json", flush=True)
    if report["worker"]["exit_confirmed"] is False:
        print("子プロセスの終了は未確認です。結果保存後にiSHを終了してください。", flush=True)
    return 0 if report["status"] == "completed" else 2


def main(argv=None):
    args = parser().parse_args(argv)
    previous = {}
    if not args.worker:
        supervisor._cancel_requested = False
        def interrupted(_signum, _frame):
            supervisor._cancel_requested = True
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.getsignal(signum)
            signal.signal(signum, interrupted)
    try:
        return run(args)
    except ProbeError as exc:
        print("TEST-013停止: " + safe_code(exc.code), file=sys.stderr)
        return 2
    except OSError:
        print("TEST-013: 結果を保存できませんでした。", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("TEST-013: 中断しました。", file=sys.stderr)
        return 130
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


if __name__ == "__main__":
    raise SystemExit(main())
