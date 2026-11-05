"""パッチの全事前検証と失敗時の非変更を、実ファイルで試す。"""
import difflib
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('ngg1_applier', HERE / 'apply_patch.py')
applier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(applier)
PATHS = ('LoopCtrlUITests/ActionCommand.swift', 'LoopCtrlUITests/ActionHandler.swift',
         'LoopCtrlKit/RPCMethod.swift')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


class ApplyPatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'source'
        self.root.mkdir()
        self.before, self.after, self.manifest = {}, {}, {}
        differences = []
        for index, name in enumerate(PATHS):
            old = f'// fixture {index}\nlet original = {index}\n'.encode()
            new = f'// fixture {index}\nlet changed = {index}\n'.encode()
            self.before[name], self.after[name] = old, new
            self.manifest[name] = {'sha256': sha(old), 'blob': blob(old), 'patched_sha256': sha(new)}
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(old)
            differences.extend(difflib.unified_diff(old.decode().splitlines(True),
                new.decode().splitlines(True), fromfile='a/' + name, tofile='b/' + name))
        self.patch_path = Path(self.temp.name) / 'change.patch'
        self.patch_path.write_text(''.join(differences))
        (self.root / 'untouched.txt').write_text('preserve me\n')

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes()
                for p in self.root.rglob('*') if p.is_file()}

    def apply(self):
        return applier.apply_patch(self.root, self.manifest, self.patch_path)

    def assert_rejected_unchanged(self):
        before = self.snapshot()
        with self.assertRaises((ValueError, OSError, RuntimeError)):
            self.apply()
        self.assertEqual(self.snapshot(), before)

    def test_matching_three_files_apply_and_preserve_other_files(self):
        self.apply()
        self.assertEqual({name: (self.root / name).read_bytes() for name in PATHS}, self.after)
        self.assertEqual((self.root / 'untouched.txt').read_text(), 'preserve me\n')

    def test_mismatch_in_last_file_writes_nothing(self):
        (self.root / PATHS[-1]).write_text('wrong source\n')
        self.assert_rejected_unchanged()

    def test_missing_last_file_writes_nothing(self):
        (self.root / PATHS[-1]).unlink()
        self.assert_rejected_unchanged()

    def test_wrong_blob_writes_nothing(self):
        self.manifest[PATHS[-1]]['blob'] = '0' * 40
        self.assert_rejected_unchanged()

    def test_second_application_writes_nothing(self):
        self.apply()
        self.assert_rejected_unchanged()

    def test_truncated_patch_writes_nothing(self):
        self.patch_path.write_text(self.patch_path.read_text()[:-8])
        self.assert_rejected_unchanged()

    def test_wrong_output_hash_writes_nothing(self):
        self.manifest[PATHS[-1]]['patched_sha256'] = '0' * 64
        self.assert_rejected_unchanged()

    def test_unexpected_fourth_target_writes_nothing(self):
        with self.patch_path.open('a') as stream:
            stream.write('--- /dev/null\n+++ b/unexpected.txt\n@@ -0,0 +1 @@\n+bad\n')
        self.assert_rejected_unchanged()

    def test_parent_path_in_patch_is_rejected(self):
        self.patch_path.write_text(self.patch_path.read_text().replace(PATHS[-1], '../escape'))
        self.assert_rejected_unchanged()
        self.assertFalse((self.root.parent / 'escape').exists())

    def test_symlink_source_is_rejected(self):
        source = self.root / PATHS[-1]
        outside = self.root.parent / 'outside.swift'
        outside.write_bytes(source.read_bytes())
        source.unlink()
        source.symlink_to(outside)
        self.assert_rejected_unchanged()
        self.assertEqual(outside.read_bytes(), self.before[PATHS[-1]])

    def test_symlink_directory_is_rejected(self):
        source = self.root / 'LoopCtrlKit'
        outside = self.root.parent / 'outside'
        source.rename(outside)
        source.symlink_to(outside, target_is_directory=True)
        self.assert_rejected_unchanged()

    def test_install_failure_rolls_back_prior_file(self):
        original_replace = applier.os.replace
        calls = 0
        def fail_second(source, destination):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError('injected second-file replace failure')
            return original_replace(source, destination)
        before = self.snapshot()
        with patch.object(applier.os, 'replace', side_effect=fail_second):
            with self.assertRaises(OSError):
                self.apply()
        self.assertEqual(self.snapshot(), before)


if __name__ == '__main__':
    unittest.main()
