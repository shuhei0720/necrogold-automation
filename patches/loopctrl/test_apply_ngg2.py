"""NG-G2の既存ソース・追加ソースを一緒に検証し、失敗では変更しない。"""
import difflib
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ngg2_applier', HERE / 'apply_ngg2.py')
applier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(applier)
verify_spec = importlib.util.spec_from_file_location('ngg2_verify', HERE / 'verify_package.py')
verifier = importlib.util.module_from_spec(verify_spec)
verify_spec.loader.exec_module(verifier)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


class NGG2ApplyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'upstream'
        self.root.mkdir()
        self.assets = Path(self.temp.name) / 'assets'
        self.assets.mkdir()
        self.name = 'LoopCtrlUITests/ActionHandler.swift'
        self.added = 'LoopCtrlUITests/NG2Runtime.swift'
        self.old = b'let version = "ngg1"\n'
        self.new = b'let version = "ngg2"\n'
        target = self.root / self.name
        target.parent.mkdir()
        target.write_bytes(self.old)
        (self.root / 'untouched.txt').write_text('preserve\n')
        self.extra = b'''// native fixture
    private func response(_ run: NG2Run) -> [String: JSONValue] {
        return ["api_version": .string("1.98.15-ngg2"), "report": .object(report)]
    }
    private func historical(_ snapshot: [String: JSONValue]) -> [String: JSONValue] {
        return snapshot
    }
'''
        (self.assets / 'NG2Runtime.swift').write_bytes(self.extra)
        self.patch_path = Path(self.temp.name) / 'ngg2.patch'
        self.patch_path.write_text(''.join(difflib.unified_diff(
            self.old.decode().splitlines(True), self.new.decode().splitlines(True),
            fromfile='a/' + self.name, tofile='b/' + self.name)))
        self.manifest = {
            'format_version': 1,
            'patch_sha256': sha(self.patch_path.read_bytes()),
            'files': {self.name: {'sha256': sha(self.old), 'blob': blob(self.old),
                                  'patched_sha256': sha(self.new)}},
            'additions': {self.added: {'source': 'NG2Runtime.swift', 'sha256': sha(self.extra)}},
        }

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes()
                for p in self.root.rglob('*') if p.is_file()}

    def apply(self):
        return applier.apply(self.root, self.manifest, self.patch_path, self.assets)

    def rejected(self, pattern=None):
        before = self.snapshot()
        with self.assertRaises((ValueError, OSError)) as caught:
            self.apply()
        if pattern:
            self.assertIn(pattern, str(caught.exception))
        self.assertEqual(before, self.snapshot())

    def test_changed_and_new_source_install_together(self):
        self.apply()
        self.assertEqual((self.root / self.name).read_bytes(), self.new)
        self.assertEqual((self.root / self.added).read_bytes(), self.extra)
        self.assertEqual((self.root / 'untouched.txt').read_text(), 'preserve\n')

    def test_last_asset_hash_mismatch_writes_nothing(self):
        (self.assets / 'NG2Runtime.swift').write_bytes(b'changed\n')
        self.rejected('asset_hash')

    def test_source_hash_mismatch_writes_nothing(self):
        (self.root / self.name).write_bytes(b'wrong\n')
        self.rejected('source_hash')

    def test_patch_hash_mismatch_writes_nothing(self):
        self.patch_path.write_text(self.patch_path.read_text() + '\n')
        self.rejected('patch_hash')

    def test_wrong_output_hash_writes_nothing(self):
        self.manifest['files'][self.name]['patched_sha256'] = '0' * 64
        self.rejected('patched_hash')

    def test_double_application_writes_nothing(self):
        self.apply()
        self.rejected()

    def test_existing_destination_writes_nothing(self):
        (self.root / self.added).write_bytes(b'old native file\n')
        self.rejected('destination_exists')

    def test_truncated_patch_writes_nothing(self):
        self.patch_path.write_text(self.patch_path.read_text()[:-6])
        self.manifest['patch_sha256'] = sha(self.patch_path.read_bytes())
        self.rejected('patch_rejected')

    def test_unexpected_target_writes_nothing(self):
        self.patch_path.write_text(self.patch_path.read_text() +
            '--- /dev/null\n+++ b/unexpected.txt\n@@ -0,0 +1 @@\n+bad\n')
        self.manifest['patch_sha256'] = sha(self.patch_path.read_bytes())
        self.rejected('patch_target')

    def test_parent_path_addition_writes_nothing(self):
        self.manifest['additions']['../escape'] = self.manifest['additions'].pop(self.added)
        self.rejected('unsafe')

    def test_symlink_source_and_asset_are_rejected(self):
        src = self.assets / 'NG2Runtime.swift'
        real = self.assets / 'outside'
        src.rename(real)
        src.symlink_to(real)
        self.rejected('symlink')

    def test_symlink_destination_directory_is_rejected(self):
        directory = self.root / 'LoopCtrlUITests'
        outside = self.root.parent / 'outside'
        directory.rename(outside)
        directory.symlink_to(outside, target_is_directory=True)
        self.rejected('symlink')

    def test_symlink_original_source_is_rejected(self):
        source = self.root / self.name
        outside = self.root.parent / 'outside.swift'
        outside.write_bytes(self.old)
        source.unlink()
        source.symlink_to(outside)
        self.rejected('symlink')

    def test_unsealed_extra_native_source_is_rejected(self):
        (self.assets / 'NG2Extra.c').write_text('int extra;\n')
        self.rejected('asset_inventory')

    def test_objective_c_asset_is_supported(self):
        raw = b'// Objective-C capture bridge fixture\n'
        (self.assets / 'NG2CaptureBridge.m').write_bytes(raw)
        self.manifest['additions']['LoopCtrlUITests/NG2CaptureBridge.m'] = {
            'source': 'NG2CaptureBridge.m', 'sha256': sha(raw)}
        self.apply()
        self.assertEqual((self.root / 'LoopCtrlUITests/NG2CaptureBridge.m').read_bytes(), raw)

    def test_rpc_contract_overlay_is_installed_only_in_logic_tests(self):
        raw = b'// real RPC XCTest fixture\n'
        name = 'Tests/LoopCtrlKitTests/NG2RPCContractsTests.swift'
        (self.root / 'Tests/LoopCtrlKitTests').mkdir(parents=True)
        (self.assets / 'NG2RPCContractsTests.swift').write_bytes(raw)
        self.manifest['additions'][name] = {'source': 'NG2RPCContractsTests.swift', 'sha256': sha(raw)}
        self.apply()
        self.assertEqual((self.root / name).read_bytes(), raw)
        self.assertFalse((self.root / 'LoopCtrlUITests/NG2RPCContractsTests.swift').exists())

    def test_rpc_contract_overlay_cannot_enter_app_sources(self):
        raw = b'// test-only Swift\n'
        (self.assets / 'NG2RPCContractsTests.swift').write_bytes(raw)
        self.manifest['additions']['LoopCtrlUITests/NG2RPCContractsTests.swift'] = {
            'source': 'NG2RPCContractsTests.swift', 'sha256': sha(raw)}
        self.rejected('unsafe_addition')

    def test_install_failure_removes_added_and_restores_changed(self):
        original = applier.os.replace
        calls = 0
        def replace(src, dst):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('injected installation failure')
            return original(src, dst)
        before = self.snapshot()
        with patch.object(applier.os, 'replace', side_effect=replace):
            with self.assertRaises(OSError):
                self.apply()
        self.assertEqual(before, self.snapshot())

    def test_failure_after_addition_removes_it_and_restores_changed(self):
        raw = b'// header fixture\n'
        (self.assets / 'NG2Bridge.h').write_bytes(raw)
        self.manifest['additions']['LoopCtrlUITests/NG2Bridge.h'] = {
            'source': 'NG2Bridge.h', 'sha256': sha(raw)}
        original = applier.os.replace
        calls = 0
        def replace(src, dst):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise OSError('injected failure after native addition')
            return original(src, dst)
        before = self.snapshot()
        with patch.object(applier.os, 'replace', side_effect=replace):
            with self.assertRaises(OSError):
                self.apply()
        self.assertEqual(before, self.snapshot())

    def test_concurrent_original_edit_is_not_overwritten(self):
        run_patch = applier.run_patch
        def change_source(stage, raw):
            run_patch(stage, raw)
            (self.root / self.name).write_text('concurrent edit\n')
        with patch.object(applier, 'run_patch', side_effect=change_source):
            with self.assertRaisesRegex(ValueError, 'source_changed_during_staging'):
                self.apply()
        self.assertEqual((self.root / self.name).read_text(), 'concurrent edit\n')
        self.assertFalse((self.root / self.added).exists())

    def native_report_fixture(self):
        self.apply()
        driver = Path(self.temp.name) / 'driver'
        destination = driver / 'patches/loopctrl'
        destination.mkdir(parents=True)
        manifest = dict(self.manifest, upstream_commit=applier.UPSTREAM_COMMIT,
                        api_version='1.98.15-ngg2', capability='necrogold_native_v1')
        import json
        (destination / 'ngg2-manifest.json').write_text(json.dumps(manifest))
        (destination / 'ngg2.patch').write_bytes(self.patch_path.read_bytes())
        return driver

    def test_package_provenance_records_all_native_sources(self):
        driver = self.native_report_fixture()
        report = verifier.inspect_native_sources(self.root, driver)
        self.assertEqual(set(report['native_source_sha256']), {self.name, self.added})
        self.assertEqual(report['capability'], 'necrogold_native_v1')

    def test_package_provenance_records_required_client_capability(self):
        import json
        driver = self.native_report_fixture()
        path = driver / 'patches/loopctrl/ngg2-manifest.json'
        manifest = json.loads(path.read_text())
        manifest['client_capability'] = 'necrogold_native_v6'
        path.write_text(json.dumps(manifest))
        report = verifier.inspect_native_sources(self.root, driver)
        self.assertEqual('necrogold_native_v6', report.get('client_capability'))

    def test_package_provenance_records_native_v8_with_strict_profile_v2(self):
        import json
        driver = self.native_report_fixture()
        path = driver / 'patches/loopctrl/ngg2-manifest.json'
        manifest = json.loads(path.read_text())
        manifest['client_capability'] = 'necrogold_native_v8'
        path.write_text(json.dumps(manifest))
        accepted = None
        try:
            accepted = verifier.inspect_native_sources(self.root, driver)
        except ValueError:
            pass
        self.assertIsNotNone(accepted, 'native_v8_package_is_supported')
        self.assertEqual('necrogold_native_v8', accepted['client_capability'])

    def test_package_provenance_records_native_v9_with_strict_profile_v2(self):
        import json
        driver = self.native_report_fixture()
        path = driver / 'patches/loopctrl/ngg2-manifest.json'
        manifest = json.loads(path.read_text())
        manifest['client_capability'] = 'necrogold_native_v9'
        path.write_text(json.dumps(manifest))
        accepted = None
        try:
            accepted = verifier.inspect_native_sources(self.root, driver)
        except ValueError:
            pass
        self.assertIsNotNone(accepted, 'native_v9_package_is_supported')
        self.assertEqual('necrogold_native_v9', accepted['client_capability'])
        self.assertEqual(2, verifier.required_native_profile(accepted['client_capability']))

    def test_package_provenance_records_native_v10_with_strict_profile_v2(self):
        import json
        driver = self.native_report_fixture()
        path = driver / 'patches/loopctrl/ngg2-manifest.json'
        manifest = json.loads(path.read_text())
        manifest['client_capability'] = 'necrogold_native_v10'
        path.write_text(json.dumps(manifest))
        accepted = None
        try:
            accepted = verifier.inspect_native_sources(self.root, driver)
        except ValueError:
            pass
        self.assertIsNotNone(accepted, 'native_v10_package_is_supported')
        self.assertEqual('necrogold_native_v10', accepted['client_capability'])
        self.assertEqual(2, verifier.required_native_profile(accepted['client_capability']))

    def test_package_provenance_records_native_v11_with_strict_profile_v2(self):
        import json
        driver = self.native_report_fixture()
        path = driver / 'patches/loopctrl/ngg2-manifest.json'
        manifest = json.loads(path.read_text())
        manifest['client_capability'] = 'necrogold_native_v11'
        path.write_text(json.dumps(manifest))
        accepted = None
        try:
            accepted = verifier.inspect_native_sources(self.root, driver)
        except ValueError:
            pass
        self.assertIsNotNone(accepted, 'native_v11_package_is_supported')
        self.assertEqual('necrogold_native_v11', accepted['client_capability'])
        self.assertEqual(2, verifier.required_native_profile(accepted['client_capability']))

    def test_package_provenance_records_native_v12_with_strict_profile_v2(self):
        import json
        driver = self.native_report_fixture()
        path = driver / 'patches/loopctrl/ngg2-manifest.json'
        manifest = json.loads(path.read_text())
        manifest['client_capability'] = 'necrogold_native_v12'
        path.write_text(json.dumps(manifest))
        accepted = None
        try:
            accepted = verifier.inspect_native_sources(self.root, driver)
        except ValueError:
            pass
        self.assertIsNotNone(accepted, 'native_v12_package_is_supported')
        self.assertEqual('necrogold_native_v12', accepted['client_capability'])
        self.assertEqual(2, verifier.required_native_profile(accepted['client_capability']))

    def test_package_profile_version_preserves_old_and_current_capabilities(self):
        for version in range(1, 14):
            with self.subTest(capability=version):
                expected = None if version < 6 else (1 if version == 6 else 2)
                self.assertEqual(expected, verifier.required_native_profile('necrogold_native_v'+str(version)))

    def test_package_provenance_records_native_v13_with_strict_profile_v2(self):
        import json
        driver = self.native_report_fixture()
        path = driver / 'patches/loopctrl/ngg2-manifest.json'
        manifest = json.loads(path.read_text())
        manifest['client_capability'] = 'necrogold_native_v13'
        path.write_text(json.dumps(manifest))
        accepted = None
        try:
            accepted = verifier.inspect_native_sources(self.root, driver)
        except ValueError:
            pass
        self.assertIsNotNone(accepted, 'native_v13_package_is_supported')
        self.assertEqual('necrogold_native_v13', accepted['client_capability'])
        self.assertEqual(2, verifier.required_native_profile(accepted['client_capability']))

    def test_package_provenance_preserves_native_v3_client_capability(self):
        import json
        driver = self.native_report_fixture()
        path = driver / 'patches/loopctrl/ngg2-manifest.json'
        manifest = json.loads(path.read_text())
        manifest['client_capability'] = 'necrogold_native_v3'
        path.write_text(json.dumps(manifest))
        report = verifier.inspect_native_sources(self.root, driver)
        self.assertEqual('necrogold_native_v3', report.get('client_capability'))

    def test_package_provenance_preserves_previous_client_capability(self):
        import json
        driver = self.native_report_fixture()
        path = driver / 'patches/loopctrl/ngg2-manifest.json'
        manifest = json.loads(path.read_text())
        manifest['client_capability'] = 'necrogold_native_v2'
        path.write_text(json.dumps(manifest))
        report = verifier.inspect_native_sources(self.root, driver)
        self.assertEqual('necrogold_native_v2', report.get('client_capability'))

    def test_package_provenance_rejects_unknown_client_capability(self):
        import json
        driver = self.native_report_fixture()
        path = driver / 'patches/loopctrl/ngg2-manifest.json'
        manifest = json.loads(path.read_text())
        manifest['client_capability'] = 'unknown'
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'native_manifest_identity'):
            verifier.inspect_native_sources(self.root, driver)

    def test_package_provenance_rejects_previous_api_for_current_build(self):
        import json
        driver = self.native_report_fixture()
        path = driver / 'patches/loopctrl/ngg2-manifest.json'
        manifest = json.loads(path.read_text())
        manifest['api_version'] = '1.98.14-ngg2'
        manifest['client_capability'] = 'necrogold_native_v13'
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'native_manifest_identity'):
            verifier.inspect_native_sources(self.root, driver)

    def test_package_provenance_rejects_even_resealed_stale_runtime_envelope_api(self):
        import json
        driver = self.native_report_fixture()
        path = driver / 'patches/loopctrl/ngg2-manifest.json'
        manifest = json.loads(path.read_text())
        manifest['client_capability'] = 'necrogold_native_v13'
        runtime = self.root / self.added
        stale = runtime.read_bytes().replace(b'1.98.15-ngg2', b'1.98.14-ngg2')
        stale += b'// unrelated expected version: 1.98.15-ngg2\n'
        runtime.write_bytes(stale)
        manifest['additions'][self.added]['sha256'] = sha(stale)
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'native_runtime_response_api'):
            verifier.inspect_native_sources(self.root, driver)

    def test_package_provenance_rejects_changed_native_source(self):
        driver = self.native_report_fixture()
        (self.root / self.added).write_text('changed after sealed installation\n')
        with self.assertRaisesRegex(ValueError, 'native_source_hash'):
            verifier.inspect_native_sources(self.root, driver)


if __name__ == '__main__':
    unittest.main()
