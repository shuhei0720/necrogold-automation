"""Bounded local engine bridge fixtures; no game, RPC, or original run writes."""
from contextlib import ExitStack, contextmanager
import hashlib
import json
import os
from pathlib import Path
import signal
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from necroprobe import ring_native as ring


class NativeRing089Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (b'\0'+b'\0\0\0\xff'*896)*414

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='ring089-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.resources = self.root/'source/necroprobe'; self.resources.mkdir(parents=True)
        self.home = self.root/'home'; self.home.mkdir()
        self.run = self.home/'.necroprobe/runtime/test-088/native-saved'
        self.run.mkdir(parents=True)
        (self.run/'report.json').write_bytes(b'unchanged native report')
        (self.run/'image.png').write_bytes(b'unchanged original pixels')
        self.features = b'fixed feature bytes for bridge fixture'
        self.feature_sha = hashlib.sha256(self.features).hexdigest()
        (self.resources/'target_ring_features.json').write_bytes(self.features)
        self.binary = b'\x7fELF\x01\x01\x01'+bytes(9)+struct.pack('<HHIIIIIHHHHHH',
            2,3,1,0x1000,52,0,0,52,32,1,0,0,0)+struct.pack('<IIIIIIII',1,0,0x1000,0,85,85,5,4096)+b'\xc3'
        self.binary_path = self.resources/'bin/ring-i386'; self.binary_path.parent.mkdir()
        self.binary_path.write_bytes(self.binary)
        source = self.resources.parent/'tools/ring_native/main.c'; source.parent.mkdir(parents=True)
        source.write_bytes(b'fixed engine source fixture')
        self.manifest_path = self.resources/'ring_native_manifest.json'
        self.manifest = dict(schema='ngg2-ring-engine-v1', protocol='ngg2-ring-raw-v1', binary='ring-i386',
            binary_bytes=len(self.binary), binary_sha256=hashlib.sha256(self.binary).hexdigest(),
            features_sha256=self.feature_sha,
            sources={'tools/ring_native/main.c': hashlib.sha256(source.read_bytes()).hexdigest()},
            toolchain=dict(name='zig',version='0.15.2',target='x86-linux-musl',cpu='i386',flags='-O ReleaseFast',
                libc='musl-bundled-with-zig-0.15.2',source_date_epoch='0'))
        self.write_manifest()
        self.reply = dict(protocol='ngg2-ring-raw-v1', features_sha256=self.feature_sha,
            input_sha256=hashlib.sha256(self.raw).hexdigest(), rows=[dict(row=[267,153], slots=[
                dict(score=.3,box=[267+36*slot-16,177,33,28],word=dict(iou=.1,coverage=.1,box=[267+36*slot-42,133,84,11]))
                for slot in range(3)])])
        self.children = []
        self.mode = 'good'; self.response = None

    def write_manifest(self):
        self.manifest_path.write_text(json.dumps(self.manifest))

    def snapshot(self):
        return {str(p.relative_to(self.run)): (p.read_bytes(),p.stat().st_mtime_ns)
                for p in self.run.iterdir()}

    @property
    def cached(self):
        return self.home/'.necroprobe/engines'/('ring-'+self.manifest['binary_sha256'])

    def fake_child(self, argv, **kwargs):
        self.assertEqual([str(self.cached)], argv)
        self.assertFalse(kwargs.get('shell', False)); self.assertEqual({}, kwargs['env'])
        self.assertTrue(kwargs['close_fds'])
        reply = json.dumps(self.reply) if self.response is None else self.response
        common = "import hashlib,json,os,signal,struct,sys,time\n"
        if self.mode in ('stall', 'ignore-term'):
            body = "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n" if self.mode == 'ignore-term' else ''
            body += 'time.sleep(10)\n'
        else:
            body = "header=sys.stdin.buffer.read(80)\nraw=sys.stdin.buffer.read()\n"
            body += "assert header[:8]==b'NG2RING1' and struct.unpack('<I',header[12:16])[0]==len(raw)==1484190\n"
            body += "assert struct.unpack('<I',header[8:12])[0]=="+str(int(sys.version_info[:2]==(3,12)))+"\n"
            body += "assert header[48:80]==hashlib.sha256(raw).digest()\n"
            if self.mode == 'stdout-overflow': body += "sys.stdout.buffer.write(b'x'*8193)\n"
            elif self.mode == 'stderr-overflow': body += "sys.stderr.buffer.write(b'x'*2049)\n"
            elif self.mode == 'exit': body += 'sys.exit(7)\n'
            else: body += 'sys.stdout.write('+repr(reply)+')\n'
        child = subprocess.Popen([sys.executable,'-c',common+body], **kwargs)
        self.children.append(child)
        return child

    @contextmanager
    def configured(self, timeout=.3):
        with ExitStack() as stack:
            stack.enter_context(patch.object(ring, '_ROOT', self.resources))
            stack.enter_context(patch.object(ring, '_TIMEOUT', timeout))
            stack.enter_context(patch.object(ring, '_popen', side_effect=self.fake_child))
            stack.enter_context(patch.object(Path,'home',return_value=self.home))
            yield
        for child in self.children:
            self.assertIsNotNone(child.poll(), 'every child must be reaped')
            for stream in (child.stdin,child.stdout,child.stderr): self.assertTrue(stream.closed)

    def invoke(self, cancelled=lambda: False):
        return ring.classify_filtered(self.raw, self.feature_sha, cancelled)

    def test_verified_install_roundtrip_and_repeat_keep_native_run_and_cache_immutable(self):
        before = self.snapshot()
        with self.configured():
            self.assertEqual(self.reply['rows'], self.invoke())
            self.assertEqual(self.binary, self.cached.read_bytes())
            self.assertEqual(0o700, self.cached.stat().st_mode&0o777)
            frozen = self.cached.read_bytes(), self.cached.stat().st_mtime_ns
            self.assertEqual(self.reply['rows'], self.invoke())
            self.assertEqual(frozen,(self.cached.read_bytes(),self.cached.stat().st_mtime_ns))
        self.assertEqual(before,self.snapshot()); self.assertEqual(2,len(self.children))
        self.reply['rows'][0]['slots'][0]['score']=1.00000001
        with self.configured(): self.assertEqual(self.reply['rows'],self.invoke())
        self.reply['rows'][0]['slots'][0]['score']=1.000001
        with self.configured(): self.assertEqual(self.reply['rows'],self.invoke())
        for index, slot in enumerate(self.reply['rows'][0]['slots']):
            cx=18+36*index; slot['box'][0]=max(0,cx-16)
            slot['word']=None if index==0 else dict(iou=.1,coverage=.1,box=[cx-42,133,84,11])
        self.reply['rows'][0]['row'][0]=18
        with self.configured(): self.assertEqual(self.reply['rows'],self.invoke())
        self.assertEqual(before,self.snapshot())
        with self.configured(),patch.object(ring.sys,'version_info',(3,13,0)),self.assertRaisesRegex(ring.NativeRingError,'ring_python_version'):
            self.invoke()

    def test_manifest_resource_elf_and_existing_cache_fail_closed_without_repairs(self):
        for fault in ('feature','manifest-extra','manifest-bool','source','source-path','toolchain','binary',
                      'elf-interp','elf-dynamic','cache','cache-mode','cache-link'):
            with self.subTest(fault=fault):
                original_manifest = dict(self.manifest); original_binary = self.binary_path.read_bytes()
                source = self.resources.parent/'tools/ring_native/main.c'; source_bytes=source.read_bytes()
                feature_path=self.resources/'target_ring_features.json'; feature_bytes=feature_path.read_bytes()
                if fault=='feature': feature_path.write_bytes(b'changed')
                elif fault=='manifest-extra': self.manifest['extra']=1
                elif fault=='manifest-bool': self.manifest['binary_bytes']=True
                elif fault=='source': source.write_bytes(b'changed')
                elif fault=='source-path': self.manifest['sources']={'../outside': '0'*64}
                elif fault=='toolchain': self.manifest['toolchain']=dict(self.manifest['toolchain'],cpu='i686')
                elif fault=='binary': self.binary_path.write_bytes(b'changed')
                elif fault in ('elf-interp','elf-dynamic'):
                    data=bytearray(self.binary); struct.pack_into('<I',data,52,3 if fault=='elf-interp' else 2)
                    self.binary_path.write_bytes(data); self.manifest['binary_sha256']=hashlib.sha256(data).hexdigest()
                elif fault in ('cache','cache-mode','cache-link'):
                    self.cached.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
                    if fault=='cache': self.cached.write_bytes(b'changed'); self.cached.chmod(0o700)
                    elif fault=='cache-mode': self.cached.write_bytes(self.binary); self.cached.chmod(0o600)
                    else: self.cached.symlink_to(self.binary_path)
                self.write_manifest(); before=self.snapshot(); count=len(self.children)
                with self.configured(),self.assertRaises(ring.NativeRingError): self.invoke()
                self.assertEqual(count,len(self.children)); self.assertEqual(before,self.snapshot())
                if fault=='cache': self.assertEqual(b'changed',self.cached.read_bytes()); self.cached.unlink()
                elif fault=='cache-mode': self.assertEqual(0o600,self.cached.stat().st_mode&0o777); self.cached.unlink()
                elif fault=='cache-link': self.assertTrue(self.cached.is_symlink()); self.cached.unlink()
                self.manifest=original_manifest; self.write_manifest(); self.binary_path.write_bytes(original_binary)
                source.write_bytes(source_bytes); feature_path.write_bytes(feature_bytes)

    def test_reply_keys_hashes_ranges_duplicate_rows_and_nonfinite_numbers_are_rejected(self):
        valid=json.dumps(self.reply)
        faults=[valid[:-1],valid+'x',valid.replace('"protocol":', '"extra":1,"protocol":'),
            valid.replace('"protocol":', '"protocol":"duplicate","protocol":'),
            valid.replace(self.feature_sha,'0'*64),valid.replace(hashlib.sha256(self.raw).hexdigest(),'0'*64),
            valid.replace('0.3','NaN'),valid.replace('0.3','true'),valid.replace('0.3','2.1'),
            valid.replace('0.3','1.5'),valid.replace('0.3','1.0000010001')]
        duplicate=dict(self.reply,rows=self.reply['rows']*2); faults.append(json.dumps(duplicate))
        invalid=json.loads(valid); invalid['rows'][0]['slots'][0]['box'][0]=-1; faults.append(json.dumps(invalid))
        invalid=json.loads(valid); invalid['rows'][0]['slots'][0]['word']['coverage']=1.01; faults.append(json.dumps(invalid))
        invalid=json.loads(valid); invalid['rows'][0]['slots'][0]['word']=None; faults.append(json.dumps(invalid))
        before=self.snapshot()
        with self.configured():
            for response in faults:
                with self.subTest(response=response[:45]),self.assertRaises(ring.NativeRingError):
                    self.response=response; self.invoke()
        self.assertEqual(before,self.snapshot())

    def test_cancel_timeout_output_bounds_nonzero_exit_always_close_and_reap(self):
        before=self.snapshot()
        for mode in ('stall','ignore-term','stdout-overflow','stderr-overflow','exit','cancel'):
            with self.subTest(mode=mode):
                self.mode='stall' if mode=='cancel' else mode
                def cancelled(): return mode=='cancel' and bool(self.children) and self.children[-1].poll() is None
                with self.configured(timeout=.08),self.assertRaises(ring.NativeRingError):
                    self.invoke(cancelled)
                self.assertEqual(before,self.snapshot())
                if mode=='ignore-term': self.assertEqual(-signal.SIGKILL,self.children[-1].returncode)
        count=len(self.children)
        with self.configured(),self.assertRaises(ring.NativeRingError): self.invoke(lambda: True)
        self.assertEqual(count,len(self.children))


if __name__=='__main__': unittest.main()
