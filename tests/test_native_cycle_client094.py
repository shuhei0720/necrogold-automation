"""TEST094 native cycle client: identity, crash recovery and whole-session ZIP."""
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import zlib

from necroprobe import native_walk
from necroprobe import native_cycle as cycle
from necroprobe import cycle_publication as publication
from necroprobe.rpc_diagnostics import RemoteRpcError
from necroprobe.validation import ProbeError
from necroprobe.crypto import Crypto
from necroprobe.deadlines import OwnedRpcTimer
from necroprobe.protocol import HttpTransport
from test_protocol import KEY, TOK, sealed_reply

RUN = 'a'*32
EXPORT = 'b'*32


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def png(extra=0, color=6):
    def entry(kind, payload):
        return struct.pack('>I', len(payload))+kind+payload+struct.pack('>I', zlib.crc32(kind+payload)&0xffffffff)
    header = struct.pack('>IIBBBBB', 896, 414, 8, color, 0, 0, 0)
    pixels = b'\x00'+bytes([40, 20, 10, 255])*896
    raw = b'\x89PNG\r\n\x1a\n'+entry(b'IHDR', header)
    if extra:
        raw += entry(b'tEXt', b'note\x00'+b'x'*extra)
    return raw+entry(b'IDAT', zlib.compress(pixels*414))+entry(b'IEND', b'')


def companion():
    result = {key:0 for key in ('abi_version', 'completed_shops', 'level_id', 'job_id', 'capture_id',
        'capture_start_ns', 'prefix', 'deadline_ns', 'hold_started_ns', 'worker_started_ns',
        'assessment_ns', 'durable_ns', 'pause_source_capture_id', 'pause_capture_id',
        'restart_command_id', 'next_floor_capture_id', 'intent_ns', 'outcome_ns',
        'release_after_ns', 'continuation_deadline_ns', 'queued_capture_id',
        'queued_capture_start_ns', 'queued_prefix')}
    result.update(abi_version=1, state='done', outcome='negative', assessment_status='ok',
        coverage='complete', partial=False, pending=False, candidate_latched=False, full_seen=True)
    return result


class Server:
    def __init__(self, base=None, raw=None):
        self.base = base
        self.calls = []
        self.fail_start = False
        self.reject_start = False
        self.reject_shape = True
        self.fail_ack = False
        self.pending = {}
        self.ready = True
        self.unpublished = []
        self.authorization = 'authorized'
        self.status_queue = []
        self.run_id = RUN
        self.image = raw or png(180000)
        frame = cycle.canonical(dict(schema='ngg2-cycle-frame-v1', run_id=RUN, capture_id=7,
            raw_sha256='c'*64, raw_bytes=896*414*4, metadata={'capture_start_ns':100, 'completed_prefix':4}))
        header = cycle.canonical(dict(schema='ngg2-cycle-spool-v1', run_id=RUN, owner_sha256='d'*64))
        assessment = cycle.canonical(dict(schema='ngg2-cycle-record-v1', run_id=RUN, sequence=1,
            kind='assessment', cycle=1, previous=None, payload={'assessment':{'outcome':'negative'}}))
        self.records = {0:header, 1:assessment, 513:frame}
        self.manifest = dict(schema='ngg2-cycle-manifest-v1', run_id=RUN, profile=cycle.PROFILE,
            export_id=EXPORT, complete=True, interrupted=False, terminal=True, workers_drained=True,
            input_state=0, native_inflight=False, ui_frozen=False, images=[dict(name='capture-000007.png',
                capture_id=7, bytes=len(self.image), sha256=sha(self.image), raw_sha256='c'*64,
                width=896, height=414)], records=[dict(sequence=seq, kind=kind, cycle=1 if seq==1 else 0,
                    bytes=len(self.records[seq]), sha256=sha(self.records[seq]))
                    for seq,kind in ((0,'session'), (1,'assessment'), (513,'frame'))],
            diagnostics=[], total_bytes=len(self.image)+sum(map(len,self.records.values())), chunk_bytes=cycle.CHUNK_BYTES)

    def check_schema(self):
        self.calls.append(('schema', {}))
        return {}

    def wrap(self, mode, payload, run_id=None):
        return dict(schema=cycle.SCHEMA, run_id=run_id or self.run_id, profile=cycle.PROFILE,
                    mode=mode, payload=payload)

    def status(self, **changes):
        value = dict(state='completed', terminal=True, workers_drained=True, input_state=0,
            ui_frozen=False, native_inflight=False, cycle=companion(),
            notification={'authorization':'authorized', 'state':'not_requested'})
        value.update(changes)
        return value

    def call(self, method, params):
        self.calls.append((method, copy.deepcopy(params)))
        if method == 'necro_native_start':
            if self.base:
                current = cycle.load_journal(self.base)
                assert current['start_intent'] and current['run_id'] == params['run_id']
            if self.reject_start:
                raise RemoteRpcError(-32095, 'unclassified', self.reject_shape)
            self.run_id = params['run_id']
            self.manifest['run_id'] = self.run_id
            for seq, data in list(self.records.items()):
                body = json.loads(data); body['run_id'] = self.run_id
                self.records[seq] = cycle.canonical(body)
            for descriptor in self.manifest['records']:
                data = self.records[descriptor['sequence']]
                descriptor.update(bytes=len(data), sha256=sha(data))
            self.manifest['total_bytes'] = len(self.image)+sum(map(len,self.records.values()))
            if self.fail_start:
                raise ProbeError('connection_error')
            return dict(run_id=self.run_id, profile=cycle.PROFILE, state='accepted',
                        api_version=cycle.API_VERSION, report={})
        if method == 'necro_native_cancel':
            return dict(run_id=self.run_id, profile=cycle.PROFILE, state='stopped',
                        api_version=cycle.API_VERSION, report={})
        mode = params['mode']
        if self.pending.get(mode, 0):
            self.pending[mode] -= 1
            raise RemoteRpcError(-32094, 'unclassified', True)
        if mode == 'prepare':
            return self.wrap(mode, dict(ready=self.ready, notification_authorization=self.authorization,
                recovery_scan='ready', unpublished_run_ids=self.unpublished, reason='none'), params['run_id'])
        if mode == 'status':
            return self.wrap(mode, self.status_queue.pop(0) if self.status_queue else self.status())
        if mode == 'manifest':
            raw = cycle.canonical(self.manifest)
            return self.wrap(mode, dict(export_id=EXPORT, manifest_sha256=sha(raw), manifest_json=raw.decode()))
        if mode in ('record', 'chunk', 'batch'):
            is_record = mode == 'record'
            selector = 'sequence' if is_record else 'capture_id'
            data = self.records[params[selector]] if is_record else self.image
            offset = params['offset']
            parts = []
            for _ in range(params.get('count', 1)):
                raw = data[offset:offset+cycle.CHUNK_BYTES]
                parts.append(dict(export_id=EXPORT, **{selector:params[selector]}, offset=offset,
                    total_bytes=len(data), sha256=sha(data), data_base64=base64.b64encode(raw).decode(),
                    next_offset=offset+len(raw), eof=offset+len(raw)==len(data)))
                offset += len(raw)
                if offset == len(data):
                    break
            return self.wrap(mode, {'export_id':EXPORT, 'chunks':parts} if mode == 'batch' else parts[0])
        if mode == 'published':
            assert self.base is not None
            active = cycle.load_journal(self.base)
            assert active['resolved'] and active['archive_sha256'] == params['archive_sha256']
            if self.fail_ack:
                raise ProbeError('connection_error')
            return self.wrap(mode, dict(accepted=True, export_id=EXPORT,
                manifest_sha256=params['manifest_sha256'], archive_sha256=params['archive_sha256'],
                receipt_sha256='f'*64))
        raise AssertionError(mode)


class CycleClient094Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = self.root/'local'/'test-094'
        self.base.mkdir(parents=True)
        self.destination = self.root/'mounted'
        self.destination.mkdir()
        self.server = Server(self.base)
        self.notices = []

    def seed(self):
        record = cycle.fresh_record(RUN)
        record['start_intent'] = True
        cycle._journal(self.base, record)
        return record

    def collect(self, record=None):
        record = record or self.seed()
        cycle.collect(self.server, self.base, record, notice=self.notices.append)
        return record

    def invoke(self):
        with patch('necroprobe.native_cycle.device_lock', lambda: native_walk.device_lock(self.root/'device.lock')):
            return publication.run(self.server, self.destination, spool=self.base, notice=self.notices.append)

    def test_new_profile_has_an_explicit_admitted_client_not_old_profile_fallback(self):
        if importlib.util.find_spec('necroprobe.native_cycle') is None:
            client_type = native_walk.NativeClient
        else:
            client_type = cycle.CycleClient
        client = client_type(lambda *_: None)
        accepted = True
        try:
            client._validate('necro_native_start', {'run_id':RUN, 'profile':cycle.PROFILE})
        except ProbeError:
            accepted = False
        self.assertTrue(accepted, 'the explicitly requested native cycle profile must be admitted')

    def test_notification_preflight_failure_can_start_on_next_explicit_invocation(self):
        self.server.ready = False
        self.server.authorization = 'denied'
        first, archive = self.invoke()
        self.assertFalse(first['start_intent'])
        self.assertIsNone(archive)
        self.server.ready = True
        self.server.authorization = 'authorized'
        second, archive = self.invoke()
        self.assertTrue(second['published'])
        self.assertEqual(first['run_id'], second['run_id'])
        self.assertEqual(1, sum(method == 'necro_native_start' for method, _ in self.server.calls))

    def test_authenticated_definitive_not_started_is_distinct_from_unknown_start(self):
        self.server.reject_start = True
        first, archive = self.invoke()
        self.assertFalse(first['start_intent'])
        self.assertIsNone(archive)
        self.assertFalse(any(method == 'necro_native_cancel' for method, _ in self.server.calls))
        self.server.reject_start = False
        second, archive = self.invoke()
        self.assertTrue(second['published'])
        self.assertEqual(first['run_id'], second['run_id'])
        # Two explicit invocations; the first was authenticated as unstarted.
        self.assertEqual(2, sum(method == 'necro_native_start' for method, _ in self.server.calls))

    def test_malformed_not_started_error_cannot_clear_uncertain_input_intent(self):
        self.server.reject_start = True
        self.server.reject_shape = False
        record, archive = self.invoke()
        self.assertTrue(record['start_intent'])
        self.assertEqual('unknown', record['state'])
        self.assertIsNone(archive)
        self.assertEqual(1, sum(method == 'necro_native_start' for method, _ in self.server.calls))

    def test_late_terminal_assessment_is_reported_as_unadopted_not_unexecuted_or_negative(self):
        from necroprobe import test094 as entry
        folder = self.base/('cycle-'+RUN)/'records'
        folder.mkdir(parents=True)
        terminal = dict(sequence=2, kind='terminal', cycle=1)
        body = {'payload': {'assessment': {'outcome':'negative', 'status':'ok'},
                'assessment_adopted':False, 'cycle':{'level_id':1, 'job_id':1, 'capture_id':7}}}
        (folder/cycle.record_name(terminal)).write_bytes(cycle.canonical(body))
        record = {'run_id':RUN, 'records':[terminal]}
        self.assertEqual([(1,'negative','not_adopted')], entry._assessments(self.base, record))
        checkpoint = dict(sequence=1, kind='checkpoint', cycle=1)
        body['payload']['assessment_adopted'] = True
        for item in (checkpoint, terminal):
            (folder/cycle.record_name(item)).write_bytes(cycle.canonical(body))
        record['records'] = [checkpoint, terminal]
        self.assertEqual([(1,'negative','ok')], entry._assessments(self.base, record),
                         'the same adopted shop must not be counted twice')

    def test_started_unknown_frozen_terminal_remains_exportable_without_new_input(self):
        self.server.status_queue = [self.server.status(state='stopped', input_state=4, ui_frozen=True)]
        self.server.manifest.update(input_state=4, ui_frozen=True)
        record = self.invoke()[0]
        self.assertTrue(record['published'])
        self.assertEqual(1, sum(method == 'necro_native_start' for method, _ in self.server.calls))
        stored = json.loads((self.base/('cycle-'+record['run_id'])/'native-manifest.json').read_bytes())
        self.assertEqual((4, True), (stored['input_state'], stored['ui_frozen']))

    def test_durable_per_run_journal_survives_interruption_before_active_mirror(self):
        record = self.seed()
        record.update(state='unknown', last_error='cycle_start_uncertain')
        atomic = cycle._atomic
        def interrupted(path, raw):
            if Path(path).name == 'active-cycle.json':
                raise OSError('injected crash boundary')
            atomic(path, raw)
        with patch.object(cycle, '_atomic', interrupted), self.assertRaises(OSError):
            cycle._journal(self.base, record)
        try:
            loaded = cycle.load_journal(self.base)
        except ProbeError:
            loaded = None
        self.assertEqual(record, loaded)

    def test_return_zip_deflates_stored_recovery_png_and_preserves_all_bytes(self):
        record = self.collect()
        storage = self.root/'archives'
        storage.mkdir()
        archive = publication.build_archive(self.base, record, storage)
        with zipfile.ZipFile(archive) as value:
            self.assertTrue(all(item.compress_type == zipfile.ZIP_DEFLATED for item in value.infolist()))
            name = next(name for name in value.namelist() if name.endswith('.png'))
            self.assertEqual(self.server.image, value.read(name))

    def test_method_admission_rejects_oldprofile_unknownfields_and_arbitrary_input(self):
        client = cycle.CycleClient(lambda *_: None)
        for method, params in (('tap', {'run_id':RUN}),
            ('necro_native_start', {'run_id':RUN, 'profile':native_walk.PROFILE}),
            ('necro_native_cycle', {'run_id':RUN, 'mode':'status', 'keepalive':True, 'extra':0}),
            ('necro_native_cycle', {'run_id':RUN, 'mode':'batch', 'export_id':EXPORT,
                'capture_id':7, 'offset':0, 'count':5})):
            with self.subTest(method=method, params=params), self.assertRaises(ProbeError):
                client._validate(method, params)

    def test_envelope_requires_exact_schema_mode_profile_and_run(self):
        good = self.server.wrap('manifest', {})
        for key, value in (('run_id','e'*32), ('profile',native_walk.PROFILE), ('schema','ngg2-cycle-v2'),
                           ('mode','status'), ('unexpected',0)):
            bad = dict(good, **{key:value})
            with self.subTest(key=key), self.assertRaises(ProbeError):
                cycle.envelope(bad, RUN, 'manifest')

    def test_manifest_hash_is_of_exact_utf8_not_python_reserialization(self):
        response = self.server.call('necro_native_cycle', {'mode':'manifest'})
        native = response['payload']['manifest_json'].replace('"diagnostics":[]', '"diagnostics":["保存"]')
        response['payload'].update(manifest_json=native, manifest_sha256=sha(native.encode()))
        parsed, raw, digest = cycle.read_manifest(response, RUN)
        self.assertEqual(native.encode(), raw)
        self.assertEqual(['保存'], parsed['diagnostics'])
        response['payload']['manifest_json'] += ' '
        with self.assertRaises(ProbeError):
            cycle.read_manifest(response, RUN)

    def test_real_encrypted_pending_reply_is_polled_but_bad_mac_is_not(self):
        calls = []
        def transport(body, timeout):
            calls.append(1)
            if len(calls) == 1:
                return sealed_reply(body, result={'code':-32094, 'message':'pending'}, rpc_error=True)
            return sealed_reply(body, result=self.server.wrap('status', self.server.status()))
        with OwnedRpcTimer() as timer:
            client = cycle.CycleClient(transport, KEY, TOK, crypto=Crypto(native=False), deadline_owner=timer)
            result = cycle._call(client, 'necro_native_cycle', {'run_id':RUN,'mode':'status','keepalive':False},
                sleep=lambda _:None)
            self.assertTrue(cycle.status(result, RUN)['terminal'])
            self.assertEqual(2, len(calls))
            def bad(body, timeout):
                calls.append(1)
                return sealed_reply(body, result={'code':-32094,'message':'pending'}, rpc_error=True, corrupt_mac=True)
            client.transport = bad
            with self.assertRaisesRegex(ProbeError, 'response_mac_mismatch'):
                cycle._call(client, 'necro_native_cycle', {'run_id':RUN,'mode':'status','keepalive':False})
            self.assertEqual(3, len(calls))
            def unavailable(body, timeout):
                calls.append(1)
                return sealed_reply(body, result={'code':-32096, 'message':'evidence unavailable'}, rpc_error=True)
            client.transport = unavailable
            with self.assertRaisesRegex(ProbeError, 'cycle_evidence_storage_unavailable'):
                cycle._call(client, 'necro_native_cycle', {'run_id':RUN,'mode':'manifest'}, sleep=lambda _:None)
            self.assertEqual(4, len(calls), 'permanent evidence error is never automatically polled')

    def test_start_admission_guard_runs_after_crypto_before_transport(self):
        calls = []
        with OwnedRpcTimer() as timer:
            client = cycle.CycleClient(lambda *args:calls.append(args), KEY, TOK,
                crypto=Crypto(native=False), deadline_owner=timer)
            def cancelled():
                raise cycle._StartNotSent('cancel_requested')
            client._before_start_post = cancelled
            with self.assertRaises(cycle._StartNotSent):
                client.call('necro_native_start', {'run_id':RUN,'profile':cycle.PROFILE})
        self.assertEqual([], calls)

    def test_schema_requires_current_api_new_capability_and_integer_protocol(self):
        class Transport(HttpTransport):
            def schema(self, _timeout):
                return cycle.canonical(self.metadata)
        transport = Transport()
        with OwnedRpcTimer() as timer:
            client = cycle.CycleClient(transport, KEY, TOK, deadline_owner=timer)
            for fault in ('missing', 'bool', 'old_api'):
                transport.metadata = {'server_version':cycle.API_VERSION, 'protocol_version':1,
                    'capability_tags':[cycle.CAPABILITY]}
                if fault == 'missing': transport.metadata['capability_tags'] = [native_walk.CAPABILITY]
                if fault == 'bool': transport.metadata['protocol_version'] = True
                if fault == 'old_api': transport.metadata['server_version'] = '1.98.14-ngg2'
                with self.subTest(fault=fault), self.assertRaises(ProbeError):
                    client.check_schema()
            transport.metadata = {'server_version':cycle.API_VERSION, 'protocol_version':1,
                'capability_tags':[native_walk.CAPABILITY, cycle.CAPABILITY]}
            self.assertEqual(cycle.CAPABILITY, client.check_schema()['capability'])

    def test_manifest_registry_rejects_extra_fields_duplicate_ids_and_bool_lengths(self):
        for fault in ('extra', 'duplicate', 'bool', 'total', 'geometry'):
            original = copy.deepcopy(self.server.manifest)
            if fault == 'extra': self.server.manifest['surprise'] = 0
            if fault == 'duplicate': self.server.manifest['images'] *= 2
            if fault == 'bool': self.server.manifest['images'][0]['bytes'] = True
            if fault == 'total': self.server.manifest['total_bytes'] += 1
            if fault == 'geometry': self.server.manifest['images'][0]['width'] = 895
            with self.subTest(fault=fault), self.assertRaises(ProbeError):
                cycle.read_manifest(self.server.call('necro_native_cycle', {'mode':'manifest'}), RUN)
            self.server.manifest = original

    def test_collection_recovers_all_records_and_batched_png_without_pixel_classifier(self):
        record = self.collect()
        self.assertTrue(record['resolved'])
        self.assertEqual(self.server.manifest, cycle.verify_evidence(self.base, record))
        calls = [params for method,params in self.server.calls if method=='necro_native_cycle']
        self.assertEqual(1, len([p for p in calls if p['mode']=='batch']))
        self.assertEqual(3, len([p for p in calls if p['mode']=='record']))
        self.assertEqual(self.server.image, (self.base/('cycle-'+RUN)/'images'/'capture-000007.png').read_bytes())

    def test_missing_frame_metadata_never_resolves_or_publishes(self):
        self.server.manifest['records'] = [r for r in self.server.manifest['records'] if r['kind']!='frame']
        self.server.manifest['total_bytes'] -= len(self.server.records[513])
        record = self.seed()
        with self.assertRaisesRegex(ProbeError, 'cycle_frame_metadata_missing'):
            self.collect(record)
        self.assertFalse(record['resolved'])
        self.assertFalse(any(p.get('mode')=='published' for _,p in self.server.calls))

    def test_png_all_chunks_crc_and_rgba_geometry_are_verified(self):
        good = png()
        cycle.verify_png(good)
        cycle.verify_png(png(color=2))
        for color in (0,3,4):
            with self.subTest(color=color), self.assertRaises(ProbeError):
                cycle.verify_png(png(color=color))
        bad = bytearray(good); bad[-5] ^= 1
        with self.assertRaisesRegex(ProbeError, 'cycle_png_crc'):
            cycle.verify_png(bytes(bad))
        with self.assertRaises(ProbeError):
            cycle.verify_png(good[:-1])

    def test_same_offset_retry_preserves_and_compares_uncheckpointed_suffix(self):
        record = self.seed()
        cycle.collect(self.server, self.base, record, notice=self.notices.append)
        image = record['images'][0]
        image.update(offset=0, prefix_sha256=sha(b''))
        record['resolved'] = False
        cycle._journal(self.base, record)
        path = self.base/('cycle-'+RUN)/'images'/'.parts'/(image['name']+'.part')
        path.write_bytes(self.server.image)
        self.server.image = self.server.image[:70000]+b'bad'+self.server.image[70003:]
        with self.assertRaises(ProbeError):
            cycle.collect(self.server, self.base, record, notice=self.notices.append)
        self.assertEqual(self.server.manifest['images'][0]['sha256'], sha(path.read_bytes()))
        self.assertEqual(0, record['images'][0]['offset'])

    def test_uncertain_start_is_sent_once_and_next_invocation_only_recovers_same_id(self):
        self.server.fail_start = True
        first = cycle.run_session(self.server, self.base, notice=self.notices.append)
        self.assertTrue(first['start_intent'])
        self.assertFalse(first['resolved'])
        run_id = first['run_id']
        self.server.manifest['run_id'] = run_id
        for seq,data in list(self.server.records.items()):
            body = json.loads(data); body['run_id'] = run_id
            self.server.records[seq] = cycle.canonical(body)
        for descriptor in self.server.manifest['records']:
            data = self.server.records[descriptor['sequence']]
            descriptor.update(bytes=len(data), sha256=sha(data))
        self.server.manifest['total_bytes'] = len(self.server.image)+sum(map(len,self.server.records.values()))
        second = cycle.run_session(self.server, self.base, notice=self.notices.append)
        self.assertEqual(run_id, second['run_id'])
        self.assertTrue(second['resolved'])
        self.assertEqual(1, sum(method=='necro_native_start' for method,_ in self.server.calls))
        statuses = [p for _,p in self.server.calls if p.get('mode')=='status']
        self.assertTrue(statuses and all(not p['keepalive'] for p in statuses))

    def test_cancel_after_durable_start_intent_never_posts_start(self):
        stopped = [False]
        original = cycle._journal
        def saved(base, record):
            original(base, record)
            if record['start_intent']:
                stopped[0] = True
        with patch.object(cycle, '_journal', saved):
            result = cycle.run_session(self.server, self.base,
                cancelled=lambda:stopped[0], notice=self.notices.append)
        self.assertFalse(any(m=='necro_native_start' for m,_ in self.server.calls),
            'cancellation after fsync must be checked again before start POST')
        self.assertFalse(result['start_intent'])

    def test_permission_denied_never_sends_start(self):
        self.server.ready = False; self.server.authorization = 'denied'
        record = cycle.run_session(self.server, self.base, notice=self.notices.append)
        self.assertFalse(record['start_intent'])
        self.assertEqual('cycle_notification_permission', record['last_error'])
        self.assertFalse(any(m=='necro_native_start' for m,_ in self.server.calls))

    def test_native_unpublished_id_is_recovered_without_new_start(self):
        self.server.ready = False; self.server.unpublished = [RUN]
        record = cycle.run_session(self.server, self.base, notice=self.notices.append)
        self.assertEqual(RUN, record['run_id'])
        self.assertTrue(record['resolved'])
        self.assertFalse(any(m=='necro_native_start' for m,_ in self.server.calls))

    def test_gameworker_drain_is_required_before_manifest(self):
        self.seed()
        self.server.status_queue = [self.server.status(workers_drained=False, native_inflight=True), self.server.status()]
        result = cycle.run_session(self.server, self.base, sleep=lambda _:None, notice=self.notices.append)
        self.assertTrue(result['resolved'])
        modes = [p.get('mode') for _,p in self.server.calls]
        self.assertEqual(['status','status','manifest'], modes[:3])

    def test_only_authenticated_dedicated_pending_code_is_automatically_polled(self):
        self.server.pending['manifest'] = 2
        cycle._call(self.server, 'necro_native_cycle', {'run_id':RUN,'mode':'manifest'}, sleep=lambda _:None)
        self.assertEqual(3, len(self.server.calls))
        self.server.pending['status'] = 1
        with self.assertRaises(ProbeError):
            cycle._call(
                type('Bad', (), {'call':lambda *_: (_ for _ in ()).throw(RemoteRpcError(-32000,'unclassified',True))})(),
                'necro_native_cycle', {'run_id':RUN,'mode':'manifest'}, sleep=lambda _:None)

    def test_fresh_session_starts_once_after_ready_and_keeps_heartbeat_before_terminal(self):
        record, archive = self.invoke()
        self.assertTrue(record['published'])
        self.assertTrue(archive.exists())
        starts = [params for method,params in self.server.calls if method=='necro_native_start']
        self.assertEqual(1, len(starts))
        self.assertEqual(record['run_id'], starts[0]['run_id'])
        self.assertEqual(cycle.PROFILE, starts[0]['profile'])
        self.assertTrue(next(params['keepalive'] for _,params in self.server.calls if params.get('mode')=='status'))
        self.assertFalse(any(method in ('necro_native_results','screenshot','tap') for method,_ in self.server.calls))

    def test_later_explicit_invocation_starts_new_id_only_after_prior_receipt_and_zip_verify(self):
        first, archive = self.invoke()
        first_bytes = archive.read_bytes()
        second, second_archive = self.invoke()
        self.assertNotEqual(first['run_id'], second['run_id'])
        self.assertNotEqual(archive, second_archive)
        self.assertEqual(first_bytes, archive.read_bytes())
        self.assertEqual(2, sum(method=='necro_native_start' for method,_ in self.server.calls))
        with zipfile.ZipFile(second_archive) as result:
            self.assertFalse(any(first['run_id'] in name for name in result.namelist()))

    def test_published_ack_occurs_only_after_full_crc_sha_zip_and_destination_copy(self):
        self.seed()
        record, archive = self.invoke()
        self.assertTrue(record['published'])
        self.assertTrue(archive.is_file())
        with zipfile.ZipFile(archive) as result:
            self.assertIsNone(result.testzip())
            self.assertEqual(6, len(result.namelist()))
            self.assertEqual(self.server.image, result.read('test-094/cycle-'+RUN+'/images/capture-000007.png'))
        self.assertEqual('published', self.server.calls[-1][1]['mode'])

    def test_ack_failure_retains_same_archive_and_retries_no_game_start(self):
        self.seed(); self.server.fail_ack = True
        with self.assertRaises(ProbeError):
            self.invoke()
        record = cycle.load_journal(self.base)
        self.assertTrue(record['resolved']); self.assertFalse(record['published'])
        archive = self.destination/'runtime'/('test-094-'+RUN+'.zip')
        before = archive.read_bytes()
        self.server.fail_ack = False
        completed, returned = self.invoke()
        self.assertEqual(before, returned.read_bytes())
        self.assertTrue(completed['published'])
        self.assertFalse(any(m=='necro_native_start' for m,_ in self.server.calls))

    def test_changed_completed_archive_blocks_ack_and_preserves_destination(self):
        record = self.collect()
        storage = self.base.parent/('.'+self.base.name+'-publication')
        storage.mkdir()
        archive = publication.build_archive(self.base, record, storage)
        archive.write_bytes(b'corrupt ZIP')
        with self.assertRaises((ProbeError, zipfile.BadZipFile)):
            publication.publish(self.server, self.base, self.destination, record, notice=self.notices.append)
        self.assertFalse(any(p.get('mode')=='published' for _,p in self.server.calls))
        self.assertFalse((self.destination/'runtime'/('test-094-'+RUN+'.zip')).exists())

    def test_native_pending_deadline_and_cancellation_do_not_reissue_after_expiry(self):
        for cancelled in (True, False):
            server = Server()
            server.pending['manifest'] = 100
            with self.subTest(cancelled=cancelled), self.assertRaises(ProbeError):
                cycle._call(server, 'necro_native_cycle', {'run_id':RUN, 'mode':'manifest'},
                    clock=lambda:10, deadline=10, cancelled=lambda:cancelled, sleep=lambda _:None)
            self.assertEqual(1, len(server.calls))

    def test_changed_png_blocks_ack(self):
        record = self.collect()
        image = self.base/('cycle-'+RUN)/'images'/'capture-000007.png'
        image.write_bytes(b'corrupt')
        with self.assertRaises(ProbeError):
            publication.publish(self.server, self.base, self.destination, record, notice=self.notices.append)
        self.assertFalse(any(p.get('mode')=='published' for _,p in self.server.calls))

    def test_missing_header_is_publishable_only_as_explicit_interrupted_diagnostic(self):
        self.seed()
        omitted = self.server.records[0]
        self.server.manifest['records'] = [item for item in self.server.manifest['records'] if item['sequence'] != 0]
        self.server.manifest['total_bytes'] -= len(omitted)
        self.server.manifest.update(complete=False, interrupted=True,
            diagnostics=[{'code':'session_header_uncommitted', 'authority':False}])
        record, archive = self.invoke()
        self.assertTrue(record['published'])
        self.assertTrue(archive.is_file())
        self.assertEqual('stopped', record['state'])

    def test_interrupted_diagnostic_is_saved_but_never_claimed_normal_completion(self):
        self.seed()
        self.server.manifest.update(complete=False, interrupted=True, diagnostics=['interrupted'])
        record, archive = self.invoke()
        self.assertTrue(record['published'])
        self.assertEqual('stopped', record['state'])
        with zipfile.ZipFile(archive) as result:
            manifest = json.loads(result.read('test-094/cycle-'+RUN+'/native-manifest.json'))
        self.assertFalse(manifest['complete']); self.assertTrue(manifest['interrupted'])
        self.assertFalse(any(m=='necro_native_start' for m,_ in self.server.calls))


if __name__ == '__main__':
    unittest.main()
