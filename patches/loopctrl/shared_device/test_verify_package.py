"""Synthetic Git/ZIP/Mach-O package contracts; not an iPhone acceptance."""
import hashlib
import importlib.util
import copy
import contextlib
import io
from pathlib import Path
import plistlib
import struct
import subprocess
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('new8_package', HERE / 'verify_package.py')
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


def macho(payload, *, kind=2, identity=b'public-fixture!!', padding=0):
    # Real 64-bit little-endian Mach-O command/section structure, synthetic code.
    start = 32 + 24 + 24 + 152 + padding
    uuid = struct.pack('<II16s', 0x1b, 24, identity)
    platform = struct.pack('<IIIIII', 0x32, 24, 2, 0x100000, 0x100000, 0)
    segment = struct.pack('<II16sQQQQiiII', 0x19, 152, b'__TEXT', 0, len(payload),
                          start, len(payload), 7, 5, 1, 0)
    section = struct.pack('<16s16sQQIIIIIIII', b'__cstring', b'__TEXT', 0, len(payload),
                          start, 0, 0, 0, 0, 0, 0, 0)
    return struct.pack('<IIIIIIII', 0xfeedfacf, 0x100000c, 0, kind, 3, 200, 0, 0) + uuid + platform + segment + section + b'\0' * padding + payload


def with_dylib(raw, name):
    text = name.encode() + b'\0'; length = (24 + len(text) + 7) // 8 * 8
    command = struct.pack('<IIIIII', 0xc, length, 24, 0, 0, 0) + text + b'\0' * (length - 24 - len(text))
    header = bytearray(raw[:32]); struct.pack_into('<II', header, 16, 4, 200 + length)
    commands = bytearray(raw[32:232])
    struct.pack_into('<Q', commands, 48 + 40, 232 + length)
    struct.pack_into('<I', commands, 48 + 72 + 48, 232 + length)
    return bytes(header) + bytes(commands) + command + raw[232:]


def with_adhoc_signature(raw):
    # Consume pre-existing 16-byte header padding; code/section layout is fixed.
    directory = struct.pack('>11I', 0xfade0c02, 44, 0x20000, 2, 0, 0, 0, 0, 0, 0, 0)
    signature = struct.pack('>IIIII', 0xfade0cc0, 20 + len(directory), 1, 0, 20) + directory
    header = bytearray(raw[:32]); struct.pack_into('<II', header, 16, 4, 216)
    alignment = b'\0' * (-len(raw) % 16)
    return bytes(header) + raw[32:232] + struct.pack('<IIII', 0x1d, 16, len(raw) + len(alignment), len(signature)) + raw[248:] + alignment + signature


def with_symbol(raw, symbol):
    oldsize = struct.unpack_from('<I', raw, 20)[0]; oldend = 32 + oldsize
    strings = b'\0' + symbol.encode() + b'\0'; payload = raw[oldend:]
    symoff = oldend + 24 + len(payload); stroff = symoff + 16
    command = struct.pack('<IIIIII', 0x2, 24, symoff, 1, stroff, len(strings))
    header = bytearray(raw[:32]); struct.pack_into('<II', header, 16, 4, oldsize + 24)
    commands = bytearray(raw[32:oldend])
    struct.pack_into('<Q', commands, 48 + 40, oldend + 24)
    struct.pack_into('<I', commands, 48 + 72 + 48, oldend + 24)
    return bytes(header) + bytes(commands) + command + payload + struct.pack('<IBBHQ', 1, 1, 0, 0, 0) + strings


class ProbePackageTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='ng8-package-test-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.products = self.root / 'products'
        self.path = self.root / 'fixture.ipa'
        self.stamp = '2026-11-16 21:42'
        self.source_sha256 = 'a' * 64
        self.app = 'Payload/LoopCtrlAllInOne.app/'
        self.test = self.app + 'PlugIns/LoopCtrlUITests.xctest/'
        self.info = {'CFBundleIdentifier': 'top.ebato.loopctrl',
            'CFBundleExecutable': 'LoopCtrlAllInOne', 'CFBundleVersion': '900001',
            'CFBundleShortVersionString': '0.3.4',
            'NG2DeviceProfileBuild': 'shared-device-profile-v1',
            'NG2DeviceProfiles': 'iphone11-legacy,iphone8',
            'NG2DeviceProfileSourceSHA256': self.source_sha256}
        self.entries = {self.app + 'Info.plist': plistlib.dumps(self.info),
            self.app + 'LoopCtrlAllInOne': macho(self.stamp.encode()),
            self.test + 'Info.plist': plistlib.dumps(dict(self.info, CFBundleExecutable='LoopCtrlUITests')),
            self.test + 'LoopCtrlUITests': macho(self.stamp.encode(), kind=8),
            self.test + 'loopctrl': macho(b'public synthetic cli')}
        for name, raw in self.entries.items():
            target = self.products / name.removeprefix('Payload/')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)

    def write_ipa(self):
        with zipfile.ZipFile(self.path, 'w') as archive:
            for name, raw in self.entries.items():
                archive.writestr(name, raw)

    def inspect(self):
        self.write_ipa()
        return verifier.inspect_normal_ipa(self.path, build_number='900001',
            source_sha256=self.source_sha256, stamp=self.stamp, products=self.products)

    def test_actual_unsigned_bundle_binds_both_builds_markers_and_compiled_stamp(self):
        try:
            report = self.inspect()
        except ValueError:
            outcome = 'rejected'
        else:
            outcome = 'accepted'
            self.assertEqual('900001', report.get('build'))
            self.assertEqual(self.source_sha256, report['normal_build_markers']['NG2DeviceProfileSourceSHA256'])
            self.assertEqual(self.stamp, report['compiled_build_stamp'])
        self.assertEqual('accepted', outcome, 'a normal shared-device unsigned IPA must pass exact normal markers')

    def test_capture_only_bundle_keys_are_forbidden_in_a_normal_package(self):
        info = dict(self.info, NG8CaptureProbeBuild='ng8-capture-only-v1')
        self.entries[self.app + 'Info.plist'] = plistlib.dumps(info)
        with self.assertRaisesRegex(ValueError, 'capture_only_identity_forbidden'):
            self.inspect()

    def test_each_build_and_probe_marker_must_match_in_both_bundles(self):
        for bundle in (self.app, self.test):
            for key, bad in [('CFBundleVersion', '204'), ('NG2DeviceProfileBuild', True),
                             ('NG2DeviceProfiles', 'iPhone12,1'),
                             ('NG2DeviceProfileSourceSHA256', 'b' * 64)]:
                name = bundle + 'Info.plist'
                original = self.entries[name]
                with self.subTest(bundle=bundle, key=key):
                    info = plistlib.loads(original); info[key] = bad
                    self.entries[name] = plistlib.dumps(info)
                    with self.assertRaisesRegex(ValueError, 'normal_plist_identity'):
                        self.inspect()
                self.entries[name] = original

    def test_cli_identity_failure_emits_only_six_field_presence_type_and_match(self):
        sentinel = 'private-value-must-never-be-logged'
        name = self.app + 'Info.plist'
        info = plistlib.loads(self.entries[name])
        del info['CFBundleVersion']
        info['NG2DeviceProfiles'] = sentinel
        info['private_extra_field'] = sentinel
        self.entries[name] = plistlib.dumps(info)
        self.write_ipa()
        upstream = self.root / 'upstream'
        shutil.copytree(self.products, upstream / 'build/Build/Products/Debug-iphoneos')
        args = ['verify_package.py', str(upstream), str(self.root / 'driver'), str(self.path),
                '--build-log', str(self.root / 'log'), '--compiler-profile', str(self.root / 'profile'),
                '--build-number', '900001']
        sources = {'overlay_manifest_sha256': self.source_sha256, 'build_stamp': {'value': self.stamp}}
        output = io.StringIO()
        with patch.object(sys, 'argv', args), patch.object(verifier, 'inspect_sources', return_value=sources), \
                patch.object(verifier, 'inspect_compiler', return_value={}), contextlib.redirect_stdout(output):
            with self.assertRaisesRegex(ValueError, '^normal_plist_identity$'):
                verifier.main()
        self.assertTrue(output.getvalue().startswith('{'), 'CLI must emit the closed identity diagnostic')
        diagnostic = __import__('json').loads(output.getvalue())
        self.assertEqual('normal_plist_identity', diagnostic['code'])
        self.assertEqual('app', diagnostic['bundle_role'])
        self.assertEqual({'CFBundleIdentifier', 'CFBundleExecutable', 'CFBundleVersion',
                         'NG2DeviceProfileBuild', 'NG2DeviceProfiles', 'NG2DeviceProfileSourceSHA256'}, set(diagnostic['fields']))
        self.assertEqual({'present': False, 'type': 'missing', 'match': False}, diagnostic['fields']['CFBundleVersion'])
        self.assertEqual({'present': True, 'type': 'string', 'match': False}, diagnostic['fields']['NG2DeviceProfiles'])
        self.assertTrue(diagnostic['fields']['NG2DeviceProfileBuild']['match'])
        self.assertNotIn(sentinel, output.getvalue())
        self.assertNotIn('private_extra_field', output.getvalue())

    def test_ipa_executable_cannot_be_from_another_compilation(self):
        self.entries[self.app + 'LoopCtrlAllInOne'] = macho(self.stamp.encode() + b'wrong code')
        with self.assertRaisesRegex(ValueError, 'ipa_compiled_product_mismatch'):
            self.inspect()

    def test_stamp_must_be_in_compiled_section_not_only_an_app_resource(self):
        name = self.test + 'LoopCtrlUITests'
        wrong = macho(b'old compiler payload', kind=8) + self.stamp.encode()
        self.entries[name] = wrong
        (self.products / name.removeprefix('Payload/')).write_bytes(wrong)
        with self.assertRaisesRegex(ValueError, 'compiled_build_stamp_missing'):
            self.inspect()

    def test_private_profile_and_signing_key_are_rejected(self):
        for suffix in ('embedded.mobileprovision', 'private.p12'):
            name = self.test + suffix
            self.entries[name] = b'synthetic forbidden material'
            with self.subTest(suffix=suffix), self.assertRaisesRegex(ValueError, 'private_signing_material'):
                self.inspect()
            del self.entries[name]

    def test_wrong_macho_platform_is_rejected(self):
        name = self.app + 'LoopCtrlAllInOne'
        raw = bytearray(self.entries[name]); struct.pack_into('<I', raw, 32 + 24 + 8, 7)
        self.entries[name] = bytes(raw)
        with self.assertRaisesRegex(ValueError, 'macho_ios_identity'):
            self.inspect()

    def test_loader_metadata_is_bound_but_codesign_command_addition_is_allowed(self):
        name = self.app + 'LoopCtrlAllInOne'
        good = with_dylib(macho(self.stamp.encode()), '@rpath/GoodImage.dylib')
        evil = with_dylib(macho(self.stamp.encode()), '@rpath/EvilImage.dylib')
        self.entries[name] = evil
        (self.products / name.removeprefix('Payload/')).write_bytes(good)
        with self.assertRaisesRegex(ValueError, 'ipa_compiled_product_mismatch'):
            self.inspect()
        unsigned = macho(self.stamp.encode(), padding=16)
        self.entries[name] = with_adhoc_signature(unsigned)
        (self.products / name.removeprefix('Payload/')).write_bytes(unsigned)
        self.assertEqual('900001', self.inspect()['build'])

    def test_linkedit_symbol_payload_outside_sections_is_bound(self):
        name = self.app + 'LoopCtrlAllInOne'
        original = with_symbol(macho(self.stamp.encode()), '_GoodExternal')
        self.entries[name] = with_symbol(macho(self.stamp.encode()), '_EvilExternal')
        (self.products / name.removeprefix('Payload/')).write_bytes(original)
        with self.assertRaisesRegex(ValueError, 'ipa_compiled_product_mismatch'):
            self.inspect()


class SourceContracts(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='ng8-source-test-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def test_generator_form_and_only_literal_tracked_delta_are_accepted(self):
        value = '2026-11-16 21:42'
        expected = (verifier.STAMP_TEMPLATE % value).encode()
        self.assertEqual(value, verifier.generated_stamp(expected))
        for wrong in (expected + b'let injected = true\n', expected.replace(b'2026-11-16', b'2026-02-30'),
                      expected.replace(b'enum BuildStamp', b'enum OtherStamp')):
            with self.subTest(wrong=hashlib.sha256(wrong).hexdigest()), self.assertRaises(ValueError):
                verifier.generated_stamp(wrong)
        stamp = self.root / verifier.STAMP
        stamp.parent.mkdir(); stamp.write_bytes(b'old stamp')
        other = self.root / 'unexpected.swift'; other.write_bytes(b'original')
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        subprocess.run(['git', '-C', str(self.root), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.root), '-c', 'user.name=Fixture', '-c',
                        'user.email=fixture@example.invalid', 'commit', '-qm', 'public fixture'], check=True)
        stamp.write_bytes(expected)
        verifier.overlay._checkout_delta(self.root, (verifier.STAMP,))
        other.write_bytes(b'arbitrary tracked source')
        with self.assertRaisesRegex(ValueError, 'unexpected_checkout_delta'):
            verifier.overlay._checkout_delta(self.root, (verifier.STAMP,))

    def test_complete_git_inventory_and_post_commit_change_are_bound(self):
        file = self.root / 'source.swift'; file.write_bytes(b'public exact source')
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        subprocess.run(['git', '-C', str(self.root), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.root), '-c', 'user.name=Fixture', '-c',
                        'user.email=fixture@example.invalid', 'commit', '-qm', 'public fixture'], check=True)
        commit = subprocess.check_output(['git', '-C', str(self.root), 'rev-parse', 'HEAD'], text=True).strip()
        inventory = verifier.git_inventory(self.root, commit)
        self.assertEqual({'source.swift'}, set(inventory))
        self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(), verifier.verify_tree(self.root, inventory)['source.swift'])
        file.write_bytes(b'stale or changed source')
        with self.assertRaisesRegex(ValueError, 'complete_source_hash_mismatch'):
            verifier.verify_tree(self.root, inventory)

    def test_fixed_link_materializes_only_approved_git_target(self):
        target = self.root / 'Scripts/loopctrl_rpc.py'
        target.parent.mkdir(); target.write_bytes(b'public canonical reference client')
        link = self.root / verifier.LINK_PATH
        link.parent.mkdir(parents=True); link.symlink_to(verifier.LINK_TARGET)
        inventory = {verifier.LINK_PATH: {'mode': '120000', 'sha256': hashlib.sha256(verifier.LINK_TARGET.encode()).hexdigest()}}
        self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), verifier.verify_tree(self.root, inventory)[verifier.LINK_PATH])
        link.unlink(); link.symlink_to('/outside/private')
        with self.assertRaisesRegex(ValueError, 'fixed_source_link_mismatch'):
            verifier.verify_tree(self.root, inventory)

    def test_fixed_link_parent_cannot_be_a_symlink(self):
        target = self.root / 'Scripts/loopctrl_rpc.py'
        target.parent.mkdir(); target.write_bytes(b'public canonical reference client')
        outside = self.root / 'outside'; outside.mkdir()
        (outside / 'loopctrl_rpc.py').symlink_to(verifier.LINK_TARGET)
        (self.root / 'server').mkdir()
        (self.root / 'server/cli').symlink_to(outside, target_is_directory=True)
        inventory = {verifier.LINK_PATH: {'mode': '120000', 'sha256': hashlib.sha256(verifier.LINK_TARGET.encode()).hexdigest()}}
        with self.assertRaises(ValueError, msg='fixed final source link must reject a replaced parent'):
            verifier.verify_tree(self.root, inventory)

    def test_complete_source_zip_requires_exact_inventory_and_every_hash(self):
        path = self.root / 'source.zip'
        content = {'driver/test.py': b'public driver', 'upstream/Kit.swift': b'public upstream'}
        expected = {name: hashlib.sha256(raw).hexdigest() for name, raw in content.items()}
        def write(rows):
            with zipfile.ZipFile(path, 'w') as archive:
                for name, raw in rows.items(): archive.writestr(name, raw)
        write(content)
        self.assertEqual(2, verifier.inspect_source_zip(path, expected)['files'])
        for rows in ({'driver/test.py': content['driver/test.py']},
                     dict(content, **{'upstream/extra.swift': b'extra'}),
                     dict(content, **{'upstream/Kit.swift': b'wrong source'})):
            write(rows)
            with self.assertRaisesRegex(ValueError, 'complete_source_zip'):
                verifier.inspect_source_zip(path, expected)


class CompilerContracts(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='ng2-shared-compiler-test-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.additions = ['LoopCtrlUITests/NG2DeviceRaster.swift', 'LoopCtrlUITests/NG2Startup.swift',
                          'LoopCtrlUITests/NG2DeviceGeometryProfile.c', 'LoopCtrlUITests/NG2DeviceRaster.c']
        sources = [verifier.STAMP, 'LoopCtrlUITests/NG2Runtime.swift', *self.additions]
        final = {}
        for name in sources:
            path = self.root / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(('public source ' + name).encode())
            final[name] = hashlib.sha256(path.read_bytes()).hexdigest()
        self.report = {'manifest': {'additions': {name: {} for name in self.additions}},
                       'final_source_sha256': final, 'complete_source_sha256': {}}
        self.rows = []
        for target in sorted(verifier.TARGETS):
            args = ['/public/swiftc', '-module-name', target, '-target', 'arm64-apple-ios16.0', '-Onone', '-c',
                    str(self.root / verifier.STAMP)]
            if target == 'LoopCtrlAllInOne': args.append('-DLOOPCTRL_ALL_IN_ONE')
            if target == 'LoopCtrlUITests':
                args += [str(self.root / name) for name in sources if name.endswith('.swift') and name != verifier.STAMP]
                args += ['-import-objc-header', str(self.root / 'LoopCtrlUITests/XCTestPrivate-Bridging-Header.h')]
            self.rows.append({'module': target, 'arguments': args, 'command_sha256': 'a' * 64})
        self.crows = []
        for name in self.additions:
            if not name.endswith('.c'): continue
            args = ['/public/clang', '-target', 'arm64-apple-ios16.0', '-O2', '-fno-fast-math', '-ffp-contract=off',
                    '-c', str(self.root / name), '-o', str(self.root / ('build/Build/Intermediates.noindex/LoopCtrl.build/Debug-iphoneos/LoopCtrlUITests.build/Objects-normal/arm64/' + Path(name).stem + '.o'))]
            self.crows.append({'arguments': args, 'command_sha256': 'b' * 64})

    def test_each_required_normal_target_compiles_stamp_and_exact_new_membership(self):
        report = verifier.inspect_swift_records(self.root, self.rows, self.report)
        self.assertEqual(verifier.TARGETS, set(report['targets']))
        self.assertIn('LoopCtrlUITests/NG2Runtime.swift', report['compiled_source_sha256'])
        self.assertNotIn('NG8_CAPTURE_PROBE_BUILD', report['targets']['LoopCtrlUITests'][0]['defines'])

    def test_normal_flags_stamp_allinone_and_target_cannot_be_faked(self):
        for fault in ('capture', 'host', 'stamp', 'allinone', 'missing_target', 'simulator'):
            rows = copy.deepcopy(self.rows)
            if fault == 'missing_target': rows.pop()
            else:
                row = next(item for item in rows if item['module'] == 'LoopCtrlAllInOne')
                args = row['arguments']
                if fault == 'capture': args.append('-DNG8_CAPTURE_PROBE_BUILD')
                elif fault == 'host': args += ['-D', 'NG2_RUNTIME_HOST_TEST']
                elif fault == 'stamp': args.remove(str(self.root / verifier.STAMP))
                elif fault == 'allinone': args.remove('-DLOOPCTRL_ALL_IN_ONE')
                elif fault == 'simulator': args[args.index('-target') + 1] += '-simulator'
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                verifier.inspect_swift_records(self.root, rows, copy.deepcopy(self.report))

    def test_uitest_asset_in_app_and_changed_runtime_are_rejected(self):
        rows = copy.deepcopy(self.rows)
        rows[0]['arguments'].append(str(self.root / self.additions[0]))
        with self.assertRaisesRegex(ValueError, 'uitest_source_in_app_target'):
            verifier.inspect_swift_records(self.root, rows, copy.deepcopy(self.report))
        (self.root / 'LoopCtrlUITests/NG2Runtime.swift').write_bytes(b'changed after compile')
        with self.assertRaisesRegex(ValueError, 'compiled_swift_source_changed'):
            verifier.inspect_swift_records(self.root, self.rows, self.report)

    def test_every_new_c_file_has_one_strict_real_uitest_compile(self):
        proof = verifier.inspect_c_records(self.root, self.crows, self.report)
        self.assertEqual({name for name in self.additions if name.endswith('.c')}, set(proof))
        self.assertTrue(all(row['strict_flags']['optimization'] == '-O2' for row in proof.values()))

    def test_added_c_requires_source_target_strict_flags_and_no_duplicates(self):
        for fault in ('missing', 'duplicate', 'wrongtarget', 'unsafe', 'optimization', 'capture', 'host', 'outside'):
            rows = copy.deepcopy(self.crows)
            if fault == 'missing': rows.pop()
            elif fault == 'duplicate': rows.append(copy.deepcopy(rows[0]))
            else:
                args = rows[0]['arguments']
                if fault == 'wrongtarget': args[args.index('-o')+1] = args[args.index('-o')+1].replace('LoopCtrlUITests.build', 'LoopCtrlAllInOne.build')
                elif fault == 'unsafe': args.append('-ffast-math')
                elif fault == 'optimization': args.append('-O0')
                elif fault == 'capture': args += ['-D', 'NG8_CAPTURE_PROBE_BUILD']
                elif fault == 'host': args.append('-DNG2_DEVICE_RASTER_HOST_TEST')
                elif fault == 'outside': args[args.index('-c')+1] = '/outside/NG2DeviceGeometryProfile.c'
            with self.subTest(fault=fault), self.assertRaises(ValueError):
                verifier.inspect_c_records(self.root, rows, self.report)
        (self.root / self.additions[2]).write_bytes(b'changed C')
        with self.assertRaisesRegex(ValueError, 'normal_c_source_changed'):
            verifier.inspect_c_records(self.root, self.crows, self.report)


if __name__ == '__main__':
    unittest.main()
