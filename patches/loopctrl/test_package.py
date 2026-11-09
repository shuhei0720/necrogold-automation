import importlib.util
import hashlib
import json
from pathlib import Path
import plistlib
import shlex
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile


HERE = Path(__file__).resolve().parent


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class PackageTests(unittest.TestCase):
    def inspect(self, missing=None, profile=False, wrong_id=False):
        spec = importlib.util.spec_from_file_location('verify_package', Path(__file__).with_name('verify_package.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        base = 'Payload/LoopCtrlAllInOne.app/'
        plugin = base + 'PlugIns/LoopCtrlUITests.xctest/'
        entries = {
            base+'Info.plist': plistlib.dumps({'CFBundleIdentifier':'top.ebato.loopctrl', 'CFBundleExecutable':'LoopCtrlAllInOne', 'CFBundleShortVersionString':'0.3.4', 'CFBundleVersion':'1'}),
            base+'LoopCtrlAllInOne': b'fixture-main',
            plugin+'Info.plist': plistlib.dumps({'CFBundleIdentifier':'wrong' if wrong_id else 'top.ebato.loopctrl', 'CFBundleExecutable':'LoopCtrlUITests'}),
            plugin+'LoopCtrlUITests': b'fixture-runner',
            plugin+'loopctrl': b'fixture-cli',
        }
        if missing:
            del entries[plugin+missing]
        if profile:
            entries[plugin+'embedded.mobileprovision'] = b'fixture-profile'
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'fixture.ipa'
            with zipfile.ZipFile(path, 'w') as archive:
                for name, data in entries.items():
                    archive.writestr(name, data)
            return module.inspect_ipa(path)

    def test_complete_package(self):
        self.assertEqual(self.inspect()['bundle_id'], 'top.ebato.loopctrl')

    def test_missing_cli(self):
        with self.assertRaisesRegex(ValueError, 'missing_or_empty'):
            self.inspect(missing='loopctrl')

    def test_missing_test_binary(self):
        with self.assertRaisesRegex(ValueError, 'missing_or_empty'):
            self.inspect(missing='LoopCtrlUITests')

    def test_nested_profile_rejected(self):
        with self.assertRaisesRegex(ValueError, 'provisioning_profile'):
            self.inspect(profile=True)

    def test_plugin_identity_must_match(self):
        with self.assertRaisesRegex(ValueError, 'bundle_id_mismatch'):
            self.inspect(wrong_id=True)


class NativePackageProfileTests(unittest.TestCase):
    """Exercise package writing with sealed sources and real profile validation."""

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='native-package-profile-')
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.upstream = self.base / 'upstream'
        self.driver = self.base / 'driver'
        self.patchdir = self.driver / 'patches/loopctrl'
        self.patchdir.mkdir(parents=True)
        self.sources = self.upstream / 'LoopCtrlUITests'
        self.sources.mkdir(parents=True)
        self.package = load_module('native_package', 'verify_package.py')
        self.checker = load_module('native_package_build_checker', 'check_perception_build.py')
        self.ipa = self.base / 'app.ipa'
        self.report_path = self.base / 'build-manifest.json'
        (self.patchdir / 'ngg2.patch').write_text('fixture patch\n')
        self.manifest = {
            'upstream_commit': self.checker.UPSTREAM,
            'api_version': '1.98.15-ngg2',
            'capability': 'necrogold_native_v1',
            'client_capability': 'necrogold_native_v7',
            'patch_sha256': self.checker.digest((self.patchdir / 'ngg2.patch').read_bytes()),
            'files': {}, 'additions': {},
        }
        for name in self.checker.NATIVE_C:
            raw = ('/* package proof ' + name + ' */\n').encode()
            (self.sources / name).write_bytes(raw)
            self.manifest['additions']['LoopCtrlUITests/' + name] = {
                'sha256': hashlib.sha256(raw).hexdigest(), 'source': name}
        self.write_manifest()

    def write_manifest(self):
        (self.patchdir / 'ngg2-manifest.json').write_text(json.dumps(self.manifest))

    def enable_native_v13(self):
        raw = b'''    private func response(_ run: NG2Run) -> [String: JSONValue] {
        return ["api_version": .string("1.98.15-ngg2"), "report": .object(report)]
    }
    private func historical(_ snapshot: [String: JSONValue]) -> [String: JSONValue] {
        return snapshot
    }
'''
        (self.sources / 'NG2Runtime.swift').write_bytes(raw)
        self.manifest['additions']['LoopCtrlUITests/NG2Runtime.swift'] = {
            'source': 'NG2Runtime.swift', 'sha256': hashlib.sha256(raw).hexdigest()}
        self.manifest['client_capability'] = 'necrogold_native_v13'
        self.write_manifest()

    def write_profile(self, version):
        strict_sources = {'NG2Perception.c'}
        if version == 2:
            strict_sources.add('NG2Navigation.c')
        objects = {
            'ROOT': {'isa': 'PBXGroup', 'path': '', 'sourceTree': 'SOURCE_ROOT',
                     'children': []},
            'TARGET': {'isa': 'PBXNativeTarget', 'name': self.checker.TARGET,
                       'buildPhases': ['SOURCES']},
            'SOURCES': {'isa': 'PBXSourcesBuildPhase', 'files': []},
        }
        commands = []
        for index, name in enumerate(self.checker.NATIVE_C):
            ref, build = 'REF' + str(index), 'BUILD' + str(index)
            objects['ROOT']['children'].append(ref)
            objects['SOURCES']['files'].append(build)
            objects[ref] = {'isa': 'PBXFileReference',
                            'path': 'LoopCtrlUITests/' + name,
                            'sourceTree': 'SOURCE_ROOT'}
            objects[build] = {'isa': 'PBXBuildFile', 'fileRef': ref}
            if name in strict_sources:
                objects[build]['settings'] = {'COMPILER_FLAGS': list(self.checker.FLAGS)}
            flags = list(self.checker.FLAGS) if name in strict_sources else ['-O0']
            output = self.upstream / ('build/LoopCtrl.build/Debug-iphoneos/'
                'LoopCtrlUITests.build/Objects-normal/arm64/' + Path(name).stem + '.o')
            commands.append(shlex.join(['/usr/bin/clang', '-target', 'arm64-apple-ios16.0',
                *flags, '-c', str(self.sources / name), '-o', str(output)]))
        for module in sorted(self.checker.SWIFT_TARGETS):
            commands.append(shlex.join(['/usr/bin/swiftc', '-module-name', module,
                '-target', 'arm64-apple-ios16.0', '-Onone']))
        project_path = self.upstream / 'LoopCtrl.xcodeproj/project.pbxproj'
        project_path.parent.mkdir(exist_ok=True)
        project_path.write_text(json.dumps({'objects': objects}))
        log = self.base / 'build.log'
        log.write_text('\n'.join(commands) + '\n')
        # The PBX graph itself is validated normally; only Apple's plutil
        # serialization adapter is replaced for this portable host fixture.
        with patch.object(self.checker, 'read_project', side_effect=lambda path: json.loads(Path(path).read_text())):
            profile = self.checker.inspect_compile_log(
                self.upstream, log, self.base / 'proof', profile_version=version)
        self.save_profile(profile)
        return profile

    def save_profile(self, profile):
        path = self.upstream / 'release/native-perception-profile.json'
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(profile))

    def run_package(self):
        with patch.dict(sys.modules, {'check_perception_build': self.checker}), \
                patch.object(sys, 'argv', ['verify_package.py', str(self.upstream),
                                          str(self.driver), str(self.ipa)]), \
                patch.object(self.package, 'inspect_ipa', return_value={'ipa_sha256': '1' * 64}), \
                patch.object(self.package, 'command', return_value=self.checker.UPSTREAM), \
                patch.object(self.checker, 'read_project', side_effect=lambda path: json.loads(Path(path).read_text())), \
                patch('builtins.print'):
            self.package.main()
        return json.loads(self.report_path.read_text())

    def test_native_v7_manifest_identity_is_supported(self):
        result = self.package.inspect_native_sources(self.upstream, self.driver)
        self.assertEqual(result['client_capability'], 'necrogold_native_v7')
        self.assertEqual(len(result['native_source_sha256']), 4)

    def test_native_v7_package_requires_compiler_proof_before_writing(self):
        # The sealed identity is independently verified by the prior test.
        # This isolates the actual package callsite from its identity guard.
        with patch.object(self.package, 'inspect_native_sources', return_value={
                'client_capability': 'necrogold_native_v7'}):
            with self.assertRaisesRegex(ValueError, 'compile_profile_missing'):
                self.run_package()
        self.assertFalse(self.report_path.exists())

    def test_native_v6_package_preserves_fully_validated_legacy_profile(self):
        self.manifest['client_capability'] = 'necrogold_native_v6'
        self.write_manifest()
        profile = self.write_profile(1)
        result = self.run_package()
        self.assertEqual(result['perception_build_profile'], profile)
        self.assertEqual(profile['other_c_profiles']['NG2Navigation.c'][0]['optimization'], '-O0')

    def test_native_v7_package_requires_version_two_even_when_legacy_proof_is_valid(self):
        self.write_profile(1)
        with self.assertRaises(self.checker.ProfileError):
            self.run_package()
        self.assertFalse(self.report_path.exists())

    def test_native_v7_package_writes_both_strict_source_proofs(self):
        profile = self.write_profile(2)
        result = self.run_package()
        self.assertEqual(result['perception_build_profile'], profile)
        self.assertEqual(profile['format_version'], 2)
        self.assertEqual(profile['perception_compiles'][0]['optimization'], '-O2')
        self.assertEqual(profile['navigation_compiles'][0]['optimization'], '-O2')

    def test_native_v13_package_requires_compiler_proof_before_writing(self):
        self.enable_native_v13()
        with self.assertRaisesRegex(self.checker.ProfileError, 'compile_profile_missing'):
            self.run_package()
        self.assertFalse(self.report_path.exists())

    def test_native_v13_package_rejects_valid_legacy_profile(self):
        self.enable_native_v13()
        self.write_profile(1)
        with self.assertRaises(self.checker.ProfileError):
            self.run_package()
        self.assertFalse(self.report_path.exists())

    def test_native_v13_package_writes_both_strict_source_proofs(self):
        self.enable_native_v13()
        profile = self.write_profile(2)
        result = self.run_package()
        self.assertEqual(result['client_capability'], 'necrogold_native_v13')
        self.assertEqual(result['perception_build_profile'], profile)
        self.assertEqual(profile['format_version'], 2)
        self.assertEqual(profile['perception_compiles'][0]['optimization'], '-O2')
        self.assertEqual(profile['navigation_compiles'][0]['optimization'], '-O2')

    def test_native_v6_package_rechecks_tampered_legacy_navigation_arguments(self):
        self.manifest['client_capability'] = 'necrogold_native_v6'
        self.write_manifest()
        profile = self.write_profile(1)
        row = profile['other_c_profiles']['NG2Navigation.c'][0]
        for key in ('arguments', 'raw_arguments'):
            row[key].append('-ffast-math')
        self.save_profile(profile)
        with self.assertRaisesRegex(self.checker.ProfileError, 'unsafe_fp_option'):
            self.run_package()
        self.assertFalse(self.report_path.exists())

    def test_native_v7_package_rechecks_tampered_navigation_effective_optimization(self):
        profile = self.write_profile(2)
        row = profile['navigation_compiles'][0]
        for key in ('arguments', 'raw_arguments'):
            row[key].append('-O0')
        row['optimization'] = '-O0'
        self.save_profile(profile)
        with self.assertRaisesRegex(self.checker.ProfileError, 'effective_optimization'):
            self.run_package()
        self.assertFalse(self.report_path.exists())

    def test_native_v7_package_rechecks_profile_source_hash(self):
        profile = self.write_profile(2)
        profile['navigation_compiles'][0]['source_sha256'] = '0' * 64
        self.save_profile(profile)
        with self.assertRaises(self.checker.ProfileError):
            self.run_package()
        self.assertFalse(self.report_path.exists())

    def test_earlier_capabilities_preserve_package_behavior_without_compiler_profile(self):
        for version in range(1, 6):
            with self.subTest(version=version):
                self.manifest['client_capability'] = 'necrogold_native_v' + str(version)
                self.write_manifest()
                result = self.run_package()
                self.assertNotIn('perception_build_profile', result)


if __name__ == '__main__':
    unittest.main()
