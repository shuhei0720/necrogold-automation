"""TEST113 selection/retention guards; native author scope is finalized later."""
import ast
import importlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORKFLOW = ROOT/'.github/workflows/loopctrl-geometry.yml'


def module(name):
    spec = importlib.util.spec_from_file_location('device113_'+name, HERE/(name+'.py'))
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


class DeviceHostSelection113Tests(unittest.TestCase):
    def test_pending_empty_duplicate_missing_and_overrides_never_execute(self):
        runner = module('run_test113_host')
        for flag in ('SCOPE_FINALIZED', 'RUNTIME_SCOPE_FINALIZED'):
            with patch.object(runner, flag, False), self.assertRaises(ValueError):
                runner.ensure_scope()
        rows = (('m', 'C', 'one', frozenset({'test_one'}), True),)
        with patch.object(runner, 'SCOPE_FINALIZED', True), patch.object(runner, 'RUNTIME_SCOPE_FINALIZED', True), patch.object(runner, 'CURRENT_MAC_CASES', ('current',)), patch.object(runner, 'REQUIRED_NEW_SCOPES', frozenset({'m'})), patch.object(runner, 'CASES', rows):
            runner.ensure_scope()
            for bad in ((), rows*2):
                with patch.object(runner, 'CASES', bad), self.assertRaises(ValueError):
                    runner.ensure_scope()
            with patch.object(runner, 'REQUIRED_NEW_SCOPES', frozenset({'missing'})), self.assertRaises(ValueError):
                runner.ensure_scope()
        for name in ('BASELINE_NAV', 'NECRO113_CLASSIFICATION_CORE', 'NECRO_TEST113_CORE'):
            with patch.dict(runner.os.environ, {name: ''}), self.assertRaises(ValueError):
                runner.reject_fixture_overrides()

    def test_exact_native_delta_is_controller_and_navigation_only(self):
        runner = module('run_test113_host')
        expected = {'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Navigation.c'}
        self.assertEqual(expected, set(runner.EXPECTED_NATIVE_CHANGES))
        self.assertEqual('6f4925214fa2efd4e9516e898611ab3c10fd3002', runner.NATIVE_BASELINE)
        old = {name: 'a'*64 for name in expected | {'unchanged'}}
        good = {name: ('b'*64 if name in expected else value) for name, value in old.items()}
        self.assertEqual(expected, runner.native_delta(old, good, expected))
        for changed in (old, dict(good, unchanged='b'*64), dict(good, extra='b'*64),
                {name: value for name, value in good.items() if name != 'unchanged'}):
            with self.assertRaises(ValueError):
                runner.native_delta(old, changed, expected)

    def test_patch_runtime_and_old_fixtures_retain_three_exact_reviewed_method_scopes(self):
        runner = module('run_test113_host')
        raw = b'retained G2 patch'
        manifest = dict(patch_sha256=runner.sha(raw))
        self.assertEqual(runner.sha(raw), runner.approved_patch_identity(raw, raw, manifest, manifest))
        with self.assertRaises(ValueError):
            runner.approved_patch_identity(raw+b'changed', raw, manifest, manifest)
        self.assertEqual(len(runner.LEGACY_FIXTURE_EXCEPTIONS), 3)
        for row in runner.LEGACY_FIXTURE_EXCEPTIONS:
            self.assertIn(row['path'], runner.APPROVED_FIXTURE_METHODS)
            self.assertEqual([runner.APPROVED_FIXTURE_METHODS[row['path']]],
                [method['name'] for method in row['methods']])
        if runner.SCOPE_FINALIZED:
            self.assertEqual(set(runner.APPROVED_FIXTURE_METHODS), {row['path'] for row in runner.LEGACY_FIXTURE_EXCEPTIONS})
        with self.assertRaises(ValueError):
            runner.preserved_fixture_identity('tests/old.py', b'changed', b'old')
        method = 'test_geometry_near_cells_and_all_protection_materials_bound_stone_scope'
        old = ('class NativeClosedRefresh081Tests:\n    def '+method+'(self):\n        assert True\n\n    def other(self):\n        assert True\n').encode()
        new = old.replace(b'assert True', b'assert 2 == 2', 1)
        row = dict(path='tests/test_native_closed_refresh081.py', old_file_sha256=runner.sha(old),
            new_file_sha256=runner.sha(new), methods=[dict(name='NativeClosedRefresh081Tests.'+method,
                old_sha256=runner.sha(ast.get_source_segment(old.decode(), ast.parse(old).body[0].body[0]).encode()),
                new_sha256=runner.sha(ast.get_source_segment(new.decode(), ast.parse(new).body[0].body[0]).encode()))])
        with patch.object(runner, 'LEGACY_FIXTURE_EXCEPTIONS', [row]):
            self.assertEqual(runner.sha(new), runner.preserved_fixture_identity(row['path'], new, old))
            for bad in (new.replace(b'def other', b'def changed'), new.replace(b'assert 2 == 2', b'assert False')):
                with self.assertRaises(ValueError):
                    runner.preserved_fixture_identity(row['path'], bad, old)
        name = 'LoopCtrlUITests/NG2Runtime.swift'
        before = {name: runner.BASELINE_RUNTIME_SHA256}
        current = dict(before, **{'LoopCtrlUITests/NG2Controller.c': 'b'*64})
        with patch.object(runner, 'RUNTIME_SCOPE_FINALIZED', True):
            value = runner.runtime_source_identity(before, current)
            self.assertFalse(value['before_runtime_api_assertion_required'])
            self.assertTrue(value['current_mac_execution_required'])
            self.assertEqual(before[name], value['current_runtime_sha256'])
            with self.assertRaises(ValueError):
                runner.runtime_source_identity(before, dict(current, **{name: 'c'*64}))

    def test_native_inventory_is_explicit_and_current_mac_scope_matches_driver(self):
        runner = module('run_test113_host')
        if not runner.SCOPE_FINALIZED:
            self.assertFalse(runner.RUNTIME_SCOPE_FINALIZED)
            with self.assertRaises(ValueError):
                runner.ensure_scope()
            return
        runner.ensure_scope()
        sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
        for name, klass, _label, expected, exact in runner.CASES:
            source = importlib.import_module(name)
            self.assertEqual(ROOT/(name.replace('.', '/')+'.py'), Path(source.__file__).resolve())
            actual = set(unittest.defaultTestLoader.getTestCaseNames(getattr(source, klass)))
            self.assertTrue(set(expected) <= actual)
            if exact:
                self.assertEqual(set(expected), actual)
        driver = ast.parse((HERE/'check_runtime113.py').read_text())
        declared = next(ast.literal_eval(node.value) for node in driver.body
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'GREEN_CASES' for t in node.targets))
        self.assertEqual(('terminal_status', 'upper_entry'), declared)
        self.assertEqual(declared, runner.CURRENT_MAC_CASES)

    def test_actual_python39_inventory_is_exact122_and_pending_is_fail_closed(self):
        runner = module('run_test113_python39')
        self.assertEqual(122, runner.EXPECTED_METHODS)
        self.assertEqual(122, sum(len(row[3]) for row in runner.CASES))
        self.assertEqual(8, len(runner.CASES[0][3]))
        self.assertEqual('tests.test_client_drain113', runner.CASES[0][0])
        with patch.object(runner, 'SCOPE_FINALIZED', False), self.assertRaises(ValueError):
            runner.selected_suite(ROOT)
        sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
        with patch.object(runner, 'SCOPE_FINALIZED', True):
            selected = runner.selected_suite(ROOT)
        self.assertEqual(122, len(selected))
        self.assertEqual(122, len({case.id() for case in selected}))

    def test_new_entry_inherits_same_capabilities_and_keeps_new_label(self):
        sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
        from necroprobe import test112, test113
        from necroprobe.native_cycle import IRREGULAR_PROTOCOL
        self.assertTrue(issubclass(test113.DeviceClient113, test112.RestartYieldClient112))
        self.assertIs(test113.DeviceClient113.protocol_spec, IRREGULAR_PROTOCOL)
        self.assertEqual(test112.RestartYieldClient112.required_capabilities, test113.DeviceClient113.required_capabilities)
        self.assertIs(test113.DeviceClient113.yield_after_restart, True)
        self.assertIs(test113.DeviceClient113.allow_restarted_budget, True)
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(0, test113.main(['--check']))
        self.assertEqual('native-device-failures-trial-v113 / 1.98.16-ngg2\n', output.getvalue())
        with patch.object(test113, 'device_main', return_value=7) as main:
            self.assertEqual(7, test113.main(['--recovery']))
        self.assertEqual('113', main.call_args.kwargs['test_number'])
        self.assertIs(main.call_args.kwargs['client_class'], test113.DeviceClient113)
        shell = (ROOT/'test_113.sh').read_text()
        for required in ('necroprobe.test113 --check', 'native-device-failures-trial-v113 / 1.98.16-ngg2',
                'python3 -m necroprobe.test113 "$@"', '--until-target', '--recovery'):
            self.assertIn(required, shell)

    def test_device113_selects_current_boundary_without_old_runtime_api_red(self):
        source = WORKFLOW.read_text()
        host = source.split('  test061-host-contracts:\n', 1)[1].split('  focused-build:\n', 1)[0]
        self.assertIn('NATIVE_HOST_RUNNER=driver/patches/loopctrl/run_test113_host.py', host)
        self.assertLess(host.index('DEVICE_PROFILE=112'), host.index('DEVICE_PROFILE=113'))
        self.assertIn('test113-python39-provider.json', host)
        self.assertIn('steps.python39_113.outputs.python-path', host)
        self.assertIn('run_test113_python39.py driver', host)
        self.assertIn('fe04e8b27bd69ca2144fc542428f8b9b5287b6a2e45516a4acfe2c2bc3102773', host)
        build = source.split('  focused-build:\n', 1)[1].split('\n  build:\n', 1)[0]
        title = 'Verify TEST113 terminal status and upper-entry callbacks against exact sealed native sources'
        step = build.split('- name: '+title+'\n', 1)[1].split('      - ', 1)[0]
        self.assertIn("device_profile == '113'", step)
        self.assertIn('set -euo pipefail', step)
        self.assertIn('check_runtime113.py upstream', step)
        self.assertNotIn('--expect-red', step)
        self.assertNotIn('check_runtime112.py', step)
        self.assertNotIn('check_runtime110.py', step)
        self.assertIn('${{ runner.temp }}/test113-runtime/', build)
        for title in ('Install TEST094 focused Swift fixture image decoder',
                'Verify TEST094 actual authenticated owner and public cycle schema',
                'Verify TEST094 immutable spool and actual filesystem fault boundaries',
                'Verify TEST094 immutable terminal export and exact image roundtrip',
                'Verify TEST094 selected actual Runtime cycle callbacks'):
            old = build.split('- name: '+title+'\n', 1)[1].split('      - ', 1)[0]
            self.assertIn("device_profile != '113'", old)
        self.assertIn('runs-on: macos-26', build)
        self.assertIn('runs-on: ubuntu-latest', source)

    def test_skip_failure_error_duplicate_and_empty_never_become_green(self):
        runner = module('run_test113_host')
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
                self.assertTrue((output/'test113-host-scope.json').is_file())
        for selected in ([], [one_case(), one_case()]):
            with self.assertRaises(ValueError):
                runner.selected_cases(selected)


if __name__ == '__main__':
    unittest.main()
