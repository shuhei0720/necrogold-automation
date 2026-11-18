"""Selection, retained-source and entry guards for the narrow TEST114 lane."""
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
WORKFLOW = ROOT/'.github/workflows/loopctrl-geometry.yml'


def module(name):
    spec = importlib.util.spec_from_file_location('device114_'+name, HERE/(name+'.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def one_case(outcome='green'):
    def test(self):
        if outcome == 'skip':
            self.skipTest('not executed')
        elif outcome == 'failure':
            self.fail('semantic failure')
        elif outcome == 'error':
            raise RuntimeError('environment failure')
    return type('Selected', (unittest.TestCase,), {'test_one': test})('test_one')


class DeviceHostSelection114Tests(unittest.TestCase):
    def test_pending_empty_duplicate_or_overridden_scope_never_executes(self):
        runner = module('run_test114_host')
        for flag in ('SCOPE_FINALIZED', 'RUNTIME_SCOPE_FINALIZED'):
            with patch.object(runner, flag, False), self.assertRaises(ValueError):
                runner.ensure_scope()
        rows = (('m', 'C', 'one', frozenset({'test_one'}), True),)
        with patch.object(runner, 'SCOPE_FINALIZED', True), patch.object(runner, 'RUNTIME_SCOPE_FINALIZED', True), patch.object(runner, 'CURRENT_MAC_CASES', ('current_view',)), patch.object(runner, 'CLIENT_PRODUCT_CHANGES', frozenset({'client.py'})), patch.object(runner, 'NEW_PATHS', frozenset({'new.py'})), patch.object(runner, 'CASES', rows):
            runner.ensure_scope()
            for bad in ((), rows*2):
                with patch.object(runner, 'CASES', bad), self.assertRaises(ValueError):
                    runner.ensure_scope()
            for key in ('CURRENT_MAC_CASES', 'CLIENT_PRODUCT_CHANGES', 'NEW_PATHS'):
                with patch.object(runner, key, ()), self.assertRaises(ValueError):
                    runner.ensure_scope()
        for name in ('BASELINE_NAV', 'NECRO114_RING_SOURCE', 'NECRO113_GOODS_CORE', 'NECRO112_YIELD_CORE', 'NECRO_TEST114_CORE'):
            with patch.dict(runner.os.environ, {name: ''}), self.assertRaises(ValueError):
                runner.reject_fixture_overrides()

    def test_native_delta_is_exactly_ring_and_controller_from_test113(self):
        runner = module('run_test114_host')
        expected = {'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Ring.c'}
        self.assertEqual(expected, set(runner.EXPECTED_NATIVE_CHANGES))
        self.assertEqual('25d9f0d057c97fbab61f8f5d8d23d6b567cb1620', runner.NATIVE_BASELINE)
        names = expected | {'retained-'+str(index) for index in range(34)}
        old = {name: 'a'*64 for name in names}
        new = {name: ('b'*64 if name in expected else value) for name, value in old.items()}
        self.assertEqual(expected, runner.native_delta(old, new))
        for bad in (old, dict(new, extra='b'*64), {name: value for name, value in new.items() if name != 'retained-0'}, dict(new, **{'retained-0': 'b'*64})):
            with self.assertRaises(ValueError):
                runner.native_delta(old, bad)
        with self.assertRaises(ValueError):
            runner.native_delta(old, new, set())

    def test_retained_runtime_and_nav_need_the_exact_current_mac_cases(self):
        runner = module('run_test114_host')
        before = {'LoopCtrlUITests/NG2Runtime.swift': runner.BASELINE_RUNTIME_SHA256,
            'LoopCtrlUITests/NG2Navigation.c': runner.BASELINE_NAV_SHA256,
            'LoopCtrlUITests/NG2Controller.c': 'a'*64, 'LoopCtrlUITests/NG2Ring.c': 'a'*64}
        current = dict(before, **{'LoopCtrlUITests/NG2Controller.c': 'b'*64, 'LoopCtrlUITests/NG2Ring.c': 'b'*64})
        with patch.object(runner, 'RUNTIME_SCOPE_FINALIZED', True), patch.object(runner, 'CURRENT_MAC_CASES', ('current_view',)):
            result = runner.runtime_source_identity(before, current)
            self.assertTrue(result['current_mac_execution_required'])
            self.assertFalse(result['before_runtime_api_assertion_required'])
            self.assertFalse(result['executed_in_host_selector'])
            for name in ('NG2Runtime.swift', 'NG2Navigation.c'):
                with self.assertRaises(ValueError):
                    runner.runtime_source_identity(before, dict(current, **{'LoopCtrlUITests/'+name: 'c'*64}))

    def test_frozen_native_inventory_and_current_mac_case_match_authors(self):
        runner = module('run_test114_host')
        self.assertTrue(runner.SCOPE_FINALIZED)
        self.assertTrue(runner.RUNTIME_SCOPE_FINALIZED)
        runner.ensure_scope()
        sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
        for name, klass, _label, methods, exact in runner.CASES:
            source = importlib.import_module(name)
            self.assertEqual(ROOT/(name.replace('.', '/')+'.py'), Path(source.__file__).resolve())
            available = set(unittest.defaultTestLoader.getTestCaseNames(getattr(source, klass)))
            self.assertTrue(methods <= available)
            if exact:
                self.assertEqual(methods, available)
        tree = ast.parse((HERE/'check_runtime114.py').read_text())
        declared = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == 'GREEN_CASES' for target in node.targets))
        self.assertEqual(declared, runner.CURRENT_MAC_CASES)
        self.assertNotIn('tests.test_client_drain113', {row[0] for row in runner.CASES})

    def test_python39_inventory_is_explicit_and_pending_is_fail_closed(self):
        runner = module('run_test114_python39')
        with patch.object(runner, 'SCOPE_FINALIZED', False), self.assertRaises(ValueError):
            runner.selected_suite(ROOT)
        self.assertTrue(runner.SCOPE_FINALIZED)
        self.assertTrue(runner.CASES)
        sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
        _host, selected = runner.selected_suite(ROOT)
        self.assertEqual(sum(len(row[3]) for row in runner.CASES), len(selected))
        self.assertEqual(len(selected), len({case.id() for case in selected}))

    def test_entry_retains_capabilities_and_bounds_readonly_diagnostics(self):
        sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
        from necroprobe import test113, test114
        from necroprobe.native_cycle import IRREGULAR_PROTOCOL
        from necroprobe.validation import ProbeError
        self.assertTrue(issubclass(test114.DeviceClient114, test113.DeviceClient113))
        self.assertIs(test114.DeviceClient114.protocol_spec, IRREGULAR_PROTOCOL)
        self.assertEqual(test113.DeviceClient113.required_capabilities, test114.DeviceClient114.required_capabilities)
        self.assertIs(test114.DeviceClient114.yield_after_restart, True)
        self.assertIs(test114.DeviceClient114.allow_restarted_budget, True)
        self.assertIs(test114.DeviceClient114.diagnostics114, True)
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(0, test114.main(['--check']))
        self.assertEqual('native-device-failures-trial-v114 / 1.98.16-ngg2\n', output.getvalue())
        with patch.object(test114, 'device_main', return_value=7) as main:
            self.assertEqual(7, test114.main(['--recovery']))
        self.assertEqual('114', main.call_args.kwargs['test_number'])
        self.assertIs(main.call_args.kwargs['client_class'], test114.DeviceClient114)
        # Validation has no transport or game side effects.
        client = object.__new__(test114.DeviceClient114)
        client._validate('recent_logs', {'max_elements': 500})
        client._validate('necro_native_status', {'run_id': '1'*32, 'keepalive': False})
        for method, params in (('recent_logs', {'max_elements': True}),
                ('recent_logs', {'max_elements': 501}),
                ('recent_logs', {'max_elements': 500, 'extra': 0}),
                ('necro_native_status', {'run_id': '1'*32, 'keepalive': True}),
                ('necro_native_status', {'run_id': 'x'*32, 'keepalive': False}),
                ('tap', {})):
            with self.assertRaises(ProbeError):
                client._validate(method, params)
        shell = (ROOT/'test_114.sh').read_text()
        for required in ('necroprobe.test114 --check', 'native-device-failures-trial-v114 / 1.98.16-ngg2',
                'python3 -m necroprobe.test114 "$@"', '--until-target', '--recovery'):
            self.assertIn(required, shell)

    def test_workflow_selects_only_current114_boundaries_and_pinned_python39(self):
        source = WORKFLOW.read_text()
        host = source.split('  test061-host-contracts:\n', 1)[1].split('  focused-build:\n', 1)[0]
        self.assertIn('NATIVE_HOST_RUNNER=driver/patches/loopctrl/run_test114_host.py', host)
        self.assertLess(host.index('DEVICE_PROFILE=113'), host.index('DEVICE_PROFILE=114'))
        self.assertIn('test114-python39-provider.json', host)
        self.assertIn('steps.python39_114.outputs.python-path', host)
        self.assertIn('run_test114_python39.py driver', host)
        self.assertIn('fe04e8b27bd69ca2144fc542428f8b9b5287b6a2e45516a4acfe2c2bc3102773', host)
        build = source.split('  focused-build:\n', 1)[1].split('\n  build:\n', 1)[0]
        title = 'Verify TEST114 current-FULL callbacks against exact sealed native sources'
        step = build.split('- name: '+title+'\n', 1)[1].split('      - ', 1)[0]
        self.assertIn("device_profile == '114'", step)
        self.assertIn('set -euo pipefail', step)
        self.assertIn('check_runtime114.py upstream', step)
        self.assertNotIn('--expect-red', step)
        before = build.split('- name: Verify TEST114 current-FULL before-Controller assertion with retained Runtime\n', 1)[1].split('      - ', 1)[0]
        self.assertIn("device_profile == '114'", before)
        self.assertIn('--expect-red --before-controller', before)
        self.assertIn('1df5c2df744e154e0af8be29c862bb48743d516daa97858f9575be35017d8fc3', before)
        self.assertIn('25d9f0d057c97fbab61f8f5d8d23d6b567cb1620:patches/loopctrl/ngg2/NG2Controller.c', before)
        self.assertIn('${{ runner.temp }}/test114-runtime-before/', build)
        self.assertIn('            upstream/LoopCtrlKit/RPCTypes.swift\n', build)
        self.assertIn('${{ runner.temp }}/test114-runtime/', build)
        for title in ('Install TEST094 focused Swift fixture image decoder',
                'Verify TEST094 actual authenticated owner and public cycle schema',
                'Verify TEST094 immutable spool and actual filesystem fault boundaries',
                'Verify TEST094 immutable terminal export and exact image roundtrip',
                'Verify TEST094 selected actual Runtime cycle callbacks'):
            old = build.split('- name: '+title+'\n', 1)[1].split('      - ', 1)[0]
            self.assertIn("device_profile != '114'", old)
        self.assertIn('runs-on: macos-26', build)
        self.assertIn('runs-on: ubuntu-latest', source)

    def test_skip_error_failure_duplicates_and_empty_are_never_green(self):
        runner = module('run_test114_host')
        for outcome in ('green', 'skip', 'failure', 'error'):
            with tempfile.TemporaryDirectory() as temporary, patch('builtins.print'):
                output = Path(temporary)
                evidence = {}
                if outcome == 'green':
                    runner.run_scope('unit', [one_case()], output, evidence)
                else:
                    with self.assertRaises(RuntimeError):
                        runner.run_scope('unit', [one_case(outcome)], output, evidence)
                self.assertEqual(1, evidence['unit']['tests_run'])
                self.assertTrue((output/'test114-host-scope.json').is_file())
        for cases in ([], [one_case(), one_case()]):
            with self.assertRaises(ValueError):
                runner.selected_cases(cases)


if __name__ == '__main__':
    unittest.main()
