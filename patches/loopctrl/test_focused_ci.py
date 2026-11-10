"""Keep routine native validation focused while preserving release evidence."""
from pathlib import Path
import importlib.util
import re
import tempfile
import types
import unittest
from unittest.mock import patch


WORKFLOW = Path(__file__).resolve().parents[2] / '.github/workflows/loopctrl-geometry.yml'
SPEC = importlib.util.spec_from_file_location('focused_host_runner',
    Path(__file__).with_name('run_test061_host.py'))
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def job_blocks(source):
    jobs = source.split('\njobs:\n', 1)[1]
    boundaries = list(re.finditer(r'^  ([a-z0-9-]+):\n', jobs, re.MULTILINE))
    return {match.group(1): jobs[match.start():
        boundaries[index + 1].start() if index + 1 < len(boundaries) else len(jobs)]
        for index, match in enumerate(boundaries)}


class FocusedNativeWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.source = WORKFLOW.read_text()
        self.jobs = job_blocks(self.source)

    def test_native_build_requires_explicit_dispatch_and_defaults_to_device(self):
        trigger = self.source.split('\npermissions:', 1)[0]
        self.assertNotRegex(trigger, r'(?m)^  push:', 'native_build_is_explicit_dispatch')
        self.assertIn('  workflow_dispatch:\n', trigger)
        self.assertIn('        default: device\n', trigger)
        self.assertRegex(trigger, r'options: \[[^\]]*focused[^\]]*full[^\]]*\]')

    def test_focused_requires_selected_host_contracts_without_world160(self):
        self.assertIn('focused-build', self.jobs, 'focused_native_build_exists')
        focused = self.jobs['focused-build']
        self.assertIn('needs: [native-source-ready, test061-host-contracts]', focused)
        self.assertNotIn('native-host-contracts', focused)
        self.assertIn('runs-on: macos-26', focused)
        host = self.jobs['test061-host-contracts']
        self.assertIn('runs-on: ubuntu-latest', host)
        self.assertIn('NATIVE_HOST_RUNNER=driver/patches/loopctrl/run_test061_host.py', host)
        self.assertIn('"$NATIVE_HOST_RUNNER" driver upstream', host)
        self.assertNotIn('test_native_goal_world', host)

    def test_focused_runs_new_public_boundary_faults_and_independent_goods_path(self):
        self.assertIn('focused-build', self.jobs, 'focused_native_build_exists')
        focused = self.jobs['focused-build']
        for mode in ('--test061-public-only', '--test061-new-mutations-only', '--test058-shop-only'):
            self.assertIn('check_ngg2.py ' + mode + ' upstream', focused)
        self.assertNotRegex(focused, r'check_ngg2\.py upstream\b')
        self.assertNotIn('--test058-runtime-green-only', focused)

    def test_actual_build_profile_package_and_raw_evidence_remain_in_order(self):
        self.assertIn('focused-build', self.jobs, 'focused_native_build_exists')
        focused = self.jobs['focused-build']
        names = [
            'Generate and inspect actual source-specific project configuration',
            'Build and package unsigned IPA',
            'Preserve actual compiler inputs for verification diagnostics',
            'Verify actual source-specific Perception compiler profile',
            'Verify package and record provenance', 'Save unsigned IPA',
        ]
        positions = [focused.index('- name: ' + name) for name in names]
        self.assertEqual(positions, sorted(positions))
        self.assertIn('make ipa UNSIGNED=1', focused)
        self.assertIn('--compile-profile upstream "$RUNNER_TEMP/ngg2/ios-build.txt"', focused)
        self.assertIn('upstream/LoopCtrl.xcodeproj/project.pbxproj', focused)
        self.assertIn('${{ runner.temp }}/ngg2/perception-build/', focused)
        self.assertIn('driver/patches/loopctrl/ngg2-manifest.json', focused)
        self.assertRegex(focused, r'Preserve actual compiler inputs[^\n]*\n        if: always\(\)')

    def test_full_remains_explicit_and_preserves_historical_runtime_and_world_contracts(self):
        full = self.jobs['build']
        self.assertIn("if: inputs.native_lane == 'full' &&", full)
        self.assertIn('needs: [native-source-ready, native-host-contracts, test061-host-contracts]', full)
        self.assertIn("inputs.native_lane == 'full'", self.jobs['test061-host-contracts'])
        self.assertIn('--test061-public-only upstream', full)
        self.assertIn('--test061-new-mutations-only upstream', full)
        self.assertIn('check_ngg2.py upstream "$RUNNER_TEMP/ngg2"', full)
        self.assertIn('check_ngg2_rpc.py upstream', full)
        self.assertIn('test_native_goal_world', self.jobs['native-host-contracts'])
        self.assertNotIn("inputs.native_lane != 'test058-red'", self.jobs['native-host-contracts'])


def case_with_outcome(name, outcome='green'):
    def check(self):
        if outcome == 'failure':
            self.fail('semantic assertion')
        elif outcome == 'error':
            raise RuntimeError('compile/setup failure')
        elif outcome == 'skip':
            self.skipTest('not executed')
        elif outcome == 'expected_failure':
            self.fail('expected failure is not executed Green')
    if outcome == 'expected_failure':
        check = unittest.expectedFailure(check)
    return type('SelectedCase', (unittest.TestCase,), {name: check})(name)


class FocusedHostSelectionTests(unittest.TestCase):
    def test_empty_duplicate_missing_or_entirely_excluded_cases_fail_closed(self):
        case = case_with_outcome('test_public')
        for cases, excluded in (([], set()), ([case, case], set()),
                                ([case], {'test_missing'}), ([case], {'test_public'})):
            with self.subTest(excluded=excluded, cases=len(cases)), self.assertRaises(ValueError):
                runner.selected_cases(unittest.TestSuite(cases), excluded)

    def test_exact_private_exclusions_preserve_all_other_cases(self):
        public = case_with_outcome('test_public')
        private = case_with_outcome('test_private')
        selected = runner.selected_cases(unittest.TestSuite([private, public]), {'test_private'})
        self.assertEqual(selected, [public])

    def test_only_executed_green_is_accepted_and_failure_evidence_is_written(self):
        for outcome in ('green', 'failure', 'error', 'skip', 'expected_failure'):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as folder:
                output = Path(folder)
                record = {}
                with patch('builtins.print'):
                    if outcome == 'green':
                        runner.run_scope('fixture', [case_with_outcome('test_one')], output, record)
                    else:
                        with self.assertRaises(RuntimeError):
                            runner.run_scope('fixture', [case_with_outcome('test_one', outcome)], output, record)
                self.assertEqual(record['fixture']['tests_run'], 1)
                self.assertTrue((output / 'fixture.txt').is_file())
                self.assertTrue((output / 'test061-host-scope.json').is_file())

    def test_native_suites_bind_all_core_modules_to_patched_upstream_before_loading(self):
        calls = []
        modules = {}
        for name, class_name, _ in runner.NATIVE_CASES:
            case = case_with_outcome('test_public')
            modules[name] = types.SimpleNamespace(**{class_name: type(case)})
        world = modules['tests.test_native_recovery_world']
        world.base = types.SimpleNamespace()
        def load(case_type):
            calls.append(case_type)
            self.assertTrue(all(module.CORE == Path('/patched/LoopCtrlUITests')
                                for module in modules.values()))
            self.assertEqual(world.base.CORE, Path('/patched/LoopCtrlUITests'))
            return unittest.TestSuite([case_type('test_public')])
        with patch.object(runner.importlib, 'import_module', side_effect=modules.__getitem__), \
                patch.object(runner.unittest.defaultTestLoader, 'loadTestsFromTestCase', side_effect=load), \
                patch.object(runner, 'PRIVATE_CONTROLLER', frozenset()), \
                patch.object(runner, 'WORLD_METHODS', frozenset({'test_public'})):
            selected = runner.native_suites(Path('/patched'))
        self.assertEqual(len(calls), 4)
        self.assertEqual([name for name, _ in selected],
                         ['test061-controller', 'test061-recovery', 'test061-beat', 'test061-world'])

    def test_focused_world_rejects_missing_and_unregistered_whole_path_methods(self):
        for change in ('missing', 'extra'):
            modules = {}
            for name, class_name, label in runner.NATIVE_CASES:
                methods = set(runner.WORLD_METHODS) if label == 'test061-world' else {'test_public'}
                if label == 'test061-world':
                    if change == 'missing':
                        methods.remove('test_turn_left_then_up_open_enter_and_hold_goods')
                    else:
                        methods.add('test_unregistered')
                case_type = type(class_name, (unittest.TestCase,),
                                 {method: (lambda self: None) for method in methods})
                modules[name] = types.SimpleNamespace(**{class_name: case_type})
            modules['tests.test_native_recovery_world'].base = types.SimpleNamespace()
            with self.subTest(change=change), \
                    patch.object(runner.importlib, 'import_module', side_effect=modules.__getitem__), \
                    patch.object(runner, 'PRIVATE_CONTROLLER', frozenset()), \
                    self.assertRaisesRegex(ValueError, 'focused world method inventory changed'):
                runner.native_suites(Path('/patched'))


if __name__ == '__main__':
    unittest.main()
