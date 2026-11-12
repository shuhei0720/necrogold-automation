"""Compiled local assessment through the saved TEST088 publication entry.

Only procedural stdlib PNG data is used. A test harness may select QEMU for
development hosts; the product has no runner/environment override.
"""
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

from necroprobe import native_walk as native, ring_native as ring
from necroprobe import target_assessment as target, test069 as publication, test088
from tests.test_recover087 import seed
from tests.test_target_assessment087 import png, shop

TEST_RUNNER_PREFIX = []


class RingPublication089Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pixels = png(shop())

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ring-publication089-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.configure('initial')

    def configure(self, name):
        self.user = self.root/name/'user'; self.user.mkdir(parents=True)
        self.base = self.user/'.necroprobe/runtime/test-088'
        self.destination = self.root/name/'mounted'; self.destination.mkdir()
        self.record = seed(self.base, self.pixels)
        self.folder = self.base/('native-'+self.record['run_id'])
        self.storage = self.base.parent/'.test-088-publication'
        self.evidence = self.base.parent/'.test-088-evidence'; self.evidence.mkdir()
        (self.evidence/'preserved.zip').write_bytes(b'previous diagnostic archive')
        (self.evidence/'preserved.receipt.json').write_bytes(b'previous diagnostic receipt')

    def originals(self):
        paths = list(self.base.rglob('*'))+list(self.evidence.rglob('*'))
        return {path: (path.read_bytes(),path.stat().st_mtime_ns) for path in paths if path.is_file()}

    def assert_unchanged(self, before):
        self.assertEqual(before,{path:(path.read_bytes(),path.stat().st_mtime_ns) for path in before})
        self.assertEqual({p for p in before if self.evidence in p.parents},
                         {p for p in self.evidence.rglob('*') if p.is_file()})
        self.assertEqual(self.record,native._load(self.base))

    @contextmanager
    def local_entry(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(Path,'home',return_value=self.user))
            stack.enter_context(patch.object(Path,'cwd',return_value=self.destination))
            forbidden = [stack.enter_context(patch.object(native,name,
                side_effect=AssertionError('saved publication called '+name)))
                for name in ('main','run_session','Client','NativeClient','HttpTransport')]
            if TEST_RUNNER_PREFIX:
                launch = ring._popen
                stack.enter_context(patch.object(ring,'_popen',
                    side_effect=lambda argv,**kwargs: launch(list(TEST_RUNNER_PREFIX)+argv,**kwargs)))
            yield
            for called in forbidden: called.assert_not_called()

    def invoke(self):
        with self.local_entry(),patch('sys.stdout',new_callable=io.StringIO) as output:
            result = test088.main([])
        return result,output.getvalue()

    def test_compiled_saved_run_publishes_same_uuid_canonical_sidecar_and_verified_zip_without_rpc(self):
        before = self.originals()
        with patch.object(ring,'_exchange',wraps=ring._exchange) as engine:
            code,output = self.invoke()
        self.assertEqual(0,code); self.assertEqual(1,engine.call_count)
        self.assertIn('のろいのゆびわ',output); self.assertIn('保存・照合が完了',output)
        self.assert_unchanged(before)
        raw = (self.folder/target.SIDECAR).read_bytes(); value = json.loads(raw)
        self.assertEqual('target',value['outcome']); self.assertEqual(self.record['run_id'],value['run_id'])
        self.assertEqual(raw,target._encoded(value))
        score = value['sources'][0]['slots'][1]['icon_score']
        self.assertIs(type(score),float); self.assertEqual(1.0,score)
        self.assertIn(b'"icon_score":1.0',raw)
        self.assertIs(type(value['sources'][0]['word']['iou']),float)
        self.assertEqual(1.0,value['sources'][0]['word']['iou'])
        final = self.destination/'runtime'/('test-088-'+self.record['run_id']+'.zip')
        with zipfile.ZipFile(final) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(raw,archive.read('test-088/'+self.folder.name+'/'+target.SIDECAR))
            for path,(data,_mtime) in before.items():
                if self.base in path.parents:
                    self.assertEqual(data,archive.read('test-088/'+path.relative_to(self.base).as_posix()))
        receipt = json.loads((self.storage/(self.record['run_id']+'.receipt.json')).read_bytes())
        self.assertEqual('ngg2-publication-v1',receipt['schema'])
        self.assertEqual(self.record['run_id'],receipt['run_id'])
        self.assertEqual(hashlib.sha256(final.read_bytes()).hexdigest(),receipt['archive_sha256'])
        self.assertEqual(final.stat().st_size,receipt['archive_bytes'])
        self.assertTrue(publication._published(self.base,self.destination,self.record,self.storage,lambda:False,'088'))

    def test_helper_faults_and_int_term_keep_pending_originals_and_show_only_fixed_reasons(self):
        faults = [(name,None) for name in ('ring_native_timeout','ring_native_reply','ring_native_failed','ring_native_cancelled')]
        faults += [('ring_native_cancelled',sig) for sig in (signal.SIGINT,signal.SIGTERM)]
        faults += [('/private/untrusted-token-path',None)]
        for index,(reason,sig) in enumerate(faults):
            with self.subTest(reason=reason,signal=sig):
                self.configure('fault-'+str(index)); before = self.originals()
                previous = {s:signal.getsignal(s) for s in (signal.SIGINT,signal.SIGTERM)}
                def failed_engine(*_args):
                    if sig is not None: signal.getsignal(sig)(sig,None)
                    raise ring.NativeRingError(reason)
                with patch.object(ring,'_exchange',side_effect=failed_engine) as engine:
                    code,output = self.invoke()
                self.assertEqual(2,code); self.assertEqual(1,engine.call_count)
                self.assertIn('未完了',output); self.assertIn('保持',output)
                if reason.startswith('ring_native_'): self.assertIn(reason,output)
                else: self.assertNotIn(reason,output)
                self.assertNotIn(str(self.user),output); self.assertNotIn('保存・照合が完了',output)
                self.assert_unchanged(before)
                self.assertFalse((self.folder/target.SIDECAR).exists())
                self.assertFalse(list(self.storage.glob('*.zip')))
                self.assertFalse(list(self.storage.glob('*.receipt.json')))
                self.assertFalse(list(self.destination.rglob('*.zip')))
                for s,handler in previous.items(): self.assertIs(handler,signal.getsignal(s))


if __name__=='__main__': unittest.main()
