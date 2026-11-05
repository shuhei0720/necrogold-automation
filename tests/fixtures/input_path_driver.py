"""本物の親子監視へ停止不能な合成処理を挿入する専用fixture。"""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from necroprobe import input_path as probe
from input_path_support import FakeClient


def main():
    if sys.argv[1] == "worker":
        phase, marker = sys.argv[2:4]
        client = FakeClient()
        def block():
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            pending = Path(marker).with_suffix(".pending")
            pending.write_text(json.dumps({"pid": os.getpid(), "calls": len(client.calls)}))
            os.replace(pending, marker)
            while True:
                time.sleep(1)
        original_call = client.call
        def call(method, params=None, timeout=None):
            with Path(marker).with_name("rpc-calls.jsonl").open("a") as stream:
                stream.write(json.dumps({"method": method}) + "\n")
            result = original_call(method, params, timeout)
            if method == "find_element" and phase == "rpc":
                block()
            return result
        client.call = call
        probe.InputPathClient = lambda *args, **kwargs: client
        probe.load_pairing = lambda *_: (b"test-key" * 4, "test-tok")
        original_inspect = probe.inspect_payload
        def inspect(payload):
            if phase == "decode":
                block()
            return original_inspect(payload)
        probe.inspect_payload = inspect
        original_write = probe.atomic_write
        def write(path, raw):
            if Path(path).suffix == ".jpg" and phase == "save":
                block()
            return original_write(path, raw)
        probe.atomic_write = write
        return probe.main(sys.argv[4:])
    phase, folder, mode = sys.argv[1:]
    if phase == "spawn":
        original_popen = subprocess.Popen
        def interrupted_spawn(command, **kwargs):
            # 無出力の子なのでpipeを継承させず、親の異常終了を直ちに観測する。
            kwargs["stdout"] = subprocess.DEVNULL
            process = original_popen([sys.executable, "-c", "import time; time.sleep(60)"], **kwargs)
            Path(folder, "blocked.json").write_text(json.dumps({"pid": process.pid, "calls": 0}))
            os.kill(os.getpid(), signal.SIGTERM if mode == "term" else signal.SIGINT)
            return process
        subprocess.Popen = interrupted_spawn
        return probe.main(["--output", folder, "--python-crypto"])
    original_supervise = probe.supervise
    def supervise(command, timeout, diagnostics):
        command = [sys.executable, str(Path(__file__).resolve()), "worker", phase, str(Path(folder) / "blocked.json")] + command[3:]
        return original_supervise(command, 2 if mode == "deadline" else 15, diagnostics)
    probe.supervise = supervise
    return probe.main(["--output", folder, "--python-crypto"])


if __name__ == "__main__":
    raise SystemExit(main())
