"""Fail-closed selection and source identity guards for TEST116 device CI."""
import argparse
import ast
import copy
import importlib
import importlib.util
from pathlib import Path
import shlex
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location('device116_'+name, HERE/(name+'.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def declared_parser(path):
    """Read literal argparse declarations without importing/executing a checker."""
    tree = ast.parse(path.read_text())
    main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
    parser = argparse.ArgumentParser(add_help=False)
    for statement in main.body:
        if not isinstance(statement, ast.Expr) or not isinstance(statement.value, ast.Call):
            continue
        call = statement.value
        if not isinstance(call.func, ast.Attribute) or call.func.attr != 'add_argument':
            continue
        if not isinstance(call.func.value, ast.Name) or call.func.value.id != 'parser':
            raise ValueError('checker parser declaration changed')
        names = [ast.literal_eval(arg) for arg in call.args]
        keywords = {}
        for keyword in call.keywords:
            if keyword.arg == 'type':
                if not isinstance(keyword.value, ast.Name) or keyword.value.id != 'Path':
                    raise ValueError('checker path type changed')
                keywords['type'] = Path
            else:
                keywords[keyword.arg] = ast.literal_eval(keyword.value)
        parser.add_argument(*names, **keywords)
    return parser


class DeviceHostSelection116Tests(unittest.TestCase):
    def test_workflow_selects_116_after_115_on_standard_runners(self):
        source = (ROOT/'.github/workflows/loopctrl-geometry.yml').read_text()
        host = source.split('  test061-host-contracts:\n', 1)[1].split('  focused-build:\n', 1)[0]
        self.assertIn('NATIVE_HOST_RUNNER=driver/patches/loopctrl/run_test116_host.py', host)
        self.assertLess(host.index('DEVICE_PROFILE=115'), host.index('DEVICE_PROFILE=116'))
        self.assertIn('runs-on: ubuntu-latest', host)
        build = source.split('  focused-build:\n', 1)[1].split('\n  build:\n', 1)[0]
        self.assertIn('runs-on: macos-26', build)

    def test_pending_empty_duplicate_or_overridden_scope_never_executes(self):
        runner = module('run_test116_host')
        for flag in ('SCOPE_FINALIZED', 'RUNTIME_SCOPE_FINALIZED'):
            with patch.object(runner, flag, False), self.assertRaises(ValueError):
                runner.ensure_scope()
        controls = dict(SCOPE_FINALIZED=True, RUNTIME_SCOPE_FINALIZED=True,
            CASES=(('m', 'C', 'one', frozenset({'test_one'}), True),),
            NEW_PATHS=frozenset({'new.py'}), EXPECTED_NATIVE_CHANGES=frozenset({'native.c'}),
            EXPECTED_REPOSITORY_CHANGES=frozenset({'path.c'}), CURRENT_MAC_CASES=('one',),
            RUNTIME_CASE_GROUPS=(('checker', ('one',)),))
        with patch.multiple(runner, **controls):
            runner.ensure_scope()
            for name in ('CASES', 'NEW_PATHS', 'EXPECTED_NATIVE_CHANGES',
                    'EXPECTED_REPOSITORY_CHANGES', 'CURRENT_MAC_CASES', 'RUNTIME_CASE_GROUPS'):
                with patch.object(runner, name, ()), self.assertRaises(ValueError):
                    runner.ensure_scope()
            with patch.object(runner, 'CASES', controls['CASES']*2), self.assertRaises(ValueError):
                runner.ensure_scope()
            with patch.object(runner, 'RUNTIME_CASE_GROUPS', (('checker', ('other',)),)), self.assertRaises(ValueError):
                runner.ensure_scope()
        for name in ('BASELINE_NAV', 'NECRO116_CONTINUOUS_BEFORE', 'NECRO116_EARLY_CORE', 'NECRO_TEST116_CORE'):
            with patch.dict(runner.os.environ, {name: ''}), self.assertRaises(ValueError):
                runner.reject_fixture_overrides()

    def test_native_inventory_rejects_missing_retained_unapproved_and_no_change_sources(self):
        runner = module('run_test116_host')
        before = {'changed.c': 'a'*64, **{'retained-'+str(index): 'a'*64 for index in range(35)}}
        current = dict(before, **{'changed.c': 'b'*64, 'new.swift': 'c'*64})
        with patch.object(runner, 'EXPECTED_NATIVE_CHANGES', frozenset({'changed.c'})), patch.object(
                runner, 'EXPECTED_NATIVE_ADDITIONS', frozenset({'new.swift'})):
            self.assertEqual(({'changed.c'}, {'new.swift'}), runner.native_delta(before, current))
            bad = [before, dict(current, extra='d'*64), dict(current, **{'retained-0': 'd'*64}),
                {key: value for key, value in current.items() if key != 'retained-0'}]
            for value in bad:
                with self.subTest(value=value), self.assertRaises(ValueError):
                    runner.native_delta(before, value)
        inputs = {name: 'a'*64 for name in runner.SPOOL_INPUT_PATHS}
        def receipt(baseline):
            return dict(schema='test116-spool-evidence-v1', baseline_only=baseline,
                baseline_adapter_is_test_only=True, green_cases=['green'],
                source_sha256='b'*64 if baseline else 'a'*64, fixture_sha256='a'*64,
                adapter_sha256='a'*64, compiler='Apple Swift version fixture',
                device_acceptance=False, input_authority=False,
                results={'red' if baseline else 'green': dict(returncode=1 if baseline else 0,
                    compile_errors=0, failures=['FAIL expected'] if baseline else [])})
        proof = dict(schema='test116-spool-reuse-v1', run_id=1, run_number=245,
            driver_commit='c'*40, artifact_name='loopctrl-test116-spool-green',
            artifact_sha256='d'*64, source_inputs=inputs, before=receipt(True), current=receipt(False))
        check = lambda value: runner.validate_spool_reuse(value, inputs, baseline_sha='b'*64,
            green_cases=('green',), red_cases={'red': 'FAIL expected'})
        self.assertTrue(check(proof)['same_bytes_reused'])
        bad_proofs = [{}, dict(proof, extra=True), dict(proof, artifact_sha256='pending'),
            dict(proof, source_inputs=dict(inputs, **{runner.SPOOL_INPUT_PATHS[0]: 'e'*64}))]
        for section, key, value in (('current', 'source_sha256', 'e'*64),
                ('current', 'fixture_sha256', 'e'*64), ('current', 'adapter_sha256', 'e'*64),
                ('current', 'baseline_only', True), ('current', 'green_cases', []),
                ('current', 'compiler', 'not executed'), ('before', 'source_sha256', 'a'*64)):
            changed = copy.deepcopy(proof); changed[section][key] = value; bad_proofs.append(changed)
        for section, key, value in (('current', 'returncode', 1), ('current', 'compile_errors', 1),
                ('current', 'failures', ['FAIL ignored']), ('before', 'returncode', 0),
                ('before', 'failures', ['compile failure'])):
            changed = copy.deepcopy(proof)
            changed[section]['results']['red' if section == 'before' else 'green'][key] = value
            bad_proofs.append(changed)
        for value in bad_proofs:
            with self.subTest(spool_proof=value), self.assertRaises(ValueError):
                check(value)

    def test_method_missing_duplicate_skip_failure_and_error_are_never_green(self):
        runner = module('run_test116_host')
        old = module('test_device_ci114')
        for outcome in ('green', 'skip', 'failure', 'error'):
            with tempfile.TemporaryDirectory() as directory, patch('builtins.print'):
                output, evidence = Path(directory), {}
                if outcome == 'green':
                    runner.run_scope('unit', [old.one_case()], output, evidence)
                else:
                    with self.assertRaises(RuntimeError):
                        runner.run_scope('unit', [old.one_case(outcome)], output, evidence)
                self.assertEqual(1, evidence['unit']['tests_run'])
        for cases in ([], [old.one_case(), old.one_case()]):
            with self.assertRaises(ValueError):
                runner.selected_cases(cases)
        with self.assertRaises(ValueError):
            runner.method_cases(type(old.one_case()), frozenset({'test_missing'}))

    def test_pending_python39_scope_cannot_import_or_execute_any_product(self):
        runner = module('run_test116_python39')
        with patch.object(runner, 'SCOPE_FINALIZED', False), patch.object(runner.importlib, 'import_module') as imported:
            with self.assertRaises(ValueError):
                runner.selected_suite(ROOT)
        imported.assert_not_called()

    def test_author_native_methods_are_explicit_unique_and_keep_the_approved_direct_scope(self):
        runner = module('run_test116_host')
        self.assertEqual(89, sum(len(row[3]) for row in runner.CASES))
        selected = []
        for name, klass, label, methods, exact in runner.CASES:
            imported = importlib.import_module(name)
            self.assertEqual(ROOT/(name.replace('.', '/')+'.py'), Path(imported.__file__).resolve())
            selected.extend(runner.method_cases(getattr(imported, klass), methods, exact=exact))
            self.assertTrue(label.startswith('test116-native-'))
        self.assertEqual(89, len(runner.selected_cases(selected)))
        self.assertEqual('c17ffd2e4c583b16b322dd9e8a973003e179389c', runner.NATIVE_BASELINE)
        client = module('run_test116_python39')
        client_selected = []
        for name, klass, _label, methods, exact in client.CASES:
            imported = importlib.import_module(name)
            self.assertEqual(ROOT/(name.replace('.', '/')+'.py'), Path(imported.__file__).resolve())
            client_selected.extend(runner.method_cases(getattr(imported, klass), methods, exact=exact))
        self.assertEqual(40, len(runner.selected_cases(client_selected)))

    def test_workflow_uses_actual_pinned_python39_without_replaying_old_device_profiles(self):
        source = (ROOT/'.github/workflows/loopctrl-geometry.yml').read_text()
        host = source.split('  test061-host-contracts:\n', 1)[1].split('  focused-build:\n', 1)[0]
        for text in ('test116-python39-provider.json', 'steps.python39_116.outputs.python-path',
                'run_test116_python39.py driver',
                'fe04e8b27bd69ca2144fc542428f8b9b5287b6a2e45516a4acfe2c2bc3102773'):
            self.assertIn(text, host)
        block = host.split('- name: Select actual Python 3.9 for TEST116 client compatibility\n', 1)[1].split('      - name: Save selected host evidence', 1)[0]
        self.assertEqual(2, block.count("device_profile == '116'"))
        self.assertNotIn('run_test115_python39.py', block)
        build = source.split('  focused-build:\n', 1)[1].split('\n  build:\n', 1)[0]
        for title in ('Install TEST094 focused Swift fixture image decoder',
                'Verify TEST094 immutable spool and actual filesystem fault boundaries',
                'Verify TEST094 immutable terminal export and exact image roundtrip',
                'Verify TEST094 selected actual Runtime cycle callbacks'):
            step = build.split('- name: '+title+'\n', 1)[1].split('      - ', 1)[0]
            self.assertIn("device_profile != '116'", step)
        runtime = build.split('- name: Verify TEST116 current continuous Runtime and retained final-clock callbacks against sealed sources\n', 1)[1].split('      - ', 1)[0]
        self.assertIn("device_profile == '116'", runtime)
        self.assertIn('check_runtime116.py upstream "$RUNNER_TEMP/test116-runtime"', runtime)
        self.assertNotIn('--diagnostic', runtime)
        self.assertIn('${{ runner.temp }}/test116-runtime/', build)
        self.assertIn('${{ runner.temp }}/test116-spool-proof/', build)

    def test_spool_red_lane_is_source_pinned_and_never_builds_or_replays_product_suites(self):
        source = (ROOT/'.github/workflows/loopctrl-geometry.yml').read_text()
        red = source.split('  test116-spool-red:\n', 1)[1].split('  test116-runtime-red:\n', 1)[0]
        for value in ('runs-on: macos-26', 'ref: ${{ github.sha }}',
                'c17ffd2e4c583b16b322dd9e8a973003e179389c:patches/loopctrl/ngg2/NG2CycleSpool.swift',
                '074d76fc732a2287d14d8dd11256ac4d63462974556006b518f52ee66eefe84f',
                '--baseline-only --before-spool', 'native_sources_applied=False',
                'linux_host_replayed=False,python39_replayed=False', 'loopctrl-${{ inputs.native_lane }}'):
            self.assertIn(value, red)
        for unrelated in ('xcodebuild', 'run_test116_host.py', 'run_test116_python39.py',
                'apply_ngg2.py', 'apply_patch.py'):
            self.assertNotIn(unrelated, red)
        ready = source.split('  native-source-ready:\n', 1)[1].split('  native-host-contracts:\n', 1)[0]
        self.assertIn("inputs.native_lane != 'test116-spool-red'", ready)
        self.assertIn("inputs.native_lane != 'test116-spool-green'", ready)
        self.assertIn("if: inputs.native_lane == 'test116-spool-green'", red)
        self.assertIn('check_cycle_spool116.py "$RUNNER_TEMP/test116-spool-red/current"', red)

    def test_spool_red_workflow_arguments_are_accepted_by_the_real_checker_declarations(self):
        source = (ROOT/'.github/workflows/loopctrl-geometry.yml').read_text()
        red = source.split('  test116-spool-red:\n', 1)[1].split('  test116-runtime-red:\n', 1)[0]
        command = next(line.strip().split(' 2>&1', 1)[0] for line in red.splitlines()
            if 'python3 driver/patches/loopctrl/check_cycle_spool116.py ' in line)
        tokens = shlex.split(command)
        self.assertEqual(['python3', 'driver/patches/loopctrl/check_cycle_spool116.py'], tokens[:2])
        args = declared_parser(HERE/'check_cycle_spool116.py').parse_args(tokens[2:])
        self.assertTrue(args.baseline_only)
        self.assertEqual(Path('$RUNNER_TEMP/test116-spool-red/before-source/NG2CycleSpool.swift'), args.before_spool)
        self.assertEqual(Path('$RUNNER_TEMP/test116-spool-red'), args.output)

    def test_runtime_red_lane_uses_author_assertion_and_the_real_retained_parser(self):
        source = (ROOT/'.github/workflows/loopctrl-geometry.yml').read_text()
        red = source.split('  test116-runtime-red:\n', 1)[1].split('  test112-runtime-diagnostic:\n', 1)[0]
        for text in ('runs-on: macos-26', 'ref: ${{ github.sha }}',
                'e655aa10f0ba48a9e2f719e25a5cbd9c7f5c69f6e907de0ac1bcae9da228dbe0',
                'FAIL test116_continuous_native_mode_is_admitted_without_old_pause_yield',
                'ipa_built=False,linux_host_replayed=False,python39_replayed=False'):
            self.assertIn(text, red)
        for text in ('xcodebuild', 'run_test116_host.py', 'run_test116_python39.py'):
            self.assertNotIn(text, red)
        command = next(line.strip().split(' 2>&1', 1)[0] for line in red.splitlines()
            if 'python3 driver/patches/loopctrl/check_runtime116.py upstream ' in line)
        tokens = shlex.split(command)
        # The TEST116 adapter explicitly reuses this immutable parser/body.
        adapter = (HERE/'check_runtime116.py').read_text()
        self.assertIn('import check_runtime115 as retained', adapter)
        self.assertIn('inspect.getsource(retained.main)', adapter)
        checker = module('check_runtime116')
        runner = module('run_test116_host')
        self.assertEqual(36, len(set(checker.GREEN_CASES)))
        self.assertEqual(checker.GREEN_CASES, runner.CURRENT_MAC_CASES)
        self.assertEqual(('new_mode', 'normal_chain'), checker.DIAGNOSTIC_CASES)
        self.assertNotIn('NG2RuntimeContinuousTestHooks', checker.fixture_source(admission=True))
        for old_whole_scope in ('passage_fresh', 'partial_view', 'partial_cancel'):
            self.assertNotIn(old_whole_scope, checker.GREEN_CASES)
        args = declared_parser(HERE/'check_runtime115.py').parse_args(tokens[2:])
        self.assertTrue(args.expect_runtime_red)
        self.assertFalse(args.expect_red)
        self.assertEqual(Path('upstream'), args.upstream)
        self.assertEqual(Path('$RUNNER_TEMP/test116-runtime-red/before-source/NG2Runtime.swift'), args.before_runtime)
        ready = source.split('  native-source-ready:\n', 1)[1].split('  native-host-contracts:\n', 1)[0]
        self.assertIn("inputs.native_lane != 'test116-runtime-red'", ready)


if __name__ == '__main__':
    unittest.main()
