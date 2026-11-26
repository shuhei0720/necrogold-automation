"""TEST122 adds one capability while preserving all four historical bindings."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
CAPABILITY = 'necrogold_native_device_fixes122_v1'
PRIOR_BINDINGS = (
    (118, 'device_fixes_capability', 'necrogold_native_device_fixes118_v1'),
    (119, 'device_fixes119_capability', 'necrogold_native_device_fixes119_v1'),
    (120, 'device_fixes120_capability', 'necrogold_native_device_fixes120_v1'),
    (121, 'device_fixes121_capability', 'necrogold_native_device_fixes121_v1'),
)


def module(name):
    spec = importlib.util.spec_from_file_location('device122_'+name, HERE/(name+'.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def rpc_source(*, declared=True, block_comment=None):
    line = '        "'+CAPABILITY+'",\n' if declared else ''
    if block_comment == 'entry':
        line = '/*\n'+line+'*/\n'
    elif block_comment == 'nested':
        line = '/* outer /* nested */\n'+line+'*/\n'
    raw = ('struct RPCMethod {\n'
        '    static let capabilityTags: [String] = [\n'
        '        "necrogold_native_visible_goods_v1",\n'
        + ''.join('        "'+cap+'",\n' for _version,_field,cap in PRIOR_BINDINGS)
        + line+'    ]\n}\n').encode()
    return b'/*\n'+raw+b'*/\n' if block_comment == 'array' else raw


class DeviceImplementationCapability122Tests(unittest.TestCase):
    def metadata(self, patch, rpc):
        # Before implementation, a missing new claim is an assertion Red.
        helper = getattr(module('apply_ngg2'), 'device_fixes122_metadata', lambda *_: {})
        return helper(patch, rpc)

    def fixture(self, directory, *, declared=True, metadata=CAPABILITY, patch_declared=True,
                block_comment=None):
        upstream = directory/'upstream'
        driver = directory/'driver'
        destination = driver/'patches/loopctrl'
        destination.mkdir(parents=True)
        runtime = b'''    private func response(_ run: NG2Run, includeInitialRestart: Bool = false) -> [String: JSONValue] {
        return ["api_version": .string("1.98.16-ngg2"), "report": .object(report)]
    }
    private func historical(_ snapshot: [String: JSONValue]) -> [String: JSONValue] {
        return snapshot
    }
'''
        sources = {'LoopCtrlKit/RPCMethod.swift': rpc_source(declared=declared, block_comment=block_comment),
            'LoopCtrlUITests/NG2Runtime.swift': runtime,
            'LoopCtrlUITests/NG2CycleWire.swift': b'// procedural metadata fixture\n'}
        patch = (''.join('+        "'+cap+'",\n' for _version,_field,cap in PRIOR_BINDINGS)
            + ('+        "'+CAPABILITY+'",\n' if patch_declared else '')).encode()
        manifest = dict(upstream_commit='6e25cf6a9f65bc86c372cdce94bdb151d0cf6767',
            api_version='1.98.16-ngg2', capability='necrogold_native_v1', client_capability='necrogold_native_v15',
            cycle_capability='necrogold_native_cycle_v1', cycle_profile='normal-1-1-cycle-v1',
            compiler_profile_version=3, visible_goods_capability='necrogold_native_visible_goods_v1',
            initial_restart_start_flag='initial_restart',
            patch_sha256=hashlib.sha256(patch).hexdigest(), files={}, additions={})
        manifest.update({field:cap for _version,field,cap in PRIOR_BINDINGS})
        if metadata is not None:
            manifest['device_fixes122_capability'] = metadata
        for name, raw in sources.items():
            target = upstream/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            if name.startswith('LoopCtrlKit/'):
                manifest['files'][name] = dict(patched_sha256=hashlib.sha256(raw).hexdigest())
            else:
                manifest['additions'][name] = dict(sha256=hashlib.sha256(raw).hexdigest())
        (destination/'ngg2.patch').write_bytes(patch)
        (destination/'ngg2-manifest.json').write_text(json.dumps(manifest))
        return upstream, driver, manifest

    def test_current_patch_adds_122_without_replacing_118_119_120_or_121(self):
        patch = (HERE/'ngg2.patch').read_bytes()
        for cap in (*[cap for _version,_field,cap in PRIOR_BINDINGS], CAPABILITY):
            self.assertEqual(1, patch.count(('+        "'+cap+'",').encode()))
        self.assertEqual({'device_fixes122_capability': CAPABILITY}, self.metadata(patch, rpc_source()))
        for version,field,cap in PRIOR_BINDINGS:
            self.assertEqual({field:cap},
                getattr(module('apply_ngg2'), 'device_fixes'+str(version)+'_metadata')(patch, rpc_source()))

    def test_sealing_requires_one_real_uncommented_122_array_entry(self):
        patch = ('+        "'+CAPABILITY+'",\n').encode()
        bad = (
            (patch, rpc_source(declared=False)),
            (patch, rpc_source(declared=False)+('// "'+CAPABILITY+'"\n').encode()),
            (patch, rpc_source().replace(('        "'+CAPABILITY+'",').encode(),
                ('        // "'+CAPABILITY+'",').encode())),
            (patch+patch, rpc_source()),
            (patch, rpc_source()+rpc_source()),
            (patch, rpc_source(block_comment='entry')),
            (patch, rpc_source(block_comment='nested')),
            (patch, rpc_source(block_comment='array')),
        )
        for raw_patch, rpc in bad:
            with self.subTest(patch=raw_patch, rpc=rpc), self.assertRaisesRegex(ValueError, 'device_fixes122'):
                self.metadata(raw_patch, rpc)
        self.assertEqual({'device_fixes122_capability': CAPABILITY}, self.metadata(patch, rpc_source()))
        self.assertEqual({}, self.metadata(b'// old patch\n', rpc_source(declared=False)))

    def test_package_has_separate_122_field_and_unchanged_prior_API_and_profile(self):
        with tempfile.TemporaryDirectory() as temporary:
            upstream, driver, _ = self.fixture(Path(temporary))
            report = module('verify_package').inspect_native_sources(upstream, driver)
            self.assertEqual(CAPABILITY, report.get('device_fixes122_capability'))
            for _version,field,cap in PRIOR_BINDINGS:
                self.assertEqual(cap, report[field])
            self.assertEqual(('1.98.16-ngg2', 'necrogold_native_v15', 3),
                (report['api_version'], report['client_capability'], report['compiler_profile_version']))

    def test_resealed_mismatched_122_metadata_patch_or_rpc_is_rejected(self):
        faults = ({'metadata': None}, {'metadata': 'wrong'}, {'declared': False}, {'patch_declared': False},
            {'block_comment': 'entry'}, {'block_comment': 'nested'}, {'block_comment': 'array'})
        for fault in faults:
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as temporary:
                upstream, driver, _ = self.fixture(Path(temporary), **fault)
                # The retained120 prerequisite rejects block delimiters first.
                error = 'device_fixes120' if 'block_comment' in fault else 'device_fixes122'
                with self.assertRaisesRegex(ValueError, error):
                    module('verify_package').inspect_native_sources(upstream, driver)

    def test_historical_121_manifest_gets_no_unrequested_122_field(self):
        with tempfile.TemporaryDirectory() as temporary:
            upstream, driver, _ = self.fixture(Path(temporary), declared=False, metadata=None, patch_declared=False)
            report = module('verify_package').inspect_native_sources(upstream, driver)
            self.assertNotIn('device_fixes122_capability', report)
            for _version,field,cap in PRIOR_BINDINGS:
                self.assertEqual(cap, report[field])

    def test_122_cannot_bypass_the_existing_121_package_binding(self):
        with tempfile.TemporaryDirectory() as temporary:
            upstream, driver, manifest = self.fixture(Path(temporary))
            del manifest['device_fixes121_capability']
            (driver/'patches/loopctrl/ngg2-manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'device_fixes121'):
                module('verify_package').inspect_native_sources(upstream, driver)


# Selector checks only construct procedural unittest objects. They do not run
# a native matcher, compile C, or claim an iPhone/gameplay result.
import os
import subprocess
from unittest.mock import patch

ROOT = HERE.parents[1]


def host_runner():
    # The previous runner is executable for semantic Red before 122 exists.
    return module('run_test122_host' if (HERE/'run_test122_host.py').exists() else 'run_test121_host')


def one_case(outcome='green'):
    class Fixture(unittest.TestCase):
        def runTest(self):
            if outcome == 'skip':
                self.skipTest('procedural selector boundary')
            if outcome == 'failure':
                self.fail('procedural selector boundary')
            if outcome == 'error':
                raise ValueError('procedural selector boundary')
    return Fixture()


def python39_runner():
    # 120 is the executable pre-implementation subject; absent122 must not
    # produce an import/compile failure in the intended assertion Red.
    name = 'run_test122_python39' if (HERE/'run_test122_python39.py').exists() else 'run_test121_python39'
    return module(name)


def focused_steps(source):
    return module('test_device_ci117').focused_steps(source)


def condition_selected(condition, profile, lane='device'):
    return module('test_device_ci117').condition_selected(condition, profile, lane)


def historical_test_step(row):
    source = '\n'.join(row['source'])
    versions = [str(n).zfill(3) for n in range(94,122)]
    return (any('TEST'+v in row['name'] or 'check_runtime'+v+'.py' in source
            or 'check_cycle_api'+v+'.py' in source or 'check_cycle_spool'+v+'.py' in source
            or 'check_cycle_export'+v+'.py' in source for v in versions)
        or 'check_ngg2.py' in source or 'check_ngg2_rpc.py' in source or 'world16' in source)


class DeviceHostSelection122Tests(unittest.TestCase):
    def controls(self):
        return dict(SCOPE_FINALIZED=True, MAC_SCOPE_FINALIZED=True,
            CASES=(('m', 'C', 'one', frozenset({'test_one'}), True),), CORE_MODULES=('m',),
            NEW_PATHS=frozenset({'new.py'}), EXPECTED_NATIVE_CHANGES=frozenset({'native.c'}),
            EXPECTED_REPOSITORY_CHANGES=frozenset({'path.c'}),
            MAC_CASE_GROUPS=())

    def test_pending_native_scope_cannot_import_or_execute_fixtures(self):
        runner = host_runner()
        with patch.object(runner, 'SCOPE_FINALIZED', False), \
                patch.object(runner.shared, 'native_suites') as execute:
            with self.assertRaisesRegex(ValueError, 'pending'):
                runner.native_suites(ROOT/'upstream', ROOT)
        execute.assert_not_called()
        for variable in ('BASELINE_NAV', 'NECRO_TEST_DLL', 'NECRO121_FIXTURE', 'NECRO122_FIXTURE',
                'NECRO_NAV120_RED_SOURCE', 'NECRO_NAV121_RED_SOURCE',
                'NG2_TEST122_CORE', 'NG2_TEST122_CONTROLLER_CORE'):
            with patch.dict(os.environ, {variable:'forged'}), self.assertRaises(ValueError):
                runner.reject_fixture_overrides()

    def test_empty_duplicate_or_nonzero_mac_scope_is_rejected(self):
        runner = host_runner()
        controls = self.controls()
        with patch.multiple(runner, create=True, **controls):
            # No Runtime/queue boundary changed: the new scope is exactly zero Mac cases.
            try:
                runner.ensure_scope()
            except ValueError as error:
                self.fail('the explicit zero-Mac122 scope was rejected: '+str(error))
            for flag in ('SCOPE_FINALIZED','MAC_SCOPE_FINALIZED'):
                with patch.object(runner,flag,False), self.assertRaises(ValueError):
                    runner.ensure_scope()
            for name in ('CASES','CORE_MODULES','NEW_PATHS','EXPECTED_NATIVE_CHANGES','EXPECTED_REPOSITORY_CHANGES'):
                with patch.object(runner,name,()), self.assertRaises(ValueError):
                    runner.ensure_scope()
            with patch.object(runner,'CASES',controls['CASES']*2), self.assertRaises(ValueError):
                runner.ensure_scope()
            for groups in ((('check_runtime120.py',('partial_begin_dispatch',)),),
                    (('check_runtime122.py',('unselected_boundary',)),)):
                with patch.object(runner,'MAC_CASE_GROUPS',groups), self.assertRaises(ValueError):
                    runner.ensure_scope()

    def test_pending_python39_scope_cannot_import_or_execute_fixtures(self):
        runner = python39_runner()
        with patch.object(runner, 'SCOPE_FINALIZED', False), \
                patch.object(runner.importlib, 'import_module') as imported:
            with self.assertRaises(ValueError):
                runner.selected_suite(ROOT)
        imported.assert_not_called()

    def test_python39_exact_122_and_direct_retained_subset_has_86_unique_methods(self):
        runner = python39_runner()
        self.assertEqual(86, sum(len(row[3]) for row in runner.CASES))
        host = host_runner()
        with patch.object(runner, 'SCOPE_FINALIZED', True), \
                patch.multiple(host, create=True, **self.controls()), \
                patch.object(runner, 'host_module', return_value=host):
            try:
                _, selected = runner.selected_suite(ROOT)
            except ValueError as error:
                self.fail('the exact122 client scope was rejected: '+str(error))
        self.assertEqual(86, len(selected), 'new12211 + prior12111 + prior12011 + prior11911 + prior11811 + prior11725 + direct1166')
        self.assertEqual(86, len({case.id() for case in selected}))
        counts = {}
        for name, _klass, _label, methods, _exact in runner.CASES:
            counts[name] = counts.get(name, 0)+len(methods)
        self.assertEqual(11, counts['tests.test_continuous_client122'])
        self.assertEqual(11, counts['tests.test_continuous_client121'])
        self.assertEqual(11, counts['tests.test_continuous_client120'])
        self.assertEqual(11, counts['tests.test_continuous_client119'])
        self.assertEqual(11, counts['tests.test_continuous_client118'])
        self.assertEqual(6, counts['tests.test_continuous_client116'])
        self.assertEqual(25, counts['tests.test_continuous_client117']+counts['tests.test_initial_restart117'])

    def test_native_inventory_requires_all37_and_only_the_declared_changed_sources(self):
        runner = host_runner()
        check = getattr(runner, 'native_inventory', lambda *_:(set(),set()))
        required = {'LoopCtrlKit/RPCMethod.swift', 'LoopCtrlUITests/NG2Controller.c',
            'LoopCtrlUITests/NG2Navigation.c', 'LoopCtrlUITests/NG2Ring.c', 'LoopCtrlUITests/NG2Ring.h'}
        changed = set(runner.EXPECTED_NATIVE_CHANGES)
        self.assertEqual(required, changed)
        before = {name:'0'*64 for name in changed}
        before.update({'retained'+str(n):'0'*64 for n in range(37-len(changed))})
        current = dict(before)
        current.update({name:'1'*64 for name in changed})
        self.assertEqual((changed,set()),check(before,current))
        faults = [dict(current, foreign='1'*64), {k:v for k,v in current.items() if k!='retained0'},
            dict(current, retained0='1'*64), dict(before), {}]
        for values in faults:
            with self.subTest(native_sources=len(values)), self.assertRaises(ValueError):
                check(before,values)

    def test_file_core_and_controller_aliases_bind_the_sealed_sibling_set(self):
        from types import SimpleNamespace
        runner = host_runner()
        source = ROOT/'patches/loopctrl/ngg2/NG2Ring.c'
        values = {}
        for name in ('tests.test_native_goods_coverage121', 'tests.test_native_price_independent_goods122'):
            values[name] = SimpleNamespace(CORE=source)
            values[name.rsplit('.', 1)[-1]] = SimpleNamespace(CORE=source)
        singleton = 'tests.test_native_singleton_dependency122'
        for name in (singleton, singleton.rsplit('.', 1)[-1]):
            values[name] = SimpleNamespace(CORE=source.parent, CONTROLLER_CORE=ROOT/'unsealed-core')
        upstream = ROOT/'procedural-sealed-upstream'
        with patch.multiple(runner, create=True, **self.controls()), \
                patch.dict('sys.modules', values), \
                patch.object(runner.shared, 'native_suites', return_value=[]) as load:
            self.assertEqual([], runner.native_suites(upstream, ROOT))
        load.assert_called_once_with(upstream, ROOT)
        expected = upstream/'LoopCtrlUITests'
        for name, fixture in values.items():
            if 'singleton' in name:
                self.assertEqual(expected, fixture.CORE)
                self.assertEqual(expected, fixture.CONTROLLER_CORE)
            else:
                self.assertEqual(expected/'NG2Ring.c', fixture.CORE)
                self.assertEqual(expected, fixture.CORE.parent)

    def test_source_identity_preserves_runtime_G1_and_all_five_versioned_caps(self):
        runner = host_runner()
        self.assertEqual('d78159a9d535178df8282d69f182b2ae544facf0',runner.NATIVE_BASELINE)
        self.assertEqual((),runner.MAC_CASE_GROUPS)
        self.assertEqual(frozenset(),runner.EXPECTED_NATIVE_ADDITIONS)
        for _version,field,cap in PRIOR_BINDINGS:
            self.assertEqual(cap,runner.EXPECTED_API.get(field))
        self.assertEqual(CAPABILITY,runner.EXPECTED_API.get('device_fixes122_capability'))
        for name in ('NG2Runtime.swift','NG2Ticket.swift','NG2Raster.swift','NG2CycleSpool.swift',
                'NG2CycleWire.swift','NG2CycleExport.swift','NG2Perception.c'):
            self.assertIn('patches/loopctrl/ngg2/'+name,runner.PRESERVED_PATHS)
        self.assertNotIn('patches/loopctrl/ngg2/NG2Ring.c',runner.PRESERVED_PATHS)
        for name in ('patches/loopctrl/ngg1.patch','patches/loopctrl/source-manifest.json',
                'patches/loopctrl/run_test120_host.py','patches/loopctrl/run_test120_python39.py',
                'patches/loopctrl/run_test121_host.py','patches/loopctrl/run_test121_python39.py',
                'patches/loopctrl/test_device_ci121.py'):
            self.assertIn(name,runner.PRESERVED_PATHS)
        counts = {label:len(methods) for _module,_klass,label,methods,_exact in runner.CASES}
        self.assertEqual(20,len(counts))
        self.assertEqual(74,sum(len(methods) for name,_klass,_label,methods,_exact in runner.CASES
            if name.startswith('tests.')))
        self.assertEqual(6,counts['test122-capability'])
        self.assertEqual(8,counts['test122-package-related'])
        self.assertEqual(102,sum(counts.values())+len(unittest.defaultTestLoader.getTestCaseNames(type(self))))
        self.assertEqual(59,len(set(runner.CORE_MODULES)))
        modules = {row[0] for row in runner.CASES}
        for name in ('tests.test_native_upper_material122', 'tests.test_native_full_halo_data122',
                'tests.test_native_singleton_dependency122', 'tests.test_native_price_independent_goods122',
                'tests.test_native_goods_coverage121'):
            self.assertIn(name,modules)
        self.assertEqual({'tests.test_native_goods_coverage121':'NG2Ring.c',
            'tests.test_native_price_independent_goods122':'NG2Ring.c'},runner.FILE_CORE_SOURCES)

    def test_source_identity_rejects_unpinned_applier_before_importing_it(self):
        runner=host_runner()
        controls=self.controls()
        changed=set(runner.EXPECTED_NATIVE_CHANGES)
        controls['EXPECTED_NATIVE_CHANGES']=frozenset(changed)
        old={name:'0'*64 for name in changed}
        old.update({'retained'+str(n):'0'*64 for n in range(37-len(changed))})
        current=dict(old)
        current.update({name:'1'*64 for name in changed})
        def manifest(values):
            return dict(files={name:dict(patched_sha256=digest) for name,digest in values.items()},
                additions={},**runner.EXPECTED_API)
        current_manifest=json.dumps(manifest(current)).encode()
        old_manifest=json.dumps(manifest(old)).encode()
        path='patches/loopctrl/ngg2-manifest.json'
        def git(_driver,*arguments):
            if arguments==('rev-parse','HEAD'):
                return b'1111111111111111111111111111111111111111\n'
            self.assertEqual(('show',runner.NATIVE_BASELINE+':'+path),arguments)
            return old_manifest
        def pinned(_driver,name,_code):
            if name==path:
                return current_manifest
            self.assertEqual('patches/loopctrl/apply_ngg2.py',name)
            raise ValueError('unpinned applier source')
        with patch.multiple(runner,create=True,**controls), patch.object(runner,'git',side_effect=git), \
                patch.object(runner,'pinned_bytes',side_effect=pinned), \
                patch.object(runner.importlib.util,'spec_from_file_location',
                    side_effect=lambda *_:self.fail('an unpinned applier was imported')) as imported:
            with self.assertRaisesRegex(ValueError,'unpinned applier source'):
                runner.source_identity(ROOT,dict(native_source_sha256=current),ROOT/'upstream')
        imported.assert_not_called()

    def test_python_receipt_never_overwrites_native_receipt(self):
        runner = host_runner()
        for outcome in ('green','failure','error','skip'):
            with self.subTest(outcome=outcome), tempfile.TemporaryDirectory() as temporary, patch('builtins.print'):
                output = Path(temporary)
                native = output/'test122-host-scope.json'
                sentinel = b'{"scope":"native source-bound sentinel"}\n'
                native.write_bytes(sentinel)
                evidence = {'scope':'procedural selector fixture'}
                if outcome == 'green':
                    runner.run_scope('python-fixture',[one_case(outcome)],output,evidence,
                        receipt_name='test122-python39-scope.json')
                else:
                    with self.assertRaises(RuntimeError):
                        runner.run_scope('python-fixture',[one_case(outcome)],output,evidence,
                            receipt_name='test122-python39-scope.json')
                self.assertEqual(sentinel,native.read_bytes())
                self.assertEqual(evidence,json.loads((output/'test122-python39-scope.json').read_bytes()))
                self.assertEqual(1,evidence['python-fixture']['tests_run'])

    def test_receipt_names_are_closed_before_any_test_executes(self):
        runner = host_runner()
        for name in ('test119-host-scope.json','other.json','../test122-host-scope.json',
                '/tmp/test122-host-scope.json','',None,0):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                output=Path(temporary)
                with patch.object(runner,'selected_cases') as selected, self.assertRaises(ValueError):
                    runner.run_scope('fixture',[],output,{},receipt_name=name)
                selected.assert_not_called()
                self.assertEqual([],list(output.iterdir()))

    def test_empty_duplicate_failure_error_or_skip_is_not_a_green_selection(self):
        runner=host_runner()
        for cases in ([],[one_case(),one_case()]):
            with self.assertRaises(ValueError):
                runner.selected_cases(cases)
        for outcome in ('failure','error','skip'):
            with tempfile.TemporaryDirectory() as temporary, patch('builtins.print'), self.assertRaises(RuntimeError):
                runner.run_scope('fixture',[one_case(outcome)],Path(temporary),{})

    def test_workflow_selects_122_and_uses_the_pinned_actual_python39(self):
        source=(ROOT/'.github/workflows/loopctrl-geometry.yml').read_text()
        body=source.split('  test061-host-contracts:\n',1)[1].split('  focused-build:\n',1)[0]
        self.assertIn('NATIVE_HOST_RUNNER=driver/patches/loopctrl/run_test122_host.py',body)
        self.assertLess(body.index('DEVICE_PROFILE=121'),body.index('DEVICE_PROFILE=122'))
        self.assertEqual(1,body.count('run_test122_python39.py driver'))
        self.assertIn("inputs.native_lane == 'device' && steps.host_contracts.outputs.device_profile == '122'",body)
        self.assertIn('steps.python39_116.outputs.python-path',body)
        self.assertIn('fe04e8b27bd69ca2144fc542428f8b9b5287b6a2e45516a4acfe2c2bc3102773',body)
        provider=body.split('      - name: Select actual Python 3.9 for TEST116 client compatibility\n',1)[1]
        provider=provider.split('      - name: Run TEST116 exact client methods',1)[0]
        self.assertIn("steps.host_contracts.outputs.device_profile == '122'",provider)

    def test_122_device_has_zero_mac_cases_and_keeps_actual_IPA_build(self):
        source=(ROOT/'.github/workflows/loopctrl-geometry.yml').read_text()
        rows=focused_steps(source)
        selected=[row for row in rows if condition_selected(row['condition'],'122')]
        self.assertEqual([], [row['name'] for row in selected if historical_test_step(row)])
        self.assertEqual([], [row['name'] for row in selected
            if 'check_runtime' in '\n'.join(row['source'])])
        self.assertNotIn('${{ runner.temp }}/test122-runtime/',source)
        names={row['name'] for row in selected}
        for name in ('Generate and inspect actual source-specific project configuration',
                'Build and package unsigned IPA','Verify actual source-specific Perception compiler profile',
                'Verify package and record provenance'):
            self.assertIn(name,names)
        self.assertFalse(any('world' in row['name'] for row in selected))

    def test_prior_094_through_121_lanes_keep_their_exact_selected_steps(self):
        before=subprocess.check_output(['git','show',
            'd78159a9d535178df8282d69f182b2ae544facf0:.github/workflows/loopctrl-geometry.yml'],cwd=ROOT,text=True)
        old=focused_steps(before)
        now=focused_steps((ROOT/'.github/workflows/loopctrl-geometry.yml').read_text())
        for profile in (str(n).zfill(3) for n in range(94,122)):
            for lane in ('device','focused','full'):
                with self.subTest(profile=profile,lane=lane):
                    self.assertEqual([r for r in old if condition_selected(r['condition'],profile,lane)],
                        [r for r in now if condition_selected(r['condition'],profile,lane)])
        for profile in ('123','','forged'):
            with self.subTest(profile=profile):
                selected=[r for r in now if condition_selected(r['condition'],profile)]
                self.assertEqual([], [r['name'] for r in selected if historical_test_step(r)])


if __name__ == '__main__':
    unittest.main()
