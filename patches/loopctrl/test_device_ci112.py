"""Closed TEST112 selection, source exceptions, and focused current Mac contracts."""
import ast
import importlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORKFLOW = ROOT / '.github/workflows/loopctrl-geometry.yml'
EXPECTED_PYTHON_METHODS = 55
EXPECTED_OWNED_METHODS = 47
EXPECTED_HOST_METHODS = 219
EXPECTED_HOST_SCOPES = 21


def module(name):
    spec = importlib.util.spec_from_file_location('device112_' + name, HERE / (name + '.py'))
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


def one_case(outcome='green'):
    def test(self):
        if outcome == 'skip': self.skipTest('not executed')
        elif outcome == 'failure': self.fail('semantic failure')
        elif outcome == 'error': raise RuntimeError('environment failure')
    return type('Selected', (unittest.TestCase,), {'test_one': test})('test_one')


class DeviceHostSelection112Tests(unittest.TestCase):
    def test_exact_unittest_inventory_includes_explicit_alias_methods(self):
        runner = module('run_test112_host')
        sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
        self.assertTrue(runner.SCOPE_FINALIZED); self.assertTrue(runner.RUNTIME_SCOPE_FINALIZED)
        self.assertEqual(EXPECTED_HOST_METHODS, sum(len(row[3]) for row in runner.CASES))
        self.assertEqual(EXPECTED_HOST_SCOPES, len(runner.CASES))
        driver = ast.parse((HERE / 'check_runtime112.py').read_text())
        declared = next(ast.literal_eval(n.value) for n in driver.body if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == 'GREEN_CASES' for t in n.targets))
        self.assertEqual(('legacy', 'yield', 'first_partial', 'first_full', 'producer_return', 'commit_return', 'capture_drain', 'upper_entry'), declared)
        self.assertEqual(declared, runner.CURRENT_MAC_CASES)
        for new in ('check_runtime112.py', 'ngg2_runtime112_tests.swift'):
            self.assertIn('patches/loopctrl/' + new, (HERE / 'run_test112_host.py').read_text())
        owned = 0
        for name, klass, _label, expected, exact in runner.CASES:
            source = importlib.import_module(name)
            self.assertEqual(ROOT / (name.replace('.', '/') + '.py'), Path(source.__file__).resolve())
            actual = set(unittest.defaultTestLoader.getTestCaseNames(getattr(source, klass)))
            self.assertTrue(set(expected) <= actual)
            if exact: self.assertEqual(set(expected), actual)
            if name in {'tests.test_native_singleton_phase112', 'tests.test_native_entered112',
                        'tests.test_native_upper_entry112', 'tests.test_native_restart_yield112'}:
                self.assertTrue(exact); owned += len(expected)
        self.assertEqual(EXPECTED_OWNED_METHODS, owned)
        row = next(row for row in runner.CASES if row[1] == 'NativeSingletonPhaseWait112Tests')
        self.assertEqual(6, len(row[3]))  # Public aliases installed by the fixture factory.

    def test_pending_empty_duplicate_missing_and_overrides_never_execute(self):
        runner = module('run_test112_host')
        for flag in ('SCOPE_FINALIZED', 'RUNTIME_SCOPE_FINALIZED'):
            with patch.object(runner, flag, False), self.assertRaises(ValueError): runner.ensure_scope()
        rows = (('m', 'C', 'one', frozenset({'test_one'}), True),)
        with patch.object(runner, 'SCOPE_FINALIZED', True), patch.object(runner, 'RUNTIME_SCOPE_FINALIZED', True), patch.object(runner, 'CURRENT_MAC_CASES', ('current',)), patch.object(runner, 'REQUIRED_NEW_SCOPES', frozenset({'m'})), patch.object(runner, 'CASES', rows):
            runner.ensure_scope()
            for bad in ((), rows * 2):
                with patch.object(runner, 'CASES', bad), self.assertRaises(ValueError): runner.ensure_scope()
            with patch.object(runner, 'REQUIRED_NEW_SCOPES', frozenset({'missing'})), self.assertRaises(ValueError): runner.ensure_scope()
        for name in ('BASELINE_NAV', 'NECRO112_CLASSIFICATION_CORE', 'NECRO_TEST112_CORE'):
            with patch.dict(runner.os.environ, {name: ''}), self.assertRaises(ValueError): runner.reject_fixture_overrides()

    def test_changed_runtime_requires_separate_before_api_red_and_current_callbacks(self):
        runner = module('run_test112_host')
        before = {'LoopCtrlUITests/NG2Runtime.swift': runner.BASELINE_RUNTIME_SHA256}
        current = {'LoopCtrlUITests/NG2Runtime.swift': 'a' * 64, 'LoopCtrlUITests/NG2Controller.c': 'c' * 64}
        value = runner.runtime_source_identity(before,current)
        self.assertEqual('selected_current_runtime_boundaries_required', value['policy'])
        self.assertIs(value['executed_in_host_selector'], False)
        self.assertIs(value['current_mac_execution_required'], True)
        self.assertIs(value['before_runtime_api_assertion_required'], True)
        self.assertEqual('optin_red',value['expected_before_runtime_case'])
        self.assertEqual(list(runner.CURRENT_MAC_CASES),value['expected_current_mac_cases'])
        self.assertNotIn('historical_mac',value)
        for bad in ({}, dict(current, **{'LoopCtrlUITests/NG2Runtime.swift': runner.BASELINE_RUNTIME_SHA256}), dict(current, **{'LoopCtrlUITests/NG2Runtime.swift': 'x'*64})):
            with self.assertRaises(ValueError): runner.runtime_source_identity(before,bad)
        with patch.object(runner,'RUNTIME_SCOPE_FINALIZED',False), self.assertRaises(ValueError): runner.runtime_source_identity(before,current)

    def test_all_native_sources_patch_and_exact_legacy_method_exceptions_stay_bound(self):
        runner = module('run_test112_host')
        self.assertEqual('08d6ce9a8d329e114740b2a5d67618d7f37dc3ae', runner.NATIVE_BASELINE)
        self.assertEqual(5, len(runner.EXPECTED_NATIVE_CHANGES)); self.assertFalse(runner.EXPECTED_NATIVE_ADDITIONS)
        self.assertIn('LoopCtrlUITests/NG2Runtime.swift', runner.EXPECTED_NATIVE_CHANGES)
        before = {'changed': 'a', 'retained': 'r'}
        self.assertEqual({'changed'}, runner.native_delta(before, {'changed': 'b', 'retained': 'r'}, {'changed'}))
        for current in ({'changed': 'b'}, {'changed': 'b', 'retained': 'x'}, dict(before, new='x'), before):
            with self.assertRaises(ValueError): runner.native_delta(before, current, {'changed'})
        now, old = b'current patch', b'old patch'
        manifests = ({'patch_sha256':runner.sha(now)}, {'patch_sha256':runner.sha(old)})
        self.assertEqual(runner.sha(now), runner.approved_patch_identity(now, old, *manifests))
        with self.assertRaises(ValueError): runner.approved_patch_identity(now+b'x', old, *manifests)
        exceptions = runner.LEGACY_FIXTURE_EXCEPTIONS
        self.assertEqual(1, len(exceptions)); self.assertEqual(1, sum(len(r['methods']) for r in exceptions))
        for row in exceptions:
            original = runner.git(ROOT, 'show', runner.NATIVE_BASELINE + ':' + row['path'])
            current = (ROOT / row['path']).read_bytes()
            self.assertEqual(runner.sha(current), runner.preserved_fixture_identity(row['path'], current, original))
            with self.assertRaises(ValueError): runner.preserved_fixture_identity(row['path'], current+b'\n', original)
        with self.assertRaises(ValueError): runner.preserved_fixture_identity('retained.py', now, old)

    def test_actual_python39_closed_scope_and_entry_are_separate_from_host(self):
        sys.path[:0] = [str(ROOT),str(ROOT/'tests')]
        reporter = module('run_test112_python39')
        self.assertTrue(reporter.SCOPE_FINALIZED)
        self.assertEqual(EXPECTED_PYTHON_METHODS, sum(len(row[3]) for row in reporter.CASES))
        for name, klass, _label, expected, exact in reporter.CASES:
            source = importlib.import_module(name)
            actual = set(unittest.defaultTestLoader.getTestCaseNames(getattr(source, klass)))
            self.assertTrue(set(expected) <= actual)
            if exact: self.assertEqual(set(expected), actual)
        with patch.object(reporter, 'SCOPE_FINALIZED', False), self.assertRaises(ValueError): reporter.selected_suite(ROOT)
        source = (HERE / 'run_test112_python39.py').read_text()
        self.assertIn('sys.version_info[:2] != (3, 9)', source)
        self.assertIn("hasattr(0, 'bit_count')", source)
        self.assertIn("'native-restart-yield-trial-v1 / 1.98.16-ngg2'", source)

    def test_device112_keeps_old_lanes_and_selects_only_focused_current_mac(self):
        source = WORKFLOW.read_text()
        host = source.split('  test061-host-contracts:\n',1)[1].split('  focused-build:\n',1)[0]
        for version in ('109','110','111','112'):
            self.assertIn('NATIVE_HOST_RUNNER=driver/patches/loopctrl/run_test'+version+'_host.py',host)
        self.assertLess(host.index('DEVICE_PROFILE=111'),host.index('DEVICE_PROFILE=112'))
        self.assertIn('test112-python39-provider.json',host)
        self.assertIn('fe04e8b27bd69ca2144fc542428f8b9b5287b6a2e45516a4acfe2c2bc3102773',host)
        self.assertIn('steps.python39_112.outputs.python-path',host)
        self.assertIn('run_test112_python39.py driver',host)
        build=source.split('  focused-build:\n',1)[1].split('\n  build:\n',1)[0]
        for title,red in (('Verify TEST112 opt-in API assertion Red against exact before Runtime',True),('Verify TEST112 current restart-yield callbacks and real shop entry against exact sealed native sources',False)):
            block=build.split('- name: '+title+'\n',1)[1].split('      - ',1)[0]
            self.assertIn("device_profile == '112'",block);self.assertIn('set -euo pipefail',block)
            self.assertIn('check_runtime112.py upstream',block)
            self.assertEqual(red,'--expect-red --baseline-runtime' in block)
            self.assertNotIn('check_runtime110.py',block);self.assertNotIn('--fault-red',block)
        self.assertIn('08d6ce9a8d329e114740b2a5d67618d7f37dc3ae:patches/loopctrl/ngg2/NG2Runtime.swift',build)
        for path in ('test112-runtime/','test112-runtime-before/'):
            self.assertIn('${{ runner.temp }}/'+path,build)
        for title in ('Install TEST094 focused Swift fixture image decoder','Verify TEST094 selected actual Runtime cycle callbacks'):
            old=build.split('- name: '+title+'\n',1)[1].split('      - ',1)[0]
            self.assertIn("device_profile != '112'",old)
        for title,profile in (('Verify TEST110 current Runtime callbacks against exact sealed native sources','110'),('Verify TEST110 current Spool reservations and actual filesystem fault boundaries','110'),('Verify TEST111 current classification source boundaries against exact sealed native sources','111')):
            old=build.split('- name: '+title+'\n',1)[1].split('      - ',1)[0]
            self.assertIn("device_profile == '"+profile+"'",old)
        self.assertIn('runs-on: macos-26',build);self.assertIn('runs-on: ubuntu-latest',source)
        self.assertIn('test112-runtime-diagnostic]',source.split('jobs:',1)[0])
        diagnostic=source.split('  test112-runtime-diagnostic:\n',1)[1].split('\n  test110-runtime-red:\n',1)[0]
        self.assertIn("if: inputs.native_lane == 'test112-runtime-diagnostic'",diagnostic)
        self.assertIn('runs-on: macos-26',diagnostic);self.assertNotIn('needs:',diagnostic)
        self.assertEqual(2,diagnostic.count('fetch-depth: 0'))
        self.assertIn('ref: ${{ github.sha }}',diagnostic)
        self.assertIn('ref: 6e25cf6a9f65bc86c372cdce94bdb151d0cf6767',diagnostic)
        for command in ('apply_patch.py upstream','apply_ngg2.py upstream','inspect_native_sources','check_runtime112.py upstream'):
            self.assertIn(command,diagnostic)
        self.assertIn('set -euo pipefail',diagnostic)
        self.assertIn('loopctrl-test112-runtime-diagnostic',diagnostic)
        self.assertIn('${{ runner.temp }}/test112-runtime-diagnostic/',diagnostic)
        self.assertIn('if: always()',diagnostic)
        for excluded in ('--expect-red','--baseline-runtime','check_runtime110.py','--fault-red','run_test112_host.py','run_test112_python39.py','build_unsigned_ipa','xcodebuild','brew install','setup-python'):
            self.assertNotIn(excluded,diagnostic)
        ready=source.split('  native-source-ready:\n',1)[1].split('\n  native-host-contracts:\n',1)[0]
        self.assertIn("inputs.native_lane != 'test112-runtime-diagnostic'",ready)

    def test_skip_error_failure_duplicate_and_empty_never_become_green(self):
        runner = module('run_test112_host')
        for outcome in ('green', 'skip', 'failure', 'error'):
            with tempfile.TemporaryDirectory() as temporary, patch('builtins.print'):
                output=Path(temporary); evidence={}
                if outcome == 'green': runner.run_scope('unit', [one_case()], output, evidence)
                else:
                    with self.assertRaises(RuntimeError): runner.run_scope('unit', [one_case(outcome)], output, evidence)
                self.assertEqual(1,evidence['unit']['tests_run'])
                self.assertTrue((output/'test112-host-scope.json').is_file())
        for selected in ([],[one_case(),one_case()]):
            with self.assertRaises(ValueError): runner.selected_cases(selected)


if __name__ == '__main__': unittest.main()
