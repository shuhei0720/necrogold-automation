"""Test-only fault injection into the real CLI/worker lifecycle; never a device test."""
import base64
import io
import json
import os
from pathlib import Path
import signal
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from PIL import Image
from necroprobe import __main__ as cli
from necroprobe import session
from necroprobe.protocol import RpcReply


def block(marker, phase):
    marker.write_text(json.dumps({"pid": os.getpid(), "phase": phase}))
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    while True:
        time.sleep(1)


def worker_harness(phase, marker, arguments):
    with io.BytesIO() as stream:
        Image.new("RGB", (20, 40), "white").save(stream, "PNG")
        data = base64.b64encode(stream.getvalue()).decode()
    class BlockingClient:
        def __init__(self, *args, **kwargs):
            self.timeout = 8
            self.allow_launch = False
            self.crypto = type("TestCrypto", (), {"engine": "synthetic-test"})()
            self.count = 0
        def call(self, method, params=None, timeout=None):
            if method == "device_info":
                return RpcReply({}, {})
            if method != "screenshot":
                raise AssertionError("Unexpected operation in measurement test")
            self.count += 1
            if self.count == 2 and phase == "rpc":
                block(marker, phase)
            return RpcReply({"data": data, "point_width": 414, "point_height": 896}, {})
    cli.Client = BlockingClient
    cli.load_pairing = lambda *_: (b"test-key" * 4, "test-tok")
    real_inspect = session.inspect_payload
    inspect_count = [0]
    def interrupted_inspect(payload):
        inspect_count[0] += 1
        if inspect_count[0] == 2 and phase == "decode":
            block(marker, phase)
        return real_inspect(payload)
    session.inspect_payload = interrupted_inspect
    real_atomic_write = session.atomic_write
    image_count = [0]
    def interrupted_write(path, raw):
        if Path(path).suffix == ".png":
            image_count[0] += 1
            if image_count[0] == 2 and phase == "save":
                block(marker, phase)
        return real_atomic_write(path, raw)
    session.atomic_write = interrupted_write
    return cli.main(arguments)


def main():
    if sys.argv[1] == "worker":
        return worker_harness(sys.argv[2], Path(sys.argv[3]), sys.argv[4:])
    phase, destination, seconds = sys.argv[1:]
    marker = Path(destination) / "blocked.json"
    real_supervise = cli.supervise
    def supervised_test_worker(command, timeout, diagnostics=None):
        injected = [sys.executable, str(Path(__file__).resolve()), "worker", phase, str(marker)] + command[3:]
        return real_supervise(injected, timeout, diagnostics)
    cli.supervise = supervised_test_worker
    return cli.main(["capture", "--output", destination, "--samples", "6", "--seconds", seconds, "--python-crypto"])


if __name__ == "__main__":
    raise SystemExit(main())
