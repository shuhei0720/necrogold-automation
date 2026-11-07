"""TEST041: isolated worker bootstrap. Host fork checks do not establish iSH support."""
import inspect
import unittest
from unittest.mock import Mock, patch

from necroprobe import input_path as supervisor


class BootstrapSupervisorTests(unittest.TestCase):
    def test_public_supervisor_uses_selected_worker_without_starting_exec_again(self):
        class Process:
            returncode = 0
            def wait(self, timeout):
                return 0
        selected = Mock(return_value=Process())
        # Exercise the previous public API too; an absent new keyword is not the Red.
        options = {'spawn': selected} if 'spawn' in inspect.signature(supervisor.supervise).parameters else {}
        with patch.object(supervisor.subprocess, 'Popen', return_value=Process()) as old_exec:
            details = {}
            result = supervisor.supervise(['synthetic-worker'], 1, details, **options)
        self.assertEqual(1, selected.call_count)
        old_exec.assert_not_called()
        self.assertIsNone(result)
        self.assertTrue(details['exit_confirmed'])
        self.assertEqual(0, details['returncode'])


class BootstrapProcessTests(unittest.TestCase):
    def bootstrap(self):
        from necroprobe import bootstrap
        return bootstrap

    def spawn(self, target, command=None, on_mode=None):
        bootstrap = self.bootstrap()
        self.assertTrue(bootstrap._fork_ready(), 'host fork test requires isolated parent conditions')
        process = bootstrap.spawn_worker(command or ['synthetic-worker'], target, on_mode=on_mode)
        self.addCleanup(self.reap, process)
        self.assertEqual('fork', process.worker_mode)
        self.assertIsNotNone(process.pid)
        return process

    @staticmethod
    def reap(process):
        import subprocess
        try:
            if process.returncode is None:
                try:
                    process.kill()
                except OSError:
                    pass
                try:
                    process.wait(timeout=1)
                except (OSError, subprocess.TimeoutExpired):
                    pass
        finally:
            finish = getattr(process, 'finalize', None)
            if finish is not None:
                finish()

    def test_host_worker_does_not_exec_or_mutate_parent_and_returns_owned_pid(self):
        import json
        import os
        from pathlib import Path
        import tempfile
        bootstrap = self.bootstrap()
        parent = os.getpid()
        local = []
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder) / 'child.json'
            def child():
                local.append('child-only')
                marker.write_text(json.dumps({'pid': os.getpid(), 'parent': os.getppid()}))
                return 0
            with patch.object(bootstrap.subprocess, 'Popen', side_effect=AssertionError('unexpected exec')):
                process = self.spawn(child)
                self.assertEqual(0, process.wait(timeout=2))
            recorded = json.loads(marker.read_text())
            self.assertEqual(process.pid, recorded['pid'])
            self.assertEqual(parent, recorded['parent'])
            self.assertNotEqual(parent, process.pid)
            self.assertEqual([], local)
            self.assertEqual(0, process.poll())

    def test_child_resets_handlers_closes_inherited_nonstdio_fds_and_keeps_parent_fd(self):
        import errno
        import json
        import os
        from pathlib import Path
        import signal
        import tempfile
        bootstrap = self.bootstrap()
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder) / 'environment.json'
            descriptor = os.open(Path(folder) / 'parent-private', os.O_CREAT | os.O_RDWR, 0o600)
            self.addCleanup(os.close, descriptor)
            before = signal.pthread_sigmask(signal.SIG_BLOCK, ())
            def child():
                try:
                    os.fstat(descriptor)
                    closed = False
                except OSError as exc:
                    closed = exc.errno == errno.EBADF
                marker.write_text(json.dumps({
                    'closed': closed,
                    'int': signal.getsignal(signal.SIGINT) is signal.default_int_handler,
                    'term': signal.getsignal(signal.SIGTERM) == signal.SIG_DFL,
                    'alarm': signal.getsignal(signal.SIGALRM) == signal.SIG_DFL,
                    'mask': sorted(int(v) for v in signal.pthread_sigmask(signal.SIG_BLOCK, ())),
                    'stderr': os.readlink('/proc/self/fd/2'),
                }))
                return 0
            process = self.spawn(child)
            self.assertEqual(0, process.wait(timeout=2))
            recorded = json.loads(marker.read_text())
            self.assertTrue(recorded['closed'])
            self.assertTrue(recorded['int']); self.assertTrue(recorded['term']); self.assertTrue(recorded['alarm'])
            self.assertEqual(sorted(int(v) for v in before), recorded['mask'])
            self.assertEqual(os.devnull, recorded['stderr'])
            os.fstat(descriptor)
            self.assertEqual(before, signal.pthread_sigmask(signal.SIG_BLOCK, ()))

    def test_callback_errors_are_sanitized_without_starting_exec(self):
        bootstrap = self.bootstrap()
        for outcome in (7, 'exception', 'system_exit', 'invalid'):
            with self.subTest(outcome=outcome):
                def child():
                    if outcome == 'exception': raise RuntimeError('PRIVATE exception')
                    if outcome == 'system_exit': raise SystemExit(9)
                    return True if outcome == 'invalid' else outcome
                with patch.object(bootstrap.subprocess, 'Popen', side_effect=AssertionError('second worker')):
                    process = self.spawn(child)
                    self.assertEqual({'exception': 70, 'system_exit': 9, 'invalid': 70}.get(outcome, 7),
                                     process.wait(timeout=2))

    def test_exec_fallback_happens_once_before_child_for_unsafe_or_unsupported_parent(self):
        from types import SimpleNamespace
        import signal
        bootstrap = self.bootstrap()
        cases = (
            patch.object(bootstrap, '_fork_ready', return_value=False),
            patch.object(bootstrap, '_descriptor_snapshot', side_effect=OSError('PRIVATE descriptors')),
            patch.object(bootstrap.os, 'listdir', return_value=[]),
            patch.object(bootstrap.os, 'fork', side_effect=OSError('PRIVATE fork unsupported')),
            patch.object(bootstrap.signal, 'pthread_sigmask', side_effect=OSError('PRIVATE mask unavailable')),
        )
        for failure in cases:
            with self.subTest(failure=failure):
                modes = []
                fake = SimpleNamespace(returncode=0)
                child = Mock(side_effect=AssertionError('must not call child'))
                previous = signal.pthread_sigmask(signal.SIG_BLOCK, ())
                with failure, patch.object(bootstrap.subprocess, 'Popen', return_value=fake) as execute:
                    self.assertIs(fake, bootstrap.spawn_worker(['fallback-command'], child, on_mode=modes.append))
                execute.assert_called_once_with(['fallback-command'], stderr=bootstrap.subprocess.DEVNULL)
                child.assert_not_called()
                self.assertEqual('exec', modes[-1])
                self.assertEqual('exec', fake.worker_mode)
                self.assertEqual(previous, signal.pthread_sigmask(signal.SIG_BLOCK, ()))

    def test_real_safety_guards_refuse_owned_timer_thread_or_signal_reaper(self):
        from types import SimpleNamespace
        import signal
        import threading
        bootstrap = self.bootstrap()
        self.assertTrue(bootstrap._fork_ready())
        with patch.dict(bootstrap.sys.modules, {'necroprobe.deadlines': SimpleNamespace(_owner=object())}):
            self.assertFalse(bootstrap._fork_ready())
        with patch.object(bootstrap.threading, 'active_count', return_value=2):
            self.assertFalse(bootstrap._fork_ready())
        with patch.object(bootstrap.threading, 'current_thread', return_value=object()):
            self.assertFalse(bootstrap._fork_ready())
        for which, value in ((signal.SIGALRM, lambda *_: None),
                             (signal.SIGCHLD, signal.SIG_IGN)):
            previous = signal.getsignal(which)
            try:
                signal.signal(which, value)
                self.assertFalse(bootstrap._fork_ready())
            finally:
                signal.signal(which, previous)
        with patch.object(bootstrap.os, 'fork', None):
            self.assertFalse(bootstrap._fork_ready())
        with patch.object(bootstrap.signal, 'pthread_sigmask', None):
            self.assertFalse(bootstrap._fork_ready())

    def test_supervisor_deadline_kills_sigterm_resistant_child_and_reaps(self):
        import os
        from pathlib import Path
        import signal
        import tempfile
        import time
        bootstrap = self.bootstrap()
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder) / 'child.pid'
            def child():
                signal.signal(signal.SIGTERM, signal.SIG_IGN)
                marker.write_text(str(os.getpid()))
                while True: time.sleep(.01)
            processes = []
            def spawn(command):
                process = bootstrap.spawn_worker(command, child)
                processes.append(process)
                return process
            details = {}
            reason = supervisor.supervise(['synthetic-worker'], .15, details, spawn=spawn)
            self.assertEqual('session_deadline', reason)
            self.assertTrue(details['exit_confirmed'])
            self.assertEqual(-signal.SIGKILL, details['returncode'])
            self.assertEqual(1, len(processes))
            self.assertEqual(processes[0].pid, int(marker.read_text()))
            with self.assertRaises(ChildProcessError): os.waitpid(processes[0].pid, os.WNOHANG)

    def test_pending_cancel_after_spawn_is_handled_after_parent_stores_pid(self):
        import signal
        import time
        bootstrap = self.bootstrap()
        previous_flag = supervisor._cancel_requested
        processes = []
        def child():
            while True: time.sleep(.01)
        def selected(command):
            process = bootstrap.spawn_worker(command, child)
            processes.append(process)
            # Model the existing parent signal handler setting a flag during spawn.
            supervisor._cancel_requested = True
            return process
        try:
            supervisor._cancel_requested = False
            details = {}
            reason = supervisor.supervise(['synthetic-worker'], 2, details, spawn=selected)
            self.assertEqual('user_interrupt', reason)
            self.assertTrue(details['exit_confirmed'])
            self.assertEqual(1, len(processes))
            self.assertIn(details['returncode'], (-signal.SIGTERM, -signal.SIGKILL))
        finally:
            supervisor._cancel_requested = previous_flag
            for process in processes: self.reap(process)

    def test_lost_wait_ownership_never_signals_a_reused_or_parent_pid(self):
        import errno
        import os
        import signal
        bootstrap = self.bootstrap()
        process = bootstrap.ForkProcess(os.getpid(), None)
        process.pid = os.getpid() + 123456
        with patch.object(bootstrap.os, 'waitpid', side_effect=ChildProcessError), \
                patch.object(bootstrap.os, 'kill') as kill:
            with self.assertRaises(OSError) as lost: process.poll()
            self.assertEqual(errno.ECHILD, lost.exception.errno)
            with self.assertRaises(OSError): process.terminate()
            with self.assertRaises(OSError): process.kill()
            kill.assert_not_called()
        process = bootstrap.ForkProcess(os.getpid(), None)
        process.pid = os.getpid()
        with patch.object(bootstrap.os, 'kill') as kill:
            with self.assertRaises(OSError): process.kill()
            kill.assert_not_called()

    def test_mask_restoration_error_still_kills_and_reaps_created_child_without_exec(self):
        import os
        import signal
        import time
        bootstrap = self.bootstrap()
        original_mask = bootstrap.signal.pthread_sigmask
        previous = original_mask(signal.SIG_BLOCK, ())
        parent = os.getpid()
        fail = [False]
        processes = []
        def masks(how, values):
            if os.getpid() == parent and how == signal.SIG_SETMASK and fail[0]:
                fail[0] = False
                raise OSError('injected parent mask restoration failure')
            return original_mask(how, values)
        def child():
            while True: time.sleep(.01)
        def selected(command):
            process = bootstrap.spawn_worker(command, child)
            processes.append(process)
            fail[0] = True
            return process
        try:
            with patch.object(bootstrap.signal, 'pthread_sigmask', side_effect=masks), \
                    patch.object(bootstrap.subprocess, 'Popen', side_effect=AssertionError('second exec')):
                details = {}
                reason = supervisor.supervise(['synthetic-worker'], 2, details, spawn=selected)
            self.assertEqual('worker_cleanup_failed', reason)
            self.assertTrue(details['exit_confirmed'])
            self.assertEqual(1, len(processes))
            self.assertEqual(previous, original_mask(signal.SIG_BLOCK, ()))
        finally:
            original_mask(signal.SIG_SETMASK, previous)
            for process in processes: self.reap(process)


    def test_child_setup_failure_is_terminal_without_callback_or_second_worker(self):
        import errno
        import os
        from pathlib import Path
        import tempfile
        bootstrap = self.bootstrap()
        parent = os.getpid()
        original_close = bootstrap.os.close
        with tempfile.TemporaryDirectory() as folder:
            private = os.open(Path(folder) / 'parent-private', os.O_CREAT | os.O_RDWR, 0o600)
            marker = Path(folder) / 'should-not-exist'
            def fail_close(descriptor):
                if os.getpid() != parent and descriptor == private:
                    raise OSError(errno.EIO, 'injected child setup failure')
                return original_close(descriptor)
            def child():
                marker.write_text('unexpected worker execution')
                return 0
            try:
                with patch.object(bootstrap.os, 'close', side_effect=fail_close), patch.object(
                        bootstrap.subprocess, 'Popen', side_effect=AssertionError('second worker')):
                    process = self.spawn(child)
                    self.assertEqual(70, process.wait(timeout=2))
                self.assertFalse(marker.exists())
                os.fstat(private)
            finally:
                original_close(private)

    def test_preexisting_cancel_never_calls_factory_or_exec(self):
        previous = supervisor._cancel_requested
        selected = Mock(side_effect=AssertionError('cancelled spawn'))
        try:
            supervisor._cancel_requested = True
            with patch.object(supervisor.subprocess, 'Popen') as execute:
                self.assertEqual('user_interrupt', supervisor.supervise(
                    ['synthetic-worker'], 1, {}, spawn=selected))
            selected.assert_not_called()
            execute.assert_not_called()
        finally:
            supervisor._cancel_requested = previous


class BootstrapRunIntegrationTests(unittest.TestCase):
    def completed_record(self, walk, args, module_ns):
        # Simulated device outcome only. Exercise real strict report and parent run.
        import json
        import os
        from pathlib import Path
        import time
        entered = time.monotonic_ns()
        report = walk.read_report(Path(args.checkpoint_dir) / 'report.json',
                                  args.run_id, args.start_ns)
        validated = time.monotonic_ns()
        report['startup'].update(worker_module_started_ns=module_ns,
                                 worker_entered_ns=entered, worker_validated_ns=validated)
        report['worker_mode'] = args.worker_mode
        report['search'].update(status='completed', reason='gold_candidate', candidate=True)
        report['walk'].update(started_ns=validated, end_ns=validated,
                              reason='goods_visible', goods_visible=True, paused=True)
        report.update(phase='done', status='completed', reason='goods_visible',
                      control_reason='goods_visible', control_end_ns=validated, end_ns=validated)
        walk.write(args.checkpoint_dir, report)
        sentinel = {'pid': os.getpid(), 'parent_pid': os.getppid(), 'mode': args.worker_mode,
                    'module_ns': module_ns, 'cancelled': supervisor._cancel_requested}
        (Path(args.output) / 'child-sentinel.json').write_text(json.dumps(sentinel))
        return 0

    def result(self, walk, root):
        import json
        from pathlib import Path
        folder = next(Path(root).glob('shop-walk-*'))
        raw = json.loads((folder / 'report.json').read_text())
        result = walk.read_report(folder / 'report.json', raw['run_id'], raw['start_ns'])
        self.assertEqual(result, json.loads((folder / 'parent-result.json').read_text()))
        return result, json.loads((folder / 'child-sentinel.json').read_text())

    def test_public_run_uses_independent_fork_worker_and_keeps_parent_clock(self):
        from contextlib import redirect_stdout
        import io
        import os
        import tempfile
        from necroprobe import bootstrap, shop_walk as walk
        self.assertTrue(bootstrap._fork_ready())
        parent = os.getpid()
        old_module = walk._MODULE_STARTED_NS
        original_fork = bootstrap.os.fork
        def inherited_cancel_fork():
            child_pid = original_fork()
            if child_pid == 0:
                supervisor._cancel_requested = True  # Simulate a stale inherited flag.
            return child_pid
        with tempfile.TemporaryDirectory() as folder:
            args = walk.parser().parse_args(['--output', folder])
            def inherited(args):
                self.assertEqual('fork', args.worker_mode)
                self.assertGreaterEqual(walk._MODULE_STARTED_NS, args.start_ns)
                self.assertFalse(supervisor._cancel_requested)
                return self.completed_record(walk, args, walk._MODULE_STARTED_NS)
            with patch.object(bootstrap.os, 'fork', side_effect=inherited_cancel_fork), patch.object(
                    walk, 'worker', side_effect=inherited) as worker, patch.object(
                    walk.base, 'load_pairing', side_effect=AssertionError('unexpected pairing')), patch.object(
                    walk, 'WalkClient', side_effect=AssertionError('unexpected device client')), patch.object(
                    bootstrap.subprocess, 'Popen', side_effect=AssertionError('unexpected exec')), redirect_stdout(io.StringIO()):
                self.assertEqual(0, walk.run(args))
            # The mock and module data live in separate process memory.
            self.assertEqual(0, worker.call_count)
            self.assertEqual(old_module, walk._MODULE_STARTED_NS)
            result, sentinel = self.result(walk, folder)
            self.assertEqual('fork', result['worker_mode'])
            self.assertTrue(result['worker_exit_confirmed'])
            self.assertEqual(0, result['worker_returncode'])
            self.assertNotEqual(parent, sentinel['pid'])
            self.assertEqual(parent, sentinel['parent_pid'])
            self.assertEqual('fork', sentinel['mode'])
            self.assertFalse(sentinel['cancelled'])
            self.assertEqual(sentinel['module_ns'], result['startup']['worker_module_started_ns'])
            self.assertGreaterEqual(sentinel['module_ns'], result['start_ns'])
            self.assertTrue(result['walk']['paused'])
            self.assertTrue(result['walk']['goods_visible'])

    def test_public_run_records_exec_after_unsafe_parent_or_failed_fork_before_child(self):
        from contextlib import redirect_stdout
        import io
        import tempfile
        import time
        from necroprobe import bootstrap, shop_walk as walk
        for fault in ('unsafe_parent', 'fork_unavailable'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as folder:
                args = walk.parser().parse_args(['--output', folder])
                events = []
                original_spawn = bootstrap.spawn_worker
                def traced_spawn(command, child, *, on_mode=None):
                    def chosen(mode):
                        events.append(mode)
                        on_mode(mode)
                    return original_spawn(command, child, on_mode=chosen)
                class Process:
                    returncode = 0
                    def wait(self, timeout): return 0
                def execute(command, **kwargs):
                    child_args = walk.parser().parse_args(command[3:])
                    self.assertEqual('exec', child_args.worker_mode)
                    self.completed_record(walk, child_args, time.monotonic_ns())
                    return Process()
                failure = (patch.object(bootstrap, '_fork_ready', return_value=False)
                           if fault == 'unsafe_parent' else
                           patch.object(bootstrap.os, 'fork', side_effect=OSError('unsupported fork')))
                with failure, patch.object(bootstrap, 'spawn_worker', side_effect=traced_spawn), patch.object(
                        bootstrap.subprocess, 'Popen', side_effect=execute) as popen, patch.object(
                        walk, 'worker', side_effect=AssertionError('must not invoke fork callback')), patch.object(
                        walk.base, 'load_pairing', side_effect=AssertionError('unexpected pairing')), patch.object(
                        walk, 'WalkClient', side_effect=AssertionError('unexpected device client')), redirect_stdout(io.StringIO()):
                    self.assertEqual(0, walk.run(args))
                self.assertEqual(1, popen.call_count)
                self.assertEqual(['exec'] if fault == 'unsafe_parent' else ['fork', 'exec'], events)
                result, sentinel = self.result(walk, folder)
                self.assertEqual('exec', result['worker_mode'])
                self.assertEqual('exec', sentinel['mode'])
                self.assertTrue(result['worker_exit_confirmed'])
                self.assertEqual(0, result['worker_returncode'])


if __name__ == '__main__':
    unittest.main()
