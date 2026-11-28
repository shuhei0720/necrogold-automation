"""TEST126 adds one capability while preserving all eight historical bindings."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
CAPABILITY = 'necrogold_native_device_fixes126_v1'
PRIOR_BINDINGS = (
    (118, 'device_fixes_capability', 'necrogold_native_device_fixes118_v1'),
    (119, 'device_fixes119_capability', 'necrogold_native_device_fixes119_v1'),
    (120, 'device_fixes120_capability', 'necrogold_native_device_fixes120_v1'),
    (121, 'device_fixes121_capability', 'necrogold_native_device_fixes121_v1'),
    (122, 'device_fixes122_capability', 'necrogold_native_device_fixes122_v1'),
    (123, 'device_fixes123_capability', 'necrogold_native_device_fixes123_v1'),
    (124, 'device_fixes124_capability', 'necrogold_native_device_fixes124_v1'),
    (125, 'device_fixes125_capability', 'necrogold_native_device_fixes125_v1'),
)


def module(name):
    spec = importlib.util.spec_from_file_location('device126_'+name, HERE/(name+'.py'))
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


class DeviceImplementationCapability126Tests(unittest.TestCase):
    def metadata(self, patch, rpc):
        # Before implementation, a missing new claim is an assertion Red.
        helper = getattr(module('apply_ngg2'), 'device_fixes126_metadata', lambda *_: {})
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
            manifest['device_fixes126_capability'] = metadata
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

    def test_current_patch_adds_126_without_replacing_118_119_120_or_121_or_122_or_123_or_124_or_125(self):
        patch = (HERE/'ngg2.patch').read_bytes()
        for cap in (*[cap for _version,_field,cap in PRIOR_BINDINGS], CAPABILITY):
            self.assertEqual(1, patch.count(('+        "'+cap+'",').encode()))
        self.assertEqual({'device_fixes126_capability': CAPABILITY}, self.metadata(patch, rpc_source()))
        for version,field,cap in PRIOR_BINDINGS:
            self.assertEqual({field:cap},
                getattr(module('apply_ngg2'), 'device_fixes'+str(version)+'_metadata')(patch, rpc_source()))

    def test_sealing_requires_one_real_uncommented_126_array_entry(self):
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
            with self.subTest(patch=raw_patch, rpc=rpc), self.assertRaisesRegex(ValueError, 'device_fixes126'):
                self.metadata(raw_patch, rpc)
        self.assertEqual({'device_fixes126_capability': CAPABILITY}, self.metadata(patch, rpc_source()))
        self.assertEqual({}, self.metadata(b'// old patch\n', rpc_source(declared=False)))

    def test_package_has_separate_126_field_and_unchanged_prior_API_and_profile(self):
        with tempfile.TemporaryDirectory() as temporary:
            upstream, driver, _ = self.fixture(Path(temporary))
            report = module('verify_package').inspect_native_sources(upstream, driver)
            self.assertEqual(CAPABILITY, report.get('device_fixes126_capability'))
            for _version,field,cap in PRIOR_BINDINGS:
                self.assertEqual(cap, report[field])
            self.assertEqual(('1.98.16-ngg2', 'necrogold_native_v15', 3),
                (report['api_version'], report['client_capability'], report['compiler_profile_version']))

    def test_resealed_mismatched_126_metadata_patch_or_rpc_is_rejected(self):
        faults = ({'metadata': None}, {'metadata': 'wrong'}, {'declared': False}, {'patch_declared': False},
            {'block_comment': 'entry'}, {'block_comment': 'nested'}, {'block_comment': 'array'})
        for fault in faults:
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as temporary:
                upstream, driver, _ = self.fixture(Path(temporary), **fault)
                # The retained120 prerequisite rejects block delimiters first.
                error = 'device_fixes120' if 'block_comment' in fault else 'device_fixes126'
                with self.assertRaisesRegex(ValueError, error):
                    module('verify_package').inspect_native_sources(upstream, driver)

    def test_historical_125_manifest_gets_no_unrequested_126_field(self):
        with tempfile.TemporaryDirectory() as temporary:
            upstream, driver, _ = self.fixture(Path(temporary), declared=False, metadata=None, patch_declared=False)
            report = module('verify_package').inspect_native_sources(upstream, driver)
            self.assertNotIn('device_fixes126_capability', report)
            for _version,field,cap in PRIOR_BINDINGS:
                self.assertEqual(cap, report[field])

    def test_126_cannot_bypass_the_existing_125_package_binding(self):
        with tempfile.TemporaryDirectory() as temporary:
            upstream, driver, manifest = self.fixture(Path(temporary))
            del manifest['device_fixes125_capability']
            (driver/'patches/loopctrl/ngg2-manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'device_fixes125'):
                module('verify_package').inspect_native_sources(upstream, driver)


class DeviceHostSelection126Tests(unittest.TestCase):
    def inventory(self):
        host = module('run_test126_host')
        names = sorted(host.EXPECTED_NATIVE_CHANGES) + ['retained-'+str(n) for n in range(35)]
        before = {name: 'before-'+name for name in names}
        current = dict(before)
        for name in host.EXPECTED_NATIVE_CHANGES:
            current[name] = 'after-'+name
        return host, before, current

    def test_native_inventory_accepts_only_spool_and_rpc_changes_among_all37(self):
        host, before, current = self.inventory()
        self.assertEqual({'LoopCtrlKit/RPCMethod.swift', 'LoopCtrlUITests/NG2CycleSpool.swift'},
            set(host.EXPECTED_NATIVE_CHANGES))
        changed, added = host.native_inventory(before, current)
        self.assertEqual(set(host.EXPECTED_NATIVE_CHANGES), changed)
        self.assertEqual(set(), added)

    def test_native_inventory_rejects_missing_added_or_unrelated_sources(self):
        host, before, current = self.inventory()
        mutations = (dict(current, extra='new'), {k:v for k,v in current.items() if k != 'retained-0'},
            dict(current, **{'retained-0': 'unrelated'}), dict(before))
        for mutated in mutations:
            with self.subTest(native_sources=len(mutated)), self.assertRaises(ValueError):
                host.native_inventory(before, mutated)

    def test_api16_profile3_and_all_historical_caps_remain_required(self):
        host = module('run_test126_host')
        self.assertEqual(('1.98.16-ngg2', 'necrogold_native_v15', 3),
            tuple(host.EXPECTED_API[key] for key in ('api_version', 'client_capability', 'compiler_profile_version')))
        self.assertEqual(CAPABILITY, host.EXPECTED_API['device_fixes126_capability'])
        for _version, field, cap in PRIOR_BINDINGS:
            self.assertEqual(cap, host.EXPECTED_API[field])
        self.assertEqual('initial_restart', host.EXPECTED_API['initial_restart_start_flag'])

    def test_pending_author_scope_fails_closed(self):
        from unittest.mock import patch
        host = module('run_test126_host')
        for fields in ({'SCOPE_FINALIZED': False}, {'PENDING_SCOPE_ITEMS': ('unfrozen',)},
                {'EXPECTED_SELECTED_METHOD_COUNT': 0}):
            with self.subTest(fields=fields), patch.multiple(host, **fields), self.assertRaises(ValueError):
                host.ensure_scope()

    def test_python39_selects_exact_new14_startup14_and_direct19(self):
        client = module('run_test126_python39')
        self.assertTrue(client.SCOPE_FINALIZED)
        self.assertEqual((), client.PENDING_SCOPE_ITEMS)
        self.assertEqual(47, client.EXPECTED_SELECTED_METHOD_COUNT)
        self.assertEqual([14, 14, 11, 8], [len(row[3]) for row in client.CASES])
        self.assertEqual(['tests.test_continuous_client126', 'tests.test_campaign_startup125',
            'tests.test_continuous_client125', 'tests.test_continuous_client116'], [row[0] for row in client.CASES])
        self.assertEqual(47, len({row[0]+'.'+method for row in client.CASES for method in row[3]}))

    def test_126_receipts_cannot_overwrite_125_or_each_other(self):
        host = module('run_test126_host')
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            sentinel = b'{"source_bound_host_receipt":true}\n'
            (output/'test126-host-scope.json').write_bytes(sentinel)
            for name in ('test125-host-scope.json', 'test125-python39-scope.json', '../test126-host-scope.json',
                    '/tmp/test126-host-scope.json', '', None, 0):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    host.run_scope('bad', [], output, {}, receipt_name=name)
            host.run_scope('client', [unittest.FunctionTestCase(lambda: None)], output, {},
                receipt_name='test126-python39-scope.json')
            self.assertEqual(sentinel, (output/'test126-host-scope.json').read_bytes())
            self.assertEqual(1, json.loads((output/'test126-python39-scope.json').read_bytes())['client']['tests_run'])

    def test_standalone_workflow_has_narrow_push_and_standard_runner_scope(self):
        source = (HERE.parents[1]/'.github/workflows/test126-startup-memory.yml').read_text()
        self.assertIn('branches: [work/test126-startup-memory]', source)
        self.assertIn('paths: [.github/workflows/test126-startup-memory.yml]', source)
        self.assertIn('  workflow_dispatch:', source)
        self.assertEqual(1, source.count('runs-on: ubuntu-latest'))
        self.assertEqual(1, source.count('runs-on: macos-26'))
        self.assertIn('contents: read', source)
        self.assertNotIn('contents: write', source)
        self.assertNotIn('run_test125_host.py driver', source)
        self.assertNotIn('check_ngg2.py', source)
        self.assertNotIn('check_runtime', source)
        self.assertNotIn('--baseline-only', source)
        for name in ('loopctrl-ngg2-native-host', 'loopctrl-ngg2-unsigned', 'loopctrl-ngg2-validation'):
            self.assertIn('name: '+name, source)

    def test_actual_build_profile_and_distinct_app_number_are_required(self):
        source = (HERE.parents[1]/'.github/workflows/test126-startup-memory.yml').read_text()
        self.assertEqual(1, source.count('app_build_number=$((1000 + GITHUB_RUN_NUMBER))'))
        self.assertIn('CURRENT_PROJECT_VERSION=$APP_BUILD_NUMBER', source)
        self.assertNotIn('CURRENT_PROJECT_VERSION=$GITHUB_RUN_NUMBER', source)
        self.assertIn('ci_run_number=int(os.environ[\'GITHUB_RUN_NUMBER\'])', source)
        self.assertIn('app_build_number=app_build', source)
        self.assertIn('check_perception_build.py --project --profile-version 3 upstream', source)
        self.assertIn('check_perception_build.py --compile-profile --profile-version 3 upstream', source)
        self.assertIn('verify_package.py upstream driver upstream/release/LoopCtrl.ipa', source)
        self.assertIn('check_cycle_spool126.py "$RUNNER_TEMP/test126-spool"', source)
        self.assertIn("if len(rows) != 9", source)


if __name__ == '__main__':
    unittest.main()
