"""TEST051 bounded authenticated terminal image export and resumable checkpoints."""
import base64
from copy import deepcopy
import hashlib
import json
import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from necroprobe import native_walk as native
from necroprobe.crypto import Crypto
from necroprobe.protocol import HttpTransport
from necroprobe.validation import ProbeError
from test_native_walk import NativeServer, image_item
from test_protocol import KEY, TOK
from test_native_results import scene_change
from timer_support import TimerTestCase


def page_images(*items):
    def images(method, result):
        if method == 'necro_native_results':
            result['images'] = deepcopy(list(items))
        return result
    return images


class CountingCrypto:
    engine = 'python'
    def __init__(self):
        self.calls = 0
        self.crypto = Crypto(native=False)
    def xor(self, key, nonce, raw):
        self.calls += 1
        return self.crypto.xor(key, nonce, raw)


def detail(**updates):
    row = dict(command_id=2,source_capture_id=20,observed_capture_id=21,
        validation=2,continuous_count=1,chain_count=1,cell_count=1,omitted_cells=0,
        cells=[dict(x=-11,y=-5,tile_before=0,tile_after=1,protected_before=0,protected_after=0)])
    row.update(updates)
    return row


class PagedResultsTests(TimerTestCase):
    def client(self, server, crypto=None):
        return native.NativeClient(HttpTransport(server.server.server_port), KEY, TOK,
            deadline_owner=self.timer, crypto=crypto or Crypto(native=False), timeout=8)

    def execute(self, server, folder, **options):
        options.setdefault('max_seconds', 8)
        options.setdefault('poll_seconds', .001)
        return native.run_session(self.client(server), folder,
            lock_path=Path(folder)/'lock', **options)

    def test_fresh_client_collects_the_terminal_png_with_manifest_and_chunk(self):
        def images(method, result):
            if method == 'necro_native_results':
                result['images'] = [image_item()]
            return result
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True, transform=images) as server:
            record = self.execute(server, folder)
            self.assertTrue(record['resolved'], record['stop_reason'])
            self.assertEqual(1, len(record['images']))
            calls = [params for method,params in server.calls if method == 'necro_native_results']
            self.assertEqual(['manifest', 'chunk'], [params.get('mode') for params in calls],
                             'terminal_png_requires_authenticated_manifest_and_bounded_chunk')

    def test_chunk_offsets_are_contiguous_and_each_call_keeps_the_eight_second_ceiling(self):
        image = image_item(size=2*65536+17)
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=page_images(image)) as server:
            client = self.client(server)
            calls = []
            original = client.call
            def traced(method, params=None, *, timeout=None):
                calls.append((method, params, timeout))
                return original(method, params, timeout=timeout)
            with patch.object(client, 'call', side_effect=traced):
                record = native.run_session(client, folder, lock_path=Path(folder)/'lock',
                    max_seconds=8, poll_seconds=.001)
            self.assertTrue(record['resolved'], record['stop_reason'])
            chunks = [p for m,p,t in calls if p.get('mode') == 'chunk']
            self.assertEqual([0,65536,131072], [p['offset'] for p in chunks])
            self.assertTrue(all(0 < t <= 8 for m,p,t in calls if m == 'necro_native_results'))
            self.assertEqual([131089], record['image_export']['offsets'])
            self.assertEqual(record, native._load(Path(folder)))

    def test_http_mode_limits_reject_before_response_decrypt_with_or_without_length(self):
        for mode,limit in (('manifest',512*1024), ('chunk',256*1024)):
            for include_length in (False, True):
                for extra in (0,1):
                    with self.subTest(mode=mode, length=include_length, extra=extra), \
                            NativeServer(finish=True, transform=page_images(image_item())) as server:
                        crypto = CountingCrypto()
                        client = self.client(server, crypto)
                        run_id = 'a'*32
                        client.call('necro_native_results', {'run_id':run_id,'mode':'manifest'})
                        crypto.calls = 0
                        params = {'run_id':run_id, 'mode':mode}
                        if mode == 'chunk':
                            params.update(export_id=run_id,capture_id=1,offset=0)
                        def wire(_method,_params,raw):
                            padded = raw+b' '*(limit+extra-len(raw))
                            return padded, len(padded) if include_length else None
                        server.wire_transform = wire
                        if extra:
                            with self.assertRaisesRegex(ProbeError, 'http_body_limit'):
                                client.call('necro_native_results', params)
                            self.assertEqual(1, crypto.calls, 'oversize_must_skip_response_crypto')
                            self.assertEqual('http', client.last_failure['stage'])
                            self.assertNotIn('decrypt_start_ns',client.last_failure['host_timings'])
                            self.assertEqual('body_limit', client.transport.last_diagnostic['kind'])
                        else:
                            client.call('necro_native_results', params)
                            self.assertEqual(2, crypto.calls)
                        self.assertIsInstance(client.transport, HttpTransport)

    def test_http_truncation_precedes_decrypt_and_legacy_keeps_its_larger_admission(self):
        with NativeServer(finish=True) as server:
            crypto = CountingCrypto()
            client = self.client(server, crypto)
            server.wire_transform = lambda m,p,raw:(raw,len(raw)+1)
            with self.assertRaisesRegex(ProbeError,'http_body_truncated'):
                client.call('necro_native_results', {'run_id':'a'*32,'mode':'manifest'})
            self.assertEqual(1,crypto.calls)
            self.assertEqual('http',client.last_failure['stage'])
            server.wire_transform = lambda m,p,raw:(raw+b' '*((512*1024+1)-len(raw)),None)
            self.assertIn('images',client.call('necro_native_results', {'run_id':'a'*32}).result)
            self.assertEqual(3,crypto.calls)

    def test_lost_chunk_resumes_the_same_export_and_offset_without_schema_or_start(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=page_images(image_item(size=65553))) as server:
            lost = [False]
            def lose_second(method, params, result):
                if params.get('mode') == 'chunk' and params['offset'] == 65536 and not lost[0]:
                    lost[0] = True
                    server.lose.append(method)
                return result
            server.page_transform = lose_second
            first = self.execute(server,folder)
            self.assertFalse(first['resolved'])
            self.assertEqual([65536],first['image_export']['offsets'])
            server.schema_calls.clear()
            before = len(server.calls)
            recovered = self.execute(server,folder)
            self.assertTrue(recovered['resolved'],recovered['stop_reason'])
            self.assertEqual(first['run_id'],recovered['run_id'])
            calls = server.calls[before:]
            self.assertEqual([],server.schema_calls)
            self.assertEqual(['necro_native_status','necro_native_results','necro_native_results'],
                             [m for m,p in calls])
            self.assertEqual(65536,calls[-1][1]['offset'])
            self.assertEqual(first['image_export']['export_id'],calls[-1][1]['export_id'])

    def test_fragment_rename_before_checkpoint_replays_identical_bytes_and_rejects_conflicts(self):
        for conflict in (False,True):
            with self.subTest(conflict=conflict), tempfile.TemporaryDirectory() as folder, \
                    NativeServer(finish=True, transform=page_images(image_item(size=65553))) as server:
                atomic = native._atomic
                crashed = [False]
                class Crash(Exception):
                    pass
                def rename_then_crash(path,raw):
                    atomic(path,raw)
                    if path.name.endswith('.part') and not crashed[0]:
                        crashed[0] = True
                        raise Crash('after_rename_before_journal')
                with patch.object(native,'_atomic',side_effect=rename_then_crash):
                    with self.assertRaises(Crash):
                        self.execute(server,folder)
                first = native._load(Path(folder))
                self.assertEqual([0],first['image_export']['offsets'])
                if conflict:
                    def change_chunk(method,params,result):
                        if params.get('mode') == 'chunk':
                            raw = base64.b64decode(result['data_base64'])
                            result['data_base64'] = base64.b64encode(bytes([raw[0]^1])+raw[1:]).decode()
                        return result
                    server.page_transform = change_chunk
                server.schema_calls.clear()
                before = len(server.calls)
                recovered = self.execute(server,folder)
                self.assertEqual(not conflict,recovered['resolved'])
                self.assertEqual([],server.schema_calls)
                calls = server.calls[before:]
                self.assertNotIn('necro_native_start',[m for m,p in calls])
                chunks = [p for m,p in calls if p.get('mode') == 'chunk']
                self.assertEqual(0,chunks[0]['offset'])
                self.assertEqual(first['image_export']['export_id'],chunks[0]['export_id'])
                if conflict:
                    self.assertEqual([0],recovered['image_export']['offsets'])
                    self.assertEqual('invalid_native_images',recovered['stop_reason'])
                else:
                    self.assertEqual([65553],recovered['image_export']['offsets'])

    def test_final_image_rename_before_image_checkpoint_is_recovered_without_another_input(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=page_images(image_item())) as server:
            atomic = native._atomic
            class Crash(Exception):
                pass
            def crash_after_image(path,raw):
                atomic(path,raw)
                if path.name == 'initial.png':
                    raise Crash()
            with patch.object(native,'_atomic',side_effect=crash_after_image):
                with self.assertRaises(Crash):
                    self.execute(server,folder)
            first = native._load(Path(folder))
            self.assertEqual([],first['images'])
            self.assertEqual([32],first['image_export']['offsets'])
            before = len(server.calls)
            server.schema_calls.clear()
            recovered = self.execute(server,folder)
            self.assertTrue(recovered['resolved'])
            self.assertEqual(1,len(recovered['images']))
            self.assertEqual([],server.schema_calls)
            self.assertEqual(['necro_native_status','necro_native_results'],[m for m,p in server.calls[before:]])

    def test_terminal_export_storage_error_does_not_cancel_and_invalidate_the_cached_export(self):
        with tempfile.TemporaryDirectory() as folder,NativeServer(finish=True,
                transform=page_images(image_item())) as server:
            atomic = native._atomic
            def storage_error_after_rename(path,raw):
                atomic(path,raw)
                if path.name.endswith('.part'):
                    raise OSError('terminal_export_storage_failure')
            with patch.object(native,'_atomic',side_effect=storage_error_after_rename):
                with self.assertRaises(OSError):
                    self.execute(server,folder)
            self.assertEqual(0,sum(method == 'necro_native_cancel' for method,params in server.calls),
                             'terminal_storage_error_must_preserve_the_existing_export_cache')
            first = native._load(Path(folder))
            self.assertFalse(first['resolved'])
            before = len(server.calls)
            server.schema_calls.clear()
            recovered = self.execute(server,folder)
            self.assertTrue(recovered['resolved'],recovered['stop_reason'])
            self.assertEqual(first['image_export']['export_id'],recovered['image_export']['export_id'])
            self.assertEqual([],server.schema_calls)
            self.assertEqual(['necro_native_status','necro_native_results','necro_native_results'],
                             [m for m,p in server.calls[before:]])

    def test_partial_export_keeps_verified_images_and_cursor_when_http_chunk_is_over_limit(self):
        first_image = image_item()
        second_image = dict(image_item(name='terminal.png',size=65553),capture_id=2)
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=page_images(first_image,second_image)) as server:
            def oversized(method,params,raw):
                if params.get('mode') == 'chunk' and params['capture_id'] == 2 and params['offset'] == 65536:
                    return raw+b' '*(256*1024+1-len(raw)), None
                return raw, len(raw)
            server.wire_transform = oversized
            first = self.execute(server,folder)
            self.assertFalse(first['resolved'])
            self.assertEqual([32,65536],first['image_export']['offsets'])
            self.assertEqual(['initial.png'],[item['name'] for item in first['images']])
            image_path = Path(folder)/('native-'+first['run_id'])/'images'/'initial.png'
            self.assertEqual(first_image['sha256'],hashlib.sha256(image_path.read_bytes()).hexdigest())
            self.assertEqual('http_body_limit',first['stop_reason'])
            self.assertEqual('http',first['events'][-1]['rpc_stage'])
            before = len(server.calls)
            server.schema_calls.clear()
            server.wire_transform = None
            recovered = self.execute(server,folder)
            self.assertTrue(recovered['resolved'])
            self.assertEqual(2,len(recovered['images']))
            self.assertEqual([],server.schema_calls)
            self.assertEqual([65536],[p['offset'] for m,p in server.calls[before:] if p.get('mode') == 'chunk'])

    def test_manifest_identity_cannot_change_between_recovery_invocations(self):
        for key,value in (('export_id','b'*32),('total_bytes',33),('chunk_bytes',1)):
            with self.subTest(key=key), tempfile.TemporaryDirectory() as folder, \
                    NativeServer(finish=True,transform=page_images(image_item())) as server:
                def lose_chunk(method,params,result):
                    if params.get('mode') == 'chunk':
                        server.lose.append(method)
                    return result
                server.page_transform = lose_chunk
                first = self.execute(server,folder)
                self.assertFalse(first['resolved'])
                def changed(method,params,result):
                    if params.get('mode') == 'manifest':
                        result[key] = value
                    return result
                server.page_transform = changed
                before = len(server.calls)
                recovered = self.execute(server,folder)
                self.assertFalse(recovered['resolved'])
                self.assertEqual(first['image_export'],recovered['image_export'])
                self.assertFalse(any(p.get('mode') == 'chunk' for m,p in server.calls[before:]))

    def test_chunk_identity_offsets_lengths_and_full_digest_are_checked_before_commit(self):
        variants = [('run_id','b'*32),('export_id','b'*32),('capture_id',2),('capture_id',True),
                    ('offset',1),('offset',True),('byte_length',33),('chunk_bytes',31),
                    ('sha256','b'*64),('data_base64','!!')]
        for key,value in variants:
            with self.subTest(key=key,value=value), tempfile.TemporaryDirectory() as folder, \
                    NativeServer(finish=True,transform=page_images(image_item())) as server:
                def change(method,params,result):
                    if params.get('mode') == 'chunk':
                        result[key] = value
                    return result
                server.page_transform = change
                record = self.execute(server,folder)
                self.assertFalse(record['resolved'])
                self.assertEqual('invalid_native_images',record['stop_reason'])
                self.assertEqual([],record['images'])
                self.assertEqual([0],record['image_export']['offsets'])

    def test_export_completion_does_not_resolve_unknown_input_or_ui_frozen(self):
        for input_state,frozen in ((4,False),(0,True)):
            with self.subTest(input_state=input_state,frozen=frozen), tempfile.TemporaryDirectory() as folder, \
                    NativeServer(finish=True,input_state=input_state,transform=page_images(image_item())) as server:
                def ui(method,params,result):
                    if params.get('mode') == 'manifest':
                        result['report']['ui_frozen'] = frozen
                    return result
                server.page_transform = ui
                record = self.execute(server,folder)
                self.assertFalse(record['resolved'])
                self.assertEqual(1,len(record['images']))
                self.assertEqual('native_input_unresolved',record['stop_reason'])

    def test_paged_export_attempt_budget_is_finite_and_does_not_extend_the_invocation(self):
        for option in ('export_seconds','max_seconds'):
            with self.subTest(option=option), tempfile.TemporaryDirectory() as folder, \
                    NativeServer(finish=True,transform=page_images(image_item(size=65553))) as server:
                def delay(method,params,result):
                    if params.get('mode') == 'chunk':
                        time.sleep(.1)
                    return result
                server.page_transform = delay
                record = self.execute(server,folder,**{option:.15})
                self.assertFalse(record['resolved'])
                self.assertIn(record['stop_reason'],('rpc_deadline','host_deadline'))
                self.assertEqual([65536],record['image_export']['offsets'])
                chunks = [p for m,p in server.calls if p.get('mode') == 'chunk']
                self.assertEqual([0,65536],[p['offset'] for p in chunks])

    def test_new_paged_export_uses_remaining_180_seconds_and_old_journal_keeps_its_185_seconds(self):
        for revision,elapsed in ((native.REVISION,180), (native.REVISION,179.75),
                                 ('native-walk-v9',180), ('native-walk-v9',179.75),
                                 ('native-walk-v8',180)):
            with self.subTest(revision=revision,elapsed=elapsed), tempfile.TemporaryDirectory() as folder, \
                    NativeServer(finish=True) as server:
                seed = self.execute(server,folder)
                seed.update(revision=revision,resolved=False)
                if revision not in native.PAGED_REVISIONS:
                    seed.pop('image_export')
                native._save(Path(folder),seed)
                began = 1_000_000_000
                now = [began]
                def near_end(method,params,result):
                    if method == 'necro_native_status':
                        now[0] = began+int(elapsed*1e9)
                    return result
                server.page_transform = near_end
                before = len(server.calls)
                client = self.client(server)
                original = client.call
                timeouts = []
                def trace(method,params=None,*,timeout=None):
                    if method == 'necro_native_results':
                        timeouts.append(timeout)
                    return original(method,params,timeout=timeout)
                with patch.object(client,'call',side_effect=trace):
                    result = native.run_session(client,folder,lock_path=Path(folder)/'lock',
                        max_seconds=185,clock=lambda:now[0],poll_seconds=.001)
                calls = server.calls[before:]
                if revision in native.PAGED_REVISIONS and elapsed == 180:
                    self.assertFalse(result['resolved'])
                    self.assertEqual('host_deadline',result['stop_reason'])
                    self.assertEqual(['necro_native_status'],[m for m,p in calls])
                    self.assertEqual([],timeouts)
                else:
                    self.assertTrue(result['resolved'],result['stop_reason'])
                    self.assertEqual(1,len(timeouts))
                    self.assertEqual(.25 if revision in native.PAGED_REVISIONS else 5,timeouts[0])

    def test_export_deadline_after_final_image_io_keeps_evidence_unresolved_and_recoverable(self):
        with tempfile.TemporaryDirectory() as folder,NativeServer(finish=True,
                transform=page_images(image_item())) as server:
            now = [0]
            atomic = native._atomic
            def late_image_io(path,raw):
                atomic(path,raw)
                if path.name == 'initial.png':
                    now[0] = 500_000_000
            with patch.object(native,'_atomic',side_effect=late_image_io):
                first = self.execute(server,folder,clock=lambda:now[0],export_seconds=.5)
            self.assertFalse(first['resolved'],'final_image_io_cannot_turn_expired_export_into_success')
            self.assertEqual('host_deadline',first['stop_reason'])
            self.assertEqual(1,len(first['images']))
            self.assertEqual([32],first['image_export']['offsets'])
            before = len(server.calls)
            server.schema_calls.clear()
            recovered = self.execute(server,folder)
            self.assertTrue(recovered['resolved'])
            self.assertEqual([],server.schema_calls)
            self.assertEqual(['necro_native_status','necro_native_results'],[m for m,p in server.calls[before:]])

    def test_new_cancel_during_paged_export_stops_before_the_next_chunk_and_keeps_progress(self):
        with tempfile.TemporaryDirectory() as folder,NativeServer(finish=True,
                transform=page_images(image_item(size=65553))) as server:
            stopped = [False]
            def cancel_after_chunk(method,params,result):
                if params.get('mode') == 'chunk':
                    stopped[0] = True
                return result
            server.page_transform = cancel_after_chunk
            first = self.execute(server,folder,cancelled=lambda:stopped[0])
            self.assertFalse(first['resolved'],'new_terminal_export_cancel_must_stop_further_read_only_calls')
            self.assertEqual('cancel_requested',first['stop_reason'])
            self.assertEqual([65536],first['image_export']['offsets'])
            self.assertEqual([0],[p['offset'] for m,p in server.calls if p.get('mode') == 'chunk'])
            self.assertEqual(0,sum(m == 'necro_native_cancel' for m,p in server.calls))

    def test_final_journal_io_cannot_publish_a_late_or_newly_cancelled_export_as_resolved(self):
        for reason in ('host_deadline','cancel_requested'):
            with self.subTest(reason=reason),tempfile.TemporaryDirectory() as folder, \
                    NativeServer(finish=True,transform=page_images(image_item())) as server:
                now = [0]
                stopped = [False]
                save = native._save
                def final_io(base,record):
                    save(base,record)
                    if record['resolved'] and 'image_export' in record:
                        if reason == 'host_deadline':
                            now[0] = 500_000_000
                        else:
                            stopped[0] = True
                with patch.object(native,'_save',side_effect=final_io):
                    first = self.execute(server,folder,clock=lambda:now[0],export_seconds=.5,
                        cancelled=lambda:stopped[0])
                self.assertFalse(first['resolved'],'late_final_journal_io_must_not_publish_resolved')
                self.assertEqual(reason,first['stop_reason'])
                self.assertEqual(first,native._load(Path(folder)))
                self.assertEqual([32],first['image_export']['offsets'])
                self.assertEqual(1,len(first['images']))

    def test_manifest_processing_and_zero_or_already_verified_exports_still_check_the_attempt_deadline(self):
        for stage in ('manifest_validation','empty_checkpoint','verified_checkpoint'):
            with self.subTest(stage=stage),tempfile.TemporaryDirectory() as folder, \
                    NativeServer(finish=True,transform=page_images(image_item())
                                 if stage == 'verified_checkpoint' else None) as server:
                if stage == 'verified_checkpoint':
                    seed = self.execute(server,folder)
                    seed['resolved'] = False
                    native._save(Path(folder),seed)
                now = [0]
                manifest_seen = [False]
                manifest = native._manifest
                save = native._save
                def late_manifest(value,run_id):
                    selected = manifest(value,run_id)
                    manifest_seen[0] = True
                    if stage == 'manifest_validation':
                        now[0] = 500_000_000
                    return selected
                def late_checkpoint(base,record):
                    save(base,record)
                    if stage != 'manifest_validation' and manifest_seen[0] and 'image_export' in record:
                        now[0] = 500_000_000
                before = len(server.calls)
                with patch.object(native,'_manifest',side_effect=late_manifest), \
                        patch.object(native,'_save',side_effect=late_checkpoint):
                    record = self.execute(server,folder,clock=lambda:now[0],export_seconds=.5)
                self.assertFalse(record['resolved'])
                self.assertEqual('host_deadline',record['stop_reason'])
                self.assertEqual([], [p for m,p in server.calls[before:] if p.get('mode') == 'chunk'])
                if stage == 'verified_checkpoint':
                    self.assertEqual([32],record['image_export']['offsets'])
                    self.assertEqual(1,len(record['images']))

    def test_client_052_script_and_capability_require_same_action_runtime(self):
        path = Path(native.__file__).resolve().parents[1]/'test_052.sh'
        self.assertEqual(0,subprocess.run(['sh','-n',str(path)],capture_output=True).returncode)
        self.assertEqual('native-walk-v10',native.REVISION)
        self.assertEqual('necrogold_native_v9',native.CAPABILITY)
        self.assertEqual('runtime/test-052',native.parser().parse_args([]).output)
        self.assertIn('native-walk-v10 / 1.98.14-ngg2',path.read_text())
        self.assertIn('--output runtime/test-052',path.read_text())

    def test_manifest_counts_geometry_names_and_budgets_are_closed(self):
        raw = image_item()
        metadata = {key:value for key,value in raw.items() if key != 'data_base64'}
        metadata['byte_length'] = 32
        maximum = [dict(metadata,name='frame-'+str(i)+'.png',capture_id=i,
                        byte_length=native.MAX_IMAGE) for i in range(8)]
        self.assertEqual(4*1024*1024,sum(item['bytes'] for item in native._manifest_images(maximum)))
        twenty = [dict(metadata,name='frame-'+str(i)+'.png',capture_id=i) for i in range(20)]
        self.assertEqual(20,len(native._manifest_images(twenty)))
        bad = [None,{},[metadata,metadata],twenty+[dict(metadata,name='more.png',capture_id=20)],
               maximum+[dict(metadata,name='more.png',capture_id=8)],
               [dict(metadata,byte_length=native.MAX_IMAGE+1)],
               [dict(metadata,byte_length=True)],[dict(metadata,byte_length=23)],
               [dict(metadata,pixel_width=414)],[dict(metadata,pixel_height=True)],
               [dict(metadata,name='../image.png')],[dict(metadata,sha256='PRIVATE')],
               [dict(metadata,data_base64='PRIVATE')],
               [metadata,dict(metadata,name='second.png')]]
        for value in bad:
            with self.subTest(value=value),self.assertRaisesRegex(ProbeError,'invalid_native_images'):
                native._manifest_images(value)

    def test_full_png_digest_and_header_are_verified_before_image_publish(self):
        for mutation in ('digest','header','dimensions'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as folder:
                item = image_item()
                raw = base64.b64decode(item['data_base64'])
                if mutation == 'digest':
                    raw = raw[:-1]+b'\x01'
                elif mutation == 'header':
                    raw = b'!'+raw[1:]
                    item['sha256'] = hashlib.sha256(raw).hexdigest()
                else:
                    raw = raw[:16]+bytes(8)+raw[24:]
                    item['sha256'] = hashlib.sha256(raw).hexdigest()
                item['data_base64'] = base64.b64encode(raw).decode()
                with NativeServer(finish=True,transform=page_images(item)) as server:
                    record = self.execute(server,folder)
                    self.assertFalse(record['resolved'])
                    self.assertEqual('invalid_native_images',record['stop_reason'])
                    self.assertEqual([],record['images'])
                    self.assertFalse((Path(folder)/('native-'+record['run_id'])/'images'/'initial.png').exists())

    def test_duplicate_and_out_of_order_chunk_responses_cannot_advance_a_committed_cursor(self):
        with tempfile.TemporaryDirectory() as folder,NativeServer(finish=True,
                transform=page_images(image_item(size=65553))) as server:
            def repeated(method,params,result):
                if params.get('mode') == 'chunk' and params['offset'] == 65536:
                    result['offset'] = 0
                return result
            server.page_transform = repeated
            record = self.execute(server,folder)
            self.assertFalse(record['resolved'])
            self.assertEqual([65536],record['image_export']['offsets'])
            self.assertEqual('invalid_native_images',record['stop_reason'])

    def test_checkpoint_ranges_digests_and_revision_are_validated_before_network(self):
        with tempfile.TemporaryDirectory() as folder,NativeServer(finish=True,
                transform=page_images(image_item())) as server:
            record = self.execute(server,folder)
            record['resolved'] = False
            for key,value in (('offsets',[True]),('offsets',[-1]),('offsets',[1]),
                              ('offsets',[33]),('offsets',[]),('prefix_sha256',['PRIVATE']),
                              ('prefix_sha256',[]),('total_bytes',33),('chunk_bytes',True),
                              ('chunk_bytes',32768),('export_id','PRIVATE')):
                with self.subTest(key=key,value=value):
                    damaged = deepcopy(record)
                    damaged['image_export'][key] = value
                    native._save(Path(folder),damaged)
                    before = len(server.calls)
                    with self.assertRaisesRegex(ProbeError,'native_journal_invalid'):
                        self.execute(server,folder)
                    self.assertEqual(before,len(server.calls))
            damaged = deepcopy(record)
            damaged['revision'] = 'native-walk-v8'
            native._save(Path(folder),damaged)
            with self.assertRaisesRegex(ProbeError,'native_journal_invalid'):
                self.execute(server,folder)

    def test_scene_change_details_survive_encrypted_manifest_and_reload_with_closed_projection(self):
        def reports(method,result):
            result['report']['scene_changes'] = [scene_change()]
            row = detail(raw='PRIVATE')
            row['cells'][0]['raw'] = 'PRIVATE'
            result['report']['scene_change_details'] = [row]
            return result
        with tempfile.TemporaryDirectory() as folder,NativeServer(finish=True,transform=reports) as server:
            record = self.execute(server,folder)
            self.assertTrue(record['resolved'])
            self.assertEqual([detail()],record['native_report']['scene_change_details'])
            self.assertEqual(record,native._load(Path(folder)))
            self.assertNotIn('PRIVATE',(Path(folder)/'active.json').read_text())

    def test_scene_change_detail_bounds_cell_order_and_alignment_are_strict(self):
        base = dict(schema='ngg2-native-v1',clock_id='a'*32,device_now_ns=1,input_state=0)
        maximum = detail(validation=11,continuous_count=8,chain_count=2,cell_count=4,omitted_cells=226,
            cells=[dict(x=x,y=-5,tile_before=0,tile_after=6,protected_before=1,protected_after=0)
                   for x in (-11,-10,-9,-8)])
        self.assertEqual([maximum]*3,native._report(dict(base,scene_change_details=[maximum]*3))['scene_change_details'])
        bad = [None,{},[detail()]*4,[detail(validation=True)],[detail(validation=12)],
               [detail(continuous_count=9)],[detail(chain_count=3)],[detail(cell_count=2)],
               [detail(omitted_cells=1)],[detail(cell_count=4,omitted_cells=227,cells=maximum['cells'])],
               [detail(cells=[dict(maximum['cells'][0],x=-12)])],
               [detail(cells=[dict(maximum['cells'][0],y=5)])],
               [detail(cells=[dict(maximum['cells'][0],tile_after=7)])],
               [detail(cells=[dict(maximum['cells'][0],protected_before=True)])],
               [detail(cells=[dict(maximum['cells'][0],tile_before=6,protected_before=0)])],
               [detail(cell_count=2,cells=[maximum['cells'][0],maximum['cells'][0]])],
               [detail(cell_count=2,cells=list(reversed(maximum['cells'][:2])))]]
        for key in detail():
            missing = detail()
            missing.pop(key)
            bad.append([missing])
        for value in bad:
            with self.subTest(value=value),self.assertRaisesRegex(ProbeError,'invalid_native_report'):
                native._report(dict(base,scene_change_details=value))
        with self.assertRaisesRegex(ProbeError,'invalid_native_report'):
            native._report(dict(base,scene_changes=[scene_change()],
                scene_change_details=[detail(command_id=3)]))

    def test_native_result_modes_and_chunk_arguments_are_validated_before_transport(self):
        with NativeServer() as server:
            client = self.client(server)
            base = dict(run_id='a'*32,mode='chunk',export_id='b'*32,capture_id=1,offset=0)
            bad = [dict(run_id='a'*32,mode='PRIVATE'),dict(run_id='a'*32,mode=[]),
                   dict(run_id='a'*32,mode='manifest',offset=0),
                   dict(base,offset=True),dict(base,offset=-1),dict(base,offset=native.MAX_IMAGE),
                   dict(base,capture_id=True),dict(base,export_id='PRIVATE')]
            for params in bad:
                with self.subTest(params=params),self.assertRaisesRegex(ProbeError,'method_not_allowed'):
                    client.call('necro_native_results',params)
            self.assertEqual([],server.calls)

