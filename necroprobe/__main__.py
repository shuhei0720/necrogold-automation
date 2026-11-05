"""iPhoneのLoopCtrl取得経路を計測するCLI。"""
import argparse
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

from . import VERSION
from .capture import inspect_bytes
from .crypto import Crypto
from .deadlines import OwnedRpcTimer
from .protocol import Client, HttpTransport, load_pairing
from .session import VARIANTS, collect, finish, new_report, output_failed, stop_report, write_report
from .validation import ProbeError

WORKER_REPORT_READ_EXIT = 74
WORKER_STAGES = {"spawn_requested", "pairing_load", "crypto_initialize", "timer_initialize", "capture_collection"}


def read_checkpoint(path, samples):
    """Validate fields consumed by finalization before replacing the initial plan."""
    def finite_float(value):
        result = float(value)
        if not math.isfinite(result):
            raise ValueError()
        return result

    def reject_constant(_value):
        raise ValueError()

    def valid_ns(value):
        return type(value) is int and 0 <= value < 2 ** 64

    try:
        with Path(path).open("rb") as file:
            raw = file.read(4 * 1024 * 1024 + 1)
        if len(raw) > 4 * 1024 * 1024:
            raise ValueError()
        report = json.loads(raw, parse_float=finite_float, parse_constant=reject_constant)
        if not isinstance(report, dict) or not valid_ns(report.get("start_ns")):
            raise ValueError()
        if report.get("status") not in ("running", "stopped", "completed"):
            raise ValueError()
        state = report.get("worker")
        if not isinstance(state, dict) or state.get("stage") not in tuple(WORKER_STAGES):
            raise ValueError()
        rows, events = report.get("rows"), report.get("events")
        if not isinstance(rows, list) or len(rows) != samples or not isinstance(events, list):
            raise ValueError()
        for index, row in enumerate(rows):
            if not isinstance(row, dict) or type(row.get("trial")) is not int or row["trial"] != index + 1:
                raise ValueError()
            if row.get("variant") != VARIANTS[index % 3][0] or row.get("status") not in ("not_started", "in_progress", "complete", "error", "interrupted"):
                raise ValueError()
            times, img = row.get("timings", {}), row.get("image", {})
            if not isinstance(times, dict) or not isinstance(img, dict):
                raise ValueError()
            if any(not valid_ns(value) for name, value in times.items() if name.endswith("_ns")):
                raise ValueError()
            if row["status"] == "complete" and img.get("image_status") not in ("blank_or_dark", "decoded_nonblank"):
                raise ValueError()
        if any(not isinstance(event, dict) for event in events):
            raise ValueError()
        return report
    except (OSError, ValueError, TypeError, KeyError, RecursionError):
        raise ValueError("report_read_failed") from None


def supervise(command, timeout, diagnostics=None):
    """A separate process makes native decode/crypto hangs terminable too."""
    details = diagnostics if diagnostics is not None else {}
    details.update(returncode=None, signal_number=None, signal_name=None)
    try:
        process = subprocess.Popen(command, stderr=subprocess.DEVNULL)
    except OSError as exc:
        details["spawn_errno"] = exc.errno if type(exc.errno) is int else None
        return "worker_start_failed"
    reason = None
    try:
        code = process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        reason = "session_deadline"
    except KeyboardInterrupt:
        reason = "user_interrupt"
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=.3)
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                process.kill()
                process.wait(timeout=1)
        details["returncode"] = process.returncode
        if process.returncode is not None and process.returncode < 0:
            details["signal_number"] = -process.returncode
            try:
                details["signal_name"] = signal.Signals(-process.returncode).name
            except ValueError:
                details["signal_name"] = "UNKNOWN_SIGNAL"
    if reason:
        return reason
    return None if code == 0 else "worker_failed"


def positive_int(value):
    result = int(value)
    if not 1 <= result <= 600:
        raise argparse.ArgumentTypeError("1〜600を指定してください")
    return result


def seconds(value):
    result = float(value)
    if not .1 <= result <= 600:
        raise argparse.ArgumentTypeError("0.1〜600秒を指定してください")
    return result


def parser():
    ap = argparse.ArgumentParser(description="P1画像取得診断。ゲームへのタップは行いません。")
    sub = ap.add_subparsers(dest="command", required=True)
    capture = sub.add_parser("capture", help="既存の端末内LoopCtrl接続で画像を取得")
    capture.add_argument("--launch-game", action="store_true", help="最初にゲームを1回だけ開く（続行は押さない）")
    capture.add_argument("--samples", type=positive_int, default=12)
    capture.add_argument("--seconds", type=seconds, default=45)
    capture.add_argument("--rpc-timeout", type=seconds, default=8)
    capture.add_argument("--token-store", default=str(Path.home() / ".loopctrl/token.json"))
    capture.add_argument("--store-key", default=None)
    capture.add_argument("--python-crypto", action="store_true")
    capture.add_argument("--output", default="runtime")
    capture.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    capture.add_argument("--stop-ns", type=int, default=0, help=argparse.SUPPRESS)
    inspect = sub.add_parser("inspect", help="保存済みの画像を通信せず検査")
    inspect.add_argument("images", nargs="+")
    return ap


def worker(args):
    folder = Path(args.output)
    timer = None
    try:
        report = read_checkpoint(folder / "report.json", args.samples)
    except ValueError:
        print("子プロセス: worker_report_read_failed", flush=True)
        return WORKER_REPORT_READ_EXIT
    state = report.setdefault("worker", {"stage": "spawn_requested"})

    def checkpoint_stage(stage):
        previous = state["stage"]
        state["stage"] = stage
        try:
            write_report(folder, report)
        except OSError:
            state["stage"] = previous
            state["checkpoint_error"] = stage
            output_failed(report)
            raise ProbeError("output_write_failed") from None

    try:
        checkpoint_stage("pairing_load")
        key, tok = load_pairing(args.token_store, args.store_key)
        checkpoint_stage("crypto_initialize")
        crypto = Crypto(native=not args.python_crypto)
        report["crypto_engine"] = crypto.engine
        checkpoint_stage("timer_initialize")
        timer = OwnedRpcTimer()
        with timer:
            client = Client(HttpTransport(), key, tok, timeout=args.rpc_timeout,
                            allow_launch=args.launch_game, crypto=crypto, deadline_owner=timer)
            checkpoint_stage("capture_collection")
            collect(client, report, folder, args.stop_ns)
    except ProbeError as exc:
        stop_report(report, exc.code)
    except KeyboardInterrupt:
        stop_report(report, "user_interrupt")
    except Exception as exc:
        stop_report(report, "internal_error")
        # Class names from arbitrary exceptions and exception messages can contain secrets.
        known = (OSError, ValueError, TypeError, RuntimeError, MemoryError, ImportError,
                 AttributeError, KeyError, OverflowError)
        state["exception_type"] = type(exc).__name__ if type(exc) in known else "Exception"
    finally:
        if timer is not None:
            report["timer"] = timer.diagnostics()
    finish(report, time.monotonic_ns())
    try:
        write_report(folder, report)
    except OSError:
        print("結果の保存に失敗しました。停止理由: " + report["stop_reason"], flush=True)
        return 2
    return 0


def run_capture(args):
    if args.rpc_timeout > 30:
        raise ProbeError("rpc_timeout_max_30")
    if os.name != "posix" or not hasattr(signal, "setitimer"):
        raise ProbeError("posix_timer_required")
    if args.worker:
        return worker(args)
    base = Path(args.output).resolve()
    base.mkdir(parents=True, exist_ok=True)
    folder = base / ("probe-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    folder.mkdir(mode=0o700)
    start = time.monotonic_ns()
    report = new_report(args.samples, start)
    report["worker"] = {"stage": "spawn_requested"}
    write_report(folder, report)
    command = [sys.executable, "-m", "necroprobe", "capture", "--worker", "--output", str(folder),
               "--samples", str(args.samples), "--seconds", str(args.seconds),
               "--rpc-timeout", str(args.rpc_timeout), "--token-store", args.token_store,
               "--stop-ns", str(start + int(args.seconds * 1e9))]
    if args.store_key:
        command.extend(["--store-key", args.store_key])
    if args.launch_game:
        command.append("--launch-game")
    if args.python_crypto:
        command.append("--python-crypto")
    print("%s 画像取得の診断版です。操作サイトは起動しません。" % VERSION, flush=True)
    print("「ゲームを続行」は押しません。タップ・オプション操作は行いません。", flush=True)
    diagnostics = {}
    try:
        reason = supervise(command, max(.001, args.seconds - (time.monotonic_ns() - start) / 1e9), diagnostics)
        if reason == "worker_failed" and diagnostics.get("returncode") == WORKER_REPORT_READ_EXIT:
            reason = "worker_report_read_failed"
        report_read_ok = False
        try:
            report = read_checkpoint(folder / "report.json", args.samples)
            report_read_ok = True
        except ValueError:
            reason = reason or "report_read_failed"
        state = report.setdefault("worker", {"stage": "spawn_requested"})
        state.update(process=diagnostics, report_read_ok=report_read_ok)
        if not report_read_ok:
            state["report_read_error"] = "report_read_failed"
            print("子の記録を読めません。件数は開始時の予定を表示します。", flush=True)
        finish(report, time.monotonic_ns(), reason)
        write_report(folder, report)
    except OSError:
        print("結果の保存に失敗しました。停止理由: " + str(report.get("stop_reason", "output_write_failed")), file=sys.stderr)
        return 2
    summary = report["summary"]
    print("診断終了: %s / 取得完了 %d/%d / エラー %d / 未実施 %d" % (
        report.get("stop_reason", report["status"]), summary["complete"], summary["planned"],
        summary["errors"], summary["not_started"]), flush=True)
    print("保存先: " + str(folder), flush=True)
    print("子プロセス: 段階=%s / 終了コード=%s / シグナル=%s" % (
        report["worker"]["stage"], diagnostics.get("returncode"), diagnostics.get("signal_name")), flush=True)
    print("report.jsonと保存画像が診断資料です。実機の自動周回は未検証です。", flush=True)
    return 0 if report["status"] == "completed" and summary["complete"] == summary["planned"] else 2


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "capture":
            return run_capture(args)
        results = []
        for name in args.images:
            try:
                with Path(name).open("rb") as file:
                    raw = file.read(4 * 1024 * 1024 + 1)
                result = inspect_bytes(raw)
                results.append({"file": Path(name).name, "result": result})
            except (ProbeError, OSError) as exc:
                results.append({"file": Path(name).name, "error": exc.code if isinstance(exc, ProbeError) else "image_read_failed"})
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 2 if any("error" in result for result in results) else 0
    except ProbeError as exc:
        print("診断を停止しました: " + exc.code, file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("診断を中断しました。", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
