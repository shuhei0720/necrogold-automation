"""TEST044 startup contracts through actual loopback HTTP and encrypted RPC."""
from pathlib import Path
from copy import deepcopy
import errno
import json
import tempfile
import time
import subprocess
import unittest
from unittest.mock import patch

from necroprobe import native_walk as native
from necroprobe.validation import ProbeError
from test_native_walk import NativeServer
from timer_support import TimerTestCase


class NativeConnectTests(TimerTestCase):
    def run_native(self, server, folder, **options):
        options.setdefault('max_seconds', 2)
        options.setdefault('poll_seconds', .001)
        options.setdefault('recovery_seconds', .3)
        return native.run_session(server.client(self.timer), folder,
            lock_path=Path(folder)/'lock', **options)

    def test_connect_refused_then_listener_ready_starts_once(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(listen=False, finish=True) as server:
            def wait(_seconds):
                server.activate()
            result = self.run_native(server, folder, sleep=wait)
            self.assertEqual(1, sum(m == 'necro_native_start' for m,p in server.calls))
            self.assertTrue(result['resolved'])
            self.assertEqual(['/schema'], server.schema_calls)

    def test_metadata_probe_never_enters_device_info_UI_lane(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(reject_info=True, finish=True) as server:
            result = self.run_native(server, folder)
            self.assertEqual(1, sum(m == 'necro_native_start' for m,p in server.calls))
            self.assertNotIn('device_info', [m for m,p in server.calls])
            self.assertEqual(['/schema'], server.schema_calls)
            self.assertTrue(result['resolved'])

    def test_failed_connection_retains_closed_diagnostics_in_both_journals(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(listen=False) as server:
            # Exercise all four diagnostics rows under CI load. Deadline
            # boundaries are covered separately with an injected clock.
            result = self.run_native(server, folder, max_seconds=8, sleep=lambda _seconds: None)
            self.assertIn('preflight', result)
            preflight = result['preflight']
            self.assertEqual(4, len(preflight['attempts']))
            self.assertTrue(all(r['diagnostic']['kind'] == 'refused' for r in preflight['attempts']))
            self.assertFalse(result['start_attempted'])
            self.assertEqual([], server.calls)
            self.assertEqual(result, native._load(Path(folder)))
            report = json.loads((Path(folder)/('native-'+result['run_id'])/'report.json').read_text())
            self.assertEqual(result, report)

    def test_cancel_during_start_intent_save_never_posts_start(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True) as server:
            saved = native._save
            stopped = [False]
            def checkpoint(base, record):
                saved(base, record)
                if record['start_attempted']:
                    stopped[0] = True
            with patch.object(native, '_save', side_effect=checkpoint):
                result = self.run_native(server, folder, cancelled=lambda: stopped[0])
            self.assertEqual(0, sum(m == 'necro_native_start' for m,p in server.calls))
            self.assertTrue(result['start_attempted'])
            self.assertTrue(result['resolved'])
            self.assertIsNone(result['native_state'])

    def test_deadline_equal_after_start_intent_save_never_posts_start(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True) as server:
            saved = native._save
            now = [time.monotonic_ns()]
            def checkpoint(base, record):
                saved(base, record)
                if record['start_attempted']:
                    now[0] += 2_000_000_000
            with patch.object(native, '_save', side_effect=checkpoint):
                result = self.run_native(server, folder, clock=lambda: now[0])
            self.assertEqual(0, sum(m == 'necro_native_start' for m,p in server.calls))
            self.assertTrue(result['start_attempted'])
            self.assertTrue(result['resolved'])
            self.assertIsNone(result['native_state'])

    def test_wrong_or_malformed_metadata_never_retries_or_starts(self):
        mutations = [
            lambda v: {},
            lambda v: dict(v, server_version=None),
            lambda v: dict(v, protocol_version=True),
            lambda v: dict(v, protocol_version=1.0),
            lambda v: dict(v, protocol_version=2),
            lambda v: {k:x for k,x in v.items() if k != 'capability_tags'},
            lambda v: dict(v, capability_tags={native.CAPABILITY:True}),
            lambda v: dict(v, capability_tags=[True]),
            lambda v: dict(v, capability_tags=['x']*257),
            lambda v: dict(v, capability_tags=['x'*129]),
            lambda v: dict(v, capability_tags=[]),
            lambda v: dict(v, server_version='PRIVATE_SERVER_VALUE'),
        ]
        for transform in mutations:
            with self.subTest(transform=transform), tempfile.TemporaryDirectory() as folder, NativeServer(schema_transform=transform) as server:
                record = self.run_native(server, folder)
                self.assertEqual(['/schema'], server.schema_calls)
                self.assertEqual([], server.calls)
                self.assertFalse(record['start_attempted'])
                self.assertTrue(record['resolved'])
                self.assertNotIn('PRIVATE_SERVER_VALUE', json.dumps(record))
                self.assertEqual(record, native._load(Path(folder)))

    def test_http_error_and_redirect_are_not_readiness_retries(self):
        for status in (301,302,307,308,401,403,404,500,503):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as folder, NativeServer(schema_status=status) as server:
                record = self.run_native(server, folder)
                self.assertEqual(['/schema'], server.schema_calls)
                self.assertEqual([], server.calls)
                row = record['preflight']['attempts'][0]
                self.assertEqual(status, row['diagnostic']['status'])
                self.assertEqual('http_status', row['diagnostic']['kind'])
                self.assertEqual('schema_http_status', record['stop_reason'])

    def test_invalid_json_and_parser_limits_stop_after_one_metadata_read(self):
        values = [b'not-json', b'[]', b'{"server_version":1,"server_version":2}',
                  b'{"x":NaN}', b'{"x":'+b'['*17+b'0'+b']'*17+b'}',
                  json.dumps({'x':[0]*10001}).encode()]
        for raw in values:
            with self.subTest(raw=raw[:32]), tempfile.TemporaryDirectory() as folder, NativeServer(schema_raw=raw) as server:
                record = self.run_native(server, folder)
                self.assertEqual(['/schema'], server.schema_calls)
                self.assertEqual([], server.calls)
                self.assertEqual('native_schema_invalid', record['stop_reason'])

    def test_valid_schema_at_byte_limit_and_one_byte_over(self):
        base = {'server_version':native.API_VERSION, 'protocol_version':1,
                'capability_tags':[native.CAPABILITY], 'padding':''}
        raw = json.dumps(base, separators=(',',':')).encode()
        base['padding'] = 'x'*(native.MAX_SCHEMA-len(raw))
        at_limit = json.dumps(base, separators=(',',':')).encode()
        self.assertEqual(native.MAX_SCHEMA, len(at_limit))
        for raw,expected in ((at_limit,1),(at_limit+b' ',0)):
            with self.subTest(size=len(raw)), tempfile.TemporaryDirectory() as folder, NativeServer(schema_raw=raw,finish=True) as server:
                record = self.run_native(server, folder)
                self.assertEqual(expected, sum(m == 'necro_native_start' for m,p in server.calls))
                self.assertEqual(['/schema'], server.schema_calls)
                self.assertNotIn('padding', json.dumps(record))

    def test_success_keeps_only_bounded_server_identity_and_valid_build(self):
        canary = 'PRIVATE_CANARY_TOKEN'
        def payload(value):
            return dict(value, build='2026-11-07 04:11', device_id=canary,
                        name=canary, token=canary, methods=[{'description':canary}],
                        capability_tags=[native.CAPABILITY,canary])
        with tempfile.TemporaryDirectory() as folder, NativeServer(schema_transform=payload,finish=True) as server:
            record = self.run_native(server, folder)
            self.assertNotIn(canary, json.dumps(record))
            self.assertEqual({'server_version':native.API_VERSION, 'protocol_version':1,
                              'native_capability':True, 'build':'2026-11-07 04:11'}, record['preflight']['server'])
            self.assertEqual(record, native._load(Path(folder)))

    def test_missing_and_invalid_build_values_are_omitted(self):
        for build in (None,True,123,{'secret':'PRIVATE'},'unknown','2026-02-30 00:00',
                      '0000-01-01 00:00','2026-13-01 00:00','2026-01-01 24:00',
                      '2026-01-01 00:60','2026-01-01 00:00 PRIVATE'):
            def payload(value, build=build):
                return dict(value, build=build)
            with self.subTest(build=build), tempfile.TemporaryDirectory() as folder, NativeServer(schema_transform=payload,finish=True) as server:
                record = self.run_native(server, folder)
                self.assertEqual('completed', record['native_state'])
                self.assertNotIn('build', record['preflight']['server'])

    def test_cancel_during_backoff_prevents_retry_and_start(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(listen=False) as server:
            stopped = [False]
            waits = []
            def sleeper(seconds):
                waits.append(seconds)
                stopped[0] = True
            record = self.run_native(server, folder, sleep=sleeper, cancelled=lambda:stopped[0])
            self.assertEqual(1, len(record['preflight']['attempts']))
            self.assertEqual('cancel_requested', record['stop_reason'])
            self.assertTrue(waits and max(waits) <= .05)
            self.assertFalse(record['start_attempted'])
            self.assertEqual([], server.calls)

    def test_session_deadline_is_absolute_even_during_backoff(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(listen=False) as server:
            now = [time.monotonic_ns()]
            def sleeper(_seconds):
                now[0] += 2_000_000_000
            record = self.run_native(server, folder, clock=lambda:now[0], sleep=sleeper)
            self.assertEqual(1, len(record['preflight']['attempts']))
            self.assertEqual('host_deadline', record['stop_reason'])
            self.assertFalse(record['start_attempted'])

    def test_readiness_budget_is_eight_seconds_inside_larger_session_budget(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(listen=False) as server:
            now = [time.monotonic_ns()]
            def sleeper(_seconds):
                now[0] += native.SCHEMA_BUDGET_NS
            record = self.run_native(server, folder, max_seconds=20,clock=lambda:now[0],sleep=sleeper)
            preflight = record['preflight']
            self.assertEqual(native.SCHEMA_BUDGET_NS, preflight['deadline_ns']-preflight['started_ns'])
            self.assertEqual(1, len(preflight['attempts']))
            self.assertFalse(record['start_attempted'])

    def test_deadline_equal_after_initial_save_sends_no_get_or_post(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer() as server:
            saved = native._save
            now = [time.monotonic_ns()]
            def checkpoint(base, record):
                saved(base, record)
                now[0] += 2_000_000_000
            with patch.object(native, '_save', side_effect=checkpoint):
                record = self.run_native(server, folder, clock=lambda:now[0])
            self.assertEqual([], server.schema_calls)
            self.assertEqual([], server.calls)
            self.assertFalse(record['start_attempted'])

    def test_crypto_time_cancel_or_expiry_is_known_unsent_and_does_not_cancel_unknown_run(self):
        for reason in ('cancel','deadline'):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as folder, NativeServer() as server:
                client = server.client(self.timer)
                xor = client.crypto.xor
                now = [time.monotonic_ns()]
                stopped = [False]
                def delayed_crypto(*args, **kwargs):
                    value = xor(*args, **kwargs)
                    if reason == 'cancel':
                        stopped[0] = True
                    else:
                        now[0] += 2_000_000_000
                    return value
                with patch.object(client.crypto, 'xor', side_effect=delayed_crypto):
                    record = native.run_session(client, folder, lock_path=Path(folder)/'lock',
                        clock=lambda:now[0],cancelled=lambda:stopped[0],max_seconds=2)
                self.assertTrue(record['start_attempted'])
                self.assertTrue(record['resolved'])
                self.assertIsNone(record['native_state'])
                self.assertEqual([], server.calls)
                self.assertEqual(['/schema'], server.schema_calls)
                self.assertEqual(record, native._load(Path(folder)))
                self.assertIsNone(client._before_start_post)
                self.assertTrue(hasattr(client.transport, 'schema'))

    def test_started_recovery_performs_no_metadata_request(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(input_state=4) as server:
            first = self.run_native(server, folder, max_seconds=.3)
            self.assertFalse(first['resolved'])
            server.schema_calls.clear()
            old_calls = len(server.calls)
            result = self.run_native(server, folder, max_seconds=.3)
            self.assertEqual([], server.schema_calls)
            self.assertEqual(first['run_id'], result['run_id'])
            self.assertNotIn('necro_native_start', [m for m,p in server.calls[old_calls:]])

    def test_legacy_journal_and_event_projection_drop_arbitrary_fields(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(input_state=4) as server:
            record = self.run_native(server, folder, max_seconds=.3)
            record.pop('preflight')
            record['revision'] = 'native-walk-v1'
            record.pop('image_export', None)
            canary = 'PRIVATE_JOURNAL_VALUE'
            record['events'][0]['token'] = canary
            record['events'][0]['host_timings']['private_ns'] = 7
            native._save(Path(folder), record)
            loaded = native._load(Path(folder))
            self.assertNotIn('preflight', loaded)
            self.assertNotIn(canary, json.dumps(loaded))
            self.assertNotIn('private_ns', json.dumps(loaded))
            native._save(Path(folder), loaded)
            self.assertNotIn(canary, (Path(folder)/'active.json').read_text())

    def test_missing_nullable_diagnostic_fields_and_bad_preflight_are_journal_errors(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True) as server:
            record = self.run_native(server, folder)
            for key in ('errno','status','kind','started_ns'):
                changed = deepcopy(record)
                changed['preflight']['attempts'][0]['diagnostic'].pop(key)
                native._save(Path(folder), changed)
                with self.subTest(key=key), self.assertRaisesRegex(ProbeError,'native_journal_invalid'):
                    native._load(Path(folder))
            changed = deepcopy(record)
            changed['preflight']['attempts'][0]['diagnostic']['raw_exception'] = 'PRIVATE'
            native._save(Path(folder),changed)
            with self.assertRaisesRegex(ProbeError,'native_journal_invalid'):
                native._load(Path(folder))

    def test_script_044_uses_current_revision_and_output(self):
        path = Path(native.__file__).resolve().parents[1]/'test_044.sh'
        self.assertEqual(0, subprocess.run(['sh','-n',str(path)],capture_output=True).returncode)
        text = path.read_text()
        self.assertIn('native-walk-v2 / 1.98.14-ngg2',text)
        self.assertIn('--output runtime/test-044',text)
        self.assertNotIn('necroprobe.preflight',text)

    def test_deadline_during_json_validation_remains_retryable_deadline(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer() as server:
            parser = native.json_object
            parsed = []
            def slow_parser(raw, limit):
                parsed.append(True)
                time.sleep(1)
                return parser(raw, limit)
            client = server.client(self.timer)
            client.timeout = .5
            with patch.object(native, 'json_object', side_effect=slow_parser):
                record = native.run_session(client, folder, lock_path=Path(folder)/'lock',
                                            max_seconds=8)
            self.assertEqual(4, len(parsed))
            self.assertEqual(4, len(server.schema_calls))
            self.assertEqual([], server.calls)
            self.assertEqual('rpc_deadline', record['stop_reason'])
            self.assertTrue(all(row['error'] == 'rpc_deadline'
                                and row['diagnostic']['kind'] == 'ok'
                                for row in record['preflight']['attempts']))

    def test_authentication_failure_mac_failure_and_lost_native_start_are_never_retried(self):
        for options in ({'start_status':401}, {'bad_start_mac':True}, {'lose':['necro_native_start']}):
            with self.subTest(options=options), tempfile.TemporaryDirectory() as folder, NativeServer(**options) as server:
                record = self.run_native(server, folder, max_seconds=.5)
                self.assertEqual(['/schema'], server.schema_calls)
                self.assertEqual(1, sum(m == 'necro_native_start' for m,p in server.calls))
                self.assertTrue(record['start_attempted'])
                self.assertTrue(all(p.get('run_id') == record['run_id'] for m,p in server.calls))

    def test_cancel_or_deadline_during_schema_checkpoint_never_creates_start_intent(self):
        for reason in ('cancel','deadline'):
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as folder, NativeServer() as server:
                saved = native._save
                now = [time.monotonic_ns()]
                stopped = [False]
                def checkpoint(base, record):
                    saved(base, record)
                    if record.get('preflight', {}).get('state') == 'ready':
                        if reason == 'cancel':
                            stopped[0] = True
                        else:
                            now[0] += 2_000_000_000
                with patch.object(native, '_save', side_effect=checkpoint):
                    record = self.run_native(server, folder, clock=lambda:now[0],
                                             cancelled=lambda:stopped[0])
                self.assertEqual(['/schema'], server.schema_calls)
                self.assertEqual([], server.calls)
                self.assertFalse(record['start_attempted'])
                self.assertTrue(record['resolved'])

    def test_metadata_deadline_uses_client_single_call_limit(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True) as server:
            client = server.client(self.timer)
            client.timeout = .1
            original = self.timer.deadline
            budgets = []
            def bounded(seconds):
                budgets.append(seconds)
                return original(seconds)
            with patch.object(self.timer, 'deadline', side_effect=bounded):
                record = native.run_session(client, folder, lock_path=Path(folder)/'lock',
                                            max_seconds=2)
            self.assertTrue(record['resolved'])
            self.assertGreater(budgets[0], 0)
            self.assertLessEqual(budgets[0], .1)

    def test_transient_and_permanent_transport_kinds_control_only_preflight_retries(self):
        kinds = {'refused':True, 'timeout':True, 'reset':True, 'disconnected':True,
                 'unreachable':True, 'io_error':False, 'protocol_error':False,
                 'body_truncated':False}
        class ClassifiedTransport:
            def __init__(self, real, kind):
                self.real, self.kind, self.reads = real, kind, 0
                self.last_diagnostic = None
            def schema(self, timeout):
                self.reads += 1
                if self.reads == 1:
                    now = time.monotonic_ns()
                    codes = {'refused':errno.ECONNREFUSED,'timeout':errno.ETIMEDOUT,
                             'reset':errno.ECONNRESET,'unreachable':errno.ENETUNREACH,
                             'io_error':errno.EACCES}
                    self.last_diagnostic = {'stage':'body' if self.kind == 'body_truncated' else 'connect',
                        'kind':self.kind,'errno':codes.get(self.kind),'status':None,
                        'started_ns':now,'ended_ns':now}
                    raise ProbeError('http_body_truncated' if self.kind == 'body_truncated' else 'connection_error')
                raw = self.real.schema(timeout)
                self.last_diagnostic = self.real.last_diagnostic
                return raw
            def __call__(self, body, timeout):
                return self.real(body, timeout)
        for kind,transient in kinds.items():
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as folder, NativeServer(finish=True) as server:
                client = server.client(self.timer)
                classified = ClassifiedTransport(client.transport,kind)
                client.transport = classified
                record = native.run_session(client, folder, lock_path=Path(folder)/'lock',
                                            max_seconds=2, poll_seconds=.001)
                self.assertEqual(2 if transient else 1, classified.reads)
                self.assertEqual(int(transient), sum(m == 'necro_native_start' for m,p in server.calls))
                self.assertEqual(kind, record['preflight']['attempts'][0]['diagnostic']['kind'])
                self.assertEqual(2 if transient else 1, len(record['preflight']['attempts']))
                self.assertEqual(record, native._load(Path(folder)))


if __name__ == '__main__':
    unittest.main()
