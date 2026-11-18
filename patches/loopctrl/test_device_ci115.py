"""Exact source, selector and entry guards for the TEST115 device lane."""
import ast
from contextlib import redirect_stdout
import importlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location('device115_'+name, HERE/(name+'.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


class DeviceHostSelection115Tests(unittest.TestCase):
    def test_pending_empty_duplicate_or_overridden_scope_never_executes(self):
        runner = module('run_test115_host')
        for flag in ('SCOPE_FINALIZED', 'RUNTIME_SCOPE_FINALIZED'):
            with patch.object(runner, flag, False), self.assertRaises(ValueError):
                runner.ensure_scope()
        rows = (('m', 'C', 'one', frozenset({'test_one'}), True),)
        with patch.object(runner, 'SCOPE_FINALIZED', True), patch.object(runner, 'RUNTIME_SCOPE_FINALIZED', True), patch.object(runner, 'CURRENT_MAC_CASES', ('passage_fresh',)), patch.object(runner, 'NEW_PATHS', frozenset({'new.py'})), patch.object(runner, 'CASES', rows):
            runner.ensure_scope()
            for bad in ((), rows*2):
                with patch.object(runner, 'CASES', bad), self.assertRaises(ValueError):
                    runner.ensure_scope()
            for key in ('CURRENT_MAC_CASES', 'NEW_PATHS'):
                with patch.object(runner, key, ()), self.assertRaises(ValueError):
                    runner.ensure_scope()
        for name in ('BASELINE_NAV', 'NECRO115_CORE', 'NECRO114_RING_SOURCE', 'NECRO_TEST115_CORE'):
            with patch.dict(runner.os.environ, {name: ''}), self.assertRaises(ValueError):
                runner.reject_fixture_overrides()

    def test_native_delta_changes_only_controller_navigation_and_runtime_from_test114(self):
        runner = module('run_test115_host')
        expected = {'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Navigation.c', 'LoopCtrlUITests/NG2Runtime.swift'}
        self.assertEqual(expected, set(runner.EXPECTED_NATIVE_CHANGES))
        self.assertEqual('c84e74f8934f88a05b02e4c58a899d2e3ebae519', runner.NATIVE_BASELINE)
        names = expected | {'retained-'+str(index) for index in range(33)}
        old = {name: 'a'*64 for name in names}
        new = {name: ('b'*64 if name in expected else value) for name, value in old.items()}
        self.assertEqual(expected, runner.native_delta(old, new))
        for bad in (old, dict(new, extra='b'*64), {name: value for name, value in new.items() if name != 'retained-0'}, dict(new, **{'retained-0': 'b'*64})):
            with self.assertRaises(ValueError):
                runner.native_delta(old, bad)

    def test_changed_runtime_and_retained_ring_need_exact_current_mac_cases(self):
        runner = module('run_test115_host')
        old = {'LoopCtrlUITests/NG2Runtime.swift': runner.BASELINE_RUNTIME_SHA256,
            'LoopCtrlUITests/NG2Ring.c': runner.BASELINE_RING_SHA256,
            'LoopCtrlUITests/NG2Controller.c': 'a'*64,
            'LoopCtrlUITests/NG2Navigation.c': 'a'*64}
        current = dict(old, **{'LoopCtrlUITests/NG2Controller.c': 'b'*64,
            'LoopCtrlUITests/NG2Navigation.c': 'b'*64, 'LoopCtrlUITests/NG2Runtime.swift': 'b'*64})
        with patch.object(runner, 'RUNTIME_SCOPE_FINALIZED', True), patch.object(runner, 'CURRENT_MAC_CASES', ('passage_fresh',)):
            result = runner.runtime_source_identity(old, current)
            self.assertTrue(result['current_mac_execution_required'])
            self.assertTrue(result['before_runtime_clock_assertion_required'])
            self.assertFalse(result['executed_in_host_selector'])
            with self.assertRaises(ValueError):
                runner.runtime_source_identity(old, dict(current, **{'LoopCtrlUITests/NG2Runtime.swift': runner.BASELINE_RUNTIME_SHA256}))
            with self.assertRaises(ValueError):
                runner.runtime_source_identity(old, dict(current, **{'LoopCtrlUITests/NG2Ring.c': 'c'*64}))

    def test_author_native_and_mac_inventories_are_frozen_and_explicit(self):
        runner = module('run_test115_host')
        runner.ensure_scope()
        sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
        for name, klass, _label, methods, exact in runner.CASES:
            source = importlib.import_module(name)
            self.assertEqual(ROOT/(name.replace('.', '/')+'.py'), Path(source.__file__).resolve())
            available = set(unittest.defaultTestLoader.getTestCaseNames(getattr(source, klass)))
            self.assertTrue(methods <= available)
            if exact:
                self.assertEqual(methods, available)
        tree = ast.parse((HERE/'check_runtime115.py').read_text())
        declared = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == 'GREEN_CASES' for target in node.targets))
        self.assertEqual(declared, runner.CURRENT_MAC_CASES)
        self.assertEqual(frozenset(), runner.CLIENT_PRODUCT_CHANGES)

    def test_python39_scope_is_frozen_and_pending_is_fail_closed(self):
        runner = module('run_test115_python39')
        with patch.object(runner, 'SCOPE_FINALIZED', False), self.assertRaises(ValueError):
            runner.selected_suite(ROOT)
        self.assertTrue(runner.SCOPE_FINALIZED)
        _host, selected = runner.selected_suite(ROOT)
        self.assertEqual(sum(len(row[3]) for row in runner.CASES), len(selected))
        self.assertEqual(len(selected), len({case.id() for case in selected}))

    def test_entry_inherits_114_without_new_authority(self):
        sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
        from necroprobe import test114, test115
        from necroprobe.native_cycle import IRREGULAR_PROTOCOL
        from necroprobe.validation import ProbeError
        self.assertTrue(issubclass(test115.DeviceClient115, test114.DeviceClient114))
        for key in ('protocol_spec', 'required_capabilities', 'yield_after_restart',
                    'allow_restarted_budget', 'diagnostics114'):
            self.assertIs(getattr(test114.DeviceClient114, key), getattr(test115.DeviceClient115, key))
        self.assertIs(test115.DeviceClient115.protocol_spec, IRREGULAR_PROTOCOL)
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(0, test115.main(['--check']))
        self.assertEqual('native-device-failures-trial-v115 / 1.98.16-ngg2\n', output.getvalue())
        with patch.object(test115, 'device_main', return_value=7) as main:
            self.assertEqual(7, test115.main(['--recovery']))
        self.assertEqual('115', main.call_args.kwargs['test_number'])
        self.assertIs(main.call_args.kwargs['client_class'], test115.DeviceClient115)
        client = object.__new__(test115.DeviceClient115)
        client._validate('recent_logs', {'max_elements': 500})
        client._validate('necro_native_status', {'run_id': '1'*32, 'keepalive': False})
        for method, params in (('recent_logs', {'max_elements': 501}),
                ('necro_native_status', {'run_id': '1'*32, 'keepalive': True}), ('tap', {})):
            with self.assertRaises(ProbeError):
                client._validate(method, params)
        shell = (ROOT/'test_115.sh').read_text()
        for required in ('necroprobe.test115 --check', 'native-device-failures-trial-v115 / 1.98.16-ngg2',
                'python3 -m necroprobe.test115 "$@"', '--until-target', '--recovery'):
            self.assertIn(required, shell)

    def test_workflow_selects_115_callbacks_and_actual_pinned_python39(self):
        source = (ROOT/'.github/workflows/loopctrl-geometry.yml').read_text()
        host = source.split('  test061-host-contracts:\n', 1)[1].split('  focused-build:\n', 1)[0]
        self.assertIn('NATIVE_HOST_RUNNER=driver/patches/loopctrl/run_test115_host.py', host)
        self.assertLess(host.index('DEVICE_PROFILE=114'), host.index('DEVICE_PROFILE=115'))
        self.assertIn('test115-python39-provider.json', host)
        self.assertIn('steps.python39_115.outputs.python-path', host)
        self.assertIn('run_test115_python39.py driver', host)
        self.assertIn('fe04e8b27bd69ca2144fc542428f8b9b5287b6a2e45516a4acfe2c2bc3102773', host)
        build = source.split('  focused-build:\n', 1)[1].split('\n  build:\n', 1)[0]
        for title in ('Verify TEST115 current-PARTIAL before-Controller assertion with current Runtime',
                'Verify TEST115 passage, PARTIAL and final-clock callbacks against sealed sources'):
            step = build.split('- name: '+title+'\n', 1)[1].split('      - ', 1)[0]
            self.assertIn("device_profile == '115'", step)
            self.assertIn('set -euo pipefail', step)
            self.assertIn('check_runtime115.py upstream', step)
        clock = build.split('- name: Verify TEST115 final-clock before-Runtime assertion against original source\n', 1)[1].split('      - ', 1)[0]
        self.assertIn("device_profile == '115'", clock)
        self.assertIn('--expect-runtime-red --before-runtime', clock)
        self.assertIn('${{ runner.temp }}/test115-runtime-before-clock/', build)
        self.assertIn('053b2da0773899a8e19db7d11454c297edcca7cf04422a17210ede2f90195843', build)
        self.assertIn('c84e74f8934f88a05b02e4c58a899d2e3ebae519:patches/loopctrl/ngg2/NG2Controller.c', build)
        self.assertIn('${{ runner.temp }}/test115-runtime-before/', build)
        self.assertIn('${{ runner.temp }}/test115-runtime/', build)
        for title in ('Install TEST094 focused Swift fixture image decoder',
                'Verify TEST094 immutable terminal export and exact image roundtrip',
                'Verify TEST094 selected actual Runtime cycle callbacks'):
            old = build.split('- name: '+title+'\n', 1)[1].split('      - ', 1)[0]
            self.assertIn("device_profile != '115'", old)
        self.assertIn('runs-on: macos-26', build)
        self.assertIn('runs-on: ubuntu-latest', source)
        red = source.split('  test115-runtime-red:\n', 1)[1].split('  test112-runtime-diagnostic:\n', 1)[0]
        self.assertIn('runs-on: macos-26', red)
        self.assertIn('--expect-runtime-red --before-runtime', red)
        self.assertIn('dc082fd9658df32924c90423c544030d327c744f4224d4d8c868762a6e2e741f', red)
        self.assertIn("required_cases=['post_begin_clock']", red)
        self.assertIn('ipa_built=False, linux_host_replayed=False, python39_replayed=False', red)
        for unrelated in ('xcodebuild', 'run_test115_host.py', 'run_test115_python39.py'):
            self.assertNotIn(unrelated, red)
        ready = source.split('  native-source-ready:\n', 1)[1].split('  native-host-contracts:\n', 1)[0]
        self.assertIn("inputs.native_lane != 'test115-runtime-red'", ready)

    def test_skip_error_failure_duplicates_and_empty_are_never_green(self):
        runner = module('run_test115_host')
        # Retained assertion helper supplies deliberate failures, not native results.
        old = module('test_device_ci114')
        for outcome in ('green', 'skip', 'failure', 'error'):
            with tempfile.TemporaryDirectory() as temporary, patch('builtins.print'):
                output, evidence = Path(temporary), {}
                if outcome == 'green':
                    runner.run_scope('unit', [old.one_case()], output, evidence)
                else:
                    with self.assertRaises(RuntimeError):
                        runner.run_scope('unit', [old.one_case(outcome)], output, evidence)
                self.assertEqual(1, evidence['unit']['tests_run'])
        for cases in ([], [old.one_case(), old.one_case()]):
            with self.assertRaises(ValueError):
                runner.selected_cases(cases)


if __name__ == '__main__':
    unittest.main()
