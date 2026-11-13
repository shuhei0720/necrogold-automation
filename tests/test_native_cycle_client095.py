"""TEST095 publication labels; native protocol and old recovery stay unchanged."""
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile
from contextlib import redirect_stdout

from necroprobe import native_cycle as cycle
from necroprobe import cycle_publication as publication
from test_native_cycle_client094 import RUN, Server


class CycleClient095Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.destination = self.root/'mounted'
        self.destination.mkdir()

    def collect(self, label):
        base = self.root/'local'/label
        base.mkdir(parents=True)
        server = Server(base)
        record = cycle.fresh_record(RUN)
        record['start_intent'] = True
        cycle._journal(base, record)
        cycle.collect(server, base, record, notice=lambda _: None)
        return base, server, record

    def test_095_zip_prefix_filename_receipt_and_all_registered_bytes(self):
        base, server, record = self.collect('test-095')
        archive = publication.publish(server, base, self.destination, record, notice=lambda _: None)
        self.assertEqual('test-095-'+RUN+'.zip', archive.name)
        with zipfile.ZipFile(archive) as zipped:
            self.assertTrue(all(name.startswith('test-095/cycle-'+RUN+'/') for name in zipped.namelist()))
            self.assertIsNone(zipped.testzip())
            folder = base/('cycle-'+RUN)
            for name in zipped.namelist():
                relative = Path(name).relative_to(Path('test-095')/('cycle-'+RUN))
                self.assertEqual((folder/relative).read_bytes(), zipped.read(name))
        self.assertTrue(record['published'])
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), record['archive_sha256'])
        published = [params for method, params in server.calls
                     if method == 'necro_native_cycle' and params['mode'] == 'published']
        self.assertEqual(1, len(published))
        self.assertEqual(record['archive_sha256'], published[0]['archive_sha256'])
        receipt = json.loads((base.parent/'.test-095-publication'/(RUN+'.receipt.json')).read_text())
        self.assertEqual('ngg2-cycle-publication-v1', receipt['schema'])
        self.assertEqual(record['archive_sha256'], receipt['archive_sha256'])

    def test_existing_094_and_generic_spools_preserve_original_zip_label(self):
        for label in ('test-094', 'spool', 'test-09x', 'test-１２３'):
            with self.subTest(label=label):
                base, server, record = self.collect(label)
                archive = publication.publish(server, base, self.destination, record, notice=lambda _: None)
                self.assertEqual('test-094-'+RUN+'.zip', archive.name)
                with zipfile.ZipFile(archive) as zipped:
                    self.assertTrue(all(name.startswith('test-094/') for name in zipped.namelist()))
                archive.unlink()

    def test_095_launcher_uses_separate_spool_and_truthful_not_started_message(self):
        from necroprobe import test094, test095
        output = io.StringIO()
        record = {'last_error': 'cycle_start_not_admitted'}
        with patch.object(test094.Path, 'home', return_value=self.root), \
             patch.object(test094, 'load_pairing', return_value=(b'key', 'token')), \
             patch.object(test094, 'Crypto'), patch.object(cycle, 'CycleClient'), \
             patch.object(test094, 'run', return_value=(record, None)) as run, redirect_stdout(output):
            self.assertEqual(2, test095.main([]))
        self.assertEqual(self.root/'.necroprobe'/'runtime'/'test-095', run.call_args.kwargs['spool'])
        self.assertIn('TEST-095: 未完了 / cycle_start_not_admitted', output.getvalue())
        self.assertIn('ゲームは開始していません。', output.getvalue())
        self.assertNotIn('TEST-094:', output.getvalue())


if __name__ == '__main__':
    unittest.main()
