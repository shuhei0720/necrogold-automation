"""専用workerのITIMER_REALを所有する。汎用タイマーの保存・復元APIではない。"""
from contextlib import contextmanager
import os
import signal
import threading
import time

from .validation import ProbeError, number

_owner = None


class OwnedRpcTimer:
    """Create only in the freshly started worker's main thread (or isolated tests).

    iSH's setitimer old-value result may be uninitialized or negative after disarm.
    Never inspect or restore it. Ownership comes from the isolated worker lifecycle,
    not from querying that result or merely seeing a default signal handler.
    """

    def __init__(self):
        self._started = self._ready = self._closed = self._poisoned = False
        self._pid = self._thread = self._expires = None
        self._cleanup_error = None
        self._handler = self._on_alarm

    def __enter__(self):
        global _owner
        if self._started or _owner is not None:
            raise ProbeError("timer_already_in_use")
        if threading.current_thread() is not threading.main_thread():
            raise ProbeError("timer_unusable")
        if not hasattr(signal, "setitimer"):
            raise ProbeError("posix_timer_required")
        if signal.getsignal(signal.SIGALRM) not in (signal.SIG_DFL, signal.SIG_IGN):
            raise ProbeError("timer_handler_in_use")
        self._started = True
        self._pid, self._thread = os.getpid(), threading.get_ident()
        _owner = self
        try:
            signal.signal(signal.SIGALRM, self._handler)
            signal.setitimer(signal.ITIMER_REAL, 0)
        except BaseException as exc:
            self._poisoned = True
            try:
                self.close()
            except ProbeError:
                pass
            if isinstance(exc, (OSError, ValueError)):
                raise ProbeError("timer_setup_failed") from None
            raise
        self._ready = True
        return self

    def _check(self):
        if (not self._ready or self._closed or self._poisoned or _owner is not self
                or self._pid != os.getpid() or self._thread != threading.get_ident()):
            raise ProbeError("timer_unusable")
        if signal.getsignal(signal.SIGALRM) is not self._handler:
            self._poisoned = True
            raise ProbeError("timer_handler_in_use")

    def _on_alarm(self, _signum, _frame):
        # A previous RPC's signal can arrive after disarm or during a later RPC.
        # A signal is only a wakeup; the current monotonic deadline decides expiry.
        if self._expires is None:
            return
        remaining = self._expires - time.monotonic()
        if remaining <= 0:
            raise ProbeError("rpc_deadline")
        # The one-shot timer itself may have fired early (iSH uses realtime).
        # Restore the remaining monotonic budget, even for an old late signal.
        try:
            signal.setitimer(signal.ITIMER_REAL, remaining)
        except (OSError, ValueError):
            self._poisoned = True
            raise ProbeError("timer_setup_failed") from None

    @contextmanager
    def deadline(self, seconds):
        number(seconds, .001, 60)
        self._check()
        if self._expires is not None:
            raise ProbeError("timer_already_in_use")
        self._expires = time.monotonic() + seconds
        propagating = False
        try:
            try:
                signal.setitimer(signal.ITIMER_REAL, seconds)
            except (OSError, ValueError):
                self._poisoned = True
                raise ProbeError("timer_setup_failed") from None
            yield
            # Do not accept a late result if signal delivery was deferred.
            if time.monotonic() >= self._expires:
                raise ProbeError("rpc_deadline")
        except BaseException:
            propagating = True
            raise
        finally:
            self._expires = None
            try:
                signal.setitimer(signal.ITIMER_REAL, 0)
            except (OSError, ValueError):
                self._poisoned = True
                self._cleanup_error = "timer_cleanup_failed"
                if not propagating:
                    raise ProbeError("timer_cleanup_failed") from None

    def close(self):
        global _owner
        if not self._started or self._closed:
            return
        if self._pid != os.getpid() or self._thread != threading.get_ident():
            raise ProbeError("timer_unusable")
        self._expires = None
        self._ready = False
        self._closed = True
        failed = False
        try:
            signal.setitimer(signal.ITIMER_REAL, 0)
        except (OSError, ValueError):
            failed = True
        finally:
            try:
                # This dedicated worker is ending. A late signal must not invoke
                # SIG_DFL and kill it while the final report is being saved.
                signal.signal(signal.SIGALRM, signal.SIG_IGN)
            except (OSError, ValueError):
                failed = True
            if _owner is self:
                _owner = None
        if failed:
            self._poisoned = True
            self._cleanup_error = "timer_cleanup_failed"
            raise ProbeError("timer_cleanup_failed") from None

    def __exit__(self, exc_type, _exc, _traceback):
        try:
            self.close()
        except ProbeError:
            if exc_type is None:
                raise
        return False

    def diagnostics(self):
        return {"backend": "owned_itimer_real", "poisoned": self._poisoned,
                "closed": self._closed, "cleanup_error": self._cleanup_error}
