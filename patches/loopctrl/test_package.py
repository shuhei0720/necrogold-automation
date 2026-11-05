import importlib.util
from pathlib import Path
import plistlib
import tempfile
import unittest
import zipfile


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


if __name__ == '__main__':
    unittest.main()
