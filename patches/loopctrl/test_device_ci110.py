"""TEST110 closed selection and required current Runtime/Spool evidence contracts."""
import ast
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
WORKFLOW = HERE.parents[1] / '.github/workflows/loopctrl-geometry.yml'
EXPECTED_HOST_SCOPES = 18
EXPECTED_HOST_METHODS = 173
EXPECTED_NEW_METHODS = 75
EXPECTED_PYTHON_METHODS = 108


def module(name):
    spec = importlib.util.spec_from_file_location('device110_' + name, HERE / (name + '.py'))
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


def one_case(outcome='green'):
    def test(self):
        if outcome == 'skip': self.skipTest('not executed')
        elif outcome == 'failure': self.fail('semantic failure')
        elif outcome == 'error': raise RuntimeError('environment failure')
    return type('Selected', (unittest.TestCase,), {'test_one': test})('test_one')


class DeviceHostSelection110Tests(unittest.TestCase):
    def test_frozen_source_methods_match_the_selected_inventory_exactly(self):
        runner = module('run_test110_host')
        self.assertEqual(EXPECTED_HOST_SCOPES, len(runner.CASES))
        self.assertEqual(EXPECTED_HOST_METHODS, sum(len(row[3]) for row in runner.CASES))
        self.assertEqual(EXPECTED_NEW_METHODS, sum(len(row[3]) for row in runner.CASES if row[0].endswith('110')))
        self.assertTrue(runner.RUNTIME_SCOPE_FINALIZED)
        driver = ast.parse((HERE / 'check_runtime110.py').read_text())
        declared = next(ast.literal_eval(n.value) for n in driver.body if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == 'GREEN_CASES' for t in n.targets))
        self.assertEqual(29, len(declared)); self.assertEqual(29, len(set(declared)))
        self.assertEqual(declared, runner.CURRENT_MAC_CASES)
        for name, klass, _label, expected, exact in runner.CASES:
            tree = ast.parse((HERE.parents[1] / (name.replace('.', '/') + '.py')).read_text())
            target = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == klass)
            actual = {n.name for n in target.body if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')}
            self.assertTrue(exact); self.assertEqual(set(expected), actual, name + '.' + klass)

    def test_pending_empty_duplicate_missing_and_fixture_overrides_cannot_execute(self):
        runner = module('run_test110_host')
        with patch.object(runner, 'SCOPE_FINALIZED', False), self.assertRaises(ValueError):
            runner.ensure_scope()
        with patch.object(runner, 'SCOPE_FINALIZED', True), patch.object(runner, 'RUNTIME_SCOPE_FINALIZED', True), patch.object(runner, 'CURRENT_MAC_CASES', ('current',)):
            runner.ensure_scope()
            for rows in ((), (('m', 'C', 'dup', frozenset({'test_one'}), True),) * 2):
                with patch.object(runner, 'CASES', rows), self.assertRaises(ValueError): runner.ensure_scope()
            with patch.object(runner, 'REQUIRED_NEW_SCOPES', frozenset({'missing'})), self.assertRaises(ValueError):
                runner.ensure_scope()
        for name in ('BASELINE_NAV', 'NECRO_TEST110_ACK_CORE', 'NECRO110_FIXTURE'):
            with patch.dict(runner.os.environ, {name: ''}), self.assertRaises(ValueError): runner.reject_fixture_overrides()

    def test_current_runtime_policy_never_accepts_unchanged_history_as_execution(self):
        runner = module('run_test110_host')
        before = {'LoopCtrlUITests/NG2Runtime.swift': runner.BASELINE_RUNTIME_SHA256}
        current = {'LoopCtrlUITests/NG2Runtime.swift': 'a' * 64, 'LoopCtrlUITests/NG2Controller.c': 'b' * 64}
        with patch.object(runner, 'RUNTIME_SCOPE_FINALIZED', True), patch.object(runner, 'CURRENT_MAC_CASES', ('actual_case',)):
            value = runner.runtime_source_identity(before, current)
            self.assertEqual('selected_current_runtime_callbacks_required', value['policy'])
            self.assertIs(value['executed_in_host_selector'], False)
            self.assertIs(value['current_mac_execution_required'], True)
            self.assertEqual(['actual_case'], value['expected_current_mac_cases'])
            self.assertNotIn('historical_mac', value)
            for bad in ({}, dict(current, **{'LoopCtrlUITests/NG2Runtime.swift': runner.BASELINE_RUNTIME_SHA256}),
                dict(current, **{'LoopCtrlUITests/NG2Runtime.swift': 'g' * 64})):
                with self.assertRaises(ValueError): runner.runtime_source_identity(before, bad)
        with patch.object(runner, 'RUNTIME_SCOPE_FINALIZED', False), self.assertRaises(ValueError):
            runner.runtime_source_identity(before, current)

    def test_native_delta_keeps_all_36_sources_and_only_the_approved_changes(self):
        runner = module('run_test110_host')
        self.assertEqual('c2f76243c77a51682c24a4e059002cd732fd547d', runner.NATIVE_BASELINE)
        self.assertEqual(10, len(runner.EXPECTED_NATIVE_CHANGES))
        self.assertFalse(runner.EXPECTED_NATIVE_ADDITIONS)
        self.assertIn('patches/loopctrl/ngg2.patch', runner.APPROVED_CHANGED_REPOSITORY)
        self.assertIn('patches/loopctrl/ngg2.patch', runner.PRODUCT_PATHS)
        patch_now,patch_old=b'current G2 patch',b'baseline G2 patch'
        manifests=({'patch_sha256':runner.sha(patch_now)},{'patch_sha256':runner.sha(patch_old)})
        self.assertEqual(runner.sha(patch_now),runner.approved_patch_identity(patch_now,patch_old,*manifests))
        for current,original in ((patch_now+b'x',patch_old),(patch_now,patch_old+b'x'),(patch_old,patch_old)):
            with self.assertRaises(ValueError):runner.approved_patch_identity(current,original,*manifests)
        changed=set(runner.git(HERE.parents[1],'diff','--name-only',runner.NATIVE_BASELINE,'HEAD').decode().splitlines())
        self.assertFalse((changed & set(runner.PRESERVED_REPOSITORY))-runner.APPROVED_CHANGED_REPOSITORY)
        before = {'changed': 'a', 'retained': 'r'}
        self.assertEqual({'changed'}, runner.native_delta(before, {'changed': 'b', 'retained': 'r'}, {'changed'}))
        for current in ({'changed': 'b'}, {'changed': 'b', 'retained': 'x'},
            {'changed': 'b', 'retained': 'r', 'new': 'x'}, before):
            with self.assertRaises(ValueError): runner.native_delta(before, current, {'changed'})
        self.assertIn('necroprobe/native_walk.py', runner.PRESERVED_REPOSITORY)
        for path in ('patches/loopctrl/run_test109_host.py', 'patches/loopctrl/test_device_ci109.py', *runner.shared.PRODUCT_PATHS):
            self.assertIn(path, runner.PRESERVED_REPOSITORY)
        self.assertFalse(set(runner.APPROVED_CHANGED_REPOSITORY) & {'necroprobe/native_walk.py', 'necroprobe/protocol.py'})
        self.assertEqual({'patches/loopctrl/ngg2_runtime_fakes.swift', 'patches/loopctrl/ngg2_cycle_runtime_tests.swift'},
            set(runner.APPROVED_CHANGED_FIXTURE_SHA256))
        self.assertTrue(set(runner.APPROVED_CHANGED_FIXTURE_SHA256) <= set(runner.APPROVED_CHANGED_REPOSITORY))
        for name, expected in runner.APPROVED_CHANGED_FIXTURE_SHA256.items():
            self.assertEqual(expected['current_sha256'], runner.sha((HERE.parents[1] / name).read_bytes()))
            self.assertEqual(expected['baseline_sha256'], runner.sha(runner.git(HERE.parents[1],
                'show', runner.NATIVE_BASELINE + ':' + name)))

    def test_python39_scope_has_exact_methods_and_is_not_a_host_interpreter_claim(self):
        reporter = module('run_test110_python39')
        self.assertEqual(EXPECTED_PYTHON_METHODS, sum(len(row[3]) for row in reporter.CASES))
        for name, klass, _label, expected, exact in reporter.CASES:
            tree = ast.parse((HERE.parents[1] / (name.replace('.', '/') + '.py')).read_text())
            target = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == klass)
            actual = {n.name for n in target.body if isinstance(n, ast.FunctionDef) and n.name.startswith('test_')}
            self.assertTrue(exact); self.assertEqual(set(expected), actual)
        with patch.object(reporter, 'SCOPE_FINALIZED', False), self.assertRaises(ValueError):
            reporter.selected_suite(HERE.parents[1])
        source = (HERE / 'run_test110_python39.py').read_text()
        self.assertIn('sys.version_info[:2] != (3, 9)', source)
        self.assertIn("hasattr(0, 'bit_count')", source)
        self.assertIn("'native-irregular-trial-v1 / 1.98.16-ngg2'", source)

    def test_device_lane_keeps_previous_selectors_and_requires_current_mac_fixtures(self):
        source = WORKFLOW.read_text()
        host = source.split('  test061-host-contracts:\n', 1)[1].split('  focused-build:\n', 1)[0]
        for version in ('094', '095', '096', '097', '098', '099', '100', '101', '102', '103', '104', '105', '106', '107', '108', '109', '110'):
            self.assertIn('NATIVE_HOST_RUNNER=driver/patches/loopctrl/run_test' + version + '_host.py', host)
        self.assertLess(host.index('DEVICE_PROFILE=109'), host.index('DEVICE_PROFILE=110'))
        self.assertIn("python-version: '3.9'", host)
        self.assertIn('steps.python39.outputs.python-path', host)
        self.assertIn('run_test110_python39.py driver', host)
        build = source.split('  focused-build:\n', 1)[1].split('\n  build:\n', 1)[0]
        for title in ('Install TEST094 focused Swift fixture image decoder',
            'Verify TEST094 actual authenticated owner and public cycle schema',
            'Verify TEST094 immutable spool and actual filesystem fault boundaries',
            'Verify TEST094 immutable terminal export and exact image roundtrip',
            'Verify TEST094 selected actual Runtime cycle callbacks'):
            block = build.split('- name: ' + title + '\n', 1)[1].split('      - ', 1)[0]
            self.assertIn("device_profile != '110'", block)
        for title, command in (
            ('Verify TEST110 current Runtime callbacks against exact sealed native sources', 'check_runtime110.py upstream'),
            ('Verify TEST110 current Spool reservations and actual filesystem fault boundaries', 'check_cycle_spool110.py')):
            block = build.split('- name: ' + title + '\n', 1)[1].split('      - ', 1)[0]
            self.assertIn("device_profile == '110'", block)
            self.assertIn('set -euo pipefail', block); self.assertIn(command, block)
            self.assertNotIn('--expect-red', block)
        self.assertIn('check_cycle_spool110.py "$RUNNER_TEMP/test110-spool" --fault-red', build)
        self.assertIn('${{ runner.temp }}/test110-runtime/', build)
        self.assertIn('${{ runner.temp }}/test110-spool/', build)
        self.assertIn('runs-on: macos-26', build)
        red = source.split('  test110-runtime-red:\n', 1)[1].split('  test099-runtime-red:\n', 1)[0]
        self.assertIn('check_runtime110.py upstream "$RUNNER_TEMP/test110-runtime-red" --expect-red', red)
        self.assertNotIn('run_test110_host.py', red)

    def test_skip_error_failure_duplicate_and_empty_never_become_green(self):
        runner = module('run_test110_host')
        for outcome in ('green', 'skip', 'failure', 'error'):
            with tempfile.TemporaryDirectory() as temporary, patch('builtins.print'):
                output = Path(temporary); evidence = {}
                if outcome == 'green': runner.run_scope('unit', [one_case()], output, evidence)
                else:
                    with self.assertRaises(RuntimeError): runner.run_scope('unit', [one_case(outcome)], output, evidence)
                self.assertEqual(1, evidence['unit']['tests_run'])
                self.assertTrue((output / 'test110-host-scope.json').is_file())
        for selected in ([], [one_case(), one_case()]):
            with self.assertRaises(ValueError): runner.selected_cases(selected)


if __name__ == '__main__':
    unittest.main()
