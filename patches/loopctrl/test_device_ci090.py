"""The TEST090 lane binds selected methods to the exact source used by its IPA."""
from pathlib import Path
import importlib.util
import tempfile
import types
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
WORKFLOW = HERE.parents[1]/'.github/workflows/loopctrl-geometry.yml'
BASELINE = '169eb67bc4906c83e6bedf30678b99a240b44522'


def runner_module():
    spec = importlib.util.spec_from_file_location('device_host_runner090', HERE/'run_test090_host.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def case(result='green'):
    def test(self):
        if result == 'skip': self.skipTest('not executed')
        elif result == 'failure': self.fail('semantic failure')
        elif result == 'error': raise RuntimeError('environment failure')
    return type('Selected', (unittest.TestCase,), {'test_one': test})('test_one')


class DeviceHostSelection090Tests(unittest.TestCase):
    def test_device_lane_selects_current_runner_and_reuses_unchanged_runtime_proofs(self):
        source = WORKFLOW.read_text()
        host = source.split('  test061-host-contracts:\n', 1)[1].split('  focused-build:\n', 1)[0]
        self.assertIn('NATIVE_HOST_RUNNER=driver/patches/loopctrl/run_test090_host.py', host)
        build = source.split('  focused-build:\n', 1)[1].split('\n  build:\n', 1)[0]
        for title in ('Verify TEST070 Runtime dispatch Red and Green',
                      'Verify TEST081 all-restart decision retention through actual Runtime cache and export'):
            block = build.split('- name: '+title+'\n', 1)[1].split('      - ', 1)[0]
            self.assertIn("        if: inputs.native_lane != 'device'\n", block)
        for title in ('Build and package unsigned IPA', 'Verify actual source-specific Perception compiler profile',
                      'Verify package and record provenance'):
            block = build.split('- name: '+title+'\n', 1)[1].split('      - ', 1)[0]
            self.assertNotIn('        if:', block)

    def test_baseline_and_required_new_scopes_cannot_silently_reuse_old_source_pins(self):
        runner = runner_module()
        self.assertEqual(BASELINE, runner.NATIVE_BASELINE)
        expected = {'test090-hud-unit', 'test090-revealed-route', 'test090-thin-gate'}
        actual = {row[2] for row in runner.NATIVE_CASES}
        self.assertTrue(expected <= actual, 'all three independently diagnosed fixes need their new unit scope')
        self.assertTrue(all(row[4] for row in runner.NATIVE_CASES if row[2] in expected))
        self.assertEqual({'LoopCtrlUITests/NG2Controller.c', 'LoopCtrlUITests/NG2Navigation.c',
                          'LoopCtrlUITests/NG2Perception.c'}, runner.EXPECTED_NATIVE_CHANGES)

    def test_invalid_inventory_overrides_and_unbound_native_fixtures_are_rejected(self):
        runner = runner_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'unit.py').write_bytes(b'changed')
            with patch.object(runner, 'git', return_value=b'pinned'), self.assertRaises(ValueError):
                runner.pinned_bytes(root, 'unit.py', 'f'*40)
        with patch.object(runner, 'RETAINED_PATHS', ('necroprobe/native_walk.py',)), \
                patch.object(runner, 'pinned_bytes', return_value=b'new'), \
                patch.object(runner, 'git', side_effect=[b'f'*40, b'old']), \
                self.assertRaisesRegex(ValueError, 'retained TEST089 source changed'):
            runner.source_identity(Path('/driver'), {})
        for path, (old, new) in runner.DISPLAY_LITERAL_CHANGES.items():
            baseline = ('prefix '+old+' suffix').encode()
            self.assertEqual(('prefix '+new+' suffix').encode(), runner.expected_retained_bytes(path, baseline))
            with self.assertRaises(ValueError): runner.expected_retained_bytes(path, baseline+old.encode())
        self.assertEqual(b'unchanged', runner.expected_retained_bytes('necroprobe/native_walk.py', b'unchanged'))
        for values in ([], [case(), case()]):
            with self.subTest(count=len(values)), self.assertRaises(ValueError): runner.selected_cases(values)
        for methods in ({'test_other'}, {'test_expected', 'test_unregistered'}):
            klass = type('Selected', (unittest.TestCase,), {m: lambda self: None for m in methods})
            with self.subTest(methods=sorted(methods)), self.assertRaises(ValueError):
                runner.method_cases(klass, {'test_expected'}, exact=True)
        for name in ('BASELINE_NAV', 'NECRO_TEST090_BASELINE_CONTROLLER', 'NECRO_TEST087_PROOF_BASELINE_CORE'):
            with self.subTest(name=name), patch.dict(runner.os.environ, {name: ''}), self.assertRaises(ValueError):
                runner.reject_fixture_overrides()
        modules = {}
        for name, klass, _label, methods, _exact in runner.NATIVE_CASES:
            modules[name] = types.SimpleNamespace(**{klass: type(klass, (unittest.TestCase,),
                {method: lambda self: None for method in methods})})
        for name in runner.CORE_MODULES: modules.setdefault(name, types.SimpleNamespace())
        original = runner.method_cases
        def selected(*args, **kwargs):
            self.assertTrue(all(module.CORE == Path('/patched/LoopCtrlUITests') for module in modules.values()))
            return original(*args, **kwargs)
        with patch.object(runner.importlib, 'import_module', side_effect=modules.__getitem__), \
                patch.object(runner, 'method_cases', side_effect=selected):
            runner.native_suites(Path('/patched'))
        self.assertNotIn('world', ' '.join(modules))

    def test_skip_failure_error_and_empty_scopes_never_become_passing_evidence(self):
        runner = runner_module()
        for outcome in ('green', 'skip', 'failure', 'error'):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as folder, patch('builtins.print'):
                output = Path(folder); evidence = {}
                if outcome == 'green': runner.run_scope('unit', [case(outcome)], output, evidence)
                else:
                    with self.assertRaises(RuntimeError): runner.run_scope('unit', [case(outcome)], output, evidence)
                self.assertEqual(1, evidence['unit']['tests_run'])
                self.assertTrue((output/'test090-host-scope.json').is_file())
        with tempfile.TemporaryDirectory() as folder, self.assertRaises(ValueError):
            runner.run_scope('empty', [], Path(folder), {})


if __name__ == '__main__': unittest.main()
