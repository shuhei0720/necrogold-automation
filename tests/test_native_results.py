"""TEST045 result collection and closed native diagnostics contracts."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from necroprobe import native_walk as native
from necroprobe import protocol
from necroprobe.crypto import Crypto
from necroprobe.protocol import HttpTransport
from necroprobe.validation import ProbeError
from test_native_walk import NativeServer, image_item
from test_protocol import KEY, TOK
from timer_support import TimerTestCase


def scene_change(**extra):
    value = dict(command_id=2, source_capture_id=20, observed_capture_id=21,
        change_mask=4, changed_tiles=1, changed_protected=0,
        state_before=1, state_after=1, goods_before=0, goods_after=0,
        replan_count=1, replan_allowed=True, target_ns=1000, deadline_ns=900)
    value.update(extra)
    return value


class NativeResultsCliTests(unittest.TestCase):
    def test_real_encrypted_results_over_two_seconds_are_collected(self):
        def delayed_images(method, result):
            if method == 'necro_native_results':
                time.sleep(2.15)
                result['images'] = [image_item()]
            return result
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True, transform=delayed_images) as server:
            transport = HttpTransport(server.server.server_port)
            run = native.run_session
            def bounded_run(client, output, **options):
                return run(client, output, lock_path=Path(folder)/'lock',
                           max_seconds=8, poll_seconds=.001, **options)
            with patch.object(native, 'HttpTransport', return_value=transport), \
                    patch.object(native, 'load_pairing', return_value=(KEY,TOK)), \
                    patch.object(native, 'Crypto', return_value=Crypto(native=False)), \
                    patch.object(native, 'run_session', side_effect=bounded_run), \
                    redirect_stdout(io.StringIO()):
                code = native.main(['--output', folder])
            self.assertEqual(0, code)
            record = native._load(Path(folder))
            self.assertTrue(record['resolved'])
            self.assertEqual(1, len(record['images']))
            self.assertEqual(1, sum(m == 'necro_native_start' for m,p in server.calls))
            self.assertEqual(1, sum(m == 'necro_native_results' for m,p in server.calls))


class NativeResultsTests(TimerTestCase):
    def client(self, server, timeout=8):
        return native.NativeClient(HttpTransport(server.server.server_port), KEY, TOK,
            deadline_owner=self.timer, crypto=Crypto(native=False), timeout=timeout)

    def execute(self, server, folder, client=None, **options):
        options.setdefault('max_seconds', 8)
        options.setdefault('poll_seconds', .001)
        return native.run_session(client or self.client(server), folder,
            lock_path=Path(folder)/'lock', **options)

    def test_results_are_not_requested_at_the_absolute_cleanup_deadline(self):
        now = [time.monotonic_ns()]
        stopped = [False]
        def expire_at_terminal(method, result):
            if method == 'necro_native_start':
                stopped[0] = True
            if method == 'necro_native_cancel':
                now[0] += 1_000_000_000
            return result
        with tempfile.TemporaryDirectory() as folder, NativeServer(transform=expire_at_terminal) as server:
            record = self.execute(server, folder, max_seconds=2, recovery_seconds=1,
                cancelled=lambda:stopped[0], clock=lambda:now[0])
            self.assertFalse(record['resolved'])
            self.assertEqual('host_deadline', record['stop_reason'])
            self.assertEqual(0, sum(m == 'necro_native_results' for m,p in server.calls))

    def test_operation_deadline_keeps_the_existing_finite_cleanup_for_results(self):
        now = [time.monotonic_ns()]
        def expire_at_terminal(method, result):
            if method == 'necro_native_status':
                now[0] += 2_000_000_000
            return result
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True, transform=expire_at_terminal) as server:
            record = self.execute(server, folder, max_seconds=2, recovery_seconds=1, clock=lambda:now[0])
            self.assertTrue(record['resolved'])
            self.assertEqual('host_deadline', record['stop_reason'])
            self.assertEqual(1, sum(m == 'necro_native_results' for m,p in server.calls))

    def test_ordinary_rpc_stays_at_two_seconds_with_an_eight_second_client(self):
        def delay_status(method, result):
            if method == 'necro_native_status':
                time.sleep(2.15)
            return result
        with NativeServer(transform=delay_status) as server:
            with self.assertRaisesRegex(ProbeError, 'rpc_deadline'):
                self.client(server).call('necro_native_status', {'run_id':'a'*32,'keepalive':False})

    def test_result_timeout_retains_http_stage_and_partial_numeric_timings(self):
        def delay_results(method, result):
            if method == 'necro_native_results':
                time.sleep(.3)
            return result
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True, transform=delay_results) as server:
            record = self.execute(server, folder, results_seconds=.15)
            row = record['events'][-1]
            self.assertEqual('rpc_deadline', row['error'])
            self.assertEqual('http', row.get('rpc_stage'))
            self.assertIn('request_start_ns', row.get('host_timings', {}))
            self.assertIn('http_start_ns', row.get('host_timings', {}))
            self.assertNotIn('http_end_ns', row['host_timings'])
            self.assertEqual(record, native._load(Path(folder)))

    def test_results_budget_is_shortened_to_the_invocation_remaining_time(self):
        now = [time.monotonic_ns()]
        initial = now[0]
        def delay_results(method, result):
            if method == 'necro_native_status':
                now[0] = initial + 7_900_000_000
            if method == 'necro_native_results':
                time.sleep(.25)
            return result
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True, transform=delay_results) as server:
            began = time.monotonic()
            record = self.execute(server, folder, clock=lambda:now[0])
            self.assertFalse(record['resolved'])
            self.assertEqual('rpc_deadline', record['stop_reason'])
            self.assertEqual('http', record['events'][-1]['rpc_stage'])
            self.assertLess(time.monotonic()-began, 1)
            self.assertEqual(1, sum(m == 'necro_native_results' for m,p in server.calls))

    def test_http_completed_crypto_and_json_deadlines_keep_the_matching_stage(self):
        for stage in ('response_json','response_auth','response_crypto','result_json'):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as folder:
                receiving = [False]
                def mark_results(method, result):
                    if method == 'necro_native_results':
                        receiving[0] = True
                    return result
                with NativeServer(finish=True, transform=mark_results) as server:
                    client = self.client(server)
                    parse, xor, auth = protocol.json_object, client.crypto.xor, protocol.mac
                    def slow_parse(raw, *args):
                        value = parse(raw, *args)
                        if receiving[0] and ((stage == 'response_json' and 'ct' in value)
                                or (stage == 'result_json' and 'result' in value)):
                            time.sleep(.3)
                        return value
                    def slow_xor(*args):
                        if receiving[0] and stage == 'response_crypto':
                            time.sleep(.3)
                        return xor(*args)
                    def slow_auth(key, data):
                        if receiving[0] and stage == 'response_auth' and data.startswith(b'resp'):
                            time.sleep(.3)
                        return auth(key, data)
                    with patch.object(protocol, 'json_object', side_effect=slow_parse), \
                            patch.object(client.crypto, 'xor', side_effect=slow_xor), \
                            patch.object(protocol, 'mac', side_effect=slow_auth):
                        record = self.execute(server, folder, client, results_seconds=.15)
                    row = record['events'][-1]
                    self.assertEqual('rpc_deadline', row['error'])
                    self.assertEqual(stage, row['rpc_stage'])
                    self.assertIn('http_end_ns', row['host_timings'])
                    self.assertNotIn('response_end_ns', row['host_timings'])
                    self.assertEqual(stage in ('response_crypto','result_json'),
                                     'decrypt_start_ns' in row['host_timings'])
                    self.assertEqual(stage == 'result_json', 'decrypt_end_ns' in row['host_timings'])
                    self.assertEqual(record, native._load(Path(folder)))

    def test_failed_results_recover_v1_and_v2_journals_without_get_or_start(self):
        slow = [True]
        def delay_once(method, result):
            if method == 'necro_native_results' and slow[0]:
                time.sleep(.3)
            return result
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True, transform=delay_once) as server:
            first = self.execute(server, folder, results_seconds=.15)
            self.assertFalse(first['resolved'])
            self.assertEqual('rpc_deadline', first['stop_reason'])
            slow[0] = False
            for revision in ('native-walk-v1','native-walk-v2'):
                legacy = deepcopy(first)
                legacy['revision'] = revision
                native._save(Path(folder), legacy)
                server.schema_calls.clear()
                before = len(server.calls)
                recovered = self.execute(server, folder)
                self.assertTrue(recovered['resolved'])
                self.assertEqual(first['run_id'], recovered['run_id'])
                self.assertEqual([], server.schema_calls)
                calls = server.calls[before:]
                self.assertEqual(['necro_native_status','necro_native_results'], [m for m,p in calls])
                self.assertFalse(calls[0][1]['keepalive'])

    def test_failure_diagnostics_project_legacy_unknown_fields_and_reject_bad_stage(self):
        row = {'invocation':'a'*32, 'method':'necro_native_results','host_ns':7,
               'error':'rpc_deadline','rpc_stage':'result_json','secret':'PRIVATE',
               'host_timings':{'request_start_ns':1,'http_start_ns':2,'http_end_ns':3,
                    'decrypt_start_ns':4,'decrypt_end_ns':5,'private_ns':6,'raw':'PRIVATE'}}
        clean = native._events([row])
        self.assertEqual('result_json', clean[0]['rpc_stage'])
        self.assertNotIn('PRIVATE', json.dumps(clean))
        self.assertNotIn('private_ns', json.dumps(clean))
        with self.assertRaisesRegex(ProbeError,'native_journal_invalid'):
            native._events([dict(row, rpc_stage='PRIVATE')])

    def test_scene_changes_are_projected_and_survive_journal_roundtrip(self):
        canary = 'PRIVATE_SCENE_VALUE'
        def change(method, result):
            result['report']['scene_changes'] = [scene_change(secret=canary)]
            return result
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True, transform=change) as server:
            record = self.execute(server, folder)
            self.assertEqual([scene_change()], record['native_report'].get('scene_changes'))
            self.assertNotIn(canary, json.dumps(record))
            self.assertEqual(record, native._load(Path(folder)))
            legacy = deepcopy(record)
            legacy['native_report']['scene_changes'][0]['private'] = canary
            native._save(Path(folder), legacy)
            loaded = native._load(Path(folder))
            self.assertEqual([scene_change()], loaded['native_report']['scene_changes'])
            self.assertNotIn(canary, json.dumps(loaded))

    def test_bad_scene_change_required_values_are_rejected(self):
        base = {'schema':'ngg2-native-v1','clock_id':'a'*32,'device_now_ns':1,'input_state':0}
        for bad in (scene_change(change_mask=0),scene_change(changed_tiles=231),
                    scene_change(replan_allowed=1),scene_change(target_ns=True),
                    scene_change(state_after=3),scene_change(replan_count=3)):
            with self.subTest(change=bad), self.assertRaisesRegex(ProbeError,'invalid_native_report'):
                native._report(dict(base, scene_changes=[bad]))
        with self.assertRaisesRegex(ProbeError,'invalid_native_report'):
            native._report(dict(base, scene_changes=[scene_change()]*4))
        for key in scene_change():
            missing = scene_change()
            missing.pop(key)
            with self.subTest(missing=key), self.assertRaisesRegex(ProbeError,'invalid_native_report'):
                native._report(dict(base, scene_changes=[missing]))

    def test_old_v1_capability_cannot_start_the_new_client(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True, capabilities=['necrogold_native_v1']) as server:
            record = self.execute(server, folder)
            self.assertFalse(record['start_attempted'])
            self.assertEqual('native_capability_missing', record['stop_reason'])
            self.assertEqual([], server.calls)

    def test_045_script_requires_v3_and_uses_045_output(self):
        path = Path(native.__file__).resolve().parents[1]/'test_045.sh'
        import subprocess
        self.assertEqual(0, subprocess.run(['sh','-n',str(path)],capture_output=True).returncode)
        text = path.read_text()
        self.assertIn('native-walk-v3 / 1.98.14-ngg2',text)
        self.assertIn('--output runtime/test-045',text)
        self.assertNotIn('necroprobe.preflight',text)


if __name__ == '__main__':
    unittest.main()
