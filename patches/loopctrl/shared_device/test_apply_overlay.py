import difflib
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ng2_shared_overlay', HERE / 'apply_overlay.py')
overlay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(overlay)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


class OverlayApplyTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='ng8-overlay-unit-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / 'upstream'
        self.root.mkdir()
        self.assets = self.base / 'assets'
        self.assets.mkdir()
        self.name = 'LoopCtrlUITests/NG2Runtime.swift'
        self.old = b'let mode = "normal"\n'
        self.new = b'let mode = "conditional NEW8"\n'
        target = self.root / self.name
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(self.old)
        self.added = 'LoopCtrlUITests/NG2DeviceGeometryProfile.h'
        self.asset = b'// public synthetic NEW8 mode fixture\n'
        (self.assets / 'NG2DeviceGeometryProfile.h').write_bytes(self.asset)
        self.patch_path = self.base / 'overlay.patch'
        self.patch_path.write_text(''.join(difflib.unified_diff(
            self.old.decode().splitlines(True), self.new.decode().splitlines(True),
            fromfile='a/' + self.name, tofile='b/' + self.name)))
        self.baseline = {self.name: sha(self.old)}
        self.protected = 'LoopCtrlUITests/NG2Controller.c'
        protected = self.root / self.protected
        protected.parent.mkdir(exist_ok=True)
        protected.write_bytes(b'/* unchanged synthetic protected native */\n')
        self.baseline[self.protected] = sha(protected.read_bytes())
        self.manifest = {
            'schema': 'ng2-shared-device-overlay-v1',
            'upstream_commit': '6e25cf6a9f65bc86c372cdce94bdb151d0cf6767',
            'baseline': dict(overlay.BASELINE_PINS),
            'patch_sha256': sha(self.patch_path.read_bytes()),
            'files': {self.name: {'base_sha256': sha(self.old), 'final_sha256': sha(self.new)}},
            'additions': {self.added: {'source': 'NG2DeviceGeometryProfile.h', 'sha256': sha(self.asset)}},
        }

    def test_valid_sealed_overlay_installs_exact_expected_bytes(self):
        final = self.apply()
        self.assertEqual(self.new, (self.root / self.name).read_bytes())
        self.assertEqual(self.asset, (self.root / self.added).read_bytes())
        self.assertEqual(self.baseline[self.protected], sha((self.root / self.protected).read_bytes()))
        self.assertEqual(final[self.name], sha(self.new))
        self.assertEqual(final[self.added], sha(self.asset))

    def test_fixed_build_identity_plist_is_a_sealed_allowed_asset(self):
        raw = b'<?xml version="1.0"?><plist version="1.0"><dict/></plist>\n'
        source = 'NG2DeviceBuildInfo.plist'
        target = 'LoopCtrlUITests/' + source
        (self.assets / source).write_bytes(raw)
        self.manifest['additions'][target] = {'source': source, 'sha256': sha(raw)}
        try:
            self.apply()
        except ValueError:
            outcome = 'rejected'
        else:
            outcome = 'accepted'
        self.assertEqual('accepted', outcome)
        self.assertEqual(raw, (self.root / target).read_bytes())

    def test_other_plist_assets_remain_forbidden(self):
        for source in ('NG2DeviceOther.plist', 'NG2DeviceBuildInfoOther.plist',
                       'NG2DeviceBuildInfo.plist.bak'):
            with self.subTest(source=source):
                manifest = copy.deepcopy(self.manifest)
                manifest['additions']['LoopCtrlUITests/' + source] = {
                    'source': source, 'sha256': sha(b'not the fixed build plist')}
                with self.assertRaisesRegex(ValueError, 'invalid_asset_name'):
                    overlay._validate(manifest, self.baseline)

    def apply(self):
        return overlay._apply(self.root, self.manifest, self.patch_path, self.assets, self.baseline)

    def snapshot(self):
        return {p.relative_to(self.root).as_posix(): ('link', os.readlink(p)) if p.is_symlink()
                else ('file', p.read_bytes()) for p in self.root.rglob('*')
                if p.is_file() or p.is_symlink()}

    def rejects_without_source_mutation(self):
        before = self.snapshot()
        with self.assertRaises(ValueError):
            self.apply()
        self.assertEqual(before, self.snapshot())

    def reseal_patch(self):
        self.manifest['patch_sha256'] = sha(self.patch_path.read_bytes())

    def test_closed_manifest_and_fixed_baseline_identity(self):
        for field, value in [('extra', True), ('upstream_commit', '0' * 40),
                             ('baseline', {}), ('schema', 'another-schema')]:
            with self.subTest(field=field):
                original = dict(self.manifest)
                self.manifest[field] = value
                self.rejects_without_source_mutation()
                self.manifest = original

    def test_absolute_traversal_backslash_and_noncanonical_paths_rejected(self):
        for name in ['/outside.swift', '../outside.swift', 'LoopCtrlKit/../outside.swift',
                     'LoopCtrlKit//JSONRPCServer.swift', 'LoopCtrlKit\\outside.swift', 'C:/outside.swift']:
            with self.subTest(name=name):
                original = self.manifest['files']
                self.manifest['files'] = {name: next(iter(original.values()))}
                self.rejects_without_source_mutation()
                self.manifest['files'] = original

    def test_protected_native_never_becomes_an_overlay_target(self):
        for name in [self.protected, 'LoopCtrlUITests/NG2Raster.swift',
                     'LoopCtrlUITests/NG2CaptureBridge.m', 'LoopCtrlUITests/ActionHandler.swift',
                     'LoopCtrlUITests/ObjCException.m', 'LoopCtrlUITests/ScreenStream.swift']:
            with self.subTest(name=name):
                self.manifest['files'] = {name: {'base_sha256': '1' * 64, 'final_sha256': '2' * 64}}
                self.rejects_without_source_mutation()

    def test_resealed_wrong_base_cannot_replace_independent_baseline(self):
        wrong = b'let mode = "caller resealed wrong base"\n'
        (self.root / self.name).write_bytes(wrong)
        self.manifest['files'][self.name]['base_sha256'] = sha(wrong)
        self.patch_path.write_text(''.join(difflib.unified_diff(
            wrong.decode().splitlines(True), self.new.decode().splitlines(True),
            fromfile='a/' + self.name, tofile='b/' + self.name)))
        self.reseal_patch()
        self.rejects_without_source_mutation()

    def test_unchanged_protected_source_hash_is_checked(self):
        (self.root / self.protected).write_bytes(b'changed protected source\n')
        self.rejects_without_source_mutation()

    def test_bad_patch_hash_and_final_output_hash_are_rejected(self):
        self.manifest['patch_sha256'] = '0' * 64
        self.rejects_without_source_mutation()
        self.reseal_patch()
        self.manifest['files'][self.name]['final_sha256'] = '0' * 64
        self.rejects_without_source_mutation()

    def test_duplicate_json_keys_are_not_silently_accepted(self):
        for raw in [b'{"schema":1,"schema":2}', b'{"files":{"same":1,"same":2}}']:
            with self.subTest(raw=raw):
                with self.assertRaisesRegex(ValueError, 'duplicate_json_key'):
                    overlay._json(raw)

    def test_extra_asset_and_missing_asset_are_rejected(self):
        extra = self.assets / 'NG2DeviceUnlisted.swift'
        extra.write_bytes(b'// unlisted source\n')
        self.rejects_without_source_mutation()
        extra.unlink()
        (self.assets / 'NG2DeviceGeometryProfile.h').unlink()
        self.rejects_without_source_mutation()

    def test_asset_hash_and_symlink_asset_are_rejected(self):
        source = self.assets / 'NG2DeviceGeometryProfile.h'
        source.write_bytes(b'changed asset\n')
        self.rejects_without_source_mutation()
        source.unlink()
        other = self.base / 'outside-asset.swift'
        other.write_bytes(self.asset)
        source.symlink_to(other)
        self.rejects_without_source_mutation()
        self.assertEqual(self.asset, other.read_bytes())

    def test_symlink_parent_of_overlay_input_is_rejected(self):
        alias = self.base / 'input-alias'
        alias.symlink_to(self.base, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'invalid_source_parent'):
            overlay._read_path(alias / self.patch_path.name)
        with self.assertRaisesRegex(ValueError, 'invalid_source_parent'):
            overlay._assets(alias / self.assets.name, self.manifest['additions'])

    def test_addition_destination_and_reused_source_are_closed(self):
        original = dict(self.manifest['additions'])
        for name in ['LoopCtrlKit/NG2DeviceGeometryProfile.h', 'LoopCtrlKit/NG2Raster.swift', '../NG2DeviceGeometryProfile.h']:
            self.manifest['additions'] = {name: next(iter(original.values()))}
            self.rejects_without_source_mutation()
        self.manifest['additions'] = dict(original)
        self.manifest['additions']['LoopCtrlKit/NG8Duplicate.swift'] = dict(next(iter(original.values())))
        self.rejects_without_source_mutation()

    def test_unlisted_existing_ng8_source_or_directory_is_rejected(self):
        extra = self.root / 'LoopCtrlUITests/NG2DeviceUnlisted.swift'
        extra.write_bytes(b'// unexpected destination source\n')
        self.rejects_without_source_mutation()
        extra.unlink()
        extra = self.root / 'LoopCtrlUITests/NG2DeviceUnlisted'
        extra.mkdir()
        (extra / 'Evil.swift').write_bytes(b'// hidden nested compile source\n')
        self.rejects_without_source_mutation()

    def test_existing_addition_is_never_overwritten_even_if_bytes_match(self):
        (self.root / self.added).write_bytes(self.asset)
        self.rejects_without_source_mutation()

    def test_omitted_patch_target_is_rejected(self):
        other = 'LoopCtrlUITests/XCTestPrivate-Bridging-Header.h'
        (self.root / other).write_bytes(self.old)
        self.baseline[other] = sha(self.old)
        self.patch_path.write_text(self.patch_path.read_text() + ''.join(difflib.unified_diff(
            self.old.decode().splitlines(True), self.new.decode().splitlines(True),
            fromfile='a/' + other, tofile='b/' + other)))
        self.reseal_patch()
        self.rejects_without_source_mutation()

    def test_patch_mode_change_or_duplicate_file_header_is_rejected(self):
        original = self.patch_path.read_text()
        for value in ['old mode 100644\nnew mode 120000\n' + original, original + original]:
            self.patch_path.write_text(value)
            self.reseal_patch()
            self.rejects_without_source_mutation()

    def test_symlink_root_source_and_parent_cannot_escape(self):
        alias = self.base / 'root-alias'
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError):
            overlay._apply(alias, self.manifest, self.patch_path, self.assets, self.baseline)
        outside = self.base / 'outside.swift'
        outside.write_bytes(self.old)
        target = self.root / self.name
        target.unlink()
        target.symlink_to(outside)
        self.rejects_without_source_mutation()
        target.unlink()
        target.write_bytes(self.old)
        moved = self.root / 'OriginalKit'
        target.parent.rename(moved)
        external = self.base / 'outside-directory'
        external.mkdir()
        (external / 'NG2Runtime.swift').write_bytes(self.old)
        (self.root / 'LoopCtrlUITests').symlink_to(external, target_is_directory=True)
        self.rejects_without_source_mutation()
        self.assertEqual(self.old, outside.read_bytes())
        self.assertEqual(self.old, (external / 'NG2Runtime.swift').read_bytes())

    def test_source_changed_during_staging_is_preserved_not_overwritten(self):
        run_patch = overlay._run_patch
        changed = b'concurrent editor source\n'
        def mutate(stage, raw):
            run_patch(stage, raw)
            (self.root / self.name).write_bytes(changed)
        with patch.object(overlay, '_run_patch', side_effect=mutate):
            with self.assertRaises(ValueError):
                self.apply()
        self.assertEqual(changed, (self.root / self.name).read_bytes())
        self.assertFalse((self.root / self.added).exists())

    def test_asset_or_patch_changed_during_staging_causes_no_source_install(self):
        run_patch = overlay._run_patch
        before = self.snapshot()
        def mutate_asset(stage, raw):
            run_patch(stage, raw)
            (self.assets / 'NG2DeviceGeometryProfile.h').write_bytes(b'asset changed\n')
        with patch.object(overlay, '_run_patch', side_effect=mutate_asset):
            with self.assertRaises(ValueError):
                self.apply()
        self.assertEqual(before, self.snapshot())
        (self.assets / 'NG2DeviceGeometryProfile.h').write_bytes(self.asset)
        def mutate_patch(stage, raw):
            run_patch(stage, raw)
            self.patch_path.write_bytes(b'changed patch\n')
        with patch.object(overlay, '_run_patch', side_effect=mutate_patch):
            with self.assertRaises(ValueError):
                self.apply()
        self.assertEqual(before, self.snapshot())

    def test_second_replace_failure_rolls_back_owned_changes(self):
        other = 'LoopCtrlUITests/XCTestPrivate-Bridging-Header.h'
        (self.root / other).write_bytes(self.old)
        self.baseline[other] = sha(self.old)
        self.manifest['files'][other] = {'base_sha256': sha(self.old), 'final_sha256': sha(self.new)}
        self.patch_path.write_text(self.patch_path.read_text() + ''.join(difflib.unified_diff(
            self.old.decode().splitlines(True), self.new.decode().splitlines(True),
            fromfile='a/' + other, tofile='b/' + other)))
        self.reseal_patch()
        replace = overlay.os.replace
        calls = 0
        before = self.snapshot()
        def fail_second(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('synthetic replacement fault')
            return replace(*args, **kwargs)
        with patch.object(overlay.os, 'replace', side_effect=fail_second):
            with self.assertRaises(OSError):
                self.apply()
        self.assertEqual(before, self.snapshot())

    def test_new_addition_uses_atomic_no_clobber_against_a_last_moment_writer(self):
        replace, link = overlay.os.replace, overlay.os.link
        injected = False
        concurrent = b'concurrent new destination must survive\n'
        def race(operation, source, destination, **kwargs):
            nonlocal injected
            if destination == Path(self.added).name and not injected:
                injected = True
                fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                             0o644, dir_fd=kwargs['dst_dir_fd'])
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(concurrent)
            return operation(source, destination, **kwargs)
        with patch.object(overlay.os, 'replace', side_effect=lambda *a, **k: race(replace, *a, **k)), \
                patch.object(overlay.os, 'link', side_effect=lambda *a, **k: race(link, *a, **k)):
            with self.assertRaises(FileExistsError):
                self.apply()
        self.assertEqual(concurrent, (self.root / self.added).read_bytes())
        self.assertEqual(self.old, (self.root / self.name).read_bytes())

    def test_post_mutation_stat_failure_still_rolls_back_the_successful_replace(self):
        replace, stat_call = overlay.os.replace, overlay.os.stat
        mutated = False
        failed = False
        before = self.snapshot()
        def record_replace(*args, **kwargs):
            nonlocal mutated
            result = replace(*args, **kwargs)
            mutated = True
            return result
        def fail_once_after_mutation(*args, **kwargs):
            nonlocal failed
            if mutated and not failed:
                failed = True
                raise OSError('synthetic post-mutation stat failure')
            return stat_call(*args, **kwargs)
        with patch.object(overlay.os, 'replace', side_effect=record_replace), \
                patch.object(overlay.os, 'stat', side_effect=fail_once_after_mutation):
            with self.assertRaises(OSError):
                self.apply()
        self.assertTrue(failed)
        self.assertEqual(before, self.snapshot())

    def test_post_first_replace_asset_mutation_rolls_back(self):
        replace = overlay.os.replace
        injected = False
        before = self.snapshot()
        def mutate(*args, **kwargs):
            nonlocal injected
            result = replace(*args, **kwargs)
            if not injected:
                injected = True
                (self.assets / 'NG2DeviceGeometryProfile.h').write_bytes(b'concurrent asset change\n')
            return result
        with patch.object(overlay.os, 'replace', side_effect=mutate):
            with self.assertRaises(ValueError):
                self.apply()
        self.assertEqual(before, self.snapshot())

    def test_rollback_does_not_destroy_a_concurrent_edit_of_installed_file(self):
        replace = overlay.os.replace
        injected = False
        changed = b'newer editor source after first install\n'
        def mutate(*args, **kwargs):
            nonlocal injected
            result = replace(*args, **kwargs)
            if not injected:
                injected = True
                (self.root / self.name).write_bytes(changed)
            return result
        with patch.object(overlay.os, 'replace', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'rollback_concurrent_change'):
                self.apply()
        self.assertEqual(changed, (self.root / self.name).read_bytes())
        self.assertFalse((self.root / self.added).exists())

    def test_parent_symlink_swap_at_replace_cannot_write_outside_anchored_directory(self):
        replace = overlay.os.replace
        external = self.base / 'outside-swap'
        external.mkdir()
        (external / 'NG2Runtime.swift').write_bytes(b'outside must stay\n')
        moved = self.root / 'OriginalKit'
        injected = False
        def swap(*args, **kwargs):
            nonlocal injected
            if not injected:
                injected = True
                (self.root / 'LoopCtrlUITests').rename(moved)
                (self.root / 'LoopCtrlUITests').symlink_to(external, target_is_directory=True)
            return replace(*args, **kwargs)
        with patch.object(overlay.os, 'replace', side_effect=swap):
            with self.assertRaises(ValueError):
                self.apply()
        self.assertEqual(b'outside must stay\n', (external / 'NG2Runtime.swift').read_bytes())
        self.assertEqual(self.old, (moved / 'NG2Runtime.swift').read_bytes())

    def test_final_dual_seal_map_retains_protected_paths_and_checks_overlay(self):
        expected = overlay.effective_expected_map(self.manifest, self.baseline)
        self.assertEqual(self.baseline[self.protected], expected[self.protected])
        self.assertEqual(sha(self.new), expected[self.name])
        self.assertEqual(sha(self.asset), expected[self.added])
        self.apply()
        fd = overlay._directory(self.root)
        self.addCleanup(os.close, fd)
        overlay._verify_map(fd, expected)
        (self.root / self.name).write_bytes(self.old)
        with self.assertRaisesRegex(ValueError, 'source_hash_mismatch'):
            overlay._verify_map(fd, expected)

    def test_pinned_baseline_seal_cannot_be_replaced_by_new_manifest_claim(self):
        real_read = overlay._read_path
        def forged(path):
            if Path(path).name == 'ngg2-manifest.json':
                return json.dumps({'upstream_commit': overlay.UPSTREAM, 'files': {}}).encode()
            return real_read(path)
        with patch.object(overlay, '_read_path', side_effect=forged):
            with self.assertRaisesRegex(ValueError, 'pinned_baseline_changed'):
                overlay._trusted_baseline(self.root)

    def test_unpatched_integration_base_comes_from_fixed_git_object(self):
        def fixed_git(_root, *args):
            if args == ('rev-parse', 'HEAD'):
                return (overlay.UPSTREAM + '\n').encode()
            self.assertEqual('show', args[0])
            self.assertTrue(args[1].startswith(overlay.UPSTREAM + ':'))
            return ('fixed Git object for ' + args[1]).encode()
        with patch.object(overlay, '_git', side_effect=fixed_git):
            baseline = overlay._trusted_baseline(self.root)
        target = 'LoopCtrlApp/Info.plist'
        fixed = ('fixed Git object for ' + overlay.UPSTREAM + ':' + target).encode()
        self.assertEqual(sha(fixed), baseline[target])
        g2 = json.loads((HERE.parent / 'ngg2-manifest.json').read_text())
        self.assertEqual(g2['additions'][self.name]['sha256'], baseline[self.name])

    def test_wrong_upstream_commit_is_not_accepted_as_a_trusted_base(self):
        with patch.object(overlay, '_git', return_value=b'wrong-commit\n'):
            with self.assertRaisesRegex(ValueError, 'fixed_upstream_mismatch'):
                overlay._trusted_baseline(self.root)

    def test_production_checkout_guard_rejects_unrelated_and_staged_changes(self):
        permitted = b' M LoopCtrlKit/JSONRPCServer.swift\0?? LoopCtrlUITests/NG2Runtime.swift\0'
        with patch.object(overlay, '_git', return_value=permitted):
            overlay._checkout_delta(self.root)
        for forbidden in [b'?? LoopCtrlUITests/Evil.swift\0', b' M LoopCtrlKit/AuthManager.swift\0',
                          b'M  LoopCtrlUITests/NG2Runtime.swift\0', b'?? .owned-stage-lookalike/source\0']:
            with self.subTest(forbidden=forbidden), patch.object(overlay, '_git', return_value=forbidden):
                with self.assertRaisesRegex(ValueError, 'unexpected_checkout_delta'):
                    overlay._checkout_delta(self.root, owned_stage='.owned-stage')
        with patch.object(overlay, '_git', return_value=b'?? .owned-stage/source\0'):
            overlay._checkout_delta(self.root, owned_stage='.owned-stage')

    def test_production_cli_does_not_offer_manifest_asset_or_baseline_overrides(self):
        for option in ['--manifest', '--assets', '--baseline']:
            with self.subTest(option=option), patch.object(sys, 'argv', ['apply_overlay.py', str(self.root), option, 'untrusted']), \
                    patch.object(overlay, '_trusted_baseline') as trusted, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as exit_result:
                    overlay.main()
                self.assertEqual(2, exit_result.exception.code)
                trusted.assert_not_called()


if __name__ == '__main__':
    unittest.main()
