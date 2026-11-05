import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location("source_info", Path(__file__).resolve().parents[1] / "tools/inspect_capture_source.py")
source = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(source)

class SourceInfoTests(unittest.TestCase):
    def test_keep_expected_fields_and_drop_private_values(self):
        expected = {"server_version": "1.98.14", "build": "2026-11-05 12:00", "protocol_version": 1,
                    "point_width": 414, "point_height": 896, "pixel_width": 828, "pixel_height": 1792, "scale": 2}
        result = source.sanitize(dict(expected, device_name="PRIVATE", device_id="PRIVATE", token="PRIVATE",
                                      capabilities=["video_stream", "stream_ticket", "PRIVATE"]))
        self.assertEqual(expected, result.get("values"))
        self.assertEqual([], result["issues"])
        self.assertEqual(["video_stream", "stream_ticket"], result["known_capabilities"])
        self.assertNotIn("PRIVATE", str(result))

    def test_missing_fields_are_explicit(self):
        result = source.sanitize({})
        self.assertEqual({}, result['values'])
        self.assertEqual(8, len(result['issues']))
        self.assertTrue(all(x.endswith('_missing') for x in result['issues']))
        self.assertEqual([], result['known_capabilities'])

    def test_invalid_values_never_escape(self):
        import math
        for key, values in {
            'server_version': ['', 'x'*65, 'bad\nPRIVATE', '日本語', None, 10, True],
            'build': ['\x00PRIVATE', 'x'*65, [], {}],
            'protocol_version': [True, 1.5, 0, 10001, float('nan'), '1'],
            'point_width': [True, 0, -1, 4097, float('nan'), float('inf'), '414'],
            'point_height': [None, {}, []],
            'pixel_width': [1.5, 0, 8193, True, float('inf')],
            'pixel_height': [-1, float('nan'), '1792'],
            'scale': [True, 0, 9, float('inf'), float('nan')],
        }.items():
            for value in values:
                with self.subTest(key=key, value=value):
                    result = source.sanitize({key: value, 'device_name': 'PRIVATE'})
                    self.assertNotIn(key, result['values'])
                    self.assertIn(key+'_invalid', result['issues'])
                    self.assertNotIn('PRIVATE', str(result))

    def test_boundary_values_and_wrong_capabilities(self):
        result = source.sanitize({'server_version': 'a'*64, 'build': '1._:+- ', 'protocol_version': 10000,
                                  'point_width': .1, 'point_height': 4096, 'pixel_width': 1,
                                  'pixel_height': 8192, 'scale': 8, 'capabilities': {'video_stream': True}})
        self.assertEqual([], result['issues'])
        self.assertEqual([], result['known_capabilities'])
        expected = ['run_steps', 'wait_for', 'screenshot_stream', 'video_stream', 'stream_ticket']
        self.assertEqual(expected, source.sanitize({'capabilities': expected + ['PRIVATE', 'run_steps']})['known_capabilities'])
        for value in [None, [], 'PRIVATE']:
            self.assertEqual({}, source.sanitize(value)['values'])

class QueryTests(unittest.TestCase):
    def test_parent_rejects_valid_json_with_private_extra_keys(self):
        import sys
        result = source.run_query([sys.executable, '-c', 'print(\'{"token":"PRIVATE"}\')'])
        self.assertEqual({'error': 'source_info_invalid_output'}, result)
        self.assertNotIn('PRIVATE', str(result))

    def child(self, text, code=0):
        import sys
        return [sys.executable, '-c', 'import sys; print(%r); sys.stderr.write("PRIVATE"); sys.exit(%d)' % (text, code)]

    def test_normal_output_is_reconstructed(self):
        import json
        expected = {'server': source.sanitize({'server_version': '1.98.14', 'capabilities': ['video_stream']}),
                    'crypto_engine': 'python'}
        self.assertEqual(expected, source.run_query(self.child(json.dumps(expected))))

    def test_invalid_output_and_failed_children(self):
        import json
        good = {'server': source.sanitize({}), 'crypto_engine': 'native_i386'}
        candidates = ['PRIVATE', '[]', 'x'*4097]
        for extra in [dict(good, token='PRIVATE'), dict(good, crypto_engine='PRIVATE'),
                      dict(good, server=dict(good['server'], issues=['PRIVATE'])),
                      dict(good, server=dict(good['server'], values={'device_name': 'PRIVATE'})),
                      dict(good, server=dict(good['server'], known_capabilities=['PRIVATE'])),
                      dict(good, server=[]), dict(good, server=dict(good['server'], issues=[]))]:
            candidates.append(json.dumps(extra))
        for text in candidates:
            with self.subTest(text=text[:80]):
                self.assertEqual({'error': 'source_info_invalid_output'}, source.run_query(self.child(text)))
        self.assertEqual({'error': 'source_info_worker_failed', 'returncode': 7}, source.run_query(self.child('PRIVATE', 7)))
        self.assertEqual({'error': 'source_info_start_failed'}, source.run_query(['/nonexistent-source-info-fixture']))

    def test_deadline_recovers_owned_child(self):
        import os, sys, tempfile, time
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder)/'pid'
            code = 'import os,time; from pathlib import Path; Path(%r).write_text(str(os.getpid())); time.sleep(30)' % str(marker)
            start = time.monotonic()
            result = source.run_query([sys.executable, '-c', code], timeout=.3)
            self.assertEqual({'error': 'source_info_deadline'}, result)
            self.assertLess(time.monotonic()-start, 2)
            self.assertTrue(marker.exists())
            with self.assertRaises(ProcessLookupError): os.kill(int(marker.read_text()), 0)

    def test_parent_interrupt_and_term_recover_child(self):
        import json, os, signal, subprocess, sys, tempfile, time
        for sig, group in [(signal.SIGINT, False), (signal.SIGTERM, False), (signal.SIGINT, True), (signal.SIGTERM, True)]:
            with self.subTest(signal=sig), tempfile.TemporaryDirectory() as folder:
                marker = Path(folder)/'pid'
                child = 'import os,time; from pathlib import Path; Path(%r).write_text(str(os.getpid())); time.sleep(30)' % str(marker)
                parent = ('import importlib.util,json,sys; s=importlib.util.spec_from_file_location("s",%r); '
                          'm=importlib.util.module_from_spec(s); s.loader.exec_module(m); '
                          'print(json.dumps(m.run_query([sys.executable,"-c",%r])))') % (SPEC.origin, child)
                p = subprocess.Popen([sys.executable, '-c', parent], stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
                try:
                    limit = time.monotonic()+5
                    while not marker.exists() and p.poll() is None and time.monotonic()<limit: time.sleep(.01)
                    self.assertTrue(marker.exists())
                    os.killpg(p.pid, sig) if group else p.send_signal(sig)
                    stdout, stderr = p.communicate(timeout=3)
                    self.assertEqual(0, p.returncode, stderr)
                    self.assertEqual({'error':'source_info_cancelled'}, json.loads(stdout))
                    with self.assertRaises(ProcessLookupError): os.kill(int(marker.read_text()), 0)
                finally:
                    try: os.killpg(p.pid, signal.SIGKILL)
                    except ProcessLookupError: pass
                    p.communicate(timeout=2)

    def test_signal_handlers_restored(self):
        import signal
        before = [signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)]
        source.run_query(self.child('{}'))
        self.assertEqual(before, [signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)])


class ProbeContractTests(unittest.TestCase):
    def test_only_one_read_uses_owned_timer_and_never_launches(self):
        from unittest.mock import patch, MagicMock
        import necroprobe.protocol as protocol
        import necroprobe.crypto as crypto
        import necroprobe.deadlines as deadlines
        reply = protocol.RpcReply({'server_version':'1.2.3', 'token':'PRIVATE'}, {})
        client = MagicMock()
        client.call.return_value = reply
        timer = MagicMock()
        timer.__enter__.return_value = timer
        with patch.object(protocol, 'load_pairing', return_value=(b'fixture', 'PRIVATE')), \
             patch.object(protocol, 'HttpTransport'), patch.object(protocol, 'Client', return_value=client) as ctor, \
             patch.object(crypto, 'Crypto', return_value=type('C', (), {'engine':'python'})()), \
             patch.object(deadlines, 'OwnedRpcTimer', return_value=timer):
            result = source.probe_device()
        client.call.assert_called_once_with('device_info')
        self.assertFalse(ctor.call_args.kwargs['allow_launch'])
        self.assertEqual(8, ctor.call_args.kwargs['timeout'])
        self.assertIs(timer, ctor.call_args.kwargs['deadline_owner'])
        timer.__enter__.assert_called_once()
        timer.__exit__.assert_called_once()
        self.assertNotIn('PRIVATE', str(result))

    def test_standalone_file_and_worker_resolve_package_from_cwd(self):
        import json, os, subprocess, sys, tempfile
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            package = root/'necroprobe'; package.mkdir()
            (package/'__init__.py').write_text('VERSION="P1.4"\n')
            (package/'crypto.py').write_text('class Crypto:\n    engine="python"\n')
            (package/'deadlines.py').write_text('class OwnedRpcTimer:\n    def __enter__(self): return self\n    def __exit__(self,*args): pass\n')
            (package/'protocol.py').write_text('''
def load_pairing(*args): return b"fixture", "PRIVATE"
class HttpTransport: pass
class Client:
    def __init__(self,*args,**kwargs):
        assert kwargs["timeout"] == 8 and kwargs["allow_launch"] is False
    def call(self, method):
        assert method == "device_info"
        from pathlib import Path
        with Path("calls").open("a") as file: file.write(method+"\\n")
        return type("Reply", (), {"result":{"server_version":"1.98.14", "token":"PRIVATE"}})()
''')
            env = {k:v for k,v in os.environ.items() if k != 'PYTHONPATH'}
            for args in [[], ['--worker']]:
                result = subprocess.run([sys.executable, SPEC.origin]+args, cwd=folder, env=env, capture_output=True, text=True, timeout=5)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual('1.98.14', json.loads(result.stdout)['server']['values']['server_version'])
                self.assertNotIn('PRIVATE', result.stdout+result.stderr)
            self.assertEqual(['device_info','device_info'], (root/'calls').read_text().splitlines())
            (package/'__init__.py').write_text('VERSION="old"\n')
            result = subprocess.run([sys.executable, SPEC.origin], cwd=folder, env=env, capture_output=True, text=True, timeout=5)
            self.assertEqual(2, result.returncode)
            self.assertEqual({'error':'requires_P1.4'}, json.loads(result.stdout))

class QueryBoundaryTests(unittest.TestCase):
    def test_signal_during_spawn_is_retained_until_child_is_owned(self):
        import os, signal, subprocess, sys
        from unittest.mock import patch
        real = subprocess.Popen
        for signum in (signal.SIGINT, signal.SIGTERM):
            children = []
            def injected(*args, **kwargs):
                process = real(*args, **kwargs)
                children.append(process)
                os.kill(os.getpid(), signum)
                return process
            try:
                with self.subTest(signal=signum), patch.object(source.subprocess, 'Popen', side_effect=injected):
                    result = source.run_query([sys.executable, '-c', 'import time; time.sleep(30)'])
                self.assertEqual({'error': 'source_info_cancelled'}, result)
                self.assertIsNotNone(children[0].poll(), 'a cancelled spawn must be reaped')
            finally:
                for process in children:
                    if process.poll() is None: process.kill()
                    process.communicate(timeout=2)

    def test_cleanup_failure_is_fixed_and_always_restores_handlers(self):
        import signal, subprocess
        from unittest.mock import patch, MagicMock
        before = [signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)]
        fake = MagicMock()
        fake.poll.return_value = None
        fake.communicate.side_effect = subprocess.TimeoutExpired('PRIVATE', 1)
        with patch.object(source.subprocess, 'Popen', return_value=fake):
            result = source.run_query(['fixture'], timeout=0)
        self.assertEqual({'error':'source_info_cleanup_failed'}, result)
        self.assertEqual(before, [signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)])
        fake.kill.assert_called_once()

    def test_kill_failure_is_fixed_and_restores_handlers(self):
        import signal, subprocess
        from unittest.mock import patch, MagicMock
        before = [signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)]
        fake = MagicMock()
        fake.poll.return_value = None
        fake.communicate.side_effect = subprocess.TimeoutExpired('PRIVATE', 1)
        fake.kill.side_effect = OSError('PRIVATE')
        with patch.object(source.subprocess, 'Popen', return_value=fake):
            self.assertEqual({'error':'source_info_cleanup_failed'}, source.run_query(['fixture'], timeout=0))
        self.assertEqual(before, [signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)])

    def test_spawn_time_reduces_remaining_budget(self):
        import json
        from unittest.mock import patch, MagicMock
        fake = MagicMock()
        fake.returncode = 0
        fake.poll.return_value = 0
        fake.communicate.return_value = (json.dumps({'error':'requires_P1.4'}).encode(), None)
        with patch.object(source.subprocess, 'Popen', return_value=fake), patch.object(source.time, 'monotonic', side_effect=[100, 114.95]):
            source.run_query(['fixture'], timeout=15)
        self.assertAlmostEqual(.05, fake.communicate.call_args.kwargs['timeout'])

    def test_signals_at_cleanup_transition_never_skip_child_reaping(self):
        import os, signal, subprocess, sys
        from unittest.mock import patch
        real_spawn, real_signal = subprocess.Popen, signal.signal
        for initial in ['cancel', 'deadline']:
            children, injected = [], []
            def spawn(*args, **kwargs):
                child = real_spawn(*args, **kwargs)
                children.append(child)
                if initial == 'cancel': os.kill(os.getpid(), signal.SIGINT)
                return child
            def set_signal(signum, handler):
                result = real_signal(signum, handler)
                if signum == signal.SIGINT and handler == signal.SIG_IGN and not injected:
                    injected.append(True)
                    os.kill(os.getpid(), signal.SIGTERM)
                return result
            try:
                with self.subTest(initial=initial), patch.object(source.subprocess,'Popen',side_effect=spawn), patch.object(source.signal,'signal',side_effect=set_signal):
                    result = source.run_query([sys.executable,'-c','import time; time.sleep(30)'], timeout=0 if initial=='deadline' else 15)
                self.assertEqual({'error':'source_info_cancelled' if initial=='cancel' else 'source_info_deadline'}, result)
                self.assertIsNotNone(children[0].poll())
            finally:
                for child in children:
                    if child.poll() is None: child.kill()
                    child.communicate(timeout=2)
