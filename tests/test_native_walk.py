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


def bind_legacy_api(record):
    """Keep relabelled legacy fixtures faithful to their original ready preflight."""
    if record['revision'] != native.REVISION:
        if record.get('preflight', {}).get('server') is not None:
            record['preflight']['server']['server_version'] = '1.98.14-ngg2'
        if 'api_version' in record.get('result_metadata', {}):
            record['result_metadata']['api_version'] = '1.98.14-ngg2'


class NativeServer:
    def __init__(self, *, lose=(), input_state=0, capabilities=None, version=None,
                 finish=False, transform=None, lose_before=(), reject_info_active=False,
                 reject_info=False, listen=True, schema_transform=None, schema_status=200,
                 schema_raw=None, start_status=None, bad_start_mac=False):
        self.lose = list(lose)
        self.input_state = input_state
        self.calls = []
        self.runs = {}
        self.capabilities = [native.CAPABILITY] if capabilities is None else capabilities
        self.version = native.API_VERSION if version is None else version
        self.finish = finish
        self.transform = transform
        self.lose_before = list(lose_before)
        self.reject_info_active = reject_info_active
        self.reject_info = reject_info
        self.listen = listen
        self.schema_calls = []
        self.schema_transform = schema_transform
        self.schema_status = schema_status
        self.schema_raw = schema_raw
        self.start_status = start_status
        self.bad_start_mac = bad_start_mac
        self.exports = {}
        self.page_transform = None
        self.wire_transform = None

    def __enter__(self):
        fake = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args):
                pass
            def reply(self, status, raw, declared_length='actual'):
                # A correct early client rejection can close before this
                # fixture finishes writing; it is not a server-test failure.
                try:
                    self.send_response(status)
                    if declared_length is not None:
                        self.send_header('Content-Length', str(len(raw)) if declared_length == 'actual'
                                         else str(declared_length))
                    self.end_headers()
                    self.wfile.write(raw)
                except (BrokenPipeError, ConnectionResetError):
                    self.close_connection = True
            def do_GET(self):
                fake.schema_calls.append(self.path)
                result = {'server_version':fake.version, 'protocol_version':1,
                          'capability_tags':fake.capabilities, 'build':'2026-11-07 04:11'}
                if fake.schema_transform:
                    result = fake.schema_transform(result)
                raw = fake.schema_raw if fake.schema_raw is not None else json.dumps(result).encode()
                self.reply(fake.schema_status, raw)
            def do_POST(self):
                body = self.rfile.read(int(self.headers['Content-Length']))
                envelope = json.loads(body)
                nonce = bytes.fromhex(envelope['nonce'])
                plain = python_xor(mac(KEY, b'loopctrl-v1|enc-req'+nonce), nonce,
                                   base64.b64decode(envelope['ct']))
                request = json.loads(plain)
                method, params = request['method'], request['params']
                fake.calls.append((method, params))
                if method == 'necro_native_start' and fake.start_status is not None:
                    self.reply(fake.start_status, b'')
                    return
                if method in fake.lose_before:
                    fake.lose_before.remove(method)
                    self.close_connection = True
                    self.connection.shutdown(socket.SHUT_RDWR)
                    return
                if method == 'device_info' and (fake.reject_info or
                        fake.reject_info_active and 'running' in fake.runs.values()):
                    raw = sealed_reply(body, result={'code':-32004,'message':'native lease'}, rpc_error=True)
                    self.reply(200, raw)
                    return
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
                                         'reason_name': 'cancelled',
                                         'events': [], 'motion_references': [],
                                         'recovery': dict(initial_reacquisitions=0,
                                             post_move_reacquisitions=0, episode_id=0, mode=0,
                                             schedule_deadline_ns=0, visual_deadline_ns=0, ack_ns=0,
                                             record_count=0, dropped_records=0, records=[])}}
                    if method == 'necro_native_results':
                        result['images'] = []
                if fake.transform:
                    result = fake.transform(method, result)
                if method == 'necro_native_results' and params.get('mode') in ('manifest', 'chunk'):
                    if params['mode'] == 'manifest':
                        exported = []
                        raw_images = {}
                        for image in result.get('images', []):
                            try:
                                raw = base64.b64decode(image.get('data_base64', ''))
                            except (ValueError, TypeError):
                                raw = b''
                            metadata = {key:value for key,value in image.items() if key != 'data_base64'}
                            metadata['byte_length'] = len(raw)
                            exported.append(metadata)
                            raw_images[metadata.get('capture_id')] = (metadata, raw)
                        manifest = dict(result, result_mode='manifest', export_id=run_id,
                            chunk_bytes=65536, total_bytes=sum(item['byte_length'] for item in exported),
                            images=exported)
                        fake.exports.setdefault(run_id, (manifest, raw_images))
                        result = manifest
                    else:
                        manifest, raw_images = fake.exports[run_id]
                        metadata, raw = raw_images[params['capture_id']]
                        part = raw[params['offset']:params['offset']+65536]
                        result = dict(run_id=run_id, result_mode='chunk', export_id=manifest['export_id'],
                            capture_id=params['capture_id'], offset=params['offset'],
                            byte_length=len(raw), data_base64=base64.b64encode(part).decode(),
                            sha256=metadata.get('sha256'), chunk_bytes=len(part))
                if fake.page_transform:
                    result = fake.page_transform(method, params, result)
                if method in fake.lose:
                    fake.lose.remove(method)
                    self.close_connection = True
                    self.connection.shutdown(socket.SHUT_RDWR)
                    return
                raw = sealed_reply(body, result=result)
                if method == 'necro_native_start' and fake.bad_start_mac:
                    changed = json.loads(raw)
                    changed['tag'] = '0'*64
                    raw = json.dumps(changed).encode()
                if fake.wire_transform:
                    raw, declared_length = fake.wire_transform(method, params, raw)
                    self.reply(200, raw, declared_length)
                else:
                    self.reply(200, raw)
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler, bind_and_activate=False)
        self.server.server_bind()
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=.01), daemon=True)
        if self.listen:
            self.activate()
        return self

    def activate(self):
        if not self.thread.is_alive():
            self.server.server_activate()
            self.thread.start()

    def __exit__(self, *_args):
        if self.thread.is_alive():
            self.server.shutdown()
        self.server.server_close()
        if self.thread.ident is not None:
            self.thread.join(timeout=1)

    def client(self, timer):
        return native.NativeClient(HttpTransport(self.server.server_port), KEY, TOK,
                                   deadline_owner=timer, crypto=Crypto(native=False), timeout=.5)


class NativeWalkTests(TimerTestCase):
    def execute(self, server, folder, **options):
        options.setdefault('max_seconds', 1)
        options.setdefault('recovery_seconds', 1)
        options.setdefault('poll_seconds', .001)
        return native.run_session(server.client(self.timer), folder,
                                  lock_path=Path(folder)/'lock', **options)

    def unresolved(self, server, folder):
        server.input_state = 4
        record = self.execute(server, folder)
        record['cancel_attempted'] = False
        if 'cancel_attempts' in record:
            record['cancel_attempts'] = 0
        if 'cancel_confirmed' in record:
            record['cancel_confirmed'] = False
        record['state'] = record['native_state'] = 'running'
        record['native_report'].update(input_state=0, terminal=0)
        native._save(Path(folder), record)
        server.runs[record['run_id']] = 'running'
        server.input_state = 0
        server.calls.clear()
        return record

    def test_cancel_lost_before_arrival_is_retried_boundedly_without_keepalive(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(lose=['necro_native_status'], lose_before=['necro_native_cancel']) as server:
            result = self.execute(server, folder)
            self.assertTrue(result['resolved'])
            self.assertEqual(2, sum(m == 'necro_native_cancel' for m,p in server.calls))
            self.assertEqual(2, result['cancel_attempts'])
            status = [p for m,p in server.calls if m == 'necro_native_status']
            self.assertTrue(status[0]['keepalive'])
            self.assertTrue(all(p['keepalive'] is False for p in status[1:]))

    def test_started_recovery_bypasses_lease_rejected_device_info(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer() as server:
            record = self.unresolved(server, folder)
            server.reject_info_active = True
            result = self.execute(server, folder)
            self.assertTrue(result['resolved'])
            self.assertEqual(record['run_id'], result['run_id'])
            self.assertNotIn('device_info', [m for m,p in server.calls])
            self.assertTrue(all(p['keepalive'] is False for m,p in server.calls if m == 'necro_native_status'))

    def test_prepared_journal_resumes_the_same_uuid_with_its_first_start(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True) as server:
            record = self.execute(server, folder, cancelled=lambda: True)
            record.update(resolved=False, state='prepared', stop_reason=None)
            native._save(Path(folder), record)
            result = self.execute(server, folder)
            starts = [p for m,p in server.calls if m == 'necro_native_start']
            self.assertEqual(1, len(starts))
            self.assertEqual(record['run_id'], starts[0]['run_id'])
            self.assertTrue(result['resolved'])

    def test_recovery_initial_save_failure_still_sends_emergency_cancel(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer() as server:
            self.unresolved(server, folder)
            with patch.object(native, '_save', side_effect=OSError('disk full')):
                with self.assertRaises(OSError):
                    self.execute(server, folder, cancelled=lambda: True)
            self.assertEqual(1, sum(m == 'necro_native_cancel' for m,p in server.calls))

    def test_cancel_intent_save_failure_still_sends_emergency_cancel(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer() as server:
            save = native._save
            def fail_cancel_intent(base, record):
                if record['cancel_attempted']:
                    raise OSError('disk full')
                save(base, record)
            with patch.object(native, '_save', side_effect=fail_cancel_intent):
                with self.assertRaises(OSError):
                    self.execute(server, folder, cancelled=lambda: bool(server.runs))
            self.assertEqual(1, sum(m == 'necro_native_cancel' for m,p in server.calls))

    def test_full_diagnostic_ring_never_prevents_same_run_recovery(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer() as server:
            record = self.unresolved(server, folder)
            row = {'invocation':'0'*32,'method':'necro_native_status','host_ns':1,'error':None}
            record['events'] = [dict(row) for _ in range(1024)]
            native._save(Path(folder), record)
            result = self.execute(server, folder)
            self.assertTrue(result['resolved'])
            self.assertLessEqual(len(result['events']), 128)
            self.assertGreaterEqual(result['events_dropped'], 896)

    def test_lost_start_response_is_never_restarted_and_same_run_is_collected(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(lose=['necro_native_start']) as server:
            result = native.run_session(server.client(self.timer), folder,
                                        lock_path=Path(folder)/'lock', poll_seconds=.001, max_seconds=.5)
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
            native.run_session(client, folder, lock_path=Path(folder)/'lock', poll_seconds=.001, max_seconds=.5)
            self.assertEqual(1, len(snapshots))
            self.assertTrue(snapshots[0]['start_attempted'])
            start = next(p for m,p in server.calls if m == 'necro_native_start')
            self.assertEqual(start['run_id'], snapshots[0]['run_id'])

    def test_unknown_terminal_is_retained_and_reexecution_cannot_start_again(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(input_state=4) as server:
            options = {'lock_path': Path(folder)/'lock', 'poll_seconds': .001,
                       'max_seconds': .3, 'cancelled': lambda: False}
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
        losses = ['necro_native_status']*10000 + ['necro_native_cancel']*3
        with tempfile.TemporaryDirectory() as folder, NativeServer(lose=losses) as server:
            first = self.execute(server, folder, max_seconds=.3, recovery_seconds=.3)
            self.assertFalse(first['resolved'])
            self.assertTrue(first['cancel_attempted'])
            attempted = sum(m == 'necro_native_cancel' for m,p in server.calls)
            self.assertGreaterEqual(attempted, 1)
            self.assertLessEqual(attempted, 3)
            server.lose.clear()
            second = self.execute(server, folder)
            self.assertTrue(second['resolved'])
            self.assertEqual(first['run_id'], second['run_id'])
            self.assertEqual(1, sum(m == 'necro_native_start' for m,p in server.calls))
            self.assertEqual(attempted, sum(m == 'necro_native_cancel' for m,p in server.calls))

    def test_cancel_budget_is_durable_across_reexecution_and_never_renews_lease(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(
                lose=['necro_native_status'], lose_before=['necro_native_cancel']*10) as server:
            first = self.execute(server, folder, max_seconds=.5, recovery_seconds=.3)
            self.assertFalse(first['resolved'])
            self.assertEqual(3, first['cancel_attempts'])
            count = sum(m == 'necro_native_cancel' for m,p in server.calls)
            self.assertEqual(3, count)
            last_call = len(server.calls)
            second = self.execute(server, folder)
            self.assertFalse(second['resolved'])
            self.assertEqual(3, second['cancel_attempts'])
            self.assertEqual(count, sum(m == 'necro_native_cancel' for m,p in server.calls))
            self.assertTrue(all(p['keepalive'] is False for m,p in server.calls[last_call:]
                                if m == 'necro_native_status'))

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
                self.assertEqual([], server.calls)
                self.assertEqual(['/schema'], server.schema_calls)
                expected = 'native_schema_invalid' if isinstance(kwargs.get('capabilities'), dict) else 'native_capability_missing'
                self.assertEqual(expected, result['stop_reason'])
                self.assertTrue(result['resolved'])

    def test_minimal_accepted_report_can_progress_into_completed_results(self):
        def transform(method, result):
            if method == 'necro_native_start':
                result['state'] = 'accepted'
                result['report'] = {key: result['report'][key] for key in (
                    'schema', 'clock_id', 'device_now_ns', 'input_state', 'events', 'motion_references', 'recovery')}
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
                       ('necro_native_status', {'run_id':run_id}),
                       ('necro_native_status', {'run_id':run_id, 'keepalive':1}),
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
                self.assertEqual(3, sum(m == 'necro_native_cancel' for m,p in server.calls))

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
                    'original_lock=n.device_lock; n.device_lock=lambda _path=None:original_lock(%r); '
                    'raise SystemExit(n.main(["--output",%r,"--python-crypto"]))') % (
                        server.server.server_port, KEY, TOK, str(Path(folder)/'private.lock'), folder)
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
    def test_old_journal_images_project_extra_fields_and_resave_no_secrets(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True) as server:
            result = native.run_session(server.client(self.timer), folder,
                lock_path=Path(folder)/'lock', poll_seconds=.001, max_seconds=.5)
            metadata, _raw = native._images([image_item()])[0]
            result['revision'] = 'native-walk-v1'
            result.pop('image_export', None)
            result.pop('preflight')
            result['images'] = [dict(metadata, token='PRIVATE_IMAGE_TOKEN', raw_exception='PRIVATE')]
            native._save(Path(folder), result)
            loaded = native._load(Path(folder))
            self.assertEqual([metadata], loaded['images'])
            native._save(Path(folder), loaded)
            self.assertNotIn('PRIVATE', (Path(folder)/'active.json').read_text())
            self.assertNotIn('PRIVATE', (Path(folder)/('native-'+result['run_id'])/'report.json').read_text())

    def test_invalid_saved_image_metadata_and_limits_are_journal_errors(self):
        metadata, _raw = native._images([image_item()])[0]
        invalid = [None, {}, 'PRIVATE']
        for changes in ({'name':'../active.json'}, {'name':'/initial.png'}, {'format':'jpeg'},
                        {'pixel_width':True}, {'pixel_height':896}, {'sha256':'PRIVATE'},
                        {'bytes':True}, {'bytes':23}, {'bytes':native.MAX_IMAGE+1},
                        {'capture_id':True}, {'capture_id':-1}, {'capture_start_ns':4},
                        {'capture_end_ns':2**63}, {'completed_prefix':True},
                        {'stable_prefix':0}, {'decode_end_ns':2}, {'inflight_start':'PRIVATE'}):
            invalid.append([dict(metadata, **changes)])
        invalid.extend(([metadata,metadata],
                        [dict(metadata,name='frame-'+str(i)+'.png') for i in range(21)],
                        [dict(metadata,name='frame-'+str(i)+'.png',bytes=native.MAX_IMAGE) for i in range(9)],
                        [{k:v for k,v in metadata.items() if k != 'sha256'}]))
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True) as server:
            result = native.run_session(server.client(self.timer), folder,
                lock_path=Path(folder)/'lock', poll_seconds=.001, max_seconds=.5)
            for images in invalid:
                with self.subTest(images=images):
                    result['images'] = images
                    native._save(Path(folder), result)
                    with self.assertRaisesRegex(ProbeError,'native_journal_invalid'):
                        native._load(Path(folder))
            result['images'] = [dict(metadata,name='frame-'+str(i)+'.png',bytes=native.MAX_IMAGE)
                                for i in range(8)]
            result['revision'] = 'native-walk-v8'
            bind_legacy_api(result)
            result.pop('image_export', None)
            native._save(Path(folder), result)
            self.assertEqual(result['images'], native._load(Path(folder))['images'])

    def test_results_images_are_validated_hashed_and_saved_without_image_imports(self):
        def transform(method, result):
            if method == 'necro_native_results':
                result['images'] = [image_item()]
            return result
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True, transform=transform) as server:
            result = native.run_session(server.client(self.timer), folder,
                                        lock_path=Path(folder)/'lock', poll_seconds=.001, max_seconds=5)
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
                                        lock_path=Path(folder)/'lock', poll_seconds=.001, max_seconds=5)
            self.assertTrue(any(m == 'necro_native_results' for m,p in server.calls), result['stop_reason'])
            self.assertEqual('completed', result['native_state'], result['stop_reason'])
            self.assertFalse(result['resolved'])
            self.assertEqual('invalid_native_images', result['stop_reason'])
            self.assertEqual([], list(Path(folder).rglob('*.png')))

    def test_capture_prefix_and_stability_metadata_survive_export(self):
        item = image_item()
        item.update(completed_prefix=7, stable_prefix=False, decode_end_ns=4,
                    completed_prefix_start=6, completed_prefix_end=7,
                    inflight_start=True, inflight_end=False)
        metadata, raw = native._images([item])[0]
        self.assertEqual(7, metadata['completed_prefix'])
        self.assertIs(False, metadata['stable_prefix'])
        for key in ('decode_end_ns', 'completed_prefix_start', 'completed_prefix_end',
                    'inflight_start', 'inflight_end'):
            self.assertEqual(item[key], metadata[key])
        item['stable_prefix'] = 0
        with self.assertRaisesRegex(ProbeError, 'invalid_native_images'):
            native._images([item])

    def test_maximum_native_measurements_and_host_ring_roundtrip_and_recover(self):
        def measurements(report):
            value = dict(report)
            value.update({key:0 for key in native.NUMERIC_KEYS})
            value.update(schema='ngg2-native-v1', clock_id=report['clock_id'],
                         device_now_ns=100_000, input_state=4, captures=[], events=[])
            value.update(native.FIXED_TEXT)
            value.update({key:False for key in native.BOOL_KEYS})
            value['workers_drained'] = True
            value['terminal'] = 1
            value['retained_image_count'] = 20
            value['pinned_image_count'] = 16
            value['recent_image_count'] = 4
            value['referenced_capture_ids'] = list(range(1,132))
            value['missing_capture_ids'] = list(range(21,132))
            value['scene_changes'] = [dict(command_id=i+1, source_capture_id=20,
                observed_capture_id=21+i, change_mask=15, changed_tiles=230,
                changed_protected=230, state_before=0, state_after=2,
                goods_before=0, goods_after=2, replan_count=min(i,2),
                replan_allowed=i<2, target_ns=1000, deadline_ns=900) for i in range(3)]
            for i in range(256):
                value['captures'].append({'id':i+1,'start_ns':100*i,'end_ns':100*i+1,
                    'decode_end_ns':100*i+2,'analysis_start_ns':100*i+3,'analysis_end_ns':100*i+4,
                    'completed_prefix_start':i,'completed_prefix_end':i,
                    'inflight_start':False,'inflight_end':False,'stable':True})
            for i in range(64):
                value['events'].append({key:0 for key in (
                    'id','ordinal','kind','direction','x','y','target_ns','not_before_ns','deadline_ns',
                    'source_capture_id','source_start_ns','phase_sample_ns','begin_ns','end_ns',
                    'observed_capture_id','outcome','reason','motion','dx','dy')})
            return value
        def transform(method, result):
            if 'report' in result:
                result['report'] = measurements(result['report'])
            if method == 'necro_native_results':
                result.update(retained_images=20, exported_images=0, omitted_image_count=300,
                              exported_capture_ids=[], omitted_capture_ids=list(range(1,132)))
            return result
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True, transform=transform) as server:
            options = {'lock_path':Path(folder)/'lock','max_seconds':5,'poll_seconds':.001}
            record = native.run_session(server.client(self.timer), folder, **options)
            self.assertFalse(record['resolved'])
            self.assertEqual(256, len(record['native_report']['captures']))
            self.assertEqual(64, len(record['native_report']['events']))
            self.assertEqual(300, record['result_metadata']['omitted_image_count'])
            row = {'invocation':'0'*32,'method':'necro_native_status','host_ns':1,'error':None,
                   'rpc_stage':'result_json',
                   'host_timings':{key:1 for key in ('request_start_ns','http_start_ns','http_end_ns',
                       'decrypt_start_ns','decrypt_end_ns','response_end_ns')}}
            record['events'] = [dict(row) for _ in range(128)]
            # Four readiness attempts must coexist with the largest native
            # evidence and HTTP ring without exceeding the JSON node limit.
            template = record['preflight']['attempts'][0]
            record['preflight']['attempts'] = []
            for index in range(1,5):
                start = record['preflight']['started_ns']+index
                diagnostic = dict(template['diagnostic'], started_ns=start, ended_ns=start)
                diagnostic.update(kind='ok' if index == 4 else 'refused',
                                  errno=None if index == 4 else errno.ECONNREFUSED,
                                  status=200 if index == 4 else None)
                record['preflight']['attempts'].append({'attempt':index, 'started_ns':start,
                    'ended_ns':start, 'error':None if index == 4 else 'connection_error',
                    'diagnostic':diagnostic})
            native._save(Path(folder), record)
            loaded = native._load(Path(folder))
            self.assertEqual(record, loaded)
            # The same maximal JSON shape must also be accepted on reconnect.
            recovered = native.run_session(server.client(self.timer), folder, **options)
            self.assertEqual(record['run_id'], recovered['run_id'])
            self.assertFalse(recovered['resolved'])
            self.assertEqual(256, len(recovered['native_report']['captures']))
            self.assertEqual(64, len(recovered['native_report']['events']))
            self.assertEqual(3, len(recovered['native_report']['scene_changes']))
            self.assertEqual(131, len(recovered['result_metadata']['omitted_capture_ids']))
            self.assertLessEqual(len(recovered['events']), 128)
            self.assertGreater(recovered['events_dropped'], record['events_dropped'])

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
