"""Evidence-only recovery of procedural stdlib TEST088 data; no device simulation."""
from contextlib import ExitStack, contextmanager
import hashlib
import io
import json
from pathlib import Path
import signal
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from necroprobe import evidence088 as evidence
from necroprobe import native_walk as native, target_assessment as target
from necroprobe import test069 as publication, test087
from tests.test_recover087 import seed
from tests.test_target_assessment087 import png


class Evidence088Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pixels = png(bytes(896*414*4))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='evidence088-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.configure('initial')

    def configure(self, name):
        self.user = self.root/name/'user'; self.user.mkdir(parents=True)
        self.base = self.user/'.necroprobe/runtime/test-088'
        self.normal = self.base.parent/'.test-088-publication'
        self.normal.mkdir(parents=True)
        (self.normal/'publication.lock').touch()
        self.storage = self.base.parent/'.test-088-evidence'
        self.destination = self.root/name/'source'; self.destination.mkdir()

    def saved(self, extras=False):
        record = seed(self.base, self.pixels)
        if extras:
            folder = self.base/('native-'+record['run_id'])
            (folder/'target-assessment.json').write_bytes(b'interrupted assessment')
            (folder/'images/.parts').mkdir()
            (folder/'images/.parts/interrupted.part').write_bytes(b'keep me')
            for suffix in ('.zip', '.receipt.json'):
                (self.normal/(record['run_id']+suffix)).write_bytes(b'normal artifact remains untouched')
        return record

    def snapshot(self):
        return {str(p): (p.read_bytes(), p.stat().st_mtime_ns)
                for base in (self.base, self.normal) for p in base.rglob('*')
                if p.is_file() and not p.is_symlink()}

    @contextmanager
    def local_only(self, normal_publication=False):
        with ExitStack() as stack:
            stack.enter_context(patch.object(Path, 'home', return_value=self.user))
            stack.enter_context(patch.object(Path, 'cwd', return_value=self.destination))
            forbidden = []
            for module, names in ((native, ('main', 'run_session', 'Client', 'NativeClient', 'HttpTransport')),
                    (target, ('classify_png', 'prepare_assessment')), (test087, ('_prepare',)),
                    (publication, ('_inventory',) if normal_publication else ('_inventory', '_publish'))):
                for name in names:
                    forbidden.append(stack.enter_context(patch.object(module, name,
                        side_effect=AssertionError('evidence export called '+name))))
            yield
            for called in forbidden: called.assert_not_called()

    def invoke(self):
        with self.local_only(), patch('sys.stdout', new_callable=io.StringIO) as output:
            try:
                code = evidence.main([])
            except AssertionError as error:
                self.fail('Saved evidence must bypass the device and classifier: '+str(error))
            return code, output.getvalue()

    def paths(self, record):
        run_id = record['run_id']
        return (self.storage/(run_id+'.zip'), self.storage/(run_id+'.receipt.json'),
                self.destination/'runtime'/('test-088-evidence-'+run_id+'.zip'))

    def test_saved_run_exports_only_verified_raw_members_same_uuid_without_device_or_classifier(self):
        record = self.saved(extras=True); before = self.snapshot()
        held = [False]; calls = []
        lock, load, certificate = native.device_lock, native._load, publication._certificate
        @contextmanager
        def checked_lock(path):
            self.assertEqual(self.normal/'publication.lock', path)
            with lock(path):
                held[0] = True
                try: yield
                finally: held[0] = False
        def checked_load(base):
            self.assertTrue(held[0]); calls.append('load'); return load(base)
        def checked_certificate(*args):
            self.assertTrue(held[0]); self.assertEqual(['load'], calls)
            calls.append('certificate'); return certificate(*args)
        with patch.object(native, 'device_lock', checked_lock), patch.object(native, '_load', checked_load), \
                patch.object(publication, '_certificate', checked_certificate):
            code, output = self.invoke()
        self.assertEqual(0, code); self.assertEqual(['load', 'certificate'], calls)
        self.assertIn('対象判定未完', output); self.assertIn('証拠', output)
        self.assertEqual(before, self.snapshot())
        local, receipt, final = self.paths(record)
        folder = 'test-088/native-'+record['run_id']
        names = ['test-088/active.json', folder+'/report.json', folder+'/images/'+record['images'][0]['name']]
        with zipfile.ZipFile(final) as archive:
            self.assertEqual(names, archive.namelist()); self.assertIsNone(archive.testzip())
            for info in archive.infolist():
                self.assertEqual(zipfile.ZIP_STORED, info.compress_type)
                self.assertEqual((1980,1,1,0,0,0), info.date_time)
                source = self.base/info.filename[len('test-088/'):]
                self.assertEqual(source.read_bytes(), archive.read(info))
        self.assertEqual(local.read_bytes(), final.read_bytes())
        value = json.loads(receipt.read_bytes())
        self.assertEqual({'schema', 'run_id', 'report_sha256', 'archive_bytes', 'archive_sha256'}, set(value))
        self.assertEqual('ngg2-evidence-088-v1', value['schema']); self.assertEqual(record['run_id'], value['run_id'])
        self.assertEqual(hashlib.sha256(final.read_bytes()).hexdigest(), value['archive_sha256'])

    def test_repeat_and_changed_destination_revalidate_but_corrupt_or_foreign_artifacts_are_not_overwritten(self):
        record = self.saved(); self.assertEqual(0, self.invoke()[0])
        local, receipt, final = self.paths(record)
        frozen = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in (local, receipt, final)}
        self.assertEqual(0, self.invoke()[0])
        self.assertEqual(frozen, {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in frozen})
        self.destination = self.root/'another-source'; self.destination.mkdir()
        self.assertEqual(0, self.invoke()[0]); copied = self.paths(record)[2]
        self.assertEqual(final.read_bytes(), copied.read_bytes())
        self.assertEqual(frozen[receipt], (receipt.read_bytes(), receipt.stat().st_mtime_ns))
        broken_crc = bytearray(copied.read_bytes())
        with zipfile.ZipFile(copied) as archive:
            info = archive.infolist()[-1]
            broken_crc[info.header_offset+len(info.FileHeader())] ^= 1
        for path, corruptions in ((copied, (b'foreign archive', bytes(broken_crc))), (local, (b'corrupt local ZIP',)),
                (receipt, (b'{}', json.dumps(dict(json.loads(receipt.read_bytes()), archive_bytes=True)).encode(),
                           json.dumps(dict(json.loads(receipt.read_bytes()), schema='ngg2-publication-v1')).encode(),
                           json.dumps(dict(json.loads(receipt.read_bytes()), archive_sha256='0'*64)).encode(),
                           json.dumps(dict(json.loads(receipt.read_bytes()), extra=1)).encode()))):
            original = path.read_bytes()
            for corrupted in corruptions:
                with self.subTest(path=path.name, corrupted=corrupted[:40]):
                    path.write_bytes(corrupted); before = self.snapshot()
                    self.assertEqual(2, self.invoke()[0]); self.assertEqual(corrupted, path.read_bytes())
                    self.assertEqual(before, self.snapshot())
            path.write_bytes(original)

    def test_invalid_sources_symlinks_and_int_term_preserve_originals_without_false_completion(self):
        for fault in ('empty', 'unresolved', 'cursor', 'missing', 'corrupt', 'active-link', 'image-link',
                      'images-link', 'run-link', 'lock-link', 'storage-link', 'output-link', 'receipt-link'):
            with self.subTest(fault=fault):
                self.configure(fault)
                if fault != 'empty':
                    record = self.saved(); folder = self.base/('native-'+record['run_id'])
                    image = folder/'images'/record['images'][0]['name']
                    if fault == 'unresolved': record['resolved'] = False; native._save(self.base, record)
                    elif fault == 'cursor':
                        record['image_export']['offsets'][0] = 0
                        record['image_export']['prefix_sha256'][0] = hashlib.sha256(b'').hexdigest()
                        native._save(self.base, record)
                    elif fault == 'missing': image.unlink()
                    elif fault == 'corrupt': image.write_bytes(self.pixels+b'changed')
                    elif fault.endswith('-link'):
                        path = {'active-link': self.base/'active.json', 'image-link': image,
                            'images-link': folder/'images', 'run-link': folder,
                            'lock-link': self.normal/'publication.lock', 'storage-link': self.storage,
                            'output-link': self.destination/'runtime',
                            'receipt-link': self.storage/(record['run_id']+'.receipt.json')}[fault]
                        path.parent.mkdir(parents=True, exist_ok=True)
                        target_path = self.root/(fault+'-target')
                        if path.exists(): path.rename(target_path)
                        elif fault in ('storage-link', 'output-link'): target_path.mkdir()
                        else: target_path.write_bytes(b'foreign')
                        path.symlink_to(target_path)
                before = self.snapshot()
                code, output = self.invoke()
                self.assertEqual(2, code); self.assertIn('保持', output)
                self.assertNotIn('証拠ZIPの保存・照合が完了', output)
                self.assertEqual(before, self.snapshot())
        for sig in (signal.SIGINT, signal.SIGTERM):
            with self.subTest(signal=sig):
                self.configure('signal-'+str(sig)); record = self.saved(extras=True); before = self.snapshot()
                previous = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}
                copy = publication._copy
                def interrupted_copy(*args):
                    signal.getsignal(sig)(sig, None)
                    return copy(*args)
                with patch.object(publication, '_copy', side_effect=interrupted_copy):
                    code, output = self.invoke()
                self.assertEqual(130, code); self.assertIn('保持', output)
                self.assertEqual(before, self.snapshot()); self.assertFalse(self.paths(record)[1].exists())
                for s, handler in previous.items(): self.assertIs(handler, signal.getsignal(s))

    def test_evidence_receipt_does_not_publish_the_normal_run_or_allow_new_session(self):
        record = self.saved(); self.assertEqual(0, self.invoke()[0])
        self.assertFalse(publication._published(self.base, self.destination, record, self.normal, lambda: False, '088'))
        class PrepareReached(RuntimeError): pass
        reached = []
        def prepare(base, current, report_sha, cancelled):
            self.assertEqual(self.base, base); self.assertEqual(record, current)
            reached.append(current['run_id']); raise PrepareReached()
        with self.local_only(normal_publication=True), self.assertRaises(PrepareReached):
            publication.run(self.destination, spool=self.base,
                session=lambda _: self.fail('evidence export must keep normal publication pending'),
                test_number='088', prepare=prepare, notice=lambda _: None)
        self.assertEqual([record['run_id']], reached)
        self.assertFalse((self.normal/(record['run_id']+'.receipt.json')).exists())


if __name__ == '__main__':
    unittest.main()
