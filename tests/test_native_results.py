"""TEST045/046 result collection and closed native diagnostics contracts."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import errno
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


def motion_wait(**extra):
    value = dict(command_id=2, source_capture_id=13, last_capture_id=16,
                 deadline_ns=1000, attempts=1, last_motion=0, active=True)
    value.update(extra)
    return value


def raster_sample(capture_id=1, **extra):
    value = dict(capture_id=capture_id, source_width=1792, source_height=828,
                 orientation=1, source_ns=1, draw_ns=2, orient_ns=0,
                 scale_ns=3, copy_pixels=0)
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

    def test_motion_wait_and_raster_trace_reach_results_and_saved_journal(self):
        canary = 'PRIVATE_TRACE_VALUE'
        def traces(method, result):
            if method == 'necro_native_results':
                result['report'].update(motion_wait=motion_wait(private=canary),
                    raster_samples=[raster_sample(private=canary)], raster_samples_dropped=0)
            return result
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True, transform=traces) as server:
            record = self.execute(server, folder)
            expected = dict(motion_wait=motion_wait(), raster_samples=[raster_sample()],
                            raster_samples_dropped=0)
            self.assertEqual(expected, {key:record['native_report'].get(key) for key in expected})
            self.assertTrue(record['resolved'])
            self.assertNotIn(canary, json.dumps(record))
            self.assertEqual(record, native._load(Path(folder)))
            saved = json.loads((Path(folder)/'active.json').read_text())
            self.assertEqual(expected, {key:saved['native_report'][key] for key in expected})
            self.assertEqual(1, sum(m == 'necro_native_results' for m,p in server.calls))

    def test_raster_ring_boundaries_survive_encrypted_results_and_legacy_projection(self):
        for count in (0, 31, 32, 33):
            with self.subTest(count=count):
                ids = list(range(1, count+1)) if count <= 32 else [1]+list(range(3,34))
                samples = [raster_sample(i) for i in ids]
                dropped = max(0, count-32)
                def traces(method, result):
                    result['report'].update(motion_wait=motion_wait(attempts=3, last_motion=7, active=False),
                        raster_samples=deepcopy(samples), raster_samples_dropped=dropped)
                    return result
                with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True, transform=traces) as server:
                    record = self.execute(server, folder)
                    self.assertTrue(record['resolved'])
                    self.assertEqual(samples, record['native_report']['raster_samples'])
                    self.assertEqual(dropped, record['native_report']['raster_samples_dropped'])
                    legacy = deepcopy(record)
                    legacy['revision'] = 'native-walk-v3'
                    legacy['native_report']['motion_wait']['private'] = 'PRIVATE'
                    for row in legacy['native_report']['raster_samples']:
                        row['private'] = 'PRIVATE'
                    native._save(Path(folder), legacy)
                    loaded = native._load(Path(folder))
                    self.assertEqual(record['native_report'], loaded['native_report'])
                    native._save(Path(folder), loaded)
                    self.assertNotIn('PRIVATE', (Path(folder)/'active.json').read_text())

    def test_motion_wait_requires_all_seven_bounded_typed_fields(self):
        base = dict(schema='ngg2-native-v1', clock_id='a'*32, device_now_ns=1, input_state=0)
        invalid = [None, [], {}, motion_wait(attempts=4), motion_wait(last_motion=8),
                   motion_wait(active=1), motion_wait(active=None)]
        for key in motion_wait():
            missing = motion_wait()
            missing.pop(key)
            invalid.append(missing)
            if key != 'active':
                for value in (True, -1, 2**63):
                    invalid.append(motion_wait(**{key:value}))
        for value in invalid:
            with self.subTest(value=value), self.assertRaisesRegex(ProbeError, 'invalid_native_report'):
                native._report(dict(base, motion_wait=value))
        self.assertEqual(motion_wait(command_id=2**63-1, deadline_ns=2**63-1, attempts=0),
            native._report(dict(base, motion_wait=motion_wait(command_id=2**63-1,
                deadline_ns=2**63-1, attempts=0)))['motion_wait'])

    def test_raster_trace_rejects_missing_boolean_range_geometry_and_overflow_values(self):
        base = dict(schema='ngg2-native-v1', clock_id='a'*32, device_now_ns=1, input_state=0)
        invalid = [None, {}, [raster_sample()]*33, [raster_sample(), raster_sample()],
            [raster_sample(capture_id=0)], [raster_sample(source_width=4097)],
            [raster_sample(source_width=4096, source_height=4096)],
            [raster_sample(source_width=0)], [raster_sample(source_height=0)],
            [raster_sample(orientation=0)], [raster_sample(orientation=9)],
            [raster_sample(orientation=5)], [raster_sample(source_height=829)],
            [raster_sample(copy_pixels=1792*828+1)],
            [raster_sample(source_ns=2**63-1, draw_ns=1, orient_ns=0, scale_ns=0)]]
        for key in raster_sample():
            missing = raster_sample()
            missing.pop(key)
            invalid.append([missing])
            for value in (True, -1, 2**63):
                invalid.append([raster_sample(**{key:value})])
        for value in invalid:
            with self.subTest(value=value), self.assertRaisesRegex(ProbeError, 'invalid_native_report'):
                native._report(dict(base, raster_samples=value))
        valid = [raster_sample(source_ns=2**63-1, draw_ns=0, orient_ns=0, scale_ns=0,
                               copy_pixels=1792*828),
                 raster_sample(capture_id=2, source_width=828, source_height=1792, orientation=8)]
        self.assertEqual(valid, native._report(dict(base, raster_samples=valid))['raster_samples'])
        for value in (True, -1, 2**63, None, 1.0):
            with self.subTest(dropped=value), self.assertRaisesRegex(ProbeError, 'invalid_native_report'):
                native._report(dict(base, raster_samples_dropped=value))
        self.assertEqual(base, native._report(base))

    def test_bad_trace_is_rejected_on_results_and_legacy_journal_reload(self):
        def malformed(method, result):
            if method == 'necro_native_results':
                result['report']['motion_wait'] = motion_wait(active=1)
            return result
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True, transform=malformed) as server:
            record = self.execute(server, folder)
            self.assertFalse(record['resolved'])
            self.assertEqual('invalid_native_report', record['stop_reason'])
            self.assertNotIn('motion_wait', record['native_report'])
            for invalid in ({'motion_wait':motion_wait(attempts=4)},
                            {'raster_samples':[raster_sample(capture_id=0)]},
                            {'raster_samples_dropped':True}):
                legacy = deepcopy(record)
                legacy['native_report'].update(invalid)
                native._save(Path(folder), legacy)
                with self.subTest(invalid=invalid), self.assertRaisesRegex(ProbeError, 'native_journal_invalid'):
                    native._load(Path(folder))

    def test_maximum_report_trace_images_and_host_diagnostics_fit_the_json_node_limit(self):
        samples = [raster_sample(i) for i in [1]+list(range(226,257))]
        def maximum(method, result):
            report = result['report']
            report.update({key:0 for key in native.NUMERIC_KEYS})
            report.update(native.FIXED_TEXT)
            report.update({key:False for key in native.BOOL_KEYS})
            report.update(input_state=4, terminal=1, device_now_ns=100_000, workers_drained=True,
                motion_wait=motion_wait(attempts=3, last_motion=7, active=False),
                raster_samples=deepcopy(samples), raster_samples_dropped=224,
                referenced_capture_ids=list(range(1,257)), missing_capture_ids=list(range(1,257)),
                scene_changes=[scene_change(command_id=i+1, observed_capture_id=i+21,
                    replan_count=min(i,2)) for i in range(3)],
                captures=[dict(id=i+1, start_ns=i*100, end_ns=i*100+1,
                    decode_end_ns=i*100+2, analysis_start_ns=i*100+3, analysis_end_ns=i*100+4,
                    completed_prefix_start=i, completed_prefix_end=i,
                    inflight_start=False, inflight_end=False, stable=True) for i in range(256)],
                events=[{key:0 for key in ('id','ordinal','kind','direction','x','y','target_ns',
                    'not_before_ns','deadline_ns','source_capture_id','source_start_ns','phase_sample_ns',
                    'begin_ns','end_ns','observed_capture_id','outcome','reason','motion','dx','dy')}
                    for _ in range(64)])
            if method == 'necro_native_results':
                images = []
                for i in range(20):
                    item = image_item('capture-'+str(i+1)+'.png')
                    item.update(capture_id=i+1, completed_prefix=3, stable_prefix=True, decode_end_ns=4,
                        completed_prefix_start=3, completed_prefix_end=3, inflight_start=False, inflight_end=False)
                    images.append(item)
                result.update(images=images, retained_images=20, exported_images=20,
                    omitted_image_count=236, exported_capture_ids=list(range(1,21)),
                    omitted_capture_ids=list(range(1,257)), api_version=native.API_VERSION)
            return result
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True, transform=maximum) as server:
            record = self.execute(server, folder)
            self.assertEqual('native_input_unresolved', record['stop_reason'])
            self.assertEqual((256,64,3,32,20), tuple(len(value) for value in (
                record['native_report']['captures'], record['native_report']['events'],
                record['native_report']['scene_changes'], record['native_report']['raster_samples'], record['images'])))
            row = dict(invocation='a'*32, method='necro_native_status', host_ns=1,
                error=None, rpc_stage='complete', host_timings={key:1 for key in native.HTTP_TIMING_KEYS})
            record['events'] = [deepcopy(row) for _ in range(128)]
            template = record['preflight']['attempts'][0]
            record['preflight']['attempts'] = []
            for i in range(1,5):
                start = record['preflight']['started_ns']+i
                diagnostic = dict(template['diagnostic'], started_ns=start, ended_ns=start,
                    kind='ok' if i == 4 else 'refused', errno=None if i == 4 else errno.ECONNREFUSED,
                    status=200 if i == 4 else None)
                record['preflight']['attempts'].append(dict(attempt=i, started_ns=start, ended_ns=start,
                    error=None if i == 4 else 'connection_error', diagnostic=diagnostic))
            # Run the production bounded JSON scanner, not just json.loads.
            pending, nodes = [record], 0
            while pending:
                item = pending.pop()
                nodes += 1
                if isinstance(item, dict):
                    pending.extend(item.values())
                elif isinstance(item, list):
                    pending.extend(item)
            self.assertLessEqual(nodes, 10_000)
            native._save(Path(folder), record)
            self.assertEqual(record, native._load(Path(folder)))
            server.schema_calls.clear()
            before = len(server.calls)
            recovered = self.execute(server, folder)
            self.assertEqual(record['run_id'], recovered['run_id'])
            self.assertEqual([], server.schema_calls)
            self.assertEqual(['necro_native_status','necro_native_results'],
                             [method for method,params in server.calls[before:]])
            self.assertEqual(samples, recovered['native_report']['raster_samples'])
            self.assertEqual(224, recovered['native_report']['raster_samples_dropped'])
            self.assertEqual(20, len(recovered['images']))

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

    def test_failed_results_recover_v1_v2_and_v3_journals_without_get_or_start(self):
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
            for revision in ('native-walk-v1','native-walk-v2','native-walk-v3'):
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

    def test_old_v1_v2_capabilities_cannot_start_the_new_client(self):
        for tags in ([], ['necrogold_native_v1'], ['necrogold_native_v2'],
                     ['necrogold_native_v1','necrogold_native_v2']):
            with self.subTest(tags=tags), tempfile.TemporaryDirectory() as folder, \
                    NativeServer(finish=True, capabilities=tags) as server:
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

    def test_046_script_cli_and_capability_require_the_new_runtime(self):
        path = Path(native.__file__).resolve().parents[1]/'test_046.sh'
        import subprocess
        self.assertEqual(0, subprocess.run(['sh','-n',str(path)],capture_output=True).returncode)
        text = path.read_text()
        self.assertEqual('native-walk-v4', native.REVISION)
        self.assertEqual('necrogold_native_v3', native.CAPABILITY)
        self.assertEqual('runtime/test-046', native.parser().parse_args([]).output)
        self.assertIn('native-walk-v4 / 1.98.14-ngg2', text)
        self.assertIn('--output runtime/test-046', text)
        self.assertNotIn('necroprobe.preflight', text)


if __name__ == '__main__':
    unittest.main()
