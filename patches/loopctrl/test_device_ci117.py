"""TEST117 selectors fail closed until exact author/source scopes are frozen."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location('device117_'+name, HERE/(name+'.py'))
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


def one_case(outcome='green'):
    class Fixture(unittest.TestCase):
        def runTest(self):
            if outcome == 'skip': self.skipTest('procedural boundary')
            if outcome == 'failure': self.fail('procedural boundary')
            if outcome == 'error': raise ValueError('procedural boundary')
    return Fixture()


class DeviceHostSelection117Tests(unittest.TestCase):
    def controls(self):
        return dict(SCOPE_FINALIZED=True, MAC_SCOPE_FINALIZED=True,
            CASES=(('m', 'C', 'one', frozenset({'test_one'}), True),), CORE_MODULES=('m',),
            NEW_PATHS=frozenset({'new.py'}), EXPECTED_NATIVE_CHANGES=frozenset({'native.c'}),
            EXPECTED_REPOSITORY_CHANGES=frozenset({'path.c'}), MAC_CASE_GROUPS=(('checker', ('one',)),))

    def test_pending_empty_duplicate_and_overridden_scope_never_executes(self):
        runner = module('run_test117_host')
        controls = self.controls()
        with patch.multiple(runner, **controls):
            runner.ensure_scope()
            for flag in ('SCOPE_FINALIZED', 'MAC_SCOPE_FINALIZED'):
                with patch.object(runner, flag, False), self.assertRaises(ValueError):
                    runner.ensure_scope()
            for name in ('CASES', 'CORE_MODULES', 'NEW_PATHS', 'EXPECTED_NATIVE_CHANGES',
                    'EXPECTED_REPOSITORY_CHANGES', 'MAC_CASE_GROUPS'):
                with patch.object(runner, name, ()), self.assertRaises(ValueError):
                    runner.ensure_scope()
            with patch.object(runner, 'CASES', controls['CASES']*2), self.assertRaises(ValueError):
                runner.ensure_scope()
            with patch.object(runner, 'MAC_CASE_GROUPS', (('checker', ('one', 'one')),)), self.assertRaises(ValueError):
                runner.ensure_scope()
        for variable in ('BASELINE_NAV', 'NECRO_TEST_DLL', 'NECRO117_FIXTURE'):
            with patch.dict('os.environ', {variable: 'forged'}), self.assertRaises(ValueError):
                runner.reject_fixture_overrides()

    def test_pending_python39_cannot_import_or_execute_product(self):
        runner = module('run_test117_python39')
        with patch.object(runner, 'SCOPE_FINALIZED', False), patch.object(runner.importlib, 'import_module') as imported:
            with self.assertRaises(ValueError): runner.selected_suite(ROOT)
        imported.assert_not_called()

    def test_python39_selects_exact_new_methods_and_old_40_without_duplication(self):
        runner = module('run_test117_python39'); host = module('run_test117_host')
        selected = []
        for name, klass, _label, methods, exact in runner.CASES:
            imported = __import__(name, fromlist=[klass])
            self.assertEqual(ROOT/(name.replace('.', '/')+'.py'), Path(imported.__file__).resolve())
            selected.extend(host.method_cases(getattr(imported, klass), methods, exact=exact))
        self.assertEqual(65, len(host.selected_cases(selected)))
        self.assertEqual(40, sum(len(row[3]) for row in runner.shared.CASES))

    def test_empty_duplicate_failure_error_and_skip_are_not_green(self):
        runner = module('run_test117_host')
        for cases in ([], [one_case(), one_case()]):
            with self.assertRaises(ValueError): runner.selected_cases(cases)
        with self.assertRaises(ValueError): runner.method_cases(type(one_case()), frozenset({'test_missing'}))
        for outcome in ('green', 'skip', 'failure', 'error'):
            with tempfile.TemporaryDirectory() as temporary, patch('builtins.print'):
                output = Path(temporary); evidence = {}
                if outcome == 'green': runner.run_scope('fixture', [one_case(outcome)], output, evidence)
                else:
                    with self.assertRaises(RuntimeError): runner.run_scope('fixture', [one_case(outcome)], output, evidence)
                self.assertEqual(1, evidence['fixture']['tests_run'])

    def test_device_workflow_selects_117_and_reuses_pinned_actual_python39(self):
        source = (ROOT/'.github/workflows/loopctrl-geometry.yml').read_text()
        host = source.split('  test061-host-contracts:\n', 1)[1].split('  focused-build:\n', 1)[0]
        self.assertIn('NATIVE_HOST_RUNNER=driver/patches/loopctrl/run_test117_host.py', host)
        self.assertLess(host.index('DEVICE_PROFILE=116'), host.index('DEVICE_PROFILE=117'))
        self.assertIn("steps.host_contracts.outputs.device_profile == '117'", host)
        self.assertIn('run_test117_python39.py driver', host)
        self.assertIn('steps.python39_116.outputs.python-path', host)
        self.assertIn('fe04e8b27bd69ca2144fc542428f8b9b5287b6a2e45516a4acfe2c2bc3102773', host)
        build = source.split('  focused-build:\n', 1)[1].split('\n  build:\n', 1)[0]
        old_title = '- name: Verify TEST116 current continuous Runtime and retained final-clock callbacks against sealed sources\n'
        old = build.split(old_title, 1)[1].split('      - name:', 1)[0]
        self.assertIn("device_profile == '116'", old)
        self.assertNotIn("device_profile == '117'", old)
        title = '- name: Verify TEST117 initial UI assertion Red and five current Mac boundary cases\n'
        self.assertIn(title, build, 'the selected 117 device profile needs its own actual Mac boundary checker')
        current = build.split(title, 1)[1].split('      - name:', 1)[0]
        self.assertIn("device_profile == '117'", current)
        self.assertIn('check_runtime117.py upstream', current)
        self.assertIn('--expect-initial-ui-red', current)
        self.assertNotIn('--before-runtime', current)
        self.assertNotIn('git -C driver show', current)
        self.assertNotIn('check_runtime116.py', current)


if __name__ == '__main__':
    unittest.main()
