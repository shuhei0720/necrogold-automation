"""iPhoneのLoopCtrl取得経路を計測するCLI。"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import uuid

from .capture import inspect_bytes
from .crypto import Crypto
from .protocol import Client, HttpTransport, load_pairing
from .session import collect, finish, new_report, output_failed, stop_report, write_report
from .validation import ProbeError


def supervise(command, timeout):
    """A separate process makes native decode/crypto hangs terminable too."""
    process = subprocess.Popen(command, stderr=subprocess.DEVNULL)
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
    with (folder / "report.json").open(encoding="utf-8") as file:
        report = json.load(file)
    try:
        key, tok = load_pairing(args.token_store, args.store_key)
        client = Client(HttpTransport(), key, tok, timeout=args.rpc_timeout,
                        allow_launch=args.launch_game, crypto=Crypto(native=not args.python_crypto))
        report["crypto_engine"] = client.crypto.engine
        collect(client, report, folder, args.stop_ns)
        return 0
    except ProbeError as exc:
        stop_report(report, exc.code)
    except KeyboardInterrupt:
        stop_report(report, "user_interrupt")
    except OSError:
        output_failed(report)
    except Exception:
        stop_report(report, "internal_error")
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
    print("画像取得の診断を開始します。タップ・オプション操作は行いません。", flush=True)
    try:
        reason = supervise(command, max(.001, args.seconds - (time.monotonic_ns() - start) / 1e9))
        try:
            with (folder / "report.json").open("rb") as file:
                raw = file.read(4 * 1024 * 1024 + 1)
            if len(raw) > 4 * 1024 * 1024:
                raise ValueError()
            report = json.loads(raw)
        except (OSError, ValueError):
            reason = reason or "report_read_failed"
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
