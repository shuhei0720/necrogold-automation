"""NG-G2専用の軽量な開始・状態・取消・結果回収クライアント。"""
import argparse
from contextlib import contextmanager
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import struct
import sys
import time
import uuid

from .crypto import Crypto
from .deadlines import OwnedRpcTimer
from .protocol import Client
from .protocol import HttpTransport, load_pairing
from .validation import ProbeError, b64, json_object, number

REVISION = 'native-walk-v2'
API_VERSION = '1.98.14-ngg2'
CAPABILITY = 'necrogold_native_v1'
PROFILE = 'normal-1-1-v1'
MAX_IMAGE = 512 * 1024
MAX_IMAGES = 20
MAX_TOTAL_IMAGES = 4 * 1024 * 1024
MAX_HTTP_EVENTS = 128
MAX_CAPTURES = 256
MAX_NATIVE_EVENTS = 64
MAX_CANCEL_ATTEMPTS = 3
MAX_SCHEMA = 512 * 1024
MAX_SCHEMA_ATTEMPTS = 4
SCHEMA_BUDGET_NS = 8_000_000_000
DIAGNOSTIC_STAGES = frozenset(('connect', 'request', 'headers', 'body', 'complete'))
DIAGNOSTIC_KINDS = frozenset(('ok', 'refused', 'timeout', 'reset', 'disconnected', 'unreachable',
    'deadline', 'http_status', 'body_limit', 'body_truncated', 'protocol_error', 'io_error'))
RETRY_KINDS = frozenset(('refused', 'timeout', 'reset', 'disconnected', 'unreachable'))
RPC_METHODS = frozenset(('necro_native_start', 'necro_native_status',
                         'necro_native_cancel', 'necro_native_results'))
HTTP_TIMING_KEYS = frozenset(('request_start_ns', 'http_start_ns', 'http_end_ns',
    'decrypt_start_ns', 'decrypt_end_ns', 'response_end_ns'))
STATES = frozenset(('accepted', 'running', 'completed', 'stopped', 'draining'))
TERMINAL = frozenset(('completed', 'stopped'))
REASONS = frozenset(('none', 'goods', 'cancelled', 'foreground', 'locked', 'owner_paused',
                     'capture', 'stale', 'beat', 'late', 'movement', 'unknown_input',
                     'no_path', 'partial_goods', 'limit', 'session', 'restart', 'screen',
                     'generation', 'heartbeat', 'geometry', 'unclassified'))
NUMERIC_KEYS = frozenset(('abi_version', 'struct_size', 'phase', 'reason', 'terminal', 'goods',
    'paused', 'input_state', 'inputs', 'moves', 'door_changes', 'terrain_changes', 'restarts',
    'x', 'y', 'lead_confirmed', 'started_ns', 'walk_started_ns', 'ended_ns', 'first_move_ns',
    'last_capture_id', 'last_capture_start_ns', 'last_capture_end_ns', 'last_completed_id',
    'current_command_id', 'last_ordinal', 'next_target_ns', 'lead_ns', 'capture_count',
    'accepted_frames', 'discarded_frames', 'beat_period_ns', 'device_now_ns', 'id', 'ordinal',
    'target_ns', 'not_before_ns', 'deadline_ns', 'source_capture_id', 'source_start_ns',
    'phase_sample_ns', 'kind', 'direction', 'begin_ns', 'end_ns', 'observed_capture_id',
    'outcome', 'motion', 'dx', 'dy', 'capture_id', 'start_ns', 'completed_prefix',
    'started_prefix', 'inflight', 'generation', 'sequence', 'timeout_ns', 'last_heartbeat_ns',
    'decode_end_ns', 'analysis_start_ns', 'analysis_end_ns', 'completed_prefix_start',
    'completed_prefix_end', 'accepted_started_ns', 'live_completed_prefix',
    'native_capture_requests', 'latest_frames_replaced', 'daemon_requests_outstanding',
    'analyzed_capture_count', 'evicted_capture_count', 'retained_image_count',
    'pinned_image_count', 'recent_image_count', 'retained_images', 'exported_images',
    'omitted_image_count'))
BOOL_KEYS = frozenset(('cancel_requested', 'stable', 'timed_out', 'draining', 'capture_outstanding',
    'capture_timed_out', 'workers_drained', 'bootstrap_ui_started', 'ui_frozen',
    'main_ticket_outstanding', 'native_inflight', 'inflight_start', 'inflight_end',
    'stable_prefix', 'historical_metadata_only'))
ID_LIST_KEYS = frozenset(('referenced_capture_ids', 'missing_capture_ids', 'exported_capture_ids',
                         'omitted_capture_ids'))
FIXED_TEXT = {'capture_backend': 'direct_daemon_jpeg_only', 'analysis_engine': 'native_C_v1',
    'capture_time_semantics': 'request_call_interval_not_presentation_timestamp',
    'input_time_semantics': 'synth_call_interval_not_game_receipt_timestamp'}
ERROR_CODES = frozenset(('connection_error', 'rpc_deadline', 'rpc_error', 'response_mac_mismatch',
    'response_id_mismatch', 'http_body_limit', 'http_body_truncated', 'invalid_native_status',
    'invalid_native_report', 'invalid_native_images', 'native_capability_missing',
    'cancel_requested', 'host_deadline', 'rpc_failed', 'native_input_unresolved',
    'native_results_unavailable', 'native_schema_invalid', 'schema_http_status'))


def _require(value, reason):
    if not value:
        raise ProbeError(reason)


def _uuid(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{32}', value) is not None


def _error(exc):
    return exc.code if isinstance(exc, ProbeError) and exc.code in ERROR_CODES else 'rpc_failed'


class _StartNotSent(ProbeError):
    """Only a local admission guard can establish this before transport entry."""


class NativeClient(Client):
    def call(self, method, params=None, *, timeout=None):
        guard = getattr(self, '_before_start_post', None)
        if method != 'necro_native_start' or guard is None:
            return super().call(method, params, timeout=timeout)
        transport = self.transport
        def guarded_post(body, rpc_timeout):
            try:
                guard()
            except ProbeError as exc:
                raise _StartNotSent(exc.code) from None
            return transport(body, rpc_timeout)
        self.transport = guarded_post
        try:
            return super().call(method, params, timeout=timeout)
        finally:
            self.transport = transport

    def _validate(self, method, params):
        expected = ({'run_id', 'profile'} if method == 'necro_native_start'
                    else {'run_id', 'keepalive'} if method == 'necro_native_status' else {'run_id'})
        if (method not in ('necro_native_start', 'necro_native_status',
                           'necro_native_cancel', 'necro_native_results')
                or type(params) is not dict or set(params) != expected
                or type(params.get('run_id')) is not str
                or not re.fullmatch('[0-9a-f]{32}', params['run_id'])
                or ('keepalive' in params and type(params['keepalive']) is not bool)
                or ('profile' in params and params['profile'] != PROFILE)):
            raise ProbeError('method_not_allowed')

    def read_server_schema(self, timeout):
        """Read only fixed local metadata; native RPC still supplies authentication."""
        self.last_server_schema = None
        self.transport.last_diagnostic = None
        number(timeout, .001, min(2, self.timeout))
        _require(isinstance(self.deadline_owner, OwnedRpcTimer), 'timer_owner_required')
        with self.deadline_owner.deadline(timeout):
            raw = self.transport.schema(timeout)
            try:
                value = json_object(raw, MAX_SCHEMA)
                metadata = _schema_metadata(value)
            except ProbeError as exc:
                if exc.code == 'rpc_deadline':
                    raise
                raise ProbeError('native_schema_invalid') from None
            self.last_server_schema = metadata
            _require(metadata['server_version'] == API_VERSION and metadata['native_capability'],
                     'native_capability_missing')
        return metadata


def _ns(value):
    return type(value) is int and 0 <= value < 2**63


def _build_stamp(value):
    if type(value) is not str or re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}', value) is None:
        return None
    year, month, day, hour, minute = (int(value[a:b]) for a,b in ((0,4),(5,7),(8,10),(11,13),(14,16)))
    if not (1 <= year <= 9999 and 1 <= month <= 12 and hour < 24 and minute < 60):
        return None
    days = (31, 29 if year%4 == 0 and (year%100 != 0 or year%400 == 0) else 28,
            31,30,31,30,31,31,30,31,30,31)
    return value if 1 <= day <= days[month-1] else None


def _schema_metadata(value):
    _require(type(value) is dict and type(value.get('server_version')) is str
             and len(value['server_version']) <= 128
             and type(value.get('protocol_version')) is int and value['protocol_version'] == 1
             and type(value.get('capability_tags')) is list and len(value['capability_tags']) <= 256
             and all(type(v) is str and len(v) <= 128 for v in value['capability_tags']),
             'native_schema_invalid')
    result = {'server_version': API_VERSION if value['server_version'] == API_VERSION else 'other',
              'protocol_version': 1, 'native_capability': CAPABILITY in value['capability_tags']}
    stamp = _build_stamp(value.get('build'))
    if stamp is not None:
        result['build'] = stamp
    return result


def _diagnostic(value):
    _require(type(value) is dict and set(value) == {'stage','kind','errno','status','started_ns','ended_ns'}
             and type(value.get('stage')) is str and value['stage'] in DIAGNOSTIC_STAGES
             and type(value.get('kind')) is str and value['kind'] in DIAGNOSTIC_KINDS
             and (value.get('errno') is None or type(value['errno']) is int and 0 <= value['errno'] <= 4095)
             and (value.get('status') is None or type(value['status']) is int and 100 <= value['status'] <= 599)
             and _ns(value.get('started_ns')) and _ns(value.get('ended_ns'))
             and value['started_ns'] <= value['ended_ns'], 'native_journal_invalid')
    return {key:value[key] for key in ('stage','kind','errno','status','started_ns','ended_ns')}


def _preflight(value):
    _require(type(value) is dict and set(value) == {'schema','started_ns','deadline_ns','state','attempts','server'}
             and value.get('schema') == 'ngg2-connect-v1'
             and _ns(value.get('started_ns')) and _ns(value.get('deadline_ns'))
             and value['started_ns'] <= value['deadline_ns']
             and value.get('state') in ('pending','ready','failed','cancelled')
             and type(value.get('attempts')) is list and len(value['attempts']) <= MAX_SCHEMA_ATTEMPTS,
             'native_journal_invalid')
    rows = []
    end = value['started_ns']
    for index,row in enumerate(value['attempts'], 1):
        _require(type(row) is dict and set(row) == {'attempt','started_ns','ended_ns','error','diagnostic'}
                 and type(row.get('attempt')) is int and row['attempt'] == index
                 and _ns(row.get('started_ns')) and _ns(row.get('ended_ns'))
                 and end <= row['started_ns'] <= row['ended_ns']
                 and row['started_ns'] < value['deadline_ns']
                 and (row.get('error') is None or row['error'] in ERROR_CODES), 'native_journal_invalid')
        diagnostic = _diagnostic(row['diagnostic'])
        _require(diagnostic == row['diagnostic'], 'native_journal_invalid')
        rows.append(dict(row, diagnostic=diagnostic))
        end = row['ended_ns']
    server = value['server']
    if server is not None:
        _require(type(server) is dict and set(server) <= {'server_version','protocol_version','native_capability','build'}
                 and set(server) >= {'server_version','protocol_version','native_capability'}
                 and server.get('server_version') in (API_VERSION, 'other')
                 and type(server.get('protocol_version')) is int and server['protocol_version'] == 1
                 and type(server.get('native_capability')) is bool
                 and ('build' not in server or _build_stamp(server['build']) == server['build']),
                 'native_journal_invalid')
    if value['state'] == 'ready':
        _require(rows and rows[-1]['error'] is None and server is not None
                 and server['server_version'] == API_VERSION and server['native_capability'],
                 'native_journal_invalid')
    return dict(value, attempts=rows, server=None if server is None else dict(server))


def _events(value):
    """Project legacy journal diagnostics before anything can save them again."""
    rows = []
    for row in value:
        _require(type(row) is dict and _uuid(row.get('invocation'))
                 and row.get('method') in RPC_METHODS | {'device_info'}
                 and _ns(row.get('host_ns')), 'native_journal_invalid')
        clean = {key:row[key] for key in ('invocation','method','host_ns')}
        clean['error'] = row.get('error') if row.get('error') in ERROR_CODES | {None} else 'rpc_failed'
        if 'host_timings' in row:
            _require(type(row['host_timings']) is dict, 'native_journal_invalid')
            clean['host_timings'] = {k:v for k,v in row['host_timings'].items()
                                     if k in HTTP_TIMING_KEYS and _ns(v)}
        rows.append(clean)
    return rows


@contextmanager
def device_lock(path=None):
    """Share the legacy device lease without importing its image pipeline."""
    path = Path(path) if path else Path.home()/'.necroprobe'/'restart.lock'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a') as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ProbeError('already_running') from None
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _atomic(path, raw):
    """Commit journal before network side effects, including the directory entry."""
    temporary = path.with_name(path.name + '.tmp-' + uuid.uuid4().hex)
    try:
        with temporary.open('xb') as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(str(path.parent), os.O_RDONLY)
        try:
            try:
                os.fsync(directory)
            except OSError as exc:
                # Some iSH document mounts do not implement directory fsync.
                # The file itself was flushed and replaced atomically above.
                if exc.errno not in (errno.EINVAL, errno.ENOTSUP, errno.ENOSYS):
                    raise
        finally:
            os.close(directory)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _save(base, record):
    folder = base/('native-' + record['run_id'])
    folder.mkdir(mode=0o700, exist_ok=True)
    raw = json.dumps(record, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()
    _atomic(folder/'report.json', raw)
    _atomic(base/'active.json', raw)


def _load(base):
    path = base/'active.json'
    if not path.exists():
        return None
    try:
        with path.open('rb') as handle:
            raw = handle.read(2 * 1024 * 1024 + 1)
        record = json_object(raw, 2 * 1024 * 1024)
        _require(record.get('schema') == 'ngg2-host-v1' and _uuid(record.get('run_id'))
                 and record.get('profile') == PROFILE and type(record.get('resolved')) is bool
                 and type(record.get('start_attempted')) is bool
                 and type(record.get('cancel_attempted')) is bool
                 and type(record.get('events')) is list and len(record['events']) <= 1024,
                 'native_journal_invalid')
        # Reconstruct only the persisted client schema; never echo arbitrary fields.
        allowed = ('schema', 'revision', 'run_id', 'profile', 'state', 'resolved', 'start_attempted',
                   'cancel_attempted', 'stop_reason', 'native_state', 'native_report', 'images',
                   'host_clock_domain', 'native_clock_domain', 'events')
        optional = {'cancel_attempts', 'cancel_confirmed', 'events_dropped', 'result_metadata', 'preflight'}
        _require(set(allowed) <= set(record) <= set(allowed) | optional, 'native_journal_invalid')
        record.setdefault('cancel_attempts', int(record['cancel_attempted']))
        record.setdefault('cancel_confirmed', False)
        record.setdefault('events_dropped', 0)
        record.setdefault('result_metadata', {})
        _require(type(record['cancel_attempts']) is int and 0 <= record['cancel_attempts'] <= MAX_CANCEL_ATTEMPTS
                 and type(record['cancel_confirmed']) is bool and type(record['events_dropped']) is int
                 and 0 <= record['events_dropped'] < 2**63, 'native_journal_invalid')
        excess = max(0, len(record['events']) - MAX_HTTP_EVENTS)
        record['events_dropped'] += excess
        record['events'] = _events(record['events'][excess:])
        _require(record.get('revision') in ('native-walk-v1', REVISION)
                 and record.get('host_clock_domain') == 'python.monotonic_ns'
                 and record.get('native_clock_domain') == 'device.monotonic_ns', 'native_journal_invalid')
        if 'preflight' in record:
            record['preflight'] = _preflight(record['preflight'])
        _require(record['state'] in STATES | {'prepared', 'unknown'}
                 and record['native_state'] in STATES | {None}
                 and record['stop_reason'] in ERROR_CODES | {None}, 'native_journal_invalid')
        _require(record['native_report'] is None or _report(record['native_report']) == record['native_report'],
                 'native_journal_invalid')
        _require(_result_metadata(record['result_metadata']) == record['result_metadata'], 'native_journal_invalid')
        record['images'] = _stored_images(record['images'])
        return record
    except (OSError, ProbeError, ValueError, TypeError, RecursionError):
        raise ProbeError('native_journal_invalid') from None


def _report(value, depth=0):
    _require(type(value) is dict and depth <= 3 and len(value) <= 128, 'invalid_native_report')
    result = {}
    for key, item in value.items():
        if key in NUMERIC_KEYS:
            low = -64 if key in ('x', 'y', 'dx', 'dy', 'direction', 'motion') else 0
            _require(type(item) is int and low <= item < 2**63, 'invalid_native_report')
            limits = {'input_state': 4, 'inputs': 16, 'moves': 16, 'restarts': 12,
                      'phase': 7, 'reason': 20, 'terminal': 1, 'goods': 1, 'paused': 1,
                      'lead_confirmed': 1, 'inflight': 1}
            _require(key not in limits or item <= limits[key], 'invalid_native_report')
            result[key] = item
        elif key == 'schema':
            _require(item == 'ngg2-native-v1', 'invalid_native_report')
            result[key] = item
        elif key == 'clock_id':
            _require(_uuid(item), 'invalid_native_report')
            result[key] = item
        elif key == 'reason_name':
            # Unknown free text is dropped, including remote exception messages.
            result[key] = item if type(item) is str and item in REASONS else 'unclassified'
        elif key in BOOL_KEYS:
            _require(type(item) is bool, 'invalid_native_report')
            result[key] = item
        elif key == 'backend':
            result[key] = item if item in ('daemon_direct', 'daemon', 'none') else 'none'
        elif key in ('capture', 'command'):
            result[key] = _report(item, depth+1)
        elif key in ('events', 'captures'):
            limit = MAX_NATIVE_EVENTS if key == 'events' else MAX_CAPTURES
            _require(type(item) is list and len(item) <= limit, 'invalid_native_report')
            result[key] = [_report(event, depth+1) for event in item]
        elif key in ID_LIST_KEYS:
            _require(type(item) is list and len(item) <= MAX_CAPTURES
                     and all(type(v) is int and 0 <= v < 2**63 for v in item), 'invalid_native_report')
            result[key] = list(item)
        elif key in FIXED_TEXT:
            _require(item == FIXED_TEXT[key], 'invalid_native_report')
            result[key] = item
    for timing in (('start_ns', 'end_ns', 'decode_end_ns', 'analysis_start_ns', 'analysis_end_ns'),
                   ('capture_start_ns', 'capture_end_ns', 'decode_end_ns')):
        available = [result[key] for key in timing if key in result]
        _require(available == sorted(available), 'invalid_native_report')
    if depth == 0:
        _require(result.get('schema') == 'ngg2-native-v1' and _uuid(result.get('clock_id'))
                 and 'input_state' in result and 'device_now_ns' in result, 'invalid_native_report')
    return result


def _status(value, run_id):
    _require(type(value) is dict and value.get('run_id') == run_id
             and value.get('profile') == PROFILE and type(value.get('state')) is str
             and value['state'] in STATES,
             'invalid_native_status')
    _require('api_version' not in value or value['api_version'] == API_VERSION, 'invalid_native_status')
    return value['state'], _report(value.get('report'))


def _result_metadata(value):
    selected = {key: item for key, item in value.items()
                if key in ('retained_images', 'exported_images', 'omitted_image_count')
                or key in ID_LIST_KEYS}
    result = _report(selected, depth=1)
    if 'api_version' in value:
        _require(value['api_version'] == API_VERSION, 'invalid_native_status')
        result['api_version'] = API_VERSION
    _require(all(result[key] <= MAX_IMAGES for key in ('retained_images', 'exported_images') if key in result),
             'invalid_native_images')
    return result


def _stored_images(value):
    """Keep only bounded image evidence metadata from older local journals."""
    _require(type(value) is list and len(value) <= MAX_IMAGES, 'native_journal_invalid')
    selected = []
    seen = set()
    total = 0
    for item in value:
        _require(type(item) is dict and type(item.get('name')) is str
                 and re.fullmatch(r'[a-z][a-z0-9_-]{0,63}\.png', item['name'])
                 and item['name'] not in seen and item.get('format') == 'png'
                 and type(item.get('pixel_width')) is int and item['pixel_width'] == 896
                 and type(item.get('pixel_height')) is int and item['pixel_height'] == 414
                 and type(item.get('sha256')) is str and re.fullmatch(r'[0-9a-f]{64}', item['sha256'])
                 and type(item.get('bytes')) is int and 24 <= item['bytes'] <= MAX_IMAGE,
                 'native_journal_invalid')
        seen.add(item['name'])
        total += item['bytes']
        _require(total <= MAX_TOTAL_IMAGES, 'native_journal_invalid')
        clean = {key:item[key] for key in ('name','format','pixel_width','pixel_height','sha256','bytes')}
        for key in ('capture_id','capture_start_ns','capture_end_ns'):
            _require(_ns(item.get(key)), 'native_journal_invalid')
            clean[key] = item[key]
        for key in ('completed_prefix','decode_end_ns','completed_prefix_start','completed_prefix_end'):
            if key in item:
                _require(_ns(item[key]), 'native_journal_invalid')
                clean[key] = item[key]
        for key in ('stable_prefix','inflight_start','inflight_end'):
            if key in item:
                _require(type(item[key]) is bool, 'native_journal_invalid')
                clean[key] = item[key]
        _require(clean['capture_start_ns'] <= clean['capture_end_ns']
                 and ('decode_end_ns' not in clean or clean['capture_end_ns'] <= clean['decode_end_ns']),
                 'native_journal_invalid')
        selected.append(clean)
    return selected


def _images(value):
    _require(type(value) is list and len(value) <= MAX_IMAGES, 'invalid_native_images')
    total = 0
    seen = set()
    images = []
    for item in value:
        _require(type(item) is dict, 'invalid_native_images')
        name = item.get('name')
        _require(type(name) is str and re.fullmatch('[a-z][a-z0-9_-]{0,63}\\.png', name)
                 and name not in seen and item.get('format') == 'png'
                 and type(item.get('pixel_width')) is int and item['pixel_width'] == 896
                 and type(item.get('pixel_height')) is int and item['pixel_height'] == 414,
                 'invalid_native_images')
        seen.add(name)
        try:
            raw = b64(item.get('data_base64'), MAX_IMAGE)
        except ProbeError:
            raise ProbeError('invalid_native_images') from None
        total += len(raw)
        _require(total <= MAX_TOTAL_IMAGES and len(raw) >= 24
                 and raw[:16] == b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
                 and struct.unpack('>II', raw[16:24]) == (896, 414), 'invalid_native_images')
        digest = hashlib.sha256(raw).hexdigest()
        _require(item.get('sha256') == digest, 'invalid_native_images')
        meta = {'name': name, 'format': 'png', 'pixel_width': 896, 'pixel_height': 414,
                'sha256': digest, 'bytes': len(raw)}
        for key in ('capture_id', 'capture_start_ns', 'capture_end_ns'):
            number_value = item.get(key)
            _require(type(number_value) is int and 0 <= number_value < 2**63, 'invalid_native_images')
            meta[key] = number_value
        if 'completed_prefix' in item:
            _require(type(item['completed_prefix']) is int and 0 <= item['completed_prefix'] < 2**63,
                     'invalid_native_images')
            meta['completed_prefix'] = item['completed_prefix']
        if 'stable_prefix' in item:
            _require(type(item['stable_prefix']) is bool, 'invalid_native_images')
            meta['stable_prefix'] = item['stable_prefix']
        for key in ('decode_end_ns', 'completed_prefix_start', 'completed_prefix_end'):
            if key in item:
                _require(type(item[key]) is int and 0 <= item[key] < 2**63, 'invalid_native_images')
                meta[key] = item[key]
        for key in ('inflight_start', 'inflight_end'):
            if key in item:
                _require(type(item[key]) is bool, 'invalid_native_images')
                meta[key] = item[key]
        _require(meta['capture_start_ns'] <= meta['capture_end_ns'], 'invalid_native_images')
        _require('decode_end_ns' not in meta or meta['capture_end_ns'] <= meta['decode_end_ns'],
                 'invalid_native_images')
        images.append((meta, raw))
    return images


def run_session(client, output, *, cancelled=lambda: False, clock=time.monotonic_ns,
                sleep=time.sleep, poll_seconds=.25, max_seconds=185, recovery_seconds=6,
                lock_path=None):
    """Start once; recover known work with read-only status and bounded cancel."""
    number(poll_seconds, .001, 1)
    number(max_seconds, .01, 200)
    number(recovery_seconds, .01, 10)
    base = Path(output).resolve()
    base.mkdir(mode=0o700, parents=True, exist_ok=True)
    with device_lock(lock_path):
        record = _load(base)
        if record is None or record['resolved']:
            record = {'schema': 'ngg2-host-v1', 'revision': REVISION, 'run_id': uuid.uuid4().hex,
                      'profile': PROFILE, 'state': 'prepared', 'resolved': False,
                      'start_attempted': False, 'cancel_attempted': False, 'cancel_attempts': 0,
                      'cancel_confirmed': False, 'stop_reason': None, 'events_dropped': 0,
                      'native_state': None, 'native_report': None, 'images': [], 'result_metadata': {},
                      'host_clock_domain': 'python.monotonic_ns',
                      'native_clock_domain': 'device.monotonic_ns', 'events': []}
        recovering = record['start_attempted']
        run_id = record['run_id']
        invocation = uuid.uuid4().hex
        began = clock()
        deadline = began + int(max_seconds * 1e9)
        readiness_deadline = min(deadline, began + SCHEMA_BUDGET_NS)
        cleanup_deadline = None
        cancel_required = record['cancel_attempted']
        status_before_retry = False
        cancel_calls = 0

        def event(method, error=None, timings=None):
            row = {'invocation': invocation, 'method': method, 'host_ns': clock(), 'error': error}
            if timings:
                row['host_timings'] = {key: value for key, value in timings.items()
                                       if key.endswith('_ns') and type(value) is int and 0 <= value < 2**63}
            record['events'].append(row)
            excess = max(0, len(record['events']) - MAX_HTTP_EVENTS)
            if excess:
                del record['events'][:excess]
                record['events_dropped'] += excess

        def request(method, params):
            try:
                reply = client.call(method, params)
                event(method, timings=reply.timings)
                return reply.result
            except ProbeError as exc:
                event(method, _error(exc))
                raise

        def accept(value):
            state, report = _status(value, run_id)
            record.update(state=state, native_state=state, native_report=report)
            if state in TERMINAL or report.get('cancel_requested') is True:
                record['cancel_confirmed'] = True

        def stop(reason):
            nonlocal cleanup_deadline, cancel_required
            cancel_required = True
            record['stop_reason'] = record['stop_reason'] or reason
            if cleanup_deadline is None:
                cleanup_deadline = clock() + int(recovery_seconds*1e9)

        def cancel_attempt(persist=True):
            nonlocal cancel_calls, status_before_retry
            if (not record['start_attempted'] or record['cancel_confirmed']
                    or record['cancel_attempts'] >= MAX_CANCEL_ATTEMPTS):
                return
            record['cancel_attempted'] = True
            record['cancel_attempts'] += 1
            save_error = None
            if persist:
                try:
                    _save(base, record)
                except OSError as exc:
                    save_error = exc
            # A failed cancellation checkpoint cannot prevent this idempotent RPC.
            cancel_calls += 1
            status_before_retry = True
            try:
                accept(request('necro_native_cancel', {'run_id': run_id}))
                record['cancel_confirmed'] = True
            except ProbeError:
                record['state'] = 'unknown'
            if save_error is not None:
                raise save_error

        def status():
            keepalive = not recovering and not cancel_required and not cancelled()
            return request('necro_native_status', {'run_id': run_id, 'keepalive': keepalive})

        def readiness_check():
            if cancelled():
                raise ProbeError('cancel_requested')
            now = clock()
            if now >= deadline or now >= readiness_deadline:
                raise ProbeError('host_deadline')
            return now

        def start_admission():
            try:
                return readiness_check()
            except ProbeError as exc:
                raise _StartNotSent(exc.code) from None

        def schema_readiness():
            prepared = {'schema':'ngg2-connect-v1', 'started_ns':began, 'deadline_ns':readiness_deadline,
                        'state':'pending', 'attempts':[], 'server':None}
            record['preflight'] = prepared
            for attempt in range(1, MAX_SCHEMA_ATTEMPTS+1):
                start = readiness_check()
                timeout = min(2, client.timeout, (deadline-start)/1e9, (readiness_deadline-start)/1e9)
                if timeout < .001:
                    raise ProbeError('host_deadline')
                failure = None
                try:
                    prepared['server'] = client.read_server_schema(timeout)
                except ProbeError as exc:
                    failure = exc
                    prepared['server'] = getattr(client, 'last_server_schema', None)
                diagnostic = client.transport.last_diagnostic
                if diagnostic is None:
                    diagnostic = {'stage':'connect', 'kind':'deadline' if failure is not None
                                  and failure.code == 'rpc_deadline' else 'io_error',
                                  'errno':None, 'status':None, 'started_ns':start, 'ended_ns':clock()}
                diagnostic = _diagnostic(diagnostic)
                error = _error(failure)
                if failure is None:
                    error = None
                elif re.fullmatch(r'http_status_[0-9]{3}', failure.code):
                    error = 'schema_http_status'
                prepared['attempts'].append({'attempt':attempt, 'started_ns':start, 'ended_ns':clock(),
                                             'error':error, 'diagnostic':diagnostic})
                if failure is None:
                    prepared['state'] = 'ready'
                _save(base, record)
                readiness_check()
                if failure is None:
                    return
                if not (failure.code == 'rpc_deadline' or diagnostic['kind'] in RETRY_KINDS):
                    raise ProbeError(error)
                if attempt == MAX_SCHEMA_ATTEMPTS:
                    raise ProbeError(error)
                retry_at = min(clock()+500_000_000, readiness_deadline, deadline)
                while True:
                    now = readiness_check()
                    if now >= retry_at:
                        break
                    sleep(min(.05, (retry_at-now)/1e9))
                readiness_check()

        try:
            _save(base, record)
            if not recovering:
                schema_readiness()
                readiness_check()
                # A prepared journal with this bit false has never issued start.
                # The same UUID may make its first attempt after capability checks.
                record['start_attempted'] = True
                _save(base, record)
                start_admission()
                try:
                    start_admission()
                    client._before_start_post = start_admission
                    accept(request('necro_native_start', {'run_id': run_id, 'profile': PROFILE}))
                except _StartNotSent:
                    raise
                except ProbeError as exc:
                    record['state'] = 'unknown'
                    stop(_error(exc))
                finally:
                    client._before_start_post = None
                _save(base, record)
            else:
                # device_info is a UI method rejected by the active native lease.
                # Recovery must go directly to the authenticated native endpoints.
                try:
                    accept(status())
                except ProbeError as exc:
                    record['state'] = 'unknown'
                    stop(_error(exc))
                if record['state'] not in TERMINAL:
                    stop('cancel_requested')

            while True:
                if cancelled():
                    stop('cancel_requested')
                if clock() >= deadline:
                    stop('host_deadline')
                if (cancel_required and record['state'] not in TERMINAL
                        and not status_before_retry):
                    cancel_attempt()
                if record['state'] in TERMINAL:
                    try:
                        value = request('necro_native_results', {'run_id': run_id})
                        state, report = _status(value, run_id)
                        _require(state in TERMINAL, 'invalid_native_status')
                        images = _images(value.get('images'))
                        image_folder = base/('native-'+run_id)/'images'
                        image_folder.mkdir(mode=0o700, exist_ok=True)
                        for metadata, raw in images:
                            _atomic(image_folder/metadata['name'], raw)
                        result_metadata = _result_metadata(value)
                        record.update(state=state, native_state=state, native_report=report,
                                      images=[metadata for metadata, _raw in images],
                                      result_metadata=result_metadata,
                                      resolved=report['input_state'] in (0, 3)
                                      and not report.get('ui_frozen', False)
                                      and report.get('workers_drained', True)
                                      and not report.get('native_inflight', False))
                        if not record['resolved']:
                            record['stop_reason'] = 'native_input_unresolved'
                    except ProbeError as exc:
                        record['stop_reason'] = _error(exc)
                        record['resolved'] = False
                    break
                if cleanup_deadline is not None and clock() >= cleanup_deadline:
                    break
                sleep(poll_seconds)
                try:
                    accept(status())
                except ProbeError as exc:
                    record['state'] = 'unknown'
                    stop(_error(exc))
                status_before_retry = False
                _save(base, record)
        except _StartNotSent as exc:
            record.update(stop_reason=_error(exc), state='stopped', resolved=True, native_state=None)
        except ProbeError as exc:
            record['stop_reason'] = _error(exc)
            if not recovering and 'preflight' in record and record['preflight']['state'] != 'ready':
                record['preflight']['state'] = 'cancelled' if exc.code == 'cancel_requested' else 'failed'
            if not record['start_attempted']:
                record.update(state='stopped', resolved=True)
            else:
                record.update(state='unknown', resolved=False)
        except OSError:
            # The initial recovery save and the cancel-intent save are covered.
            # RAM intent is distinct from a cancel call that was actually attempted.
            if record['start_attempted'] and cancel_calls == 0:
                cancel_attempt(persist=False)
            raise
        _save(base, record)
        return record


def parser():
    ap = argparse.ArgumentParser(description='TEST044: 接続準備を確認してNG-G2端末内制御を実行')
    ap.add_argument('--output', default='runtime/test-044')
    ap.add_argument('--token-store', default=str(Path.home()/'.loopctrl/token.json'))
    ap.add_argument('--store-key')
    ap.add_argument('--python-crypto', action='store_true')
    ap.add_argument('--check', action='store_true', help='軽量クライアントの版だけを確認')
    return ap


def main(argv=None):
    args = parser().parse_args(argv)
    if args.check:
        print(REVISION + ' / ' + API_VERSION)
        return 0
    stopped = [False]
    def stop(_signum, _frame):
        stopped[0] = True
    previous = {sig: signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        key, tok = load_pairing(args.token_store, args.store_key)
        with OwnedRpcTimer() as timer:
            client = NativeClient(HttpTransport(), key, tok, timeout=2,
                                  crypto=Crypto(native=not args.python_crypto), deadline_owner=timer)
            record = run_session(client, args.output, cancelled=lambda: stopped[0])
        print('NG-G2終了: ' + record['state'] + ' / ' + (record['stop_reason'] or 'none'))
        print('保存先: ' + str(Path(args.output).resolve()/('native-'+record['run_id'])))
        if not record['start_attempted'] and record['stop_reason'] != 'cancel_requested':
            attempts = record.get('preflight', {}).get('attempts', [])
            kind = attempts[-1]['diagnostic']['kind'] if attempts else None
            if record['stop_reason'] == 'native_capability_missing':
                print('NG-G2の版・機能が一致しません。build20のIPAとLoopCtrlの起動状態を確認してください。')
            elif kind == 'refused':
                print('LoopCtrlへの接続が拒否されました。まだゲームの開始要求は送っていません。')
            elif record['stop_reason'] in ('rpc_deadline', 'host_deadline') or kind in ('timeout','deadline'):
                print('LoopCtrlの接続準備待ちが期限に達しました。まだゲームの開始要求は送っていません。')
            else:
                print('LoopCtrlの接続準備を確認できず停止しました。まだゲームの開始要求は送っていません。')
            print('LoopCtrlを開いて「Start Server」を押し、いつものVPN/ディスクイメージ接続を確認してから再実行してください。')
        if not record['resolved']:
            print('入力・終了結果は未確定です。同じ実行IDを保持しています。手動でゲームを確認してください。')
        return 0 if record['resolved'] and record['native_state'] == 'completed' else 2
    except (ProbeError, OSError) as exc:
        reason = exc.code if isinstance(exc, ProbeError) and exc.code in (
            'pairing_missing', 'pairing_ambiguous', 'invalid_pairing_record', 'already_running',
            'native_journal_invalid', 'timer_already_in_use', 'timer_handler_in_use',
            'timer_unusable', 'timer_setup_failed') else 'client_failed'
        print('TEST044停止: ' + reason, file=sys.stderr)
        return 2
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


if __name__ == '__main__':
    raise SystemExit(main())
