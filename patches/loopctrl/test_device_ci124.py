"""TEST124 adds one capability while preserving all six historical bindings."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
CAPABILITY = 'necrogold_native_device_fixes124_v1'
PRIOR_BINDINGS = (
    (118, 'device_fixes_capability', 'necrogold_native_device_fixes118_v1'),
    (119, 'device_fixes119_capability', 'necrogold_native_device_fixes119_v1'),
    (120, 'device_fixes120_capability', 'necrogold_native_device_fixes120_v1'),
    (121, 'device_fixes121_capability', 'necrogold_native_device_fixes121_v1'),
    (122, 'device_fixes122_capability', 'necrogold_native_device_fixes122_v1'),
    (123, 'device_fixes123_capability', 'necrogold_native_device_fixes123_v1'),
)


def module(name):
    spec = importlib.util.spec_from_file_location('device124_'+name, HERE/(name+'.py'))
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


class DeviceImplementationCapability124Tests(unittest.TestCase):
    def metadata(self, patch, rpc):
        # Before implementation, a missing new claim is an assertion Red.
        helper = getattr(module('apply_ngg2'), 'device_fixes124_metadata', lambda *_: {})
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
            manifest['device_fixes124_capability'] = metadata
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

    def test_current_patch_adds_124_without_replacing_118_119_120_or_121_or_122_or_123(self):
        patch = (HERE/'ngg2.patch').read_bytes()
        for cap in (*[cap for _version,_field,cap in PRIOR_BINDINGS], CAPABILITY):
            self.assertEqual(1, patch.count(('+        "'+cap+'",').encode()))
        self.assertEqual({'device_fixes124_capability': CAPABILITY}, self.metadata(patch, rpc_source()))
        for version,field,cap in PRIOR_BINDINGS:
            self.assertEqual({field:cap},
                getattr(module('apply_ngg2'), 'device_fixes'+str(version)+'_metadata')(patch, rpc_source()))

    def test_sealing_requires_one_real_uncommented_124_array_entry(self):
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
            with self.subTest(patch=raw_patch, rpc=rpc), self.assertRaisesRegex(ValueError, 'device_fixes124'):
                self.metadata(raw_patch, rpc)
        self.assertEqual({'device_fixes124_capability': CAPABILITY}, self.metadata(patch, rpc_source()))
        self.assertEqual({}, self.metadata(b'// old patch\n', rpc_source(declared=False)))

    def test_package_has_separate_124_field_and_unchanged_prior_API_and_profile(self):
        with tempfile.TemporaryDirectory() as temporary:
            upstream, driver, _ = self.fixture(Path(temporary))
            report = module('verify_package').inspect_native_sources(upstream, driver)
            self.assertEqual(CAPABILITY, report.get('device_fixes124_capability'))
            for _version,field,cap in PRIOR_BINDINGS:
                self.assertEqual(cap, report[field])
            self.assertEqual(('1.98.16-ngg2', 'necrogold_native_v15', 3),
                (report['api_version'], report['client_capability'], report['compiler_profile_version']))

    def test_resealed_mismatched_124_metadata_patch_or_rpc_is_rejected(self):
        faults = ({'metadata': None}, {'metadata': 'wrong'}, {'declared': False}, {'patch_declared': False},
            {'block_comment': 'entry'}, {'block_comment': 'nested'}, {'block_comment': 'array'})
        for fault in faults:
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as temporary:
                upstream, driver, _ = self.fixture(Path(temporary), **fault)
                # The retained120 prerequisite rejects block delimiters first.
                error = 'device_fixes120' if 'block_comment' in fault else 'device_fixes124'
                with self.assertRaisesRegex(ValueError, error):
                    module('verify_package').inspect_native_sources(upstream, driver)

    def test_historical_123_manifest_gets_no_unrequested_124_field(self):
        with tempfile.TemporaryDirectory() as temporary:
            upstream, driver, _ = self.fixture(Path(temporary), declared=False, metadata=None, patch_declared=False)
            report = module('verify_package').inspect_native_sources(upstream, driver)
            self.assertNotIn('device_fixes124_capability', report)
            for _version,field,cap in PRIOR_BINDINGS:
                self.assertEqual(cap, report[field])

    def test_124_cannot_bypass_the_existing_123_package_binding(self):
        with tempfile.TemporaryDirectory() as temporary:
            upstream, driver, manifest = self.fixture(Path(temporary))
            del manifest['device_fixes123_capability']
            (driver/'patches/loopctrl/ngg2-manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'device_fixes123'):
                module('verify_package').inspect_native_sources(upstream, driver)



# Selector checks only construct procedural unittest objects. They do not run
# a native matcher, compile C, or claim an iPhone/gameplay result.
import os
import subprocess
from unittest.mock import patch

ROOT = HERE.parents[1]


def host_runner():
    # The exact prior123 runner is the semantic Red subject before124 is finalized.
    return module('run_test124_host' if (HERE/'run_test124_host.py').exists() else 'run_test123_host')


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
    # Prior123 remains an executable assertion subject; absence124 is not an import Red.
    name = 'run_test124_python39' if (HERE/'run_test124_python39.py').exists() else 'run_test123_python39'
    return module(name)


def focused_steps(source):
    return module('test_device_ci117').focused_steps(source)


def condition_selected(condition, profile, lane='device'):
    return module('test_device_ci117').condition_selected(condition, profile, lane)


def historical_test_step(row):
    source = '\n'.join(row['source'])
    versions = [str(n).zfill(3) for n in range(94,124)]
    return (any('TEST'+v in row['name'] or 'check_runtime'+v+'.py' in source
            or 'check_cycle_api'+v+'.py' in source or 'check_cycle_spool'+v+'.py' in source
            or 'check_cycle_export'+v+'.py' in source for v in versions)
        or 'check_ngg2.py' in source or 'check_ngg2_rpc.py' in source or 'world16' in source)


class DeviceHostSelection124Tests(unittest.TestCase):
    def controls(self):
        return dict(SCOPE_FINALIZED=True, MAC_SCOPE_FINALIZED=True, PENDING_SCOPE_ITEMS=(),
            EXPECTED_SELECTED_METHOD_COUNT=1, EXPECTED_NATIVE_METHOD_COUNT=1, EXPECTED_CORE_MODULE_COUNT=1,
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
        for variable in ('BASELINE_NAV', 'NECRO_TEST_DLL', 'NECRO121_FIXTURE', 'NECRO122_FIXTURE', 'NECRO123_FIXTURE', 'NECRO124_FIXTURE',
                'NECRO_NAV120_RED_SOURCE', 'NECRO_NAV121_RED_SOURCE',
                'NG2_TEST123_CORE', 'NG2_TEST123_CONTROLLER_CORE', 'NG2_TEST124_CORE', 'NG2_TEST124_CONTROLLER_CORE'):
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
                self.fail('the explicit zero-Mac124 scope was rejected: '+str(error))
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

    def test_python39_candidate_124_and_direct_retained_subset_has_108_unique_methods(self):
        runner = python39_runner()
        self.assertEqual(108, sum(len(row[3]) for row in runner.CASES))
        host = host_runner()
        with patch.object(runner, 'SCOPE_FINALIZED', True), \
                patch.object(runner, 'PENDING_SCOPE_ITEMS', ()), \
                patch.object(runner, 'EXPECTED_SELECTED_METHOD_COUNT', 108), \
                patch.multiple(host, create=True, **self.controls()), \
                patch.object(runner, 'host_module', return_value=host):
            try:
                _, selected = runner.selected_suite(ROOT)
            except ValueError as error:
                self.fail('the candidate108 client scope was rejected: '+str(error))
        self.assertEqual(108, len(selected), 'new12411 + prior12311 + prior12211 + prior12111 + prior12011 + prior11911 + prior11811 + prior11725 + direct1166')
        self.assertEqual(108, len({case.id() for case in selected}))
        counts = {}
        for name, _klass, _label, methods, _exact in runner.CASES:
            counts[name] = counts.get(name, 0)+len(methods)
        self.assertEqual(11, counts['tests.test_continuous_client124'])
        self.assertEqual(11, counts['tests.test_continuous_client123'])
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
            'LoopCtrlUITests/NG2Ring.c'}
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
        for name in ('tests.test_native_partial_positive124','test_native_partial_positive124'):
            values[name] = SimpleNamespace(RING=source)
        for module in ('tests.test_native_controller','tests.test_native_transferred_view124'):
            for name in (module, module.rsplit('.', 1)[-1]):
                values[name] = SimpleNamespace(CORE=ROOT/'unsealed-core')
        upstream = ROOT/'procedural-sealed-upstream'
        with patch.multiple(runner, create=True, **self.controls()), \
                patch.dict('sys.modules', values), \
                patch.object(runner.shared, 'native_suites', return_value=[]) as load:
            self.assertEqual([], runner.native_suites(upstream, ROOT))
        load.assert_called_once_with(upstream, ROOT)
        expected = upstream/'LoopCtrlUITests'
        for name, fixture in values.items():
            if 'partial_positive124' in name:
                self.assertEqual(expected/'NG2Ring.c', fixture.RING)
                self.assertEqual(values['tests.test_native_controller'].CORE, fixture.RING.parent)
            else:
                self.assertEqual(expected, fixture.CORE)

    def test_source_identity_preserves_runtime_G1_and_all_seven_versioned_caps(self):
        runner = host_runner()
        source = Path(runner.__file__).read_text()
        for binding in ("selector = importlib.import_module('test_device_ci124')",
                'selector.DeviceHostSelection124Tests', "run_scope('test124-selector',"):
            with self.subTest(binding=binding):
                self.assertIn(binding, source)
        self.assertEqual('fd5901d84145c0dcfebfa1c60607a80f3c8f82a5',runner.NATIVE_BASELINE)
        self.assertEqual((),runner.MAC_CASE_GROUPS)
        self.assertEqual({'tests.test_native_stationary_wait076.NativeStationaryWait076Tests.test_ready_or_issued_unknown_does_not_reopen_the_same_wait', 'tests.test_native_observation072.NativeObservation072Tests.test_exhausted_same_chain_reobserves_floor_before_a_new_future_ticket', 'tests.test_native_observation072.NativeObservation072Tests.test_current_hud_fifty_ms_preparation_and_original_budgets_remain_required'},set(runner.EXCLUDED_LEGACY_METHODS))
        self.assertEqual(frozenset(),runner.EXPECTED_NATIVE_ADDITIONS)
        for _version,field,cap in PRIOR_BINDINGS:
            self.assertEqual(cap,runner.EXPECTED_API.get(field))
        self.assertEqual(CAPABILITY,runner.EXPECTED_API.get('device_fixes124_capability'))
        for name in ('NG2Runtime.swift','NG2Ticket.swift','NG2Raster.swift','NG2CycleSpool.swift',
                'NG2CycleWire.swift','NG2CycleExport.swift','NG2Perception.c','NG2Navigation.c'):
            self.assertIn('patches/loopctrl/ngg2/'+name,runner.PRESERVED_PATHS)
        self.assertNotIn('patches/loopctrl/ngg2/NG2Ring.c',runner.PRESERVED_PATHS)
        for name in ('patches/loopctrl/ngg1.patch','patches/loopctrl/source-manifest.json',
                'patches/loopctrl/run_test120_host.py','patches/loopctrl/run_test120_python39.py',
                'patches/loopctrl/run_test121_host.py','patches/loopctrl/run_test121_python39.py',
                'patches/loopctrl/test_device_ci121.py',
                'patches/loopctrl/run_test122_host.py','patches/loopctrl/run_test122_python39.py',
                'patches/loopctrl/test_device_ci122.py',
                'patches/loopctrl/run_test123_host.py','patches/loopctrl/run_test123_python39.py',
                'patches/loopctrl/test_device_ci123.py'):
            self.assertIn(name,runner.PRESERVED_PATHS)
        # Source prep is closed until final author AST/native seal/CODE inventory exists.
        if runner.SCOPE_FINALIZED:
            self.assertFalse(runner.PENDING_SCOPE_ITEMS)
            for count in (runner.EXPECTED_SELECTED_METHOD_COUNT, runner.EXPECTED_NATIVE_METHOD_COUNT,
                    runner.EXPECTED_CORE_MODULE_COUNT):
                self.assertIs(type(count), int)
                self.assertGreater(count, 0)
            self.assertEqual(runner.EXPECTED_SELECTED_METHOD_COUNT,
                sum(len(row[3]) for row in runner.CASES)+14)
            self.assertEqual(runner.EXPECTED_NATIVE_METHOD_COUNT,
                sum(len(row[3]) for row in runner.CASES if row[0].startswith('tests.')))
            self.assertEqual(runner.EXPECTED_CORE_MODULE_COUNT,len(set(runner.CORE_MODULES)))
        else:
            self.assertTrue(runner.PENDING_SCOPE_ITEMS)
            self.assertEqual((),runner.CASES)
            self.assertEqual((),runner.CORE_MODULES)
            self.assertEqual((None,None,None),(runner.EXPECTED_SELECTED_METHOD_COUNT,
                runner.EXPECTED_NATIVE_METHOD_COUNT,runner.EXPECTED_CORE_MODULE_COUNT))
        self.assertEqual({},runner.FILE_CORE_SOURCES)
        self.assertEqual({'tests.test_native_partial_positive124':{'RING':'NG2Ring.c'}},runner.EXTRA_FILE_CORES)
        self.assertEqual({'tests.test_native_controller':('CORE',),
            'tests.test_native_transferred_view124':('CORE',)},runner.EXTRA_DIRECTORY_CORES)

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
                native = output/'test124-host-scope.json'
                sentinel = b'{"scope":"native source-bound sentinel"}\n'
                native.write_bytes(sentinel)
                evidence = {'scope':'procedural selector fixture'}
                try:
                    if outcome == 'green':
                        runner.run_scope('python-fixture',[one_case(outcome)],output,evidence,
                            receipt_name='test124-python39-scope.json')
                    else:
                        with self.assertRaises(RuntimeError):
                            runner.run_scope('python-fixture',[one_case(outcome)],output,evidence,
                                receipt_name='test124-python39-scope.json')
                except ValueError as error:
                    self.fail('the new closed TEST124 receipt namespace was rejected: '+str(error))
                self.assertEqual(sentinel,native.read_bytes())
                self.assertEqual(evidence,json.loads((output/'test124-python39-scope.json').read_bytes()))
                self.assertEqual(1,evidence['python-fixture']['tests_run'])

    def test_receipt_names_are_closed_before_any_test_executes(self):
        runner = host_runner()
        for name in ('test119-host-scope.json','other.json','../test124-host-scope.json',
                '/tmp/test124-host-scope.json','',None,0):
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

    def test_workflow_selects_124_and_uses_the_pinned_actual_python39(self):
        source=(ROOT/'.github/workflows/loopctrl-geometry.yml').read_text()
        body=source.split('  test061-host-contracts:\n',1)[1].split('  focused-build:\n',1)[0]
        self.assertIn('NATIVE_HOST_RUNNER=driver/patches/loopctrl/run_test124_host.py',body)
        self.assertLess(body.index('DEVICE_PROFILE=123'),body.index('DEVICE_PROFILE=124'))
        self.assertEqual(1,body.count('run_test124_python39.py driver'))
        self.assertIn("inputs.native_lane == 'device' && steps.host_contracts.outputs.device_profile == '124'",body)
        self.assertIn('steps.python39_116.outputs.python-path',body)
        self.assertIn('fe04e8b27bd69ca2144fc542428f8b9b5287b6a2e45516a4acfe2c2bc3102773',body)
        provider=body.split('      - name: Select actual Python 3.9 for TEST116 client compatibility\n',1)[1]
        provider=provider.split('      - name: Run TEST116 exact client methods',1)[0]
        self.assertIn("steps.host_contracts.outputs.device_profile == '124'",provider)

    def test_124_device_has_zero_mac_cases_and_keeps_actual_IPA_build(self):
        source=(ROOT/'.github/workflows/loopctrl-geometry.yml').read_text()
        rows=focused_steps(source)
        selected=[row for row in rows if condition_selected(row['condition'],'124')]
        self.assertEqual([], [row['name'] for row in selected if historical_test_step(row)])
        self.assertEqual([], [row['name'] for row in selected
            if 'check_runtime' in '\n'.join(row['source'])])
        self.assertNotIn('${{ runner.temp }}/test124-runtime/',source)
        names={row['name'] for row in selected}
        for name in ('Generate and inspect actual source-specific project configuration',
                'Build and package unsigned IPA','Verify actual source-specific Perception compiler profile',
                'Verify package and record provenance'):
            self.assertIn(name,names)
        self.assertFalse(any('world' in row['name'] for row in selected))

    def test_prior_094_through_123_lanes_keep_their_exact_selected_steps(self):
        before=subprocess.check_output(['git','show',
            'fd5901d84145c0dcfebfa1c60607a80f3c8f82a5:.github/workflows/loopctrl-geometry.yml'],cwd=ROOT,text=True)
        old=focused_steps(before)
        now=focused_steps((ROOT/'.github/workflows/loopctrl-geometry.yml').read_text())
        for profile in (str(n).zfill(3) for n in range(94,124)):
            for lane in ('device','focused','full'):
                with self.subTest(profile=profile,lane=lane):
                    self.assertEqual([r for r in old if condition_selected(r['condition'],profile,lane)],
                        [r for r in now if condition_selected(r['condition'],profile,lane)])
        for profile in ('125','','forged'):
            with self.subTest(profile=profile):
                selected=[r for r in now if condition_selected(r['condition'],profile)]
                self.assertEqual([], [r['name'] for r in selected if historical_test_step(r)])


if __name__ == '__main__':
    unittest.main()
