"""TEST098 explicit recovery preserves one saved run and never starts a game.

The old094 server supplies procedural PNG/record bytes to the real local
journal and publication path. This is a filesystem/client contract, not an
iPhone or encrypted-HTTP acceptance test. Before the option exists, the
baseline uses normal run() so its unwanted start is an assertion failure.
"""
import inspect
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from necroprobe import cycle_publication as publication
from necroprobe import native_cycle as cycle
from necroprobe import native_walk
from necroprobe.validation import ProbeError
from tests.test_native_cycle_client094 import RUN, Server


class CycleRecoveryOnly098Tests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='cycle-recovery098-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.base = self.root/'local'/'test-098'
        self.base.mkdir(parents=True)
        self.destination = self.root/'new-mount'
        self.destination.mkdir()
        self.server = Server(self.base)
        self.notices = []

    def seed(self, started=True):
        record = cycle.fresh_record(RUN)
        record['start_intent'] = started
        cycle._journal(self.base, record)
        return record

    def invoke(self, destination=None):
        options = {}
        if 'recovery_only' in inspect.signature(publication.run).parameters:
            options['recovery_only'] = True
        with patch('necroprobe.native_cycle.device_lock',
                   lambda: native_walk.device_lock(self.root/'device.lock')):
            return publication.run(self.server, destination or self.destination,
                spool=self.base, notice=self.notices.append, **options)

    def reject_without_start(self):
        reason = None
        with patch.object(cycle, 'fresh_record', wraps=cycle.fresh_record) as fresh:
            try:
                self.invoke()
            except ProbeError as error:
                reason = error.code
        self.assertEqual(('cycle_recovery_record_missing', [], 0),
                         (reason, self.server.calls, fresh.call_count),
                         'explicit recovery must reject before RPC or fresh UUID')

    def test_missing_journal_rejects_without_rpc_or_fresh_uuid(self):
        self.reject_without_start()
        self.assertIsNone(cycle.load_journal(self.base))
        self.assertFalse(list(self.destination.glob('runtime/*.zip')))

    def test_unstarted_journal_rejects_without_rpc_and_preserves_original_bytes(self):
        self.seed(started=False)
        paths = (self.base/'active-cycle.json', self.base/('cycle-'+RUN)/'journal.json')
        before = {path: path.read_bytes() for path in paths}
        self.reject_without_start()
        self.assertEqual(before, {path: path.read_bytes() for path in paths})
        self.assertFalse(list(self.destination.glob('runtime/*.zip')))

    def test_unfinished_run_collects_and_publishes_same_uuid_without_keepalive(self):
        self.seed()
        with patch.object(cycle, 'fresh_record', wraps=cycle.fresh_record) as fresh:
            record, archive = self.invoke()
        self.assertEqual((RUN, True, True, 0),
                         (record['run_id'], record['resolved'], record['published'], fresh.call_count))
        self.assertTrue(self.server.calls)
        self.assertTrue(all(method == 'necro_native_cycle' and params['run_id'] == RUN
                            for method, params in self.server.calls))
        status = [params for _, params in self.server.calls if params.get('mode') == 'status']
        self.assertTrue(status)
        self.assertTrue(all(params['keepalive'] is False for params in status))
        self.assertEqual('test-098-'+RUN+'.zip', archive.name)
        with zipfile.ZipFile(archive) as saved:
            self.assertIsNone(saved.testzip())
            self.assertEqual(6, len(saved.namelist()))
            self.assertTrue(all(name.startswith('test-098/cycle-'+RUN+'/')
                                for name in saved.namelist()))
            self.assertEqual(self.server.image,
                saved.read('test-098/cycle-'+RUN+'/images/capture-000007.png'))
        self.assertEqual('published', self.server.calls[-1][1]['mode'])

    def test_published_run_recreates_same_zip_at_new_mount_without_rpc_or_new_uuid(self):
        self.seed()
        original, copied = self.invoke()
        original_bytes = copied.read_bytes()
        storage = self.base.parent/'.test-098-publication'
        durable_paths = (storage/(RUN+'.zip'), storage/(RUN+'.receipt.json'))
        durable = {path: path.read_bytes() for path in durable_paths}
        copied.unlink()
        new_destination = self.root/'another-mount'
        new_destination.mkdir()
        self.server.calls.clear()
        with patch.object(cycle, 'fresh_record', wraps=cycle.fresh_record) as fresh:
            returned, archive = self.invoke(new_destination)
        self.assertEqual((RUN, original['archive_sha256'], [], 0),
                         (returned['run_id'], returned['archive_sha256'],
                          self.server.calls, fresh.call_count),
                         'published recovery must not enter the next session')
        self.assertEqual(new_destination/'runtime'/('test-098-'+RUN+'.zip'), archive)
        self.assertEqual(original_bytes, archive.read_bytes())
        self.assertEqual(durable, {path: path.read_bytes() for path in durable_paths})
        self.assertEqual(RUN, cycle.load_journal(self.base)['run_id'])

    def test_published_journal_without_original_receipt_still_rejects(self):
        self.seed()
        _record, copied = self.invoke()
        before_archive = copied.read_bytes()
        receipt = self.base.parent/'.test-098-publication'/(RUN+'.receipt.json')
        receipt.unlink()
        paths = (self.base/'active-cycle.json', self.base/('cycle-'+RUN)/'journal.json')
        before = {path: path.read_bytes() for path in paths}
        self.server.calls.clear()
        with patch.object(cycle, 'fresh_record', wraps=cycle.fresh_record) as fresh:
            with self.assertRaises((OSError, ProbeError)):
                self.invoke()
        self.assertEqual(([], 0), (self.server.calls, fresh.call_count))
        self.assertEqual(before, {path: path.read_bytes() for path in paths})
        self.assertEqual(before_archive, copied.read_bytes())


if __name__ == '__main__':
    unittest.main()
