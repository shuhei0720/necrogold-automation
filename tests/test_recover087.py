"""Saved TEST087 publication recovery, using only procedural stdlib PNG data.

No native core, game, device RPC, pairing data or iPhone result is simulated.
"""
from contextlib import ExitStack, contextmanager
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import signal
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from necroprobe import native_walk as native
from necroprobe import recover087 as recovery
from necroprobe import target_assessment as target
from necroprobe import test069 as publication, test087
from tests.test_target_assessment087 import png, shop


def seed(base, data):
    item = dict(name='capture-000007.png', format='png', pixel_width=896, pixel_height=414,
        bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), capture_id=7,
        capture_start_ns=100, capture_end_ns=200, decode_end_ns=210,
        completed_prefix=6, completed_prefix_start=6, completed_prefix_end=6,
        stable_prefix=True, inflight_start=False, inflight_end=False)
    report = dict(schema='ngg2-native-v1', clock_id='b'*32, device_now_ns=1100,
        input_state=0, terminal=1, reason_name='goods', goods=1, paused=1,
        workers_drained=True, native_inflight=False, ui_frozen=False,
        events=[dict(id=6, kind=1, outcome=2, begin_ns=30, end_ns=80,
                     source_capture_id=6, source_start_ns=10),
                dict(id=7, kind=2, outcome=2, begin_ns=900, end_ns=1000,
                     source_capture_id=7, source_start_ns=100)],
        motion_references=[], recovery=dict(initial_reacquisitions=0,
            post_move_reacquisitions=0, episode_id=0, mode=0,
            schedule_deadline_ns=0, visual_deadline_ns=0, ack_ns=0,
            record_count=0, dropped_records=0, records=[]))
    record = dict(schema='ngg2-host-v1', revision=native.REVISION, run_id='a'*32,
        profile=native.PROFILE, state='completed', resolved=True, start_attempted=True,
        cancel_attempted=False, cancel_attempts=0, cancel_confirmed=True,
        stop_reason=None, native_state='completed', native_report=report,
        images=[item], result_metadata={}, events=[], events_dropped=0,
        host_clock_domain='python.monotonic_ns', native_clock_domain='device.monotonic_ns',
        image_export=dict(export_id='c'*32, images=[deepcopy(item)], total_bytes=len(data),
            chunk_bytes=native.CHUNK_BYTES, offsets=[len(data)], prefix_sha256=[item['sha256']]))
    folder = base/('native-'+record['run_id']); (folder/'images').mkdir(parents=True)
    (folder/'images'/item['name']).write_bytes(data)
    native._save(base, record)
    record = native._load(base)
    assert native._read_only_terminal(record['native_state'], record['native_report'])
    native._save(base, record)
    return record


class Recover087Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pixels = png(shop())

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='recover087-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.user = self.root/'user'; self.user.mkdir()
        self.base = self.user/'.necroprobe'/'runtime'/'test-087'
        self.destination = self.root/'new-source'; self.destination.mkdir()

    @contextmanager
    def no_device(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(Path, 'home', return_value=self.user))
            stack.enter_context(patch.object(Path, 'cwd', return_value=self.destination))
            forbidden = [stack.enter_context(patch.object(native, name,
                side_effect=AssertionError('saved recovery called '+name)))
                for name in ('main', 'run_session', 'Client', 'NativeClient', 'HttpTransport')]
            yield forbidden
            for called in forbidden: called.assert_not_called()

    def invoke(self):
        with self.no_device(), patch('sys.stdout', new_callable=io.StringIO) as output:
            try:
                code = recovery.main([])
            except AssertionError as error:
                self.fail('The recovery entry must remain local for an already saved run: '+str(error))
            return code, output.getvalue()

    def source_bytes(self):
        return {p.relative_to(self.base).as_posix(): p.read_bytes()
                for p in self.base.rglob('*') if p.is_file()}

    def test_saved_complete_run_is_classified_and_published_under_the_same_uuid_without_device_calls(self):
        record = seed(self.base, self.pixels); before = self.source_bytes()
        locked = [False]; actual_lock, actual_load = native.device_lock, native._load
        actual_publish = publication._publish; calls = []
        @contextmanager
        def checked_lock(path):
            self.assertEqual(self.user/'.necroprobe/runtime/.test-087-publication/publication.lock', path)
            with actual_lock(path):
                locked[0] = True
                try: yield
                finally: locked[0] = False
        def checked_load(base):
            self.assertTrue(locked[0], 'strict load must happen under the publication lease')
            self.assertEqual(self.base, base); return actual_load(base)
        def checked_publish(*args, **kwargs):
            self.assertTrue(locked[0]); self.assertEqual(record, args[2])
            self.assertIs(test087._prepare, kwargs['prepare'])
            calls.append(record['run_id']); return actual_publish(*args, **kwargs)
        with patch.object(native, 'device_lock', checked_lock), \
                patch.object(native, '_load', checked_load), \
                patch.object(publication, '_publish', side_effect=checked_publish):
            code, output = self.invoke()
        self.assertEqual(0, code); self.assertEqual([record['run_id']], calls)
        self.assertIn('のろいのゆびわ', output)
        self.assertEqual(record, native._load(self.base))
        after = self.source_bytes()
        self.assertEqual(before, {name: after[name] for name in before})
        folder = 'native-'+record['run_id']
        assessment = after[folder+'/'+target.SIDECAR]
        self.assertEqual('target', json.loads(assessment)['outcome'])
        archive = self.destination/'runtime'/('test-087-'+record['run_id']+'.zip')
        with zipfile.ZipFile(archive) as saved:
            self.assertIsNone(saved.testzip())
            self.assertEqual(assessment, saved.read('test-087/'+folder+'/'+target.SIDECAR))
            for name, raw in before.items():
                self.assertEqual(raw, saved.read('test-087/'+name))
        storage = self.base.parent/'.test-087-publication'
        receipt = json.loads((storage/(record['run_id']+'.receipt.json')).read_bytes())
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), receipt['archive_sha256'])

    def test_published_rerun_only_verifies_the_same_archive_and_never_starts_a_new_session(self):
        record = seed(self.base, self.pixels)
        self.assertEqual(0, self.invoke()[0])
        archive = self.destination/'runtime'/('test-087-'+record['run_id']+'.zip')
        storage = self.base.parent/'.test-087-publication'
        receipt = storage/(record['run_id']+'.receipt.json')
        original, original_receipt, original_sources = archive.read_bytes(), receipt.read_bytes(), self.source_bytes()
        receipt_mtime = receipt.stat().st_mtime_ns
        with patch.object(publication, '_publish', side_effect=AssertionError('published recovery must verify only')), \
                patch.object(test087, '_prepare', side_effect=AssertionError('a frozen ZIP cannot be reclassified')):
            code, output = self.invoke()
        self.assertEqual(0, code); self.assertIn(str(archive), output)
        self.assertEqual(original, archive.read_bytes()); self.assertEqual(original_receipt, receipt.read_bytes())
        self.assertEqual(receipt_mtime, receipt.stat().st_mtime_ns)
        self.assertEqual(original_sources, self.source_bytes())
        archive.write_bytes(original[:-1]+bytes((original[-1]^1,)))
        corrupted = archive.read_bytes()
        self.assertEqual(2, self.invoke()[0])
        self.assertEqual(corrupted, archive.read_bytes())
        self.assertEqual(original_receipt, receipt.read_bytes())
        self.assertEqual(original_sources, self.source_bytes())

    def test_missing_incomplete_corrupt_and_signal_cancel_keep_saved_data_without_rpc(self):
        for fault in ('empty', 'unresolved', 'cursor', 'missing_image', 'changed_image'):
            with self.subTest(fault=fault):
                self.user = self.root/fault; self.user.mkdir()
                self.base = self.user/'.necroprobe/runtime/test-087'
                if fault != 'empty':
                    record = seed(self.base, self.pixels)
                    image = self.base/('native-'+record['run_id'])/'images'/record['images'][0]['name']
                    if fault == 'unresolved': record['resolved'] = False
                    elif fault == 'cursor':
                        record['image_export']['offsets'][0] = 0
                        record['image_export']['prefix_sha256'][0] = hashlib.sha256(b'').hexdigest()
                    elif fault == 'missing_image': image.unlink()
                    else: image.write_bytes(image.read_bytes()+b'changed')
                    native._save(self.base, record)
                before = self.source_bytes()
                with patch.object(test087, '_prepare', side_effect=AssertionError('uncertified data cannot be assessed')):
                    code, output = self.invoke()
                self.assertEqual(2, code); self.assertIn('保持', output)
                self.assertEqual(before, self.source_bytes())
        for sig in (signal.SIGINT, signal.SIGTERM):
            with self.subTest(signal=sig):
                self.user = self.root/('signal-'+str(sig)); self.user.mkdir()
                self.base = self.user/'.necroprobe/runtime/test-087'
                seed(self.base, self.pixels); before = self.source_bytes()
                previous = signal.getsignal(sig); digest = publication._digest
                def cancelled_digest(*args):
                    signal.getsignal(sig)(sig, None)
                    return digest(*args)
                with patch.object(publication, '_digest', side_effect=cancelled_digest):
                    code, output = self.invoke()
                self.assertEqual(130, code); self.assertIn('保持', output)
                self.assertIs(previous, signal.getsignal(sig))
                self.assertEqual(before, self.source_bytes())


if __name__ == '__main__':
    unittest.main()
