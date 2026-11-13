"""TEST094 selector/source binding and focused workflow contracts."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
WORKFLOW = HERE.parents[1] / '.github/workflows/loopctrl-geometry.yml'


def runner_module():
    spec = importlib.util.spec_from_file_location('device_host_runner094', HERE / 'run_test094_host.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def one_case(outcome='green'):
    def test(self):
        if outcome == 'skip': self.skipTest('not executed')
        elif outcome == 'failure': self.fail('semantic failure')
        elif outcome == 'error': raise RuntimeError('environment failure')
    return type('Selected', (unittest.TestCase,), {'test_one': test})('test_one')


class DeviceHostSelection094Tests(unittest.TestCase):
    def test_device_lane_selects094_and_current_focused_native_components(self):
        source = WORKFLOW.read_text()
        host = source.split('  test061-host-contracts:\n', 1)[1].split('  focused-build:\n', 1)[0]
        self.assertIn('NATIVE_HOST_RUNNER=driver/patches/loopctrl/run_test094_host.py', host)
        build = source.split('  focused-build:\n', 1)[1].split('\n  build:\n', 1)[0]
        for checker in ('check_cycle_api094.py', 'check_cycle_spool094.py --fault-red', 'check_cycle_export094.py',
                        'check_runtime_cycle094.py'):
            self.assertIn(checker, build)
        for title in ('Verify TEST070 Runtime dispatch Red and Green',
                      'Verify TEST081 all-restart decision retention through actual Runtime cache and export',
                      'Run actual Runtime TEST061 public integration fixtures',
                      'Detect TEST061 boundary rollback faults',
                      'Run independent actual Runtime shop world16 endpoint'):
            block = build.split('- name: ' + title + '\n', 1)[1].split('      - ', 1)[0]
            self.assertIn("        if: inputs.native_lane != 'device'\n", block)
        for path in ('test094-api/', 'test094-spool/', 'test094-export/', 'test094-runtime/'):
            self.assertIn(path, build)
        self.assertIn('upstream/LoopCtrlUITests/NG2RingKernel/**', build)
        for title in ('Build and package unsigned IPA', 'Verify actual source-specific Perception compiler profile',
                      'Verify package and record provenance'):
            block = build.split('- name: ' + title + '\n', 1)[1].split('      - ', 1)[0]
            self.assertNotIn('        if:', block)

    def test_fixed_scope_rejects_unfrozen_missing_duplicate_and_override_cases(self):
        runner = runner_module()
        self.assertTrue(runner.SCOPE_FINALIZED)
        counts = {row[2]: len(row[3]) for row in runner.CASES}
        self.assertEqual([14, 20, 25, 6, 30], [counts[name] for name in
            ('test094-ring', 'test094-bank', 'test094-cycle', 'test094-shadow', 'test094-client')])
        self.assertEqual(131, sum(counts.values()))
        self.assertEqual(21, len(runner.EXPECTED_NATIVE_CHANGES))
        with patch.object(runner, 'SCOPE_FINALIZED', False), self.assertRaises(ValueError):
            runner.ensure_scope()
        for rows in ((), (('m', 'C', 'dup', frozenset({'test_one'}), True),) * 2):
            with patch.object(runner, 'SCOPE_FINALIZED', True), patch.object(runner, 'CASES', rows), self.assertRaises(ValueError):
                runner.ensure_scope()
        for cases in ([], [one_case(), one_case()]):
            with self.assertRaises(ValueError): runner.selected_cases(cases)
        klass = type('Selected', (unittest.TestCase,), {'test_one': lambda self: None, 'test_extra': lambda self: None})
        for methods in ({'test_missing'}, {'test_one'}):
            with self.assertRaises(ValueError): runner.method_cases(klass, methods, exact=True)
        for name in ('BASELINE_NAV', 'NECRO_TEST093_BASELINE_CONTROLLER', 'NECRO_TEST094_BASELINE_CONTROLLER',
                     'NECRO094_BANK_FIXTURE'):
            with patch.dict(runner.os.environ, {name: ''}), self.assertRaises(ValueError):
                runner.reject_fixture_overrides()

    def test_source_roots_paths_and_hashes_are_exact_and_closed(self):
        runner = runner_module()
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'patches/loopctrl/ngg2').mkdir(parents=True)
            (root / 'tools/ring_native').mkdir(parents=True)
            (root / 'patches/loopctrl/ngg2/NG2Ring.h').write_bytes(b'header')
            (root / 'tools/ring_native/ring.h').write_bytes(b'canonical')
            specs = {
                'LoopCtrlUITests/NG2Ring.h': {'source': 'NG2Ring.h', 'sha256': runner.sha(b'header')},
                'LoopCtrlUITests/NG2RingKernel/ring.h': {'source_root': 'ring_native', 'source': 'ring.h',
                                                       'sha256': runner.sha(b'canonical')}}
            for name, spec in specs.items():
                self.assertEqual(spec['sha256'], runner.addition_identity(root, name, spec))
            bad = dict(specs['LoopCtrlUITests/NG2Ring.h'], sha256='0' * 64)
            with self.assertRaisesRegex(ValueError, 'addition hash'):
                runner.addition_identity(root, 'LoopCtrlUITests/NG2Ring.h', bad)
            for name, spec in (('../Ring.h', specs['LoopCtrlUITests/NG2Ring.h']),
                               ('LoopCtrlUITests/NG2RingKernel/ring.h', dict(specs['LoopCtrlUITests/NG2RingKernel/ring.h'], source_root='elsewhere')),
                               ('LoopCtrlUITests/NG2RingKernel/ring.h', dict(specs['LoopCtrlUITests/NG2RingKernel/ring.h'], source='../ring.h'))):
                with self.assertRaises(ValueError): runner.addition_identity(root, name, spec)
            link = root / 'patches/loopctrl/ngg2/NG2Link.h'
            link.symlink_to(root / 'tools/ring_native/ring.h')
            with self.assertRaisesRegex(ValueError, 'symlink'):
                runner.addition_identity(root, 'LoopCtrlUITests/NG2Link.h', {'source': 'NG2Link.h', 'sha256': runner.sha(b'canonical')})

    def test_resealed_canonical_changes_cannot_replace_the_retained_baseline(self):
        runner = runner_module()
        baseline = b'canonical fixed kernel'
        self.assertEqual(runner.sha(baseline), runner.retained_identity(baseline, baseline, runner.sha(baseline)))
        changed = baseline + b' changed'
        for digest in (runner.sha(baseline), runner.sha(changed)):
            with self.assertRaisesRegex(ValueError, 'retained source bytes changed'):
                runner.retained_identity(changed, baseline, digest)
        with self.assertRaises(ValueError):
            runner.retained_identity(baseline, baseline, '0' * 64)

    def test_empty_skip_failure_or_error_cannot_be_success_evidence(self):
        runner = runner_module()
        for outcome in ('green', 'skip', 'failure', 'error'):
            with tempfile.TemporaryDirectory() as folder, patch('builtins.print'):
                evidence = {}
                if outcome == 'green': runner.run_scope('unit', [one_case(outcome)], Path(folder), evidence)
                else:
                    with self.assertRaises(RuntimeError): runner.run_scope('unit', [one_case(outcome)], Path(folder), evidence)
                self.assertEqual(1, evidence['unit']['tests_run'])
                self.assertTrue((Path(folder) / 'test094-host-scope.json').is_file())
        with tempfile.TemporaryDirectory() as folder, self.assertRaises(ValueError):
            runner.run_scope('empty', [], Path(folder), {})


if __name__ == '__main__': unittest.main()
