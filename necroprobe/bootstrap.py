"""Isolated worker fork without re-importing the already prepared runtime.

The caller uses this only before parent pairing/client/lock/timer creation.
Unsupported or unsafe parent states retain the existing exec path. Once a child
exists, it is owned until reaped; no second worker may be started for that job.
"""
import errno
import math
import os
import signal
import subprocess
import sys
import threading
import time


_MAX_FDS = 4096
_CONTROL_SIGNALS = (signal.SIGINT, signal.SIGTERM)


def _fork_ready():
    if not callable(getattr(os, 'fork', None)) or not callable(getattr(signal, 'pthread_sigmask', None)):
        return False
    if threading.current_thread() is not threading.main_thread() or threading.active_count() != 1:
        return False
    timer_module = sys.modules.get('necroprobe.deadlines')
    if timer_module is not None and getattr(timer_module, '_owner', None) is not None:
        return False
    try:
        if signal.getsignal(signal.SIGALRM) not in (signal.SIG_DFL, signal.SIG_IGN):
            return False
        # A custom/ignored SIGCHLD could reap the child outside this adapter and
        # allow PID reuse between checking it and sending a signal.
        if signal.getsignal(signal.SIGCHLD) != signal.SIG_DFL:
            return False
    except (AttributeError, OSError, ValueError):
        return False
    return True


def _descriptor_snapshot():
    entries = os.listdir('/proc/self/fd')
    if len(entries) > _MAX_FDS:
        raise OSError(errno.EMFILE, 'worker descriptor enumeration unavailable')
    descriptors = []
    listed = set()
    for entry in entries:
        if not entry.isdecimal():
            raise OSError(errno.EIO, 'worker descriptor enumeration unavailable')
        descriptor = int(entry)
        listed.add(descriptor)
        if descriptor < 3:
            continue
        try:
            os.fstat(descriptor)
        except OSError as exc:
            if exc.errno == errno.EBADF:
                continue  # The listdir directory descriptor has already closed.
            raise
        descriptors.append(descriptor)
    # An emulated /proc may exist but provide no useful FD enumeration. Verify
    # the known open standard descriptors before trusting it for close_fds.
    for descriptor in (0, 1, 2):
        try:
            os.fstat(descriptor)
        except OSError as exc:
            if exc.errno != errno.EBADF:
                raise
        else:
            if descriptor not in listed:
                raise OSError(errno.EIO, 'worker descriptor enumeration unavailable')
    return tuple(sorted(descriptors))


class ForkProcess:
    """The bounded Popen subset used by input_path.supervise.

    Parent control signals stay blocked until the supervisor has stored this
    object. activate() then restores them, so an interrupt cannot lose the PID
    between fork returning and assignment in the supervisor.
    """
    def __init__(self, parent_pid, mask):
        self.pid = None
        self.returncode = None
        self.args = ('isolated-worker',)
        self._parent_pid = parent_pid
        self._mask = mask
        self._lost = False
        self._mask_failed = False

    def activate(self):
        if self._mask is not None:
            try:
                signal.pthread_sigmask(signal.SIG_SETMASK, self._mask)
            except OSError:
                self._mask_failed = True
                raise
            self._mask = None
            self._mask_failed = False

    def finalize(self):
        # Retry restoration after bounded child cleanup if the first OS call failed.
        self.activate()

    def _activate_for_operation(self):
        if not self._mask_failed:
            self.activate()

    def _owned(self):
        if (os.getpid() != self._parent_pid or type(self.pid) is not int or self.pid <= 0
                or self.pid == self._parent_pid or self._lost):
            raise OSError(errno.ECHILD, 'worker ownership unavailable')

    def poll(self):
        self._activate_for_operation()
        self._owned()
        if self.returncode is not None:
            return self.returncode
        try:
            child, status = os.waitpid(self.pid, os.WNOHANG)
        except ChildProcessError:
            self._lost = True
            raise OSError(errno.ECHILD, 'worker ownership unavailable') from None
        except OSError as exc:
            if exc.errno == errno.ECHILD:
                self._lost = True
            raise
        if child == 0:
            return None
        if child != self.pid:
            self._lost = True
            raise OSError(errno.ECHILD, 'worker ownership unavailable')
        if os.WIFEXITED(status):
            self.returncode = os.WEXITSTATUS(status)
        elif os.WIFSIGNALED(status):
            self.returncode = -os.WTERMSIG(status)
        else:
            self._lost = True
            raise OSError(errno.ECHILD, 'worker ownership unavailable')
        return self.returncode

    def wait(self, timeout=None):
        if type(timeout) not in (int, float) or not math.isfinite(timeout) or timeout < 0:
            raise ValueError('worker wait requires a finite timeout')
        self._activate_for_operation()
        expires = time.monotonic() + timeout
        while True:
            result = self.poll()
            if result is not None:
                return result
            remaining = expires - time.monotonic()
            if remaining <= 0:
                raise subprocess.TimeoutExpired(self.args, timeout)
            time.sleep(min(.01, remaining))

    def _send(self, signum):
        self._activate_for_operation()
        self._owned()
        if self.poll() is not None:
            return
        try:
            os.kill(self.pid, signum)
        except ProcessLookupError:
            # With default SIGCHLD, our unreaped child retains its PID. Read its
            # exit state instead of treating disappearance as permission to retry.
            self.poll()

    def terminate(self):
        self._send(signal.SIGTERM)

    def kill(self):
        self._send(signal.SIGKILL)


def _child_exit(child, descriptors, mask):
    code = 70
    try:
        signal.signal(signal.SIGINT, signal.default_int_handler)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGALRM, signal.SIG_DFL)
        for descriptor in descriptors:
            try:
                os.close(descriptor)
            except OSError as exc:
                if exc.errno != errno.EBADF:
                    raise
        null = os.open(os.devnull, os.O_WRONLY)
        try:
            os.dup2(null, 2)
        finally:
            if null > 2:
                os.close(null)
        signal.pthread_sigmask(signal.SIG_SETMASK, mask)
        value = child()
        code = 0 if value is None else value if type(value) is int and 0 <= value <= 255 else 70
    except SystemExit as exc:
        code = 0 if exc.code is None else exc.code if type(exc.code) is int and 0 <= exc.code <= 255 else 70
    except KeyboardInterrupt:
        code = 130
    except BaseException:
        code = 70
    finally:
        try:
            sys.stdout.flush()
        except BaseException:
            pass
        os._exit(code)


def spawn_worker(command, child, *, on_mode=None):
    """Select one isolated worker, falling back to exec only before child creation.

    on_mode is parent-only bookkeeping and must not open device resources. The
    child callback owns cancellation-flag/module-clock reset and worker args.
    """
    if not callable(child) or on_mode is not None and not callable(on_mode):
        raise ValueError('invalid worker bootstrap callback')

    def execute():
        if on_mode is not None:
            on_mode('exec')
        process = subprocess.Popen(command, stderr=subprocess.DEVNULL)
        process.worker_mode = 'exec'
        return process

    if not _fork_ready():
        return execute()
    # The callback runs before descriptor enumeration, so even a bookkeeping
    # implementation that opens a file cannot leak it into the child.
    if on_mode is not None:
        on_mode('fork')
    try:
        sys.stdout.flush()
        sys.stderr.flush()
        descriptors = _descriptor_snapshot()
        old_mask = signal.pthread_sigmask(signal.SIG_BLOCK, _CONTROL_SIGNALS)
    except (OSError, ValueError, AttributeError):
        return execute()
    process = ForkProcess(os.getpid(), old_mask)
    try:
        child_pid = os.fork()
    except OSError:
        process.activate()
        return execute()  # fork failed: POSIX guarantees no child was created.
    except BaseException:
        process.activate()
        raise
    if child_pid == 0:
        _child_exit(child, descriptors, old_mask)
    process.pid = child_pid
    process.worker_mode = 'fork'
    return process
