"""TEST040: 起動費用の固定時刻。ホストfixtureは実機の速度証明ではない。"""
from copy import deepcopy
from contextlib import nullcontext
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from necroprobe import shop_walk as walk
from necroprobe.protocol import RpcReply
from necroprobe.validation import ProbeError
import test_shop_walk as old


STARTUP_KEYS = (
    'parent_module_started_ns', 'parent_report_ready_ns',
    'worker_module_started_ns', 'worker_entered_ns', 'worker_validated_ns',
    'pairing_ready_ns', 'crypto_ready_ns', 'driver_ready_ns', 'launch_ready_ns',
    'first_observe_ns', 'first_capture_ns', 'first_seen_ns',
)


class StartupTimingTests(unittest.TestCase):
    build = old.SyncDeadlineTests.build

    def test_new_report_retains_all_fixed_unreached_startup_stages(self):
        report = walk.new_report(100, 'a' * 32)
        self.assertEqual(set(STARTUP_KEYS), set(report.get('startup', {})))
        self.assertTrue(all(value is None for value in report['startup'].values()))

    def report(self):
        report = walk.new_report(100, 'a' * 32)
        report['end_ns'] = 300
        report['startup'] = dict(zip(STARTUP_KEYS, (80, 120, 130, 140, 150, 160,
                                                  170, 180, 190, 200, 210, 220)))
        return report

    def roundtrip(self, report, name='report.json'):
        with tempfile.TemporaryDirectory() as folder:
            walk.write(folder, report, name)
            return walk.read_report(Path(folder) / name, report['run_id'], report['start_ns'])

    def test_parent_import_before_report_start_and_nullable_partial_stages_roundtrip(self):
        complete = self.report()
        self.assertLess(complete['startup']['parent_module_started_ns'], complete['start_ns'])
        self.assertEqual(complete, self.roundtrip(complete, 'parent-result.json'))
        for count in (0, 1, 2, 5, 9):
            partial = deepcopy(complete)
            for key in STARTUP_KEYS[count:]:
                partial['startup'][key] = None
            partial.update(status='stopped', reason='internal_error')
            with self.subTest(completed=count):
                self.assertEqual(partial, self.roundtrip(partial))

    def test_startup_exact_key_set_and_container_type_are_required(self):
        for fault in ('missing_container', 'missing_key', 'extra_key', 'list', 'null'):
            report = self.report()
            if fault == 'missing_container':
                report.pop('startup')
            elif fault == 'missing_key':
                report['startup'].pop(STARTUP_KEYS[-1])
            elif fault == 'extra_key':
                report['startup']['unbounded_detail'] = None
            elif fault == 'list':
                report['startup'] = list(report['startup'].values())
            else:
                report['startup'] = None
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                self.roundtrip(report)

    def test_timestamp_types_numeric_bounds_and_report_end_are_enforced(self):
        for key in STARTUP_KEYS:
            for invalid in (True, False, 1.0, '1', [], {}, -1, 2**63, 301):
                report = self.report()
                report['startup'] = dict.fromkeys(STARTUP_KEYS)
                report['startup'][key] = invalid
                with self.subTest(key=key, invalid=invalid), self.assertRaises(ValueError):
                    self.roundtrip(report)
        report = self.report()
        report['startup'] = dict.fromkeys(STARTUP_KEYS)
        report['startup']['parent_module_started_ns'] = 0
        self.assertEqual(report, self.roundtrip(report))
        report['end_ns'] = None
        report['startup']['first_seen_ns'] = 2**63 - 1
        self.assertEqual(report, self.roundtrip(report))
        for key in STARTUP_KEYS[1:]:
            report = self.report()
            report['startup'] = dict.fromkeys(STARTUP_KEYS)
            report['startup'][key] = 99
            with self.subTest(before_report_start=key), self.assertRaises(ValueError):
                self.roundtrip(report)

    def test_timestamps_stay_monotonic_across_populated_stages_and_parent_bounds(self):
        for index in range(len(STARTUP_KEYS) - 1):
            report = self.report()
            a, b = STARTUP_KEYS[index:index+2]
            report['startup'][a], report['startup'][b] = report['startup'][b], report['startup'][a]
            with self.subTest(inversion=(a, b)), self.assertRaises(ValueError):
                self.roundtrip(report)
        report = self.report()
        report['startup'] = dict.fromkeys(STARTUP_KEYS)
        report['startup']['worker_module_started_ns'] = 160
        report['startup']['first_seen_ns'] = 150
        with self.assertRaises(ValueError):
            self.roundtrip(report)
        for key, value in (('parent_module_started_ns', 101), ('parent_report_ready_ns', 99)):
            report = self.report()
            report['startup'] = dict.fromkeys(STARTUP_KEYS)
            report['startup'][key] = value
            with self.subTest(parent_bound=key), self.assertRaises(ValueError):
                self.roundtrip(report)
        # Monotonic clocks may return the same value at adjacent bounded stages.
        report = self.report()
        report['startup'] = dict.fromkeys(STARTUP_KEYS, 100)
        self.assertEqual(report, self.roundtrip(report))

    def test_first_capture_is_recorded_before_failed_rpc_once_without_extra_work(self):
        with tempfile.TemporaryDirectory() as folder:
            driver, now = old.SyncDeadlineTests.build(self, folder)
            start = now[0]
            original = driver.client.call
            calls = []

            def failed_capture(method, params, timeout):
                calls.append(method)
                if method == 'device_info':
                    now[0] += 20_000_000
                    return original(method, params, timeout)
                self.assertEqual('screenshot', method)
                # The marker must be present before an RPC whose outcome can fail.
                self.assertEqual(start + 20_000_000,
                                 driver.outer['startup']['first_capture_ns'])
                raise ProbeError('connection_error')

            with patch.object(driver.client, 'call', side_effect=failed_capture), patch.object(
                    driver, 'checkpoint', wraps=driver.checkpoint) as checkpoint:
                for _ in range(2):
                    with self.assertRaises(ProbeError):
                        driver.observe()
                checkpoint.assert_not_called()
            startup = driver.outer['startup']
            self.assertEqual(start, startup['first_observe_ns'])
            self.assertEqual(start + 20_000_000, startup['first_capture_ns'])
            self.assertIsNone(startup['first_seen_ns'])
            self.assertEqual(['device_info', 'screenshot'] * 2, calls)
            self.assertFalse(driver.pending)
            self.assertEqual([], driver.state['actions'])

    def test_first_seen_uses_observation_timestamp_and_markers_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            driver, now = old.SyncDeadlineTests.build(self, folder)
            start = now[0]
            original_calls = list(driver.client.calls)
            observations = []

            def completed(_driver):
                begin = now[0]
                driver.capture_started(begin + 3)
                now[0] = begin + 10
                observation = dict(driver.last, _captured=begin + 3, _seen_ns=begin + 8)
                observations.append(observation)
                driver.last = observation
                return observation

            with patch.object(walk.base.RuntimeDriver, 'observe', side_effect=completed, autospec=True), \
                    patch.object(driver, 'checkpoint', wraps=driver.checkpoint) as checkpoint:
                self.assertIs(driver.observe(), observations[0])
                recorded = deepcopy(driver.outer['startup'])
                now[0] += 100
                self.assertIs(driver.observe(), observations[1])
                checkpoint.assert_not_called()
            self.assertEqual(recorded, driver.outer['startup'])
            self.assertEqual(start, recorded['first_observe_ns'])
            self.assertEqual(start + 3, recorded['first_capture_ns'])
            self.assertEqual(start + 8, recorded['first_seen_ns'])
            self.assertEqual(original_calls, driver.client.calls)

    def test_guard_decode_and_classifier_failures_leave_unreached_stages_empty(self):
        for fault in ('guard', 'decode', 'classifier'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as folder, \
                    old.SyncDeadlineTests.measured_runtime(self, folder) as (
                        driver, now, captures, scenes, sent):
                start = now[0]
                original_rpc = driver.client.call

                def failed_guard(method, params, timeout):
                    self.assertEqual('device_info', method)
                    raise ProbeError('foreground_not_verified')

                hook = (patch.object(walk.base, 'inspect_payload',
                                     side_effect=ValueError('injected decode failure'))
                        if fault == 'decode' else
                        patch.object(driver, 'classify_frame',
                                     side_effect=ValueError('injected classifier failure'))
                        if fault == 'classifier' else nullcontext())
                with hook, patch.object(driver.client, 'call', wraps=original_rpc) as rpc, \
                        patch.object(driver, 'checkpoint', wraps=driver.checkpoint) as checkpoint:
                    if fault == 'guard':
                        rpc.side_effect = failed_guard
                    with self.assertRaises(ProbeError if fault == 'guard' else ValueError):
                        driver.observe()
                    checkpoint.assert_not_called()
                startup = driver.outer['startup']
                self.assertEqual(start, startup['first_observe_ns'])
                self.assertEqual(None if fault == 'guard' else start + 120_000_000,
                                 startup['first_capture_ns'])
                self.assertIsNone(startup['first_seen_ns'])
                self.assertEqual(['device_info'] + ([] if fault == 'guard' else ['screenshot']),
                                 [call.args[0] for call in rpc.call_args_list])
                self.assertEqual(0 if fault == 'guard' else 1, len(captures))
                self.assertEqual([], scenes)
                self.assertEqual([], sent)
                self.assertEqual([], driver.state['actions'])
                self.assertEqual(driver.outer, self.roundtrip(driver.outer))

    def test_worker_failure_retains_completed_prefix_without_extra_rpcs_or_checkpoints(self):
        # This uses the real worker/report writer with simulated setup failures.
        for fault in ('pairing', 'crypto', 'driver', 'launch', 'collect'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as folder:
                start = time.monotonic_ns()
                run_id = 'c' * 32
                args = walk.parser().parse_args([
                    '--worker', '--output', folder, '--checkpoint-dir', folder,
                    '--run-id', run_id, '--start-ns', str(start),
                    '--stop-ns', str(start + 20_000_000_000)])
                walk.write(folder, walk.new_report(start, run_id))
                client = type('Client', (), {'call': lambda *_a, **_k: RpcReply({}, {})})()
                crypto = type('Crypto', (), {'engine': 'python'})()
                with patch.object(walk.base, 'device_lock', return_value=nullcontext()), \
                        patch.object(walk, '_MODULE_STARTED_NS', start), \
                        patch.object(walk.base, 'load_pairing', return_value=(b'key', 'token')) as pairing, \
                        patch.object(walk.base, 'Crypto', return_value=crypto) as load_crypto, \
                        patch.object(walk.base, 'OwnedRpcTimer', return_value=nullcontext()), \
                        patch.object(walk, 'WalkClient', return_value=client), \
                        patch.object(walk, 'Driver', wraps=walk.Driver) as load_driver, \
                        patch.object(client, 'call', return_value=RpcReply({}, {})) as rpc, \
                        patch.object(walk.base, 'collect', side_effect=ProbeError('screen_unconfirmed')) as collect, \
                        patch.object(walk, 'write', wraps=walk.write) as writes:
                    if fault == 'pairing':
                        pairing.side_effect = ProbeError('pairing_missing')
                    elif fault == 'crypto':
                        load_crypto.side_effect = OSError('injected crypto setup failure')
                    elif fault == 'driver':
                        load_driver.side_effect = OSError('injected Driver setup failure')
                    elif fault == 'launch':
                        rpc.side_effect = ProbeError('connection_error')
                    self.assertEqual(0, walk.worker(args))
                result = walk.read_report(Path(folder) / 'report.json', run_id, start)
                startup = result['startup']
                for key in STARTUP_KEYS[2:5]:
                    self.assertIs(type(startup[key]), int, key)
                ready_count = {'pairing': 5, 'crypto': 6, 'driver': 7, 'launch': 8, 'collect': 9}[fault]
                for key in STARTUP_KEYS[2:ready_count]:
                    self.assertIs(type(startup[key]), int, key)
                for key in STARTUP_KEYS[ready_count:]:
                    self.assertIsNone(startup[key], key)
                self.assertEqual(0 if fault in ('pairing', 'crypto', 'driver') else 1, rpc.call_count)
                if rpc.call_count:
                    self.assertEqual('launch_app', rpc.call_args.args[0])
                self.assertEqual(int(fault == 'collect'), collect.call_count)
                # Existing worker final writes; instantiated Driver adds the
                # already-existing export checkpoint, not a telemetry checkpoint.
                self.assertEqual(2 if fault in ('pairing', 'crypto', 'driver') else 3, writes.call_count)
                self.assertEqual([], result['walk']['actions'])

    def test_parent_records_import_and_report_ready_before_existing_supervision(self):
        with tempfile.TemporaryDirectory() as folder:
            args = walk.parser().parse_args(['--output', folder])
            prepared = []

            def finished_worker(command, timeout, diagnostics, **options):
                control = Path(command[command.index('--checkpoint-dir') + 1])
                run_id = command[command.index('--run-id') + 1]
                start = int(command[command.index('--start-ns') + 1])
                report = walk.read_report(control / 'report.json', run_id, start)
                startup = report['startup']
                self.assertLessEqual(startup['parent_module_started_ns'], start)
                self.assertLessEqual(start, startup['parent_report_ready_ns'])
                self.assertEqual(walk._MODULE_STARTED_NS, startup['parent_module_started_ns'])
                self.assertTrue(all(startup[key] is None for key in STARTUP_KEYS[2:]))
                prepared.append(deepcopy(startup))
                # Simulate an already-ended worker only; no setup or game RPCs.
                report.update(phase='done', status='stopped', reason='gold_not_found',
                              end_ns=time.monotonic_ns())
                walk.write(control, report)
                diagnostics.update(returncode=0, exit_confirmed=True)
                return None

            with patch.object(walk.base.supervisor, 'supervise', side_effect=finished_worker) as supervise, \
                    patch.object(walk, 'WalkClient', side_effect=AssertionError('parent RPC')), \
                    patch.object(walk, 'write', wraps=walk.write) as writes, \
                    patch('builtins.print'):
                self.assertEqual(2, walk.run(args))
            self.assertEqual(1, supervise.call_count)
            # Parent initial/parent-result/final report plus the simulated child
            # report; telemetry adds no extra persistence operation.
            self.assertEqual(4, writes.call_count)
            report_paths = list(Path(folder).glob('shop-walk-*/parent-result.json'))
            self.assertEqual(1, len(report_paths))
            import json
            report = json.loads(report_paths[0].read_bytes())
            self.assertEqual(prepared[0], report['startup'])
            self.assertEqual([], report['walk']['actions'])


if __name__ == '__main__':
    unittest.main()
