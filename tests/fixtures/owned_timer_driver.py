"""Test-only real parent/worker lifecycle with iSH old-value fault injection."""
import os
from pathlib import Path
import signal
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]
from necroprobe import __main__ as cli
from necroprobe.deadlines import OwnedRpcTimer
from necroprobe.protocol import HttpTransport
from test_protocol import KEY, TOK


class UnreadableOldValue:
    def __eq__(self, _):
        raise AssertionError("old timer value read")
    __ne__ = __eq__
    def __iter__(self):
        raise AssertionError("old timer value restored")
    def __bool__(self):
        raise AssertionError("old timer value tested")


def pending():
    with OwnedRpcTimer() as timer:
        for _ in range(2):
            previous = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
            with timer.deadline(1):
                signal.raise_signal(signal.SIGALRM)
            signal.pthread_sigmask(signal.SIG_SETMASK, previous)
        previous = signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGALRM})
        signal.raise_signal(signal.SIGALRM)
    signal.pthread_sigmask(signal.SIG_SETMASK, previous)
    print("pending_survived")
    return 0


def worker(mode, port, arguments):
    cli.load_pairing = lambda *_: (KEY, TOK)
    cli.HttpTransport = lambda: HttpTransport(int(port))
    real = signal.setitimer
    armed = False
    def injected(which, seconds, interval=0):
        nonlocal armed
        if mode == "init_failure" or (mode == "interrupt_cleanup" and armed and seconds == 0):
            raise OSError("PRIVATE_TIMER_ERROR")
        real(which, seconds, interval)
        if seconds:
            armed = True
            if mode == "interrupt_cleanup":
                raise KeyboardInterrupt()
        return UnreadableOldValue()
    signal.setitimer = injected
    def unsupported(*_):
        os.kill(os.getpid(), signal.SIGSYS)
    signal.getitimer = unsupported
    return cli.main(arguments)


def main():
    if sys.argv[1] == "pending":
        return pending()
    if sys.argv[1] == "worker":
        return worker(sys.argv[2], sys.argv[3], sys.argv[4:])
    mode, port, destination = sys.argv[1:]
    real_supervise = cli.supervise
    def injected(command, timeout, diagnostics=None):
        child = [sys.executable, str(Path(__file__).resolve()), "worker", mode, port] + command[3:]
        return real_supervise(child, timeout, diagnostics)
    cli.supervise = injected
    return cli.main(["capture", "--launch-game", "--python-crypto", "--samples", "12",
                     "--seconds", "10", "--output", destination])


if __name__ == "__main__":
    raise SystemExit(main())
