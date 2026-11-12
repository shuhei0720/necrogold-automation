"""The selected TEST091 lane must bind current sources and complete scopes."""
import importlib.util
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
WORKFLOW = HERE.parents[1]/'.github/workflows/loopctrl-geometry.yml'
BASELINE = 'c9e087050f5d6c7c30d8385014ea0909e534c963'


def runner_module():
    spec = importlib.util.spec_from_file_location('device_host_runner091', HERE/'run_test091_host.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def case(result='green'):
    def test(self):
        if result == 'skip':
            self.skipTest('not executed')
        elif result == 'failure':
            self.fail('semantic failure')
        elif result == 'error':
            raise RuntimeError('environment failure')
    return type('Selected', (unittest.TestCase,), {'test_one': test})('test_one')


class DeviceHostSelection091Tests(unittest.TestCase):
    def test_device_lane_selects_current_runner_without_historical_runtime_suites(self):
        source = WORKFLOW.read_text()
        host = source.split('  test061-host-contracts:\n', 1)[1].split('  focused-build:\n', 1)[0]
        self.assertIn('NATIVE_HOST_RUNNER=driver/patches/loopctrl/run_test091_host.py', host)
        build = source.split('  focused-build:\n', 1)[1].split('\n  build:\n', 1)[0]
        pin = build.split('- name: Verify TEST091 initial rejection pin against baseline and current Runtime\n', 1)[1].split('      - ', 1)[0]
        self.assertIn("        if: inputs.native_lane == 'device'\n", pin)
        self.assertIn('check_initial_rejection091.py upstream "$RUNNER_TEMP/test091-initial-rejection"', pin)
        self.assertIn('${{ runner.temp }}/test091-initial-rejection/', build)
        for title in ('Verify TEST070 Runtime dispatch Red and Green',
                      'Verify TEST081 all-restart decision retention through actual Runtime cache and export',
                      'Run actual Runtime TEST061 public integration fixtures',
                      'Detect TEST061 boundary rollback faults',
                      'Run independent actual Runtime shop world16 endpoint'):
            block = build.split('- name: '+title+'\n', 1)[1].split('      - ', 1)[0]
            self.assertIn("        if: inputs.native_lane != 'device'\n", block)
        for title in ('Build and package unsigned IPA',
                      'Verify actual source-specific Perception compiler profile',
                      'Verify package and record provenance'):
            block = build.split('- name: '+title+'\n', 1)[1].split('      - ', 1)[0]
            self.assertNotIn('        if:', block)

    def test_baseline_thin_entries_and_exact_native_change_scope_are_current(self):
        runner = runner_module()
        self.assertEqual(BASELINE, runner.NATIVE_BASELINE)
        self.assertEqual({'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Navigation.c',
                          'LoopCtrlUITests/NG2Runtime.swift'}, runner.EXPECTED_NATIVE_CHANGES)
        self.assertTrue(runner.SCOPE_FINALIZED)
        new = {row[2]:len(row[3]) for row in runner.NATIVE_CASES if row[4]}
        self.assertEqual({'test091-terrain-axis':4, 'test091-opening':5, 'test091-initial-scene':8}, new)
        self.assertEqual(34, sum(len(row[3]) for row in runner.NATIVE_CASES))
        self.assertEqual(10, len(runner.NATIVE_CASES))
        root = HERE.parents[1]
        for old, new in (('necroprobe/test090.py', 'necroprobe/test091.py'),
                         ('test_090.sh', 'test_091.sh')):
            self.assertEqual((root/old).read_bytes().replace(b'090', b'091'), (root/new).read_bytes())
        with patch.object(runner, 'RETAINED_PATHS', ('necroprobe/native_walk.py',)), \
                patch.object(runner, 'pinned_bytes', return_value=b'new'), \
                patch.object(runner, 'git', side_effect=[b'f'*40, b'old']), \
                self.assertRaisesRegex(ValueError, 'retained TEST090 source changed'):
            runner.source_identity(Path('/driver'), {})

    def test_unfrozen_duplicate_missing_overridden_and_unbound_inventories_are_rejected(self):
        runner = runner_module()
        with patch.object(runner, 'SCOPE_FINALIZED', False), self.assertRaises(ValueError):
            runner.ensure_scope()
        for rows in ((), (('m', 'C', 'dup', {'test_one'}, True),)*2):
            with patch.object(runner, 'SCOPE_FINALIZED', True), \
                    patch.object(runner, 'NATIVE_CASES', rows), self.assertRaises(ValueError):
                runner.ensure_scope()
        for values in ([], [case(), case()]):
            with self.subTest(count=len(values)), self.assertRaises(ValueError):
                runner.selected_cases(values)
        klass = type('Selected', (unittest.TestCase,), {'test_one': lambda self: None,
                                                      'test_other': lambda self: None})
        for methods in ({'test_missing'}, {'test_one'}):
            with self.assertRaises(ValueError):
                runner.method_cases(klass, methods, exact=True)
        for name in ('BASELINE_NAV', 'NECRO_TEST090_BASELINE_CONTROLLER', 'NECRO_TEST091_BASELINE_NAV'):
            with self.subTest(name=name), patch.dict(runner.os.environ, {name: ''}), self.assertRaises(ValueError):
                runner.reject_fixture_overrides()
        names = ('fake091.module',)
        module = types.SimpleNamespace(C=klass)
        with patch.object(runner, 'CORE_MODULES', ()), \
                patch.object(runner, 'NATIVE_CASES', ((names[0], 'C', 'scope', {'test_one'}, False),)), \
                patch.object(runner.importlib, 'import_module', return_value=module):
            suites = runner.native_suites(Path('/patched'))
        self.assertEqual(Path('/patched/LoopCtrlUITests'), module.CORE)
        self.assertEqual(['scope'], [row[0] for row in suites])

    def test_skip_failure_error_and_empty_scopes_never_become_passing_evidence(self):
        runner = runner_module()
        for outcome in ('green', 'skip', 'failure', 'error'):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as folder, patch('builtins.print'):
                output = Path(folder)
                evidence = {}
                if outcome == 'green':
                    runner.run_scope('unit', [case(outcome)], output, evidence)
                else:
                    with self.assertRaises(RuntimeError):
                        runner.run_scope('unit', [case(outcome)], output, evidence)
                self.assertEqual(1, evidence['unit']['tests_run'])
                self.assertTrue((output/'test091-host-scope.json').is_file())
        with tempfile.TemporaryDirectory() as folder, self.assertRaises(ValueError):
            runner.run_scope('empty', [], Path(folder), {})


if __name__ == '__main__':
    unittest.main()
