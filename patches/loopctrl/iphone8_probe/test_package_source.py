import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile


spec = importlib.util.spec_from_file_location('ng8_source_package', Path(__file__).with_name('package_source.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class SourcePackageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.driver = self.root / 'driver'
        self.upstream = self.root / 'upstream'
        self.driver.mkdir()
        self.upstream.mkdir()
        (self.driver / 'main.py').write_bytes(b'print("public fixture")\n')
        (self.upstream / 'run.sh').write_bytes(b'#!/bin/sh\nexit 0\n')
        (self.upstream / 'run.sh').chmod(0o755)
        self.output = self.root / 'source.zip'
        self.inventory = {'driver/main.py': self.sha(self.driver / 'main.py'),
                          'upstream/run.sh': self.sha(self.upstream / 'run.sh')}

    def sha(self, path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def report(self):
        return {'complete_source_sha256': self.inventory, 'complete_source_materialized_links': {}}

    def test_every_source_byte_and_executable_mode_is_preserved(self):
        self.assertEqual(module.package(self.upstream, self.driver, self.output, self.report()), 2)
        with zipfile.ZipFile(self.output) as archive:
            self.assertEqual(archive.namelist(), sorted(self.inventory))
            for name in self.inventory:
                self.assertEqual(hashlib.sha256(archive.read(name)).hexdigest(), self.inventory[name])
            self.assertTrue(archive.getinfo('upstream/run.sh').external_attr >> 16 & 0o111)

    def test_changed_content_rejects_without_publishing_a_partial_zip(self):
        (self.driver / 'main.py').write_bytes(b'changed\n')
        with self.assertRaises(ValueError):
            module.package(self.upstream, self.driver, self.output, self.report())
        self.assertFalse(self.output.exists())

    def test_unsafe_inventory_and_unlisted_links_are_rejected(self):
        for name in ('../escape', 'driver/../escape', '/driver/main.py', 'driver//main.py', 'other/main.py', 'driver\\main.py'):
            with self.subTest(name=name):
                report = self.report()
                report['complete_source_sha256'] = {name: 'a' * 64}
                with self.assertRaises(ValueError):
                    module.package(self.upstream, self.driver, self.output, report)
                self.assertFalse(self.output.exists())
        (self.driver / 'alias.py').symlink_to('main.py')
        self.inventory['driver/alias.py'] = self.inventory['driver/main.py']
        with self.assertRaises(ValueError):
            module.package(self.upstream, self.driver, self.output, self.report())
        self.assertFalse(self.output.exists())

    def test_only_fixed_git_link_is_materialized_and_existing_output_is_untouched(self):
        scripts = self.upstream / 'Scripts'
        scripts.mkdir()
        (scripts / 'loopctrl_rpc.py').write_bytes(b'# public fixed tree link target\n')
        cli = self.upstream / 'server/cli'
        cli.mkdir(parents=True)
        (cli / 'loopctrl_rpc.py').symlink_to('../../Scripts/loopctrl_rpc.py')
        self.inventory['upstream/server/cli/loopctrl_rpc.py'] = self.sha(scripts / 'loopctrl_rpc.py')
        report = self.report()
        report['complete_source_materialized_links'] = {'upstream/server/cli/loopctrl_rpc.py': 'upstream/Scripts/loopctrl_rpc.py'}
        module.package(self.upstream, self.driver, self.output, report)
        with zipfile.ZipFile(self.output) as archive:
            self.assertEqual(archive.read('upstream/server/cli/loopctrl_rpc.py'), (scripts / 'loopctrl_rpc.py').read_bytes())
            self.assertEqual(archive.getinfo('upstream/server/cli/loopctrl_rpc.py').external_attr >> 16 & 0o170000, 0o100000)
        before = self.output.read_bytes()
        with self.assertRaises(FileExistsError):
            module.package(self.upstream, self.driver, self.output, report)
        self.assertEqual(self.output.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
