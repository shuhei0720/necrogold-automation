"""TEST118 implementation capability and closed, source-bound CI selection."""
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CAPABILITY = 'necrogold_native_device_fixes118_v1'


def module(name):
    spec = importlib.util.spec_from_file_location('device118_'+name, HERE/(name+'.py'))
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


def rpc_source(*, declared=True):
    line = '        "'+CAPABILITY+'",\n' if declared else ''
    return ('struct RPCMethod {\n'
        '    static let capabilityTags: [String] = [\n'
        '        "necrogold_native_visible_goods_v1",\n'+line+
        '    ]\n}\n').encode()


class DeviceImplementationCapability118Tests(unittest.TestCase):
    def metadata(self, patch, rpc):
        helper = getattr(module('apply_ngg2'), 'device_fixes118_metadata', lambda *_: {})
        return helper(patch, rpc)

    def fixture(self, directory, *, declared=True, metadata=CAPABILITY, patch_declared=True):
        upstream = directory/'upstream'; driver = directory/'driver'
        destination = driver/'patches/loopctrl'; destination.mkdir(parents=True)
        rpc = rpc_source(declared=declared)
        runtime = b'''    private func response(_ run: NG2Run, includeInitialRestart: Bool = false) -> [String: JSONValue] {
        return ["api_version": .string("1.98.16-ngg2"), "report": .object(report)]
    }
    private func historical(_ snapshot: [String: JSONValue]) -> [String: JSONValue] {
        return snapshot
    }
'''
        sources = {'LoopCtrlKit/RPCMethod.swift': rpc,
            'LoopCtrlUITests/NG2Runtime.swift': runtime,
            'LoopCtrlUITests/NG2CycleWire.swift': b'// procedural metadata fixture\n'}
        patch = ('+        "'+CAPABILITY+'",\n').encode() if patch_declared else b'// old patch\n'
        manifest = dict(upstream_commit='6e25cf6a9f65bc86c372cdce94bdb151d0cf6767',
            api_version='1.98.16-ngg2', capability='necrogold_native_v1', client_capability='necrogold_native_v15',
            cycle_capability='necrogold_native_cycle_v1', cycle_profile='normal-1-1-cycle-v1',
            compiler_profile_version=3, visible_goods_capability='necrogold_native_visible_goods_v1',
            initial_restart_start_flag='initial_restart', patch_sha256=hashlib.sha256(patch).hexdigest(),
            files={}, additions={})
        if metadata is not None:
            manifest['device_fixes_capability'] = metadata
        for name, raw in sources.items():
            target = upstream/name; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
            if name.startswith('LoopCtrlKit/'):
                manifest['files'][name] = dict(patched_sha256=hashlib.sha256(raw).hexdigest())
            else:
                manifest['additions'][name] = dict(sha256=hashlib.sha256(raw).hexdigest())
        (destination/'ngg2.patch').write_bytes(patch)
        (destination/'ngg2-manifest.json').write_text(json.dumps(manifest))
        return upstream, driver, manifest

    def test_current_patch_advertises_the_exact_118_implementation(self):
        patch = (HERE/'ngg2.patch').read_bytes()
        self.assertEqual(1, patch.count(('+        "'+CAPABILITY+'",').encode()),
            'the new trial must not silently accept TEST117 under the same API number')
        self.assertEqual({'device_fixes_capability': CAPABILITY}, self.metadata(patch, rpc_source()))

    def test_sealing_metadata_requires_the_real_array_entry_not_comments_or_duplicates(self):
        patch = ('+        "'+CAPABILITY+'",\n').encode()
        self.assertEqual({'device_fixes_capability': CAPABILITY}, self.metadata(patch, rpc_source()))
        bad = (
            (patch, rpc_source(declared=False)),
            (patch, rpc_source(declared=False)+('// "'+CAPABILITY+'"\n').encode()),
            (patch, rpc_source().replace(('        "'+CAPABILITY+'",').encode(),
                ('        // "'+CAPABILITY+'",').encode())),
            (patch+patch, rpc_source()),
            (patch, rpc_source()+rpc_source()),
        )
        for raw_patch, rpc in bad:
            with self.subTest(patch=raw_patch, rpc=rpc), self.assertRaisesRegex(ValueError, 'device_fixes118'):
                self.metadata(raw_patch, rpc)
        self.assertEqual({}, self.metadata(b'// old patch\n', rpc_source(declared=False)))

    def test_package_records_118_binding_without_changing_API_or_profile(self):
        with tempfile.TemporaryDirectory() as temporary:
            upstream, driver, _ = self.fixture(Path(temporary))
            report = module('verify_package').inspect_native_sources(upstream, driver)
            self.assertEqual(CAPABILITY, report.get('device_fixes_capability'),
                'the packaged report must bind the new client gate to its compiled RPC source')
            self.assertEqual(('1.98.16-ngg2', 'necrogold_native_v15', 3),
                (report['api_version'], report['client_capability'], report['compiler_profile_version']))

    def test_resealed_mismatched_118_metadata_patch_and_rpc_are_rejected(self):
        faults = ({'metadata': None}, {'metadata': 'wrong'}, {'declared': False}, {'patch_declared': False})
        for fault in faults:
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as temporary:
                upstream, driver, _ = self.fixture(Path(temporary), **fault)
                with self.assertRaisesRegex(ValueError, 'device_fixes118'):
                    module('verify_package').inspect_native_sources(upstream, driver)

    def test_prior_manifests_do_not_gain_an_unrequested_118_claim(self):
        with tempfile.TemporaryDirectory() as temporary:
            upstream, driver, _ = self.fixture(Path(temporary), declared=False, metadata=None, patch_declared=False)
            report = module('verify_package').inspect_native_sources(upstream, driver)
            self.assertNotIn('device_fixes_capability', report)


def one_case(outcome='green'):
    class Fixture(unittest.TestCase):
        def runTest(self):
            if outcome == 'skip': self.skipTest('procedural boundary')
            if outcome == 'failure': self.fail('procedural boundary')
            if outcome == 'error': raise ValueError('procedural boundary')
    return Fixture()


def focused_steps(source):
    return module('test_device_ci117').focused_steps(source)


def condition_selected(condition, profile, lane='device'):
    return module('test_device_ci117').condition_selected(condition, profile, lane)


def historical_test_step(row):
    source = '\n'.join(row['source'])
    versions = re.findall(r'\bTEST(\d{3})\b', row['name'])
    versions += [version for match in re.findall(
        r'(?:check_runtime(?:_[A-Za-z_]+)?|check_cycle_(?:api|spool|export))(\d{3})\.py|\brun_test(\d{3})_host\b|--test(\d{3})', source)
        for version in match if version]
    return (any(version != '118' for version in versions) or 'world16' in row['name']
        or 'actual LoopCtrlKit API and capability' in row['name'] or 'check_ngg2_rpc.py' in source)


class DeviceHostSelection118Tests(unittest.TestCase):
    def controls(self):
        return dict(SCOPE_FINALIZED=True, MAC_SCOPE_FINALIZED=True,
            CASES=(('m', 'C', 'one', frozenset({'test_one'}), True),), CORE_MODULES=('m',),
            NEW_PATHS=frozenset({'new.py'}), EXPECTED_NATIVE_CHANGES=frozenset({'native.c'}),
            EXPECTED_REPOSITORY_CHANGES=frozenset({'path.c'}), MAC_CASE_GROUPS=(('checker', ('one',)),))

    def test_pending_empty_duplicate_and_overridden_scope_never_executes(self):
        runner = module('run_test118_host'); controls = self.controls()
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
        for variable in ('BASELINE_NAV', 'NECRO_TEST_DLL', 'NECRO118_FIXTURE'):
            with patch.dict('os.environ', {variable:'forged'}), self.assertRaises(ValueError):
                runner.reject_fixture_overrides()

    def test_pending_python39_never_imports_or_executes_product(self):
        runner = module('run_test118_python39')
        with patch.object(runner, 'SCOPE_FINALIZED', False), patch.object(runner.importlib, 'import_module') as imported:
            with self.assertRaises(ValueError): runner.selected_suite(ROOT)
        imported.assert_not_called()

    def test_python39_selects_exact_11_and_retained_65_without_duplication(self):
        runner = module('run_test118_python39'); host = module('run_test118_host')
        with patch.object(runner, 'SCOPE_FINALIZED', True), \
                patch.multiple(host, SCOPE_FINALIZED=True, MAC_SCOPE_FINALIZED=True), \
                patch.object(runner, 'host_module', return_value=host):
            _, selected = runner.selected_suite(ROOT)
        self.assertEqual(76, len(selected))
        self.assertEqual(76, len({value.id() for value in selected}))
        self.assertEqual(65, sum(len(row[3]) for row in runner.shared.CASES))
        self.assertEqual(11, sum(len(row[3]) for row in runner.CASES if row[0]=='tests.test_continuous_client118'))

    def test_native_receipt_survives_python_success_failure_error_and_skip(self):
        runner = module('run_test118_host')
        for outcome in ('green', 'failure', 'error', 'skip'):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as temporary, patch('builtins.print'):
                output = Path(temporary); native = output/'test118-host-scope.json'
                sentinel = b'{"scope":"source-bound native sentinel"}\n'; native.write_bytes(sentinel)
                evidence = {'scope':'Python fixture'}
                if outcome == 'green':
                    runner.run_scope('python-fixture', [one_case(outcome)], output, evidence,
                        receipt_name='test118-python39-scope.json')
                else:
                    with self.assertRaises(RuntimeError):
                        runner.run_scope('python-fixture', [one_case(outcome)], output, evidence,
                            receipt_name='test118-python39-scope.json')
                self.assertEqual(sentinel, native.read_bytes())
                self.assertEqual(evidence, json.loads((output/'test118-python39-scope.json').read_bytes()))
                self.assertEqual(1, evidence['python-fixture']['tests_run'])

    def test_receipt_names_are_closed_before_any_test_executes(self):
        runner = module('run_test118_host')
        for name in ('test117-host-scope.json', 'other.json', '../test118-host-scope.json', '/tmp/test118-host-scope.json', '', None, 0):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary)
                with patch.object(runner, 'selected_cases') as selected, self.assertRaises(ValueError):
                    runner.run_scope('fixture', [], output, {}, receipt_name=name)
                selected.assert_not_called(); self.assertEqual([], list(output.iterdir()))

    def test_empty_duplicate_failure_error_and_skip_never_pass(self):
        runner = module('run_test118_host')
        for cases in ([], [one_case(), one_case()]):
            with self.assertRaises(ValueError): runner.selected_cases(cases)
        for outcome in ('failure', 'error', 'skip'):
            with tempfile.TemporaryDirectory() as temporary, patch('builtins.print'), self.assertRaises(RuntimeError):
                runner.run_scope('fixture', [one_case(outcome)], Path(temporary), {})

    def test_device_workflow_selects_118_and_reuses_pinned_actual_python39(self):
        source = (ROOT/'.github/workflows/loopctrl-geometry.yml').read_text()
        host = source.split('  test061-host-contracts:\n', 1)[1].split('  focused-build:\n', 1)[0]
        self.assertIn('NATIVE_HOST_RUNNER=driver/patches/loopctrl/run_test118_host.py', host)
        self.assertLess(host.index('DEVICE_PROFILE=117'), host.index('DEVICE_PROFILE=118'))
        self.assertIn("steps.host_contracts.outputs.device_profile == '118'", host)
        self.assertIn('run_test118_python39.py driver', host)
        self.assertIn('steps.python39_116.outputs.python-path', host)
        self.assertIn('fe04e8b27bd69ca2144fc542428f8b9b5287b6a2e45516a4acfe2c2bc3102773', host)
        provider = host.split('      - name: Select actual Python 3.9 for TEST116 client compatibility\n', 1)[1]
        provider = provider.split('      - name: Run TEST116 exact client methods', 1)[0]
        self.assertIn("steps.host_contracts.outputs.device_profile == '118'", provider)

    def test_118_device_selects_one_own_mac_step_and_no_historical_fallback(self):
        source = (ROOT/'.github/workflows/loopctrl-geometry.yml').read_text()
        rows = focused_steps(source)
        selected = [row for row in rows if condition_selected(row['condition'], '118')]
        own = [row for row in selected if row['name']=='Verify TEST118 selected Runtime boundaries against sealed sources']
        self.assertEqual(1, len(own), '118 must execute its own frozen Runtime scope')
        self.assertEqual([], [row['name'] for row in selected if historical_test_step(row)])
        body = '\n'.join(own[0]['source'])
        self.assertIn('check_runtime118.py upstream', body)
        self.assertIn('test118-mac-venv', body)
        self.assertIn('Pillow==11.3.0', body)
        self.assertEqual(1, body.count('check_runtime118.py upstream'))
        self.assertNotIn('--fault-red', body)
        self.assertNotIn('--expect-', body)
        self.assertNotIn('check_ngg2.py', body)
        self.assertNotIn('test094-mac-venv', body)
        self.assertEqual("inputs.native_lane == 'device' && needs.test061-host-contracts.outputs.device_profile == '118'",
            own[0]['condition'])
        focused = source.split('  focused-build:\n', 1)[1].split('\n  build:\n', 1)[0]
        artifacts = focused.split('      - name: Save test and build diagnostics\n', 1)[1]
        self.assertIn('${{ runner.temp }}/test118-runtime/', artifacts)
        self.assertIn('test118-runtime/runtime-command.txt', body)
        self.assertNotIn('test118-runtime-red', body)
        fixture = ast.parse((HERE/'check_runtime118.py').read_text())
        declared = {target.id: node.value for node in fixture.body if isinstance(node, ast.Assign)
            for target in node.targets if isinstance(target, ast.Name)}
        self.assertEqual(('preinput_refresh', 'upper_side_hhddd', 'full_data_palette'),
            ast.literal_eval(declared['SWIFT_CASES']))
        for filename in ('check_runtime118.py', 'ngg2_runtime118_tests.swift',
                'ngg2_runtime118_fixture.c', 'generate_shop118_pixels.py'):
            self.assertTrue((HERE/filename).is_file(), 'selected Runtime source must exist: '+filename)

    def test_all_prior_profile_lanes_keep_their_exact_step_selection(self):
        before = subprocess.check_output(['git', 'show',
            '419b558681ed1c12b01db26c5dadad1f569fcd7e:.github/workflows/loopctrl-geometry.yml'], cwd=ROOT, text=True)
        now = (ROOT/'.github/workflows/loopctrl-geometry.yml').read_text()
        old, current = focused_steps(before), focused_steps(now)
        for profile in [str(value).zfill(3) for value in range(94, 118)]:
            for lane in ('device', 'focused', 'full'):
                with self.subTest(profile=profile, lane=lane):
                    expected = [r['name'] for r in old if condition_selected(r['condition'], profile, lane)]
                    actual = [r['name'] for r in current if condition_selected(r['condition'], profile, lane)]
                    self.assertEqual(expected, actual)
                    self.assertEqual([r for r in old if condition_selected(r['condition'], profile, lane)
                        and historical_test_step(r)], [r for r in current if condition_selected(r['condition'], profile, lane)
                        and historical_test_step(r)], 'historical selected test source must remain byte-identical')
        for profile in ('119', '', 'forged'):
            with self.subTest(profile=profile):
                selected = [r for r in current if condition_selected(r['condition'], profile)]
                self.assertEqual([], [r['name'] for r in selected if historical_test_step(r)
                    or 'TEST118' in r['name']])


if __name__ == '__main__':
    unittest.main()
