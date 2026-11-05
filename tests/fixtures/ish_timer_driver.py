"""Host-only syscall fault injection; this is NOT an iSH emulator."""
import os
from pathlib import Path
import resource
import signal
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from necroprobe.crypto import Crypto
from necroprobe.protocol import Client
from test_protocol import KEY, TOK, sealed_reply


def unsupported_getitimer(*_):
    os.kill(os.getpid(), signal.SIGSYS)
    raise AssertionError("SIGSYS was ignored")


resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
signal.getitimer = unsupported_getitimer
reply = Client(lambda body, timeout: sealed_reply(body, result={"ok": True}),
               KEY, TOK, crypto=Crypto(native=False)).call("device_info")
assert reply.result == {"ok": True}
print("authenticated_reply_received")
