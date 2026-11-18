"""TEST094 native-only goods cycle transport and durable client journal.

This module never inspects pixels and never sends game taps.  An uncertain
start is recovered under the same UUID; it is never automatically retried.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import time
import uuid
import zlib
from typing import NamedTuple

from .native_walk import _atomic, device_lock
from . import campaign_diagnostics114 as diagnostics
from .protocol import Client, HttpTransport
from .rpc_diagnostics import RemoteRpcError
from .validation import ProbeError, b64, json_object, number

REVISION = 'native-cycle-v1'
API_VERSION = '1.98.16-ngg2'
CAPABILITY = 'necrogold_native_cycle_v1'
PROFILE = 'normal-1-1-cycle-v1'
SCHEMA = 'ngg2-cycle-v1'
MAX_WIRE = 512 * 1024
MAX_SINGLE_WIRE = 256 * 1024
# Bulk replies include escaped inner base64 plus the sealed ciphertext's
# base64. Four 64KiB chunks can exceed 512KiB on the HTTP wire; the native
# chunk/manifest bounds fit 1MiB even with maximum slash escaping.
MAX_BULK_WIRE = 1024 * 1024
CHUNK_BYTES = 64 * 1024
MAX_IMAGE = 2 * 1024 * 1024
MAX_IMAGES = 44
MAX_TOTAL = 88 * 1024 * 1024
MAX_MANIFEST = 384 * 1024
MAX_RECORD = 2 * 1024 * 1024
MAX_RECORD_TOTAL = 4 * 1024 * 1024
UUID = re.compile(r'[0-9a-f]{32}\Z')
SHA = re.compile(r'[0-9a-f]{64}\Z')
STATES = frozenset(('accepted', 'running', 'completed', 'stopped', 'draining'))
TERMINAL = frozenset(('completed', 'stopped'))


class CycleProtocolSpec(NamedTuple):
    revision: str
    profile: str
    schema: str
    capability: str
    query: str
    irregular: bool


STANDARD_PROTOCOL = CycleProtocolSpec(REVISION, PROFILE, SCHEMA, CAPABILITY,
    'necro_native_cycle', False)
IRREGULAR_PROTOCOL = CycleProtocolSpec('native-irregular-v1',
    'normal-1-1-irregular-v1', 'ngg2-irregular-cycle-v1',
    'necrogold_native_irregular_v1', 'necro_native_irregular', True)


def _spec(value):
    require(value is STANDARD_PROTOCOL or value is IRREGULAR_PROTOCOL, 'cycle_protocol_invalid')
    return value


def client_protocol(client):
    return _spec(getattr(client, 'protocol_spec', STANDARD_PROTOCOL))


def restart_yield_enabled(client):
    enabled = getattr(client, 'yield_after_restart', False)
    require(type(enabled) is bool and (not enabled or client_protocol(client) is IRREGULAR_PROTOCOL),
            'cycle_protocol_invalid')
    return enabled


def initial_restart_enabled(client):
    enabled = getattr(client, 'initial_restart', False)
    require(type(enabled) is bool and (not enabled or client_protocol(client) is IRREGULAR_PROTOCOL),
            'cycle_protocol_invalid')
    return enabled


def require(value, reason='invalid_cycle_response'):
    if not value:
        raise ProbeError(reason)


def closed(value, keys, reason='invalid_cycle_response'):
    require(type(value) is dict and set(value) == set(keys), reason)
    return value


def identifier(value):
    return type(value) is str and UUID.fullmatch(value) is not None


def digest(value):
    return type(value) is str and SHA.fullmatch(value) is not None


def ns(value):
    return type(value) is int and 0 <= value < 2**63


def canonical(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False,
                      sort_keys=True, separators=(',', ':')).encode('utf-8')


class _StartNotSent(ProbeError):
    pass


class CycleClient(Client):
    protocol_spec = STANDARD_PROTOCOL
    required_capabilities = frozenset()
    yield_after_restart = False
    initial_restart = False

    def _validate(self, method, params):
        protocol = _spec(self.protocol_spec)
        require(type(params) is dict and identifier(params.get('run_id')), 'method_not_allowed')
        if method == 'necro_native_start':
            enabled = restart_yield_enabled(self)
            initial = initial_restart_enabled(self)
            closed(params, ('run_id', 'profile') + (('yield_after_restart',) if enabled else ())
                   + (('initial_restart',) if initial else ()), 'method_not_allowed')
            require(params['profile'] == protocol.profile
                    and (not enabled or params['yield_after_restart'] is True)
                    and (not initial or params['initial_restart'] is True), 'method_not_allowed')
            return
        if method == 'necro_native_cancel':
            closed(params, ('run_id',), 'method_not_allowed')
            return
        require(method == protocol.query, 'method_not_allowed')
        mode = params.get('mode', 'status')
        keys = {'run_id', 'mode'}
        if mode == 'prepare':
            keys.add('request_authorization')
            require(type(params.get('request_authorization')) is bool, 'method_not_allowed')
        elif mode == 'status':
            keys.add('keepalive')
            require(type(params.get('keepalive')) is bool, 'method_not_allowed')
        elif mode in ('chunk', 'batch', 'record'):
            keys |= {'export_id', 'offset', 'sequence' if mode == 'record' else 'capture_id'}
            if mode == 'batch':
                keys.add('count')
                require(type(params.get('count')) is int and 1 <= params['count'] <= 4, 'method_not_allowed')
            selector = params.get('sequence' if mode == 'record' else 'capture_id')
            require(identifier(params.get('export_id')) and ns(selector)
                    and (0 <= selector <= 557 if mode == 'record' else selector > 0) and type(params.get('offset')) is int
                    and 0 <= params['offset'] < MAX_IMAGE, 'method_not_allowed')
        elif mode == 'published':
            keys |= {'export_id', 'manifest_sha256', 'archive_sha256'}
            require(identifier(params.get('export_id')) and digest(params.get('manifest_sha256'))
                    and digest(params.get('archive_sha256')), 'method_not_allowed')
        else:
            require(mode == 'manifest', 'method_not_allowed')
        closed(params, keys, 'method_not_allowed')

    def call(self, method, params=None, *, timeout=None):
        mode = params.get('mode') if type(params) is dict else None
        ceiling = min(self.timeout, 8 if mode in ('manifest', 'chunk', 'batch', 'record', 'published') else 2)
        timeout = ceiling if timeout is None else number(timeout, .001, ceiling)
        maximum = (MAX_BULK_WIRE if mode in ('batch', 'manifest') else
                   MAX_SINGLE_WIRE if mode in ('chunk', 'record') else MAX_WIRE)
        transport = self.transport
        def bounded(body, seconds):
            guard = getattr(self, '_before_start_post', None)
            if method == 'necro_native_start' and guard is not None:
                guard()
            if isinstance(transport, HttpTransport):
                return transport._exchange('POST', '/rpc', body, seconds, maximum)
            raw = transport(body, seconds)
            require(type(raw) is bytes and len(raw) <= maximum, 'http_body_limit')
            return raw
        self.transport = bounded
        try:
            return super().call(method, params, timeout=timeout)
        finally:
            self.transport = transport

    def check_schema(self):
        require(isinstance(self.transport, HttpTransport), 'cycle_schema_unavailable')
        require(self.deadline_owner is not None, 'timer_owner_required')
        with self.deadline_owner.deadline(min(2, self.timeout)):
            value = json_object(self.transport.schema(min(2, self.timeout)), MAX_WIRE)
        require(value.get('server_version') == API_VERSION,
                'native_capability_missing')
        capabilities = value.get('capability_tags')
        require(type(capabilities) is list and len(capabilities) <= 256
                and all(type(item) is str and len(item) <= 128 for item in capabilities)
                and CAPABILITY in capabilities and _spec(self.protocol_spec).capability in capabilities
                and self.required_capabilities <= set(capabilities)
                and type(value.get('protocol_version')) is int
                and value['protocol_version'] == 1, 'native_capability_missing')
        return {'api_version': API_VERSION, 'capability': _spec(self.protocol_spec).capability}


class IrregularCycleClient(CycleClient):
    protocol_spec = IRREGULAR_PROTOCOL


def envelope(value, run_id, mode, *, protocol_spec=STANDARD_PROTOCOL):
    protocol = _spec(protocol_spec)
    closed(value, ('schema', 'run_id', 'profile', 'mode', 'payload'))
    require(value['schema'] == protocol.schema and value['run_id'] == run_id
            and value['profile'] == protocol.profile and value['mode'] == mode
            and type(value['payload']) is dict)
    return value['payload']


def prepare(value, run_id, *, protocol_spec=STANDARD_PROTOCOL):
    result = closed(envelope(value, run_id, 'prepare', protocol_spec=protocol_spec), ('ready', 'notification_authorization',
                    'recovery_scan', 'unpublished_run_ids', 'reason'))
    require(type(result['ready']) is bool and result['notification_authorization'] in
            ('pending', 'not_determined', 'authorized', 'provisional', 'denied', 'unavailable')
            and result['recovery_scan'] in ('pending', 'ready', 'failed')
            and type(result['unpublished_run_ids']) is list
            and len(result['unpublished_run_ids']) <= 128
            and all(identifier(item) for item in result['unpublished_run_ids'])
            and len(set(result['unpublished_run_ids'])) == len(result['unpublished_run_ids'])
            and type(result['reason']) is str and len(result['reason']) <= 64
            and re.fullmatch('[a-z_0-9]*', result['reason']) is not None)
    if result['ready']:
        require(result['recovery_scan'] == 'ready' and not result['unpublished_run_ids']
                and result['notification_authorization'] in ('authorized', 'provisional'))
    return result


def start_reply(value, run_id, *, protocol_spec=STANDARD_PROTOCOL, yield_after_restart=False, initial_restart=False):
    protocol = _spec(protocol_spec)
    require(type(yield_after_restart) is bool and (not yield_after_restart or protocol is IRREGULAR_PROTOCOL))
    require(type(initial_restart) is bool and (not initial_restart or protocol is IRREGULAR_PROTOCOL))
    closed(value, ('run_id', 'profile', 'state', 'api_version', 'report')
           + (('yield_after_restart',) if yield_after_restart else ())
           + (('initial_restart',) if initial_restart else ()))
    require(not yield_after_restart or value['yield_after_restart'] is True)
    require(not initial_restart or value['initial_restart'] is True)
    require(value['run_id'] == run_id and value['profile'] == protocol.profile
            and value['api_version'] == API_VERSION and value['state'] in STATES
            and type(value['report']) is dict)
    return value['state']


def _bounded_tree(value, *, depth=0):
    """Validate opaque immutable evidence without interpreting it as authority."""
    require(depth <= 12)
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        require(-(2**63) < value < 2**63)
    elif type(value) is float:
        number(value, -1e30, 1e30)
    elif type(value) is str:
        require(len(value.encode('utf-8')) <= 4096 and '\x00' not in value)
    elif type(value) is list:
        require(len(value) <= 1024)
        for item in value:
            _bounded_tree(item, depth=depth+1)
    else:
        require(type(value) is dict and len(value) <= 192)
        for key, item in value.items():
            require(type(key) is str and len(key) <= 96 and '\x00' not in key)
            _bounded_tree(item, depth=depth+1)


def status(value, run_id, *, protocol_spec=STANDARD_PROTOCOL):
    protocol = _spec(protocol_spec)
    keys = ('state', 'terminal', 'workers_drained', 'input_state', 'ui_frozen', 'native_inflight', 'cycle', 'notification')
    result = closed(envelope(value, run_id, 'status', protocol_spec=protocol), keys + (('irregular',) if protocol.irregular else ()))
    if protocol.irregular:
        from .irregular import validate_status
        validate_status(result['irregular'])
    require(result['state'] in STATES and all(type(result[key]) is bool for key in
            ('terminal', 'workers_drained', 'ui_frozen', 'native_inflight'))
            and type(result['input_state']) is int and result['input_state'] in (0, 1, 2, 3, 4)
            and type(result['cycle']) is dict and type(result['notification']) is dict)
    cycle = result['cycle']
    text = {'state', 'outcome', 'assessment_status', 'coverage'}
    flags = {'partial', 'pending', 'candidate_latched', 'full_seen'}
    numeric = {'abi_version', 'completed_shops', 'level_id', 'job_id', 'capture_id',
        'capture_start_ns', 'prefix', 'deadline_ns', 'hold_started_ns', 'worker_started_ns',
        'assessment_ns', 'durable_ns', 'pause_source_capture_id', 'pause_capture_id',
        'restart_command_id', 'next_floor_capture_id', 'intent_ns', 'outcome_ns',
        'release_after_ns', 'continuation_deadline_ns', 'queued_capture_id',
        'queued_capture_start_ns', 'queued_prefix'}
    closed(cycle, text | flags | numeric)
    require(all(type(cycle[key]) is bool for key in flags)
            and all(ns(cycle[key]) for key in numeric) and cycle['abi_version'] == 1
            and cycle['completed_shops'] <= 4
            and cycle['state'] in ('search', 'hold', 'assess', 'observe_more',
                'negative_pause', 'negative_persist', 'negative_restart', 'held', 'done')
            and cycle['outcome'] in ('unknown', 'candidate', 'target', 'negative')
            and cycle['assessment_status'] in ('ok', 'cancelled', 'deadline', 'invalid', 'allocation', 'kernel')
            and cycle['coverage'] in ('unknown', 'incomplete', 'complete'))
    notification = closed(result['notification'], ('authorization', 'state'))
    require(notification['authorization'] in ('pending', 'not_determined', 'authorized',
                'provisional', 'denied', 'unavailable')
            and notification['state'] in ('not_requested', 'pending', 'requested', 'failed', 'unavailable'))
    # Native has finished gameplay before its capture, worker, and durable
    # storage leases return. This status permits waiting, not collection.
    if result['state'] == 'draining':
        require(result['terminal'] and not result['workers_drained'])
    else:
        require(not result['terminal'] or result['state'] in TERMINAL)
    return result


def read_manifest(value, run_id, *, protocol_spec=STANDARD_PROTOCOL):
    protocol = _spec(protocol_spec)
    result = closed(envelope(value, run_id, 'manifest', protocol_spec=protocol),
                    ('export_id', 'manifest_sha256', 'manifest_json'))
    require(identifier(result['export_id']) and digest(result['manifest_sha256'])
            and type(result['manifest_json']) is str)
    raw = result['manifest_json'].encode('utf-8')
    require(len(raw) <= MAX_MANIFEST and hashlib.sha256(raw).hexdigest() == result['manifest_sha256'],
            'cycle_manifest_hash')
    manifest = json_object(raw, MAX_MANIFEST)
    closed(manifest, ('schema', 'run_id', 'profile', 'export_id', 'complete', 'interrupted',
          'terminal', 'workers_drained', 'input_state', 'native_inflight', 'ui_frozen',
          'images', 'records', 'diagnostics', 'total_bytes', 'chunk_bytes'))
    require(manifest['schema'] == 'ngg2-cycle-manifest-v1' and manifest['run_id'] == run_id
            and manifest['profile'] == protocol.profile and manifest['export_id'] == result['export_id']
            and all(type(manifest[key]) is bool for key in ('complete', 'interrupted', 'terminal',
                'workers_drained', 'native_inflight', 'ui_frozen'))
            and manifest['terminal'] and manifest['workers_drained']
            and manifest['input_state'] in (0, 3, 4) and type(manifest['input_state']) is int
            and not manifest['native_inflight']
            and manifest['chunk_bytes'] == CHUNK_BYTES and type(manifest['chunk_bytes']) is int
            and type(manifest['images']) is list and len(manifest['images']) <= MAX_IMAGES
            and type(manifest['records']) is list and len(manifest['records']) <= 558
            and type(manifest['diagnostics']) is list and len(manifest['diagnostics']) <= 512)
    images = manifest['images']
    for item in images:
        closed(item, ('name', 'capture_id', 'bytes', 'sha256', 'raw_sha256', 'width', 'height'))
        require(ns(item['capture_id']) and item['capture_id'] > 0
                and item['name'] == 'capture-'+str(item['capture_id']).zfill(6)+'.png'
                and type(item['bytes']) is int and 0 < item['bytes'] <= MAX_IMAGE
                and digest(item['sha256']) and digest(item['raw_sha256'])
                and type(item['width']) is int and type(item['height']) is int
                and (item['width'], item['height']) == (896, 414))
    require(len({item['capture_id'] for item in images}) == len(images)
            and len({item['name'] for item in images}) == len(images)
            and type(manifest['total_bytes']) is int
            and manifest['total_bytes'] <= MAX_TOTAL + MAX_RECORD_TOTAL)
    for record in manifest['records']:
        closed(record, ('sequence', 'kind', 'cycle', 'bytes', 'sha256'))
        require(type(record['sequence']) is int and 0 <= record['sequence'] <= 557
                and type(record['kind']) is str and re.fullmatch('[a-z_-]{1,32}', record['kind'])
                and ns(record['cycle']) and type(record['bytes']) is int
                and 0 < record['bytes'] <= MAX_RECORD and digest(record['sha256']))
    require(len({row['sequence'] for row in manifest['records']}) == len(manifest['records'])
            and sum(row['bytes'] for row in manifest['records']) <= MAX_RECORD_TOTAL
            and sum(item['bytes'] for item in images) <= MAX_TOTAL
            and manifest['total_bytes'] == sum(item['bytes'] for item in images)
                + sum(row['bytes'] for row in manifest['records']))
    _bounded_tree(manifest['records'])
    _bounded_tree(manifest['diagnostics'])
    return manifest, raw, result['manifest_sha256']


def chunk(value, run_id, export_id, item, offset, *, record=False):
    identity = 'sequence' if record else 'capture_id'
    result = closed(value, ('export_id', identity, 'offset', 'total_bytes', 'sha256',
                           'data_base64', 'next_offset', 'eof'))
    require(result['export_id'] == export_id and type(result[identity]) is int
            and result[identity] == item[identity]
            and type(result['offset']) is int and result['offset'] == offset
            and type(result['total_bytes']) is int and result['total_bytes'] == item['bytes']
            and result['sha256'] == item['sha256'] and type(result['eof']) is bool)
    raw = b64(result['data_base64'], CHUNK_BYTES)
    require(len(raw) == min(CHUNK_BYTES, item['bytes']-offset)
            and result['next_offset'] == offset+len(raw)
            and type(result['next_offset']) is int
            and result['eof'] == (result['next_offset'] == item['bytes']))
    return raw


def _journal(base, value):
    folder = base/('cycle-'+value['run_id'])
    folder.mkdir(mode=0o700, exist_ok=True)
    require(not folder.is_symlink(), 'cycle_local_symlink')
    raw = canonical(value)
    _atomic(folder/'journal.json', raw)
    _atomic(base/'active-cycle.json', raw)


def load_journal(base, *, protocol_spec=STANDARD_PROTOCOL):
    protocol = _spec(protocol_spec)
    path = base/'active-cycle.json'
    if not path.exists():
        return None
    require(not path.is_symlink(), 'cycle_local_symlink')
    selector = json_object(_read(path, 512*1024), 512*1024)
    require(selector.get('schema') == 'ngg2-cycle-client-v1'
            and selector.get('revision') == protocol.revision and selector.get('profile') == protocol.profile
            and identifier(selector.get('run_id')), 'cycle_journal_invalid')
    folder = base/('cycle-'+selector['run_id'])
    require(not folder.is_symlink() and not (folder/'journal.json').is_symlink(), 'cycle_local_symlink')
    # The per-run record is authoritative and is synced BEFORE the active
    # selector. A crash between those two renames must retain its newer state.
    value = json_object(_read(folder/'journal.json', 512*1024), 512*1024)
    require(value.get('run_id') == selector['run_id'], 'cycle_journal_invalid')
    closed(value, ('schema', 'revision', 'run_id', 'profile', 'start_intent', 'cancel_intent',
                  'state', 'resolved', 'manifest_sha256', 'export_id', 'images', 'archive_sha256',
                  'published', 'last_error', 'records'))
    require(value['schema'] == 'ngg2-cycle-client-v1' and value['revision'] == protocol.revision
            and identifier(value['run_id']) and value['profile'] == protocol.profile
            and all(type(value[key]) is bool for key in ('start_intent', 'cancel_intent', 'resolved', 'published'))
            and value['state'] in STATES | {'prepared', 'unknown'}
            and (value['manifest_sha256'] is None or digest(value['manifest_sha256']))
            and (value['export_id'] is None or identifier(value['export_id']))
            and (value['archive_sha256'] is None or digest(value['archive_sha256']))
            and type(value['images']) is list and len(value['images']) <= MAX_IMAGES
            and type(value['records']) is list and len(value['records']) <= 558
            and (value['last_error'] is None or type(value['last_error']) is str and len(value['last_error']) <= 64))
    require(not value['published'] or value['resolved'] and value['start_intent']
            and value['manifest_sha256'] is not None and value['export_id'] is not None
            and value['archive_sha256'] is not None, 'cycle_journal_invalid')
    if not value['start_intent']:
        require(not value['resolved'] and not value['images'] and not value['records']
                and value['manifest_sha256'] is None and value['export_id'] is None
                and value['archive_sha256'] is None and not value['cancel_intent'], 'cycle_journal_invalid')
    for key, identity in (('images', 'capture_id'), ('records', 'sequence')):
        for item in value[key]:
            base_keys = ({'name', 'capture_id', 'bytes', 'sha256', 'raw_sha256', 'width', 'height'}
                         if key == 'images' else {'sequence', 'kind', 'cycle', 'bytes', 'sha256'})
            closed(item, base_keys | {'offset', 'prefix_sha256'}, 'cycle_journal_invalid')
            require(type(item['offset']) is int and type(item['bytes']) is int
                    and 0 <= item['offset'] <= item['bytes'] <= MAX_IMAGE
                    and digest(item['prefix_sha256']) and digest(item['sha256'])
                    and ns(item[identity]), 'cycle_journal_invalid')
        require(len({item[identity] for item in value[key]}) == len(value[key]), 'cycle_journal_invalid')
    folder = base/('cycle-'+value['run_id'])
    require(not folder.is_symlink() and not (folder/'journal.json').is_symlink(), 'cycle_local_symlink')
    return value


def fresh_record(run_id=None, *, protocol_spec=STANDARD_PROTOCOL):
    protocol = _spec(protocol_spec)
    return dict(schema='ngg2-cycle-client-v1', revision=protocol.revision, run_id=run_id or uuid.uuid4().hex,
        profile=protocol.profile, records=[], start_intent=False, cancel_intent=False, state='prepared', resolved=False,
        manifest_sha256=None, export_id=None, images=[], archive_sha256=None, published=False, last_error=None)


def _call(client, method, params, *, deadline=None, clock=time.monotonic_ns, sleep=time.sleep,
          cancelled=lambda: False):
    # Only the authenticated, dedicated not-ready code is retryable. Starts,
    # cancels and arbitrary transport/remote errors are never replayed here.
    cap = clock()+30_000_000_000
    deadline = cap if deadline is None else min(deadline, cap)
    while True:
        began = diagnostics.now(client)
        try:
            result = client.call(method, params)
            diagnostics.notify(client, 'rpc', method, params, result,
                               start=began, end=diagnostics.now(client) if began is not None else None)
            return result.result if hasattr(result, 'result') else result
        except ProbeError as exc:
            diagnostics.notify(client, 'rpc', method, params, error=exc,
                               failure=getattr(client, 'last_failure', None),
                               start=began, end=diagnostics.now(client) if began is not None else None)
            if (method in (STANDARD_PROTOCOL.query, IRREGULAR_PROTOCOL.query) and getattr(exc, 'rpc_code', None) == -32096
                    and getattr(exc, 'error_shape_valid', False) is True):
                raise ProbeError('cycle_evidence_storage_unavailable') from None
            if not (method in (STANDARD_PROTOCOL.query, IRREGULAR_PROTOCOL.query) and params.get('mode') in
                    ('status', 'manifest', 'chunk', 'batch', 'record')
                    and getattr(exc, 'rpc_code', None) == -32094
                    and getattr(exc, 'error_shape_valid', False)):
                raise
            _checked(cancelled, clock, deadline)
            sleep(.1)


def verify_png(raw):
    """Check bounded PNG structure and every CRC; no Python pixel classification."""
    require(type(raw) is bytes and 57 <= len(raw) <= MAX_IMAGE
            and raw[:8] == b'\x89PNG\r\n\x1a\n', 'cycle_png_invalid')
    offset = 8
    first = True
    data = False
    ended = False
    while offset < len(raw):
        require(offset+12 <= len(raw), 'cycle_png_invalid')
        length = struct.unpack('>I', raw[offset:offset+4])[0]
        kind = raw[offset+4:offset+8]
        require(length <= MAX_IMAGE and offset+12+length <= len(raw), 'cycle_png_invalid')
        payload = raw[offset+8:offset+8+length]
        checksum = struct.unpack('>I', raw[offset+8+length:offset+12+length])[0]
        require((zlib.crc32(kind+payload) & 0xffffffff) == checksum, 'cycle_png_crc')
        if first:
            require(kind == b'IHDR' and length == 13, 'cycle_png_geometry')
            width, height, bits, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', payload)
            require((width, height, bits, compression, filtering, interlace) == (896,414,8,0,0,0)
                    and color in (2,6), 'cycle_png_geometry')
            first = False
        else:
            require(kind != b'IHDR' and not ended, 'cycle_png_invalid')
        if kind == b'IDAT':
            require(length > 0, 'cycle_png_invalid')
            data = True
        if kind == b'IEND':
            require(length == 0 and data, 'cycle_png_invalid')
            ended = True
        offset += length+12
    require(ended and offset == len(raw), 'cycle_png_invalid')


def _read(path, maximum):
    require(not path.is_symlink(), 'cycle_local_symlink')
    with path.open('rb') as handle:
        raw = handle.read(maximum+1)
    require(len(raw) <= maximum, 'cycle_local_limit')
    return raw


def _checked(cancelled, clock, deadline):
    require(not cancelled(), 'cancel_requested')
    require(clock() < deadline, 'host_deadline')


def _file_folder(base, record, is_record):
    folder = base/('cycle-'+record['run_id'])/('records' if is_record else 'images')
    folder.mkdir(mode=0o700, exist_ok=True)
    require(not folder.is_symlink(), 'cycle_local_symlink')
    return folder


def record_name(item):
    return 'record-'+str(item['sequence']).zfill(4)+'-'+item['kind']+'.json'


def collect(client, base, record, *, cancelled=lambda: False, clock=time.monotonic_ns,
            deadline=None, notice=print, protocol_spec=STANDARD_PROTOCOL):
    protocol = _spec(protocol_spec)
    require(record['profile'] == protocol.profile and record['revision'] == protocol.revision, 'cycle_journal_invalid')
    deadline = clock()+300_000_000_000 if deadline is None else deadline
    check = lambda: _checked(cancelled, clock, deadline)
    check()
    wire = _call(client, protocol.query, {'run_id': record['run_id'], 'mode': 'manifest'},
                 deadline=deadline, clock=clock, cancelled=cancelled)
    manifest, raw_manifest, manifest_sha = read_manifest(wire, record['run_id'], protocol_spec=protocol)
    folder = base/('cycle-'+record['run_id'])
    manifest_path = folder/'native-manifest.json'
    if record['manifest_sha256'] is None:
        require(not manifest_path.exists() or _read(manifest_path, MAX_MANIFEST) == raw_manifest,
                'cycle_manifest_changed')
        _atomic(manifest_path, raw_manifest)
        record.update(manifest_sha256=manifest_sha, export_id=manifest['export_id'])
        record['images'] = [dict(item, offset=0, prefix_sha256=hashlib.sha256(b'').hexdigest())
                            for item in manifest['images']]
        record['records'] = [dict(item, offset=0, prefix_sha256=hashlib.sha256(b'').hexdigest())
                             for item in manifest['records']]
        _journal(base, record)
    else:
        require(record['manifest_sha256'] == manifest_sha and record['export_id'] == manifest['export_id']
                and _read(manifest_path, MAX_MANIFEST) == raw_manifest, 'cycle_manifest_changed')
        for key in ('images', 'records'):
            require([{k:v for k,v in item.items() if k not in ('offset', 'prefix_sha256')}
                     for item in record[key]] == manifest[key], 'cycle_manifest_changed')
    saved = sum(item['offset'] == item['bytes'] for item in record['images'])
    notice('画像回収中: 保存済み'+str(saved)+'/'+str(len(record['images']))+'枚。終了表示までお待ちください。')
    for is_record, key in ((True, 'records'), (False, 'images')):
        phase_started = diagnostics.now(client)
        destination = _file_folder(base, record, is_record)
        parts = destination/'.parts'
        parts.mkdir(mode=0o700, exist_ok=True)
        require(not parts.is_symlink(), 'cycle_local_symlink')
        for item in record[key]:
            check()
            name = record_name(item) if is_record else item['name']
            target = destination/name
            fragment = parts/(name+'.part')
            selected = fragment if fragment.exists() else target
            prior = _read(selected, MAX_RECORD if is_record else MAX_IMAGE) if selected.exists() else b''
            offset = item['offset']
            require(offset <= len(prior) <= item['bytes']
                    and hashlib.sha256(prior[:offset]).hexdigest() == item['prefix_sha256'], 'cycle_prefix_changed')
            raw = prior[:offset]
            while offset < item['bytes']:
                check()
                params = {'run_id': record['run_id'], 'mode': 'record' if is_record else 'batch',
                          'export_id': record['export_id'], 'offset': offset}
                params['sequence' if is_record else 'capture_id'] = item['sequence' if is_record else 'capture_id']
                if not is_record:
                    params['count'] = 4
                response = envelope(_call(client, protocol.query, params, deadline=deadline, clock=clock, cancelled=cancelled),
                                    record['run_id'], params['mode'], protocol_spec=protocol)
                if is_record:
                    chunks = [response]
                else:
                    closed(response, ('export_id', 'chunks'))
                    require(response['export_id'] == record['export_id'])
                    chunks = response['chunks']
                    require(type(chunks) is list and 1 <= len(chunks) <= 4)
                for part in chunks:
                    require(offset < item['bytes'], 'cycle_chunk_after_eof')
                    piece = chunk(part, record['run_id'], record['export_id'], item, offset, record=is_record)
                    suffix = prior[offset:offset+len(piece)]
                    require(piece[:len(suffix)] == suffix, 'cycle_prefix_changed')
                    raw += piece
                    offset += len(piece)
                # The native batch is authenticated as one bounded response.
                # Keep any renamed-but-uncheckpointed suffix until same-offset
                # replies have been compared, including after another crash.
                _atomic(fragment, raw+prior[offset:])
                item.update(offset=offset, prefix_sha256=hashlib.sha256(raw).hexdigest())
                _journal(base, record)
                check()
            require(len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256'],
                    'cycle_file_hash')
            if is_record:
                json_object(raw, MAX_RECORD)
            else:
                with diagnostics.span(client, 'evidence_verify', record['run_id']):
                    verify_png(raw)
            if target.exists():
                require(_read(target, MAX_RECORD if is_record else MAX_IMAGE) == raw, 'cycle_file_changed')
            else:
                _atomic(target, raw)
            if fragment.exists():
                fragment.unlink()
            if not is_record:
                saved += int(item['offset'] == item['bytes'] and target.exists())
                # Recalculate rather than double count an already completed file.
                saved = sum(entry['offset'] == entry['bytes'] for entry in record['images'])
                notice('画像回収中: 保存済み'+str(saved)+'/'+str(len(record['images']))+'枚。終了表示までお待ちください。')
        if phase_started is not None:
            diagnostics.notify(client, 'phase', 'records_collect' if is_record else 'images_collect',
                               record['run_id'], phase_started, diagnostics.now(client))
    with diagnostics.span(client, 'evidence_verify', record['run_id']):
        verify_evidence(base, record, manifest, protocol_spec=protocol)
    record.update(resolved=True, state='stopped' if manifest['interrupted'] else 'completed',
                  last_error=record['last_error'] if record['cancel_intent'] else None)
    _journal(base, record)
    return manifest


def verify_evidence(base, record, manifest=None, *, protocol_spec=STANDARD_PROTOCOL):
    protocol = _spec(protocol_spec)
    require(record['profile'] == protocol.profile and record['revision'] == protocol.revision, 'cycle_journal_invalid')
    folder = base/('cycle-'+record['run_id'])
    raw = _read(folder/'native-manifest.json', MAX_MANIFEST)
    require(hashlib.sha256(raw).hexdigest() == record['manifest_sha256'], 'cycle_manifest_changed')
    parsed, _, _ = read_manifest({'schema':protocol.schema, 'run_id':record['run_id'], 'profile':protocol.profile,
        'mode':'manifest', 'payload':{'export_id':record['export_id'],
            'manifest_sha256':record['manifest_sha256'], 'manifest_json':raw.decode('utf-8')}}, record['run_id'], protocol_spec=protocol)
    if manifest is not None:
        require(parsed == manifest, 'cycle_manifest_changed')
    frame_metadata = {}
    irregular_records = []
    session_count = 0
    previous_record = None
    expected_sequence = 1
    for is_record, key in ((True, 'records'), (False, 'images')):
        expected = parsed[key]
        require([{k:v for k,v in item.items() if k not in ('offset', 'prefix_sha256')}
                 for item in record[key]] == expected, 'cycle_manifest_changed')
        for item in record[key]:
            require(item['offset'] == item['bytes'] and item['prefix_sha256'] == item['sha256'],
                    'cycle_files_incomplete')
            path = folder/('records' if is_record else 'images')/(record_name(item) if is_record else item['name'])
            raw_file = _read(path, MAX_RECORD if is_record else MAX_IMAGE)
            require((len(raw_file), hashlib.sha256(raw_file).hexdigest()) == (item['bytes'], item['sha256']),
                    'cycle_file_changed')
            if not is_record:
                verify_png(raw_file)
                continue
            body = json_object(raw_file, MAX_RECORD)
            if item['kind'] == 'session':
                require(body.get('run_id') == record['run_id'], 'cycle_record_identity')
                provenance = body.get('provenance', {})
                require(type(provenance) is dict and provenance.get('native_profile', PROFILE) == protocol.profile, 'cycle_record_identity')
                if protocol.irregular:
                    require(provenance.get('native_profile') == protocol.profile, 'cycle_record_identity')
                if 'yield_after_restart' in provenance:
                    require(protocol is IRREGULAR_PROTOCOL and provenance['yield_after_restart'] is True,
                            'cycle_record_identity')
                if 'initial_restart' in provenance:
                    require(protocol is IRREGULAR_PROTOCOL and provenance['initial_restart'] is True,
                            'cycle_record_identity')
                session_count += 1
            elif item['kind'] == 'frame':
                require(body.get('schema') == 'ngg2-cycle-frame-v1' and body.get('run_id') == record['run_id']
                        and ns(body.get('capture_id')) and digest(body.get('raw_sha256'))
                        and body.get('raw_bytes') == 896*414*4
                        and body['capture_id'] not in frame_metadata, 'cycle_frame_metadata')
                frame_metadata[body['capture_id']] = body
            else:
                require(body.get('run_id') == record['run_id'], 'cycle_record_identity')
                payload = body.get('payload', {})
                if type(payload) is dict:
                    from . import irregular
                    irregular.validate_controller(payload.get('controller'), allow_irregular=protocol.irregular)
                    if 'irregular' in payload and item['kind'] not in irregular.RECORD_KINDS:
                        require(protocol.irregular, 'cycle_record_schema')
                        irregular.validate_status(payload['irregular'])
                if item['kind'].startswith('irregular_'):
                    require(protocol.irregular, 'cycle_record_schema')
                    irregular.validate_record(item['kind'], payload)
                    irregular_records.append((item['kind'], payload))
                if parsed['complete'] and not parsed['interrupted']:
                    closed(body, ('schema','run_id','sequence','kind','cycle','previous','payload'), 'cycle_record_schema')
                    require(body['schema'] == 'ngg2-cycle-record-v1'
                        and body['sequence'] == item['sequence'] == expected_sequence
                        and type(body['sequence']) is int
                        and body['kind'] == item['kind'] and body['cycle'] == item['cycle']
                        and type(body['cycle']) is int and body['previous'] == previous_record,
                        'cycle_record_chain')
                    previous_record = item['sha256']
                    expected_sequence += 1
    missing_header_diagnostic = (not parsed['complete'] and parsed['interrupted']
        and any(type(item) is dict and item.get('code') == 'session_header_uncommitted'
                and item.get('authority') is False for item in parsed['diagnostics']))
    require(session_count == 1 or session_count == 0 and missing_header_diagnostic,
            'cycle_session_header_missing')
    if protocol.irregular:
        from .irregular import sequence_summary
        sequence_summary(irregular_records, frame_metadata)
        images_by_id = {item['capture_id']:item for item in parsed['images']}
        for _kind, payload in irregular_records:
            for frame in payload['frames']:
                image = images_by_id.get(frame['capture_id'])
                require(image is not None and image['raw_sha256'] == frame['rgba_sha256'],
                    'cycle_irregular_image_missing')
    for image in parsed['images']:
        require(image['capture_id'] in frame_metadata
                and frame_metadata[image['capture_id']]['raw_sha256'] == image['raw_sha256'],
                'cycle_frame_metadata_missing')
    return parsed


def run_session(client, base, *, cancelled=lambda: False, clock=time.monotonic_ns,
                sleep=time.sleep, notice=print, session_seconds=200, protocol_spec=STANDARD_PROTOCOL):
    protocol = _spec(protocol_spec)
    require(client_protocol(client) is protocol, 'cycle_protocol_invalid')
    yield_after_restart = restart_yield_enabled(client)
    initial_restart = initial_restart_enabled(client)
    base = Path(base)
    base.mkdir(mode=0o700, parents=True, exist_ok=True)
    require(not base.is_symlink(), 'cycle_local_symlink')
    record = load_journal(base, protocol_spec=protocol)
    if record is None or record['published']:
        record = fresh_record(protocol_spec=protocol)
        _journal(base, record)
    recovering = record['start_intent'] and not record['published']
    run_id = record['run_id']
    if recovering:
        notice('前回の結果の回収のみ行います。今回はゲームを起動しません。')
    try:
        if not record['start_intent']:
            client.check_schema()
            ready_deadline = clock()+8_000_000_000
            while True:
                _checked(cancelled, clock, ready_deadline)
                prepared = prepare(_call(client, protocol.query, {'run_id':run_id,
                    'mode':'prepare', 'request_authorization':False}), run_id, protocol_spec=protocol)
                if prepared['unpublished_run_ids']:
                    # Adopt only the native unpublished identity, never start a
                    # replacement run after losing this install's local state.
                    record = fresh_record(prepared['unpublished_run_ids'][0], protocol_spec=protocol)
                    record['start_intent'] = True
                    record['state'] = 'unknown'
                    _journal(base, record)
                    run_id = record['run_id']
                    recovering = True
                    notice('端末に未回収の記録があります。同じ実行IDを回収します。ゲームは開始しません。')
                    break
                if prepared['ready']:
                    break
                require(prepared['notification_authorization'] not in ('denied', 'unavailable', 'not_determined'),
                        'cycle_notification_permission')
                require(prepared['recovery_scan'] != 'failed', 'cycle_recovery_scan_failed')
                sleep(.25)
            if not recovering:
                _checked(cancelled, clock, ready_deadline)
                record['start_intent'] = True
                record['last_error'] = None
                _journal(base, record)  # durable before the only start POST
                def start_guard():
                    try:
                        _checked(cancelled, clock, ready_deadline)
                    except ProbeError as failure:
                        raise _StartNotSent(failure.code) from None
                previous_guard = getattr(client, '_before_start_post', None)
                client._before_start_post = start_guard
                try:
                    start_guard()  # Also covers injected transports in tests.
                    params = {'run_id':run_id, 'profile':protocol.profile}
                    if yield_after_restart:
                        params['yield_after_restart'] = True
                    if initial_restart:
                        params['initial_restart'] = True
                    record['state'] = start_reply(_call(client, 'necro_native_start', params),
                        run_id, protocol_spec=protocol, yield_after_restart=yield_after_restart,
                        initial_restart=initial_restart)
                except _StartNotSent:
                    record.update(start_intent=False, state='stopped')
                    _journal(base, record)
                    raise
                except ProbeError as failure:
                    # This dedicated code is emitted only before native
                    # admission/seen-ID consumption. Other errors stay UNKNOWN.
                    if (isinstance(failure, RemoteRpcError) and failure.error_shape_valid is True
                            and failure.rpc_code == -32095):
                        record.update(start_intent=False, state='stopped', last_error='cycle_start_not_admitted')
                        _journal(base, record)
                        raise _StartNotSent('cycle_start_not_admitted') from None
                    record.update(state='unknown', last_error='cycle_start_uncertain')
                    _journal(base, record)
                    raise
                finally:
                    client._before_start_post = previous_guard
                _journal(base, record)
        if record['resolved']:
            verify_evidence(base, record, protocol_spec=protocol)
            return record
        deadline = clock()+int(session_seconds*1e9)
        wait_started = diagnostics.now(client)
        while True:
            if cancelled() or clock() >= deadline:
                record['cancel_intent'] = True
                _journal(base, record)
                try:
                    start_reply(_call(client, 'necro_native_cancel', {'run_id':run_id}), run_id,
                                protocol_spec=protocol, yield_after_restart=yield_after_restart,
                                initial_restart=initial_restart)
                except ProbeError:
                    pass
                record['last_error'] = 'cancel_requested' if cancelled() else 'host_deadline'
                _journal(base, record)
                return record
            reply = status(_call(client, protocol.query, {'run_id':run_id,
                'mode':'status', 'keepalive':not recovering and not record['cancel_intent']}), run_id, protocol_spec=protocol)
            record['state'] = reply['state']
            _journal(base, record)
            if reply['terminal'] and reply['workers_drained'] and reply['input_state'] in (0,3,4) \
                    and not reply['native_inflight']:
                if wait_started is not None:
                    diagnostics.notify(client, 'phase', 'session_wait', run_id, wait_started, diagnostics.now(client))
                diagnostics.notify(client, 'terminal', client, run_id, reply)
                collect(client, base, record, cancelled=cancelled, clock=clock, notice=notice, protocol_spec=protocol)
                return record
            sleep(.25)
    except (ProbeError, OSError) as exc:
        error = exc.code if isinstance(exc, ProbeError) else 'local_storage_failed'
        record['last_error'] = error if re.fullmatch('[a-z_0-9]{1,64}', error) else 'cycle_rpc_failed'
        if not record['start_intent']:
            record.update(state='stopped', resolved=False)
        elif not record['resolved']:
            record['state'] = 'unknown'
            # An interrupted live client cannot keep operating blindly. Save
            # cancel intent before this idempotent request; never resend start.
            if not recovering and not record['cancel_intent']:
                record['cancel_intent'] = True
                save_failed = None
                try:
                    _journal(base, record)
                except OSError as failure:
                    save_failed = failure
                try:
                    _call(client, 'necro_native_cancel', {'run_id':run_id})
                except ProbeError:
                    pass
                if save_failed is not None:
                    raise save_failed
        _journal(base, record)
        if isinstance(exc, OSError):
            raise
        return record
