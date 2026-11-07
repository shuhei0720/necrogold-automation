"""TEST043 thin client: real encrypted HTTP with lost responses and recovery."""
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import hashlib
import errno
from pathlib import Path
import socket
import signal
import stat
import os
import struct
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from necroprobe import native_walk as native
from necroprobe.crypto import Crypto, mac, python_xor
from necroprobe.protocol import HttpTransport
from necroprobe.validation import ProbeError
from test_protocol import KEY, TOK, sealed_reply
from timer_support import TimerTestCase


class NativeServer:
    def __init__(self, *, lose=(), input_state=0, capabilities=None, version=None,
                 finish=False, transform=None):
        self.lose = list(lose)
        self.input_state = input_state
        self.calls = []
        self.runs = {}
        self.capabilities = [native.CAPABILITY] if capabilities is None else capabilities
        self.version = native.API_VERSION if version is None else version
        self.finish = finish
        self.transform = transform

    def __enter__(self):
        fake = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass
            def do_POST(self):
                body = self.rfile.read(int(self.headers['Content-Length']))
                envelope = json.loads(body)
                nonce = bytes.fromhex(envelope['nonce'])
                plain = python_xor(mac(KEY, b'loopctrl-v1|enc-req'+nonce), nonce,
                                   base64.b64decode(envelope['ct']))
                request = json.loads(plain)
                method, params = request['method'], request['params']
                fake.calls.append((method, params))
                if method == 'device_info':
                    result = {'server_version': fake.version, 'capabilities': fake.capabilities}
                else:
                    run_id = params['run_id']
                    if method == 'necro_native_start':
                        fake.runs.setdefault(run_id, 'running')
                    elif method == 'necro_native_cancel':
                        fake.runs[run_id] = 'stopped'
                    elif method == 'necro_native_status' and fake.finish:
                        fake.runs[run_id] = 'completed'
                    state = fake.runs.get(run_id, 'stopped')
                    result = {'run_id': run_id, 'profile': native.PROFILE, 'state': state,
                              'report': {'schema': 'ngg2-native-v1', 'clock_id': run_id,
                                         'device_now_ns': 10, 'input_state': fake.input_state,
                                         'paused': 0, 'terminal': int(state == 'stopped'),
                                         'reason_name': 'cancelled'}}
                    if method == 'necro_native_results':
                        result['images'] = []
                if fake.transform:
                    result = fake.transform(method, result)
                if method in fake.lose:
                    fake.lose.remove(method)
                    self.close_connection = True
                    self.connection.shutdown(socket.SHUT_RDWR)
                    return
                raw = sealed_reply(body, result=result)
                self.send_response(200)
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=.01), daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=1)

    def client(self, timer):
        return native.NativeClient(HttpTransport(self.server.server_port), KEY, TOK,
                                   deadline_owner=timer, crypto=Crypto(native=False), timeout=.5)


class NativeWalkTests(TimerTestCase):
    def execute(self, server, folder, **options):
        options.setdefault('max_seconds', .03)
        options.setdefault('recovery_seconds', .03)
        options.setdefault('poll_seconds', .001)
        return native.run_session(server.client(self.timer), folder,
                                  lock_path=Path(folder)/'lock', **options)

    def test_lost_start_response_is_never_restarted_and_same_run_is_collected(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(lose=['necro_native_start']) as server:
            result = native.run_session(server.client(self.timer), folder,
                                        lock_path=Path(folder)/'lock', poll_seconds=.001, max_seconds=.1)
            starts = [p for m,p in server.calls if m == 'necro_native_start']
            self.assertEqual(1, len(starts))
            self.assertTrue(result['resolved'])
            self.assertEqual({'run_id': starts[0]['run_id'], 'profile': native.PROFILE}, starts[0])
            self.assertTrue(all(p.get('run_id') == starts[0]['run_id']
                                for m,p in server.calls if m != 'device_info'))

    def test_persisted_run_exists_before_the_start_rpc(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(lose=['necro_native_status']) as server:
            client = server.client(self.timer)
            call = client.call
            snapshots = []
            def checked(method, params=None, **kwargs):
                if method == 'necro_native_start':
                    snapshots.append(json.loads((Path(folder)/'active.json').read_text()))
                return call(method, params, **kwargs)
            client.call = checked
            native.run_session(client, folder, lock_path=Path(folder)/'lock', poll_seconds=.001, max_seconds=.1)
            self.assertEqual(1, len(snapshots))
            self.assertTrue(snapshots[0]['start_attempted'])
            self.assertEqual(server.calls[1][1]['run_id'], snapshots[0]['run_id'])

    def test_unknown_terminal_is_retained_and_reexecution_cannot_start_again(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(input_state=4) as server:
            options = {'lock_path': Path(folder)/'lock', 'poll_seconds': .001,
                       'max_seconds': .03, 'cancelled': lambda: False}
            first = native.run_session(server.client(self.timer), folder, **options)
            second = native.run_session(server.client(self.timer), folder, **options)
            self.assertEqual(1, sum(m == 'necro_native_start' for m,p in server.calls))
            self.assertFalse(first['resolved'])
            self.assertFalse(second['resolved'])
            self.assertEqual(first['run_id'], second['run_id'])

    def test_poll_loss_cancels_once_and_collects_the_same_session(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(lose=['necro_native_status']) as server:
            result = self.execute(server, folder)
            self.assertTrue(result['resolved'])
            self.assertEqual('connection_error', result['stop_reason'])
            self.assertEqual(1, sum(m == 'necro_native_cancel' for m,p in server.calls))
            self.assertEqual(1, len(server.runs))
            self.assertEqual(result, json.loads((Path(folder)/'active.json').read_text()))

    def test_lost_cancel_and_poll_responses_reconnect_without_restarting_or_discarding(self):
        losses = ['necro_native_status']*100 + ['necro_native_cancel']
        with tempfile.TemporaryDirectory() as folder, NativeServer(lose=losses) as server:
            first = self.execute(server, folder, max_seconds=.01, recovery_seconds=.01)
            self.assertFalse(first['resolved'])
            self.assertTrue(first['cancel_attempted'])
            server.lose.clear()
            second = self.execute(server, folder)
            self.assertTrue(second['resolved'])
            self.assertEqual(first['run_id'], second['run_id'])
            self.assertEqual(1, sum(m == 'necro_native_start' for m,p in server.calls))
            self.assertEqual(1, sum(m == 'necro_native_cancel' for m,p in server.calls))

    def test_inflight_and_reserved_ticket_are_not_replaced_by_a_new_run(self):
        for state in (1, 2, 4):
            with self.subTest(state=state), tempfile.TemporaryDirectory() as folder, NativeServer(input_state=state) as server:
                first = self.execute(server, folder)
                second = self.execute(server, folder)
                self.assertFalse(first['resolved'])
                self.assertFalse(second['resolved'])
                self.assertEqual(first['run_id'], second['run_id'])
                self.assertEqual(1, len(server.runs))

    def test_before_start_cancellation_is_input_zero_and_after_start_sends_one_cancel(self):
        for immediate in (True, False):
            with self.subTest(immediate=immediate), tempfile.TemporaryDirectory() as folder, NativeServer() as server:
                stop = lambda: immediate or any(m == 'necro_native_start' for m,p in server.calls)
                result = self.execute(server, folder, cancelled=stop)
                self.assertTrue(result['resolved'])
                self.assertEqual(int(not immediate), sum(m == 'necro_native_start' for m,p in server.calls))
                self.assertEqual(int(not immediate), sum(m == 'necro_native_cancel' for m,p in server.calls))

    def test_missing_capability_or_wrong_api_never_falls_back(self):
        for kwargs in ({'capabilities': []}, {'version': '1.98.14-ngg1'},
                       {'capabilities': {'necrogold_native_v1': True}}):
            with self.subTest(kwargs=kwargs), tempfile.TemporaryDirectory() as folder, NativeServer(**kwargs) as server:
                result = self.execute(server, folder)
                self.assertEqual(['device_info'], [m for m,p in server.calls])
                self.assertEqual('native_capability_missing', result['stop_reason'])
                self.assertTrue(result['resolved'])

    def test_minimal_accepted_report_can_progress_into_completed_results(self):
        def transform(method, result):
            if method == 'necro_native_start':
                result['state'] = 'accepted'
                result['report'] = {key: result['report'][key] for key in (
                    'schema', 'clock_id', 'device_now_ns', 'input_state')}
                result['report']['terminal'] = 0
            return result
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True, transform=transform) as server:
            result = self.execute(server, folder)
            self.assertTrue(result['resolved'])
            self.assertEqual('completed', result['native_state'])
            self.assertEqual(0, sum(m == 'necro_native_cancel' for m,p in server.calls))

    def test_fixed_rpc_allowlist_rejects_extra_owner_coordinates_types_and_methods(self):
        with NativeServer() as server:
            client = server.client(self.timer)
            run_id = 'a'*32
            invalid = [('tap', {'x':1,'y':1}), ('screenshot', {'format':'png', 'scale':1}),
                       ('launch_app', {}), ('device_info', {'owner':'a'}),
                       ('necro_native_start', {'run_id':run_id, 'profile':native.PROFILE, 'x':1}),
                       ('necro_native_start', {'run_id':run_id, 'profile':'arbitrary'}),
                       ('necro_native_status', {'run_id':run_id, 'owner':'a'}),
                       ('necro_native_cancel', {'run_id':run_id, 'actor':'a'}),
                       ('necro_native_results', {'run_id':'../outside'}),
                       ('necro_native_status', {'run_id':True})]
            for method, params in invalid:
                with self.subTest(method=method, params=params), self.assertRaises(ProbeError):
                    client.call(method, params)
            self.assertEqual([], server.calls)

    def test_terminal_results_response_loss_is_retained_and_can_be_recovered(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True, lose=['necro_native_results']) as server:
            first = self.execute(server, folder)
            self.assertFalse(first['resolved'])
            second = self.execute(server, folder)
            self.assertTrue(second['resolved'])
            self.assertEqual(first['run_id'], second['run_id'])
            self.assertEqual(1, len(server.runs))

    def test_completed_runs_can_start_a_new_run_and_keep_previous_artifacts(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True) as server:
            first = self.execute(server, folder)
            second = self.execute(server, folder)
            self.assertTrue(first['resolved'] and second['resolved'])
            self.assertNotEqual(first['run_id'], second['run_id'])
            self.assertEqual(2, len(server.runs))
            self.assertTrue((Path(folder)/('native-'+first['run_id'])/'report.json').is_file())

    def test_clock_domains_are_kept_separate_and_free_text_is_removed(self):
        def transform(_method, result):
            if 'report' in result:
                result['report'].update(reason_name='PRIVATE_SECRET', token='PRIVATE_SECRET',
                                        device_now_ns=800_000_000_000_000)
            return result
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True, transform=transform) as server:
            result = self.execute(server, folder)
            self.assertEqual('python.monotonic_ns', result['host_clock_domain'])
            self.assertEqual('device.monotonic_ns', result['native_clock_domain'])
            self.assertEqual(800_000_000_000_000, result['native_report']['device_now_ns'])
            self.assertNotIn('PRIVATE_SECRET', json.dumps(result))
            self.assertTrue(all('host_ns' in row for row in result['events']))

    def test_bad_session_identity_and_nonfinite_or_bool_native_times_stop_safely(self):
        def wrong_id(_method, result):
            if 'run_id' in result:
                result['run_id'] = '0'*32
            return result
        def bool_time(_method, result):
            if 'report' in result:
                result['report']['device_now_ns'] = True
            return result
        def nonfinite_time(_method, result):
            if 'report' in result:
                result['report']['device_now_ns'] = float('nan')
            return result
        def wrong_state(_method, result):
            if 'state' in result:
                result['state'] = ['running']
            return result
        for transform in (wrong_id, bool_time, nonfinite_time, wrong_state):
            with self.subTest(transform=transform.__name__), tempfile.TemporaryDirectory() as folder, NativeServer(transform=transform) as server:
                result = self.execute(server, folder)
                self.assertFalse(result['resolved'])
                self.assertEqual(1, sum(m == 'necro_native_start' for m,p in server.calls))
                self.assertEqual(1, sum(m == 'necro_native_cancel' for m,p in server.calls))

    def test_bad_journal_and_busy_lock_do_not_send_network_requests(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer() as server:
            (Path(folder)/'active.json').write_text('{"run_id":"invalid"}')
            with self.assertRaisesRegex(ProbeError, 'native_journal_invalid'):
                self.execute(server, folder)
            (Path(folder)/'active.json').unlink()
            with native.device_lock(Path(folder)/'lock'):
                with self.assertRaisesRegex(ProbeError, 'already_running'):
                    self.execute(server, folder)
            self.assertEqual([], server.calls)

    def test_checkpoint_failure_after_start_cancels_native_and_keeps_start_journal(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer() as server:
            save = native._save
            failed = [False]
            def fail_after_start(base, record):
                if record['native_state'] == 'running' and not failed[0]:
                    failed[0] = True
                    raise OSError('PRIVATE_STORAGE_DETAILS')
                return save(base, record)
            with patch.object(native, '_save', side_effect=fail_after_start):
                with self.assertRaises(OSError):
                    self.execute(server, folder)
            self.assertEqual(1, sum(m == 'necro_native_cancel' for m,p in server.calls))
            saved = json.loads((Path(folder)/'active.json').read_text())
            self.assertTrue(saved['start_attempted'])
            self.assertFalse(saved['resolved'])

    def test_cold_cli_check_imports_no_image_pipeline_or_execution_modules(self):
        code = ('import sys; from necroprobe import native_walk as n; '
                'assert n.main(["--check"]) == 0; '
                'assert not any(m == "PIL" or m.startswith("PIL.") or '
                'm in ("necroprobe.shop_walk", "necroprobe.restart_loop", "necroprobe.gold_scan", '
                '"necroprobe.shop_navigation", "necroprobe.beat_sync", "necroprobe.session") '
                'for m in sys.modules)')
        result = subprocess.run([sys.executable, '-c', code], capture_output=True, timeout=10)
        self.assertEqual(0, result.returncode, result.stderr.decode())

    def test_sigterm_flag_causes_one_native_cancel_and_saves_results(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer() as server:
            code = ('from necroprobe import native_walk as n; '
                    'from necroprobe.protocol import HttpTransport as H; '
                    'n.HttpTransport=lambda:H(%d); '
                    'n.load_pairing=lambda *_:(%r,%r); '
                    'raise SystemExit(n.main(["--output",%r,"--python-crypto"]))') % (
                        server.server.server_port, KEY, TOK, folder)
            process = subprocess.Popen([sys.executable, '-c', code], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic()+5
                while not any(m == 'necro_native_start' for m,p in server.calls) and process.poll() is None and time.monotonic()<deadline:
                    time.sleep(.01)
                self.assertTrue(any(m == 'necro_native_start' for m,p in server.calls))
                process.send_signal(signal.SIGTERM)
                stdout, stderr = process.communicate(timeout=5)
                self.assertEqual(2, process.returncode, stderr.decode())
                self.assertEqual(1, sum(m == 'necro_native_cancel' for m,p in server.calls))
                saved = json.loads((Path(folder)/'active.json').read_text())
                self.assertTrue(saved['resolved'])
                self.assertTrue(saved['cancel_attempted'])
                self.assertNotIn('PRIVATE', stdout.decode()+stderr.decode())
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=1)

    def test_script_uses_native_entry_without_pillow_preflight(self):
        script = Path(native.__file__).resolve().parents[1]/'test_043.sh'
        result = subprocess.run(['sh', '-n', str(script)], capture_output=True)
        self.assertEqual(0, result.returncode)
        text = script.read_text()
        self.assertIn('necroprobe.native_walk --output runtime/test-043', text)
        self.assertNotIn('necroprobe.preflight', text)


def image_item(name='initial.png', size=32):
    raw = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'+struct.pack('>II',896,414)+bytes(max(0,size-24))
    return {'name':name, 'format':'png', 'data_base64':base64.b64encode(raw).decode(),
            'pixel_width':896, 'pixel_height':414, 'sha256':hashlib.sha256(raw).hexdigest(),
            'capture_id':1, 'capture_start_ns':2, 'capture_end_ns':3}


class NativeImageTests(TimerTestCase):
    def test_results_images_are_validated_hashed_and_saved_without_image_imports(self):
        def transform(method, result):
            if method == 'necro_native_results':
                result['images'] = [image_item()]
            return result
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True, transform=transform) as server:
            result = native.run_session(server.client(self.timer), folder,
                                        lock_path=Path(folder)/'lock', poll_seconds=.001, max_seconds=.03)
            path = Path(folder)/('native-'+result['run_id'])/'images'/'initial.png'
            self.assertTrue(result['resolved'])
            self.assertEqual(image_item()['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertNotIn('data_base64', result['images'][0])

    def test_image_path_hash_dimensions_types_duplicates_and_per_image_limit(self):
        bad = []
        for changes in ({'name':'../active.json'}, {'name':'/initial.png'}, {'name':'a\\b.png'},
                        {'sha256':'0'*64}, {'pixel_width':True}, {'pixel_height':896},
                        {'format':'jpeg'}, {'capture_start_ns':4}, {'capture_id':True},
                        {'data_base64':'!!'}, {'data_base64':base64.b64encode(b'x'*32).decode()}):
            bad.append([dict(image_item(), **changes)])
        bad.extend(([image_item(), image_item()], [image_item(size=native.MAX_IMAGE+1)]))
        for items in bad:
            with self.subTest(items=[{k:v for k,v in i.items() if k!='data_base64'} for i in items]):
                with self.assertRaisesRegex(ProbeError, 'invalid_native_images'):
                    native._images(items)

    def test_image_count_and_aggregate_limits_are_enforced_before_writing(self):
        at_limit = [image_item('frame-'+str(i)+'.png', native.MAX_IMAGE) for i in range(8)]
        self.assertEqual(8, len(native._images(at_limit)))
        with self.assertRaisesRegex(ProbeError, 'invalid_native_images'):
            native._images(at_limit+[image_item('extra.png')])
        with self.assertRaisesRegex(ProbeError, 'invalid_native_images'):
            native._images([image_item('frame-'+str(i)+'.png') for i in range(21)])

    def test_invalid_later_image_prevents_any_image_export_and_retains_run(self):
        def transform(method, result):
            if method == 'necro_native_results':
                result['images'] = [image_item(), image_item('../outside.png')]
            return result
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True, transform=transform) as server:
            result = native.run_session(server.client(self.timer), folder,
                                        lock_path=Path(folder)/'lock', poll_seconds=.001, max_seconds=.03)
            self.assertFalse(result['resolved'])
            self.assertEqual('invalid_native_images', result['stop_reason'])
            self.assertEqual([], list(Path(folder).rglob('*.png')))

    def test_capture_prefix_and_stability_metadata_survive_export(self):
        item = image_item()
        item.update(completed_prefix=7, stable_prefix=False)
        metadata, raw = native._images([item])[0]
        self.assertEqual(7, metadata['completed_prefix'])
        self.assertIs(False, metadata['stable_prefix'])
        item['stable_prefix'] = 0
        with self.assertRaisesRegex(ProbeError, 'invalid_native_images'):
            native._images([item])

    def test_atomic_journal_tolerates_only_unsupported_directory_fsync(self):
        with tempfile.TemporaryDirectory() as folder:
            fsync = native.os.fsync
            def unsupported_directory(fd):
                if stat.S_ISDIR(os.fstat(fd).st_mode):
                    raise OSError(errno.EINVAL, 'unsupported')
                fsync(fd)
            with patch.object(native.os, 'fsync', side_effect=unsupported_directory):
                native._atomic(Path(folder)/'journal', b'committed')
            self.assertEqual(b'committed', (Path(folder)/'journal').read_bytes())
            with patch.object(native.os, 'fsync', side_effect=OSError(errno.EIO, 'disk failure')):
                with self.assertRaises(OSError):
                    native._atomic(Path(folder)/'journal', b'new')
            self.assertEqual(b'committed', (Path(folder)/'journal').read_bytes())
            self.assertEqual([], list(Path(folder).glob('*.tmp-*')))


if __name__ == '__main__':
    unittest.main()
