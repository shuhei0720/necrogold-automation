"""NG-G2専用の軽量な開始・状態・取消・結果回収クライアント。"""
import argparse
from contextlib import contextmanager
import errno
import fcntl
import hashlib
import json
import math
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
from .protocol import Client, RPC_STAGES
from .protocol import HttpTransport, load_pairing
from .validation import ProbeError, b64, json_object, number

REVISION = 'native-walk-v14'
API_VERSION = '1.98.15-ngg2'
CAPABILITY = 'necrogold_native_v13'
PROFILE = 'normal-1-1-v1'
MAX_IMAGE = 512 * 1024
MAX_IMAGES = 20
MAX_TOTAL_IMAGES = 4 * 1024 * 1024
MAX_HTTP_EVENTS = 128
MAX_CAPTURES = 256
MAX_NATIVE_EVENTS = 64
MAX_RASTER_SAMPLES = 32
MAX_CANCEL_ATTEMPTS = 3
MAX_SCHEMA = 512 * 1024
MAX_MANIFEST_WIRE = 512 * 1024
MAX_CHUNK_WIRE = 256 * 1024
CHUNK_BYTES = 64 * 1024
EXPORT_BATCH_CHUNKS = 4
EXPORT_BATCH_BYTES = 256 * 1024
LEGACY_REVISIONS = frozenset('native-walk-v'+str(version) for version in range(1,14))
PAGED_REVISIONS = frozenset(('native-walk-v9', 'native-walk-v10', 'native-walk-v11', 'native-walk-v12', 'native-walk-v13', REVISION))
BATCHED_REVISIONS = frozenset(('native-walk-v10', 'native-walk-v11', 'native-walk-v12', 'native-walk-v13', REVISION))
MOTION_REFERENCE_REVISIONS = frozenset(('native-walk-v12', 'native-walk-v13', REVISION))
RECOVERY_REVISIONS = frozenset((REVISION,))
_HTTP_TRANSPORT_TYPE = HttpTransport
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
    'decode_end_ns', 'analysis_start_ns', 'analysis_end_ns', 'observe_start_ns', 'observe_end_ns', 'completed_prefix_start',
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
CAPTURE_FAILURE_CODES = {
    'interval': frozenset(('invalid_interval',)),
    'reply': frozenset(('api_unavailable', 'session_unavailable', 'display_unprepared',
        'request_unavailable', 'capture_failed', 'bytes_invalid', 'reply_exception',
        'request_exception', 'missing_data', 'other')),
    'source': frozenset(('encoded_empty', 'encoded_limit', 'source_open', 'image_count', 'image_create')),
    'metadata': frozenset(('orientation', 'source_geometry', 'aspect')),
    'normalize': frozenset(('render_failed', 'orientation_copy')),
    'analysis': frozenset(('invalid_rgba',)),
}
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
        ceiling = min(self.timeout, 8 if method == 'necro_native_results' else 2)
        timeout = ceiling if timeout is None else number(timeout, .001, ceiling)
        guard = getattr(self, '_before_start_post', None)
        mode = params.get('mode') if method == 'necro_native_results' and type(params) is dict else None
        limit = {'manifest': MAX_MANIFEST_WIRE, 'chunk': MAX_CHUNK_WIRE}.get(mode) if type(mode) is str else None
        if limit is None and (method != 'necro_native_start' or guard is None):
            return super().call(method, params, timeout=timeout)
        transport = self.transport
        def guarded_post(body, rpc_timeout):
            if method == 'necro_native_start' and guard is not None:
                try:
                    guard()
                except ProbeError as exc:
                    raise _StartNotSent(exc.code) from None
            if limit is not None and isinstance(transport, _HTTP_TRANSPORT_TYPE):
                # Admission precedes body JSON, authentication and response crypto.
                return transport._exchange('POST', '/rpc', body, rpc_timeout, limit)
            raw = transport(body, rpc_timeout)
            if limit is not None:
                _require(type(raw) is bytes and len(raw) <= limit, 'http_body_limit')
            return raw
        self.transport = guarded_post
        try:
            return super().call(method, params, timeout=timeout)
        finally:
            self.transport = transport

    def _validate(self, method, params):
        expected = ({'run_id', 'profile'} if method == 'necro_native_start'
                    else {'run_id', 'keepalive'} if method == 'necro_native_status' else {'run_id'})
        if method == 'necro_native_results' and type(params) is dict and 'mode' in params:
            if params['mode'] == 'manifest':
                expected = {'run_id', 'mode'}
            elif params['mode'] == 'chunk':
                expected = {'run_id', 'mode', 'export_id', 'capture_id', 'offset'}
                _require(_uuid(params.get('export_id')) and _ns(params.get('capture_id'))
                         and type(params.get('offset')) is int and 0 <= params['offset'] < MAX_IMAGE,
                         'method_not_allowed')
            else:
                raise ProbeError('method_not_allowed')
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


def _revision_api(revision):
    # A started journal retains its original protocol, including ready preflight.
    _require(revision in LEGACY_REVISIONS | {REVISION}, 'native_journal_invalid')
    return '1.98.14-ngg2' if revision in LEGACY_REVISIONS else API_VERSION


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


def _preflight(value, *, api_version=API_VERSION):
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
                 and server.get('server_version') in (api_version, 'other')
                 and type(server.get('protocol_version')) is int and server['protocol_version'] == 1
                 and type(server.get('native_capability')) is bool
                 and ('build' not in server or _build_stamp(server['build']) == server['build']),
                 'native_journal_invalid')
    if value['state'] == 'ready':
        _require(rows and rows[-1]['error'] is None and server is not None
                 and server['server_version'] == api_version and server['native_capability'],
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
        if 'rpc_stage' in row:
            _require(type(row['rpc_stage']) is str and row['rpc_stage'] in RPC_STAGES,
                     'native_journal_invalid')
            clean['rpc_stage'] = row['rpc_stage']
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
        optional = {'cancel_attempts', 'cancel_confirmed', 'events_dropped', 'result_metadata', 'preflight',
                    'image_export'}
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
        api_version = _revision_api(record.get('revision'))
        _require(record.get('host_clock_domain') == 'python.monotonic_ns'
                 and record.get('native_clock_domain') == 'device.monotonic_ns', 'native_journal_invalid')
        if 'preflight' in record:
            record['preflight'] = _preflight(record['preflight'], api_version=api_version)
        _require(record['state'] in STATES | {'prepared', 'unknown'}
                 and record['native_state'] in STATES | {None}
                 and record['stop_reason'] in ERROR_CODES | {None}, 'native_journal_invalid')
        if record['native_report'] is not None:
            record['native_report'] = _report(record['native_report'],
                require_motion_references=record['revision'] in MOTION_REFERENCE_REVISIONS,
                require_recovery=record['revision'] in RECOVERY_REVISIONS)
        _require(_result_metadata(record['result_metadata'], api_version=api_version)
                 == record['result_metadata'], 'native_journal_invalid')
        record['images'] = _stored_images(record['images'])
        if 'image_export' in record:
            _require(record['revision'] in PAGED_REVISIONS, 'native_journal_invalid')
            record['image_export'] = _export_checkpoint(record['image_export'])
            selected = {item['name']:item for item in record['image_export']['images']}
            _require(all(selected.get(item['name']) == item for item in record['images']),
                     'native_journal_invalid')
        return record
    except (OSError, ProbeError, ValueError, TypeError, RecursionError):
        raise ProbeError('native_journal_invalid') from None


def _scene_changes(value):
    keys = ('command_id', 'source_capture_id', 'observed_capture_id', 'change_mask',
        'changed_tiles', 'changed_protected', 'state_before', 'state_after',
        'goods_before', 'goods_after', 'replan_count', 'replan_allowed', 'target_ns', 'deadline_ns')
    _require(type(value) is list and len(value) <= 3, 'invalid_native_report')
    rows = []
    limits = {'change_mask':(1,15), 'changed_tiles':(0,230), 'changed_protected':(0,230),
        'state_before':(0,2), 'state_after':(0,2), 'goods_before':(0,2),
        'goods_after':(0,2), 'replan_count':(0,2)}
    for row in value:
        _require(type(row) is dict and set(keys) <= set(row), 'invalid_native_report')
        clean = {}
        for key in keys:
            item = row[key]
            if key == 'replan_allowed':
                _require(type(item) is bool, 'invalid_native_report')
            else:
                low, high = limits.get(key, (0,2**63-1))
                _require(type(item) is int and low <= item <= high, 'invalid_native_report')
            clean[key] = item
        rows.append(clean)
    return rows


def _scene_change_details(value):
    keys = ('command_id','source_capture_id','observed_capture_id','validation','continuous_count',
            'chain_count','cell_count','omitted_cells','cells')
    limits = {'validation':(0,12), 'continuous_count':(0,8), 'chain_count':(0,2),
              'cell_count':(0,4), 'omitted_cells':(0,226)}
    cell_limits = {'x':(-11,11), 'y':(-5,4), 'tile_before':(0,6), 'tile_after':(0,6),
                   'protected_before':(0,1), 'protected_after':(0,1)}
    _require(type(value) is list and len(value) <= 3, 'invalid_native_report')
    rows = []
    for row in value:
        _require(type(row) is dict and set(keys) <= set(row), 'invalid_native_report')
        clean = {}
        for key in keys[:-1]:
            low, high = limits.get(key, (0,2**63-1))
            _require(type(row[key]) is int and low <= row[key] <= high, 'invalid_native_report')
            clean[key] = row[key]
        _require(type(row['cells']) is list and len(row['cells']) == clean['cell_count']
                 and clean['cell_count']+clean['omitted_cells'] <= 230
                 and (clean['omitted_cells'] == 0 or clean['cell_count'] == 4),
                 'invalid_native_report')
        cells = []
        positions = []
        for cell in row['cells']:
            _require(type(cell) is dict and set(cell_limits) <= set(cell), 'invalid_native_report')
            for key,(low,high) in cell_limits.items():
                _require(type(cell[key]) is int and low <= cell[key] <= high, 'invalid_native_report')
            _require(cell['tile_before'] != cell['tile_after']
                     or cell['protected_before'] != cell['protected_after'], 'invalid_native_report')
            cells.append({key:cell[key] for key in cell_limits})
            positions.append((cell['y']+5)*23+cell['x']+11)
        _require(positions == sorted(set(positions)), 'invalid_native_report')
        clean['cells'] = cells
        rows.append(clean)
    return rows


def _motion_wait(value):
    keys = ('command_id', 'source_capture_id', 'last_capture_id', 'deadline_ns',
            'attempts', 'last_motion', 'active')
    _require(type(value) is dict and set(keys) <= set(value), 'invalid_native_report')
    for key in keys[:-1]:
        _require(_ns(value[key]), 'invalid_native_report')
    _require(value['attempts'] <= 3 and value['last_motion'] <= 7
             and type(value['active']) is bool, 'invalid_native_report')
    return {key:value[key] for key in keys}


def _raster_samples(value):
    keys = ('capture_id', 'source_width', 'source_height', 'orientation',
            'source_ns', 'draw_ns', 'orient_ns', 'scale_ns', 'copy_pixels')
    _require(type(value) is list and len(value) <= MAX_RASTER_SAMPLES, 'invalid_native_report')
    rows, seen = [], set()
    for row in value:
        _require(type(row) is dict and set(keys) <= set(row)
                 and all(_ns(row[key]) for key in keys), 'invalid_native_report')
        width, height, orientation = row['source_width'], row['source_height'], row['orientation']
        _require(0 < row['capture_id'] and row['capture_id'] not in seen
                 and 1 <= width <= 4096 and 1 <= height <= 4096
                 and width * height <= 8_000_000 and 1 <= orientation <= 8
                 and row['copy_pixels'] <= width * height, 'invalid_native_report')
        oriented_width, oriented_height = (height, width) if orientation >= 5 else (width, height)
        _require(oriented_width * 414 == oriented_height * 896
                 and sum(row[key] for key in ('source_ns','draw_ns','orient_ns','scale_ns')) < 2**63,
                 'invalid_native_report')
        seen.add(row['capture_id'])
        rows.append({key:row[key] for key in keys})
    return rows


def _capture_failure(value):
    if value is None:
        return None
    keys = ('capture_id', 'stage', 'code', 'start_ns', 'end_ns', 'encoded_bytes',
            'source_width', 'source_height', 'orientation')
    _require(type(value) is dict and set(keys) <= set(value), 'invalid_native_report')
    _require(type(value['stage']) is str and type(value['code']) is str
             and value['code'] in CAPTURE_FAILURE_CODES.get(value['stage'], ()), 'invalid_native_report')
    for key in ('capture_id', 'start_ns', 'end_ns'):
        _require(_ns(value[key]), 'invalid_native_report')
    _require(value['encoded_bytes'] is None or _ns(value['encoded_bytes']), 'invalid_native_report')
    for key in ('source_width', 'source_height', 'orientation'):
        item = value[key]
        _require(item is None or type(item) is int and -(2**31) <= item < 2**31, 'invalid_native_report')
    return {key:value[key] for key in keys}


def _dispatch_failure(value):
    if value is None:
        return None
    keys = ('command_id', 'not_before_ns', 'deadline_ns', 'query_start_ns',
            'query_end_ns', 'main_entry_ns', 'gate_ns', 'code')
    _require(type(value) is dict and set(keys) <= set(value), 'invalid_native_report')
    _require(type(value['code']) is str and value['code'] in (
        'foreground', 'locked', 'owner', 'authority_stale', 'too_early',
        'too_late', 'controller_rejected'), 'invalid_native_report')
    for key in keys[:3]:
        _require(_ns(value[key]), 'invalid_native_report')
    for key in keys[3:-1]:
        _require(value[key] is None or _ns(value[key]), 'invalid_native_report')
    return {key:value[key] for key in keys}


def _motion_references(value):
    keys = ('command_id', 'authority_capture_id', 'reference_capture_id',
            'reference_start_ns', 'reference_prefix', 'observed_capture_id',
            'reference_eligible', 'primary_motion', 'fallback_attempted',
            'fallback_motion', 'selected_capture_id', 'selected_motion')
    flags = ('reference_eligible', 'fallback_attempted')
    motions = ('primary_motion', 'fallback_motion', 'selected_motion')
    _require(type(value) is list and len(value) <= 16, 'invalid_native_report')
    rows = []
    for row in value:
        _require(type(row) is dict and set(row) == set(keys), 'invalid_native_report')
        for key in keys:
            item = row[key]
            if key in flags:
                _require(type(item) is bool, 'invalid_native_report')
            elif key in motions:
                _require(type(item) is int and 0 <= item <= 7, 'invalid_native_report')
            else:
                _require(_ns(item), 'invalid_native_report')
        _require(row['command_id'] > 0 and row['authority_capture_id'] > 0
                 and row['selected_capture_id'] > 0, 'invalid_native_report')
        if row['reference_capture_id'] == 0:
            _require(row['reference_start_ns'] == row['reference_prefix'] == 0
                     and not row['reference_eligible'], 'invalid_native_report')
        if row['reference_eligible']:
            _require(0 < row['reference_capture_id'] < row['authority_capture_id'],
                     'invalid_native_report')
        if row['observed_capture_id'] == 0:
            _require(not row['fallback_attempted']
                     and row['primary_motion'] == row['fallback_motion'] == row['selected_motion'] == 0
                     and row['selected_capture_id'] == row['authority_capture_id'],
                     'invalid_native_report')
        else:
            fallback = row['primary_motion'] == 0 and row['reference_eligible']
            _require(row['fallback_attempted'] == fallback
                     and (fallback or row['fallback_motion'] == 0), 'invalid_native_report')
            selected_fallback = fallback and row['fallback_motion'] == 1
            _require(row['selected_capture_id'] == row['reference_capture_id' if selected_fallback
                         else 'authority_capture_id']
                     and row['selected_motion'] == (1 if selected_fallback else row['primary_motion']),
                     'invalid_native_report')
        rows.append({key:row[key] for key in keys})
    _require(len({row['command_id'] for row in rows}) == len(rows), 'invalid_native_report')
    return rows


def _motion_reference_events(report):
    events = report.get('events')
    _require(type(events) is list, 'invalid_native_report')
    moves, ack_ids, previous_ack = [], set(), 0
    for event in events:
        if event.get('outcome') == 2:
            _require(event.get('kind') in (1, 2, 3, 4) and _ns(event.get('id'))
                     and event['id'] > previous_ack and event['id'] not in ack_ids,
                     'invalid_native_report')
            if event['kind'] == 4:
                moves.append((event, previous_ack))
            ack_ids.add(event['id'])
            previous_ack = event['id']
    rows = report['motion_references']
    _require([row['command_id'] for row in rows] == [event['id'] for event, _ in moves],
             'invalid_native_report')
    for row, (event, prefix) in zip(rows, moves):
        _require(row['authority_capture_id'] == event.get('source_capture_id')
                 and row['selected_motion'] == event.get('motion'), 'invalid_native_report')
        observed = event.get('observed_capture_id')
        _require(_ns(observed), 'invalid_native_report')
        if row['observed_capture_id'] != observed:
            # Goods names its holding frame in the existing event before the
            # visual time gate. An early/late goods frame is not a new motion
            # assessment; retain the last actual UNKNOWN/TWEEN (or none).
            _require(report.get('goods') == 1 and event is moves[-1][0]
                     and row['observed_capture_id'] < observed
                     and row['selected_motion'] in (0, 7), 'invalid_native_report')
        if row['reference_capture_id']:
            _require(row['reference_capture_id'] <= row['authority_capture_id']
                     and row['reference_prefix'] == prefix
                     and _ns(event.get('source_start_ns'))
                     and row['reference_start_ns'] <= event['source_start_ns'], 'invalid_native_report')
        if row['observed_capture_id']:
            _require(row['observed_capture_id'] > row['authority_capture_id'], 'invalid_native_report')
        if row['selected_capture_id'] != row['authority_capture_id']:
            direction = event.get('direction')
            _require(direction in (1, 2, 3, 4)
                     and (event.get('dx'), event.get('dy'))
                         == {1:(-1,0), 2:(1,0), 3:(0,-1), 4:(0,1)}[direction],
                     'invalid_native_report')


def _recovery(value):
    keys = ('initial_reacquisitions', 'post_move_reacquisitions', 'episode_id', 'mode',
        'schedule_deadline_ns', 'visual_deadline_ns', 'ack_ns', 'record_count',
        'dropped_records', 'records')
    row_keys = ('sequence', 'episode_id', 'reason', 'clock', 'at_ns', 'capture_id',
        'command_id', 'abandoned_target_ns', 'sync_deadline_ns', 'model', 'samples')
    model_counts = ('period_ns', 'epoch_ns', 'first_ns', 'last_ns', 'gap_ns',
        'prediction_span_ns', 'sample_count', 'mode', 'candidate_count')
    model_doubles = ('residual', 'maximum', 'alternate', 'alias_gap',
        'half_width_max_ns', 'tracking_error', 'extrapolation_budget')
    sample_counts = ('start_ns', 'end_ns', 'midpoint_ns')
    sample_doubles = ('half_width_ns', 'q', 'spacing', 'center')
    def finite(item):
        return (type(item) in (int, float) and -sys.float_info.max <= item <= sys.float_info.max
                and math.isfinite(item))
    def scalars(item, counts, doubles):
        _require(type(item) is dict and set(item) == set(counts+doubles)
                 and all(_ns(item[key]) for key in counts)
                 and all(finite(item[key]) for key in doubles), 'invalid_native_report')
        return dict(item)
    _require(type(value) is dict and set(value) == set(keys)
             and all(_ns(value[key]) for key in keys[:-1]) and value['mode'] <= 2
             and type(value['records']) is list
             and len(value['records']) == min(value['record_count'], 2)
             and value['dropped_records'] == value['record_count']-len(value['records']),
             'invalid_native_report')
    records = []
    for index, row in enumerate(value['records']):
        _require(type(row) is dict and set(row) == set(row_keys)
                 and all(_ns(row[key]) for key in row_keys[:-2])
                 and row['sequence'] == (1 if index == 0 else value['record_count'])
                 and row['episode_id'] <= value['episode_id']
                 and 1 <= row['reason'] <= 8 and 1 <= row['clock'] <= 3
                 and type(row['samples']) is list and len(row['samples']) <= 13,
                 'invalid_native_report')
        model = scalars(row['model'], model_counts, model_doubles)
        _require(model['sample_count'] <= 13 and model['mode'] <= 2, 'invalid_native_report')
        samples = []
        for item in row['samples']:
            sample = scalars(item, sample_counts, sample_doubles)
            _require(sample['start_ns'] < sample['end_ns']
                     and sample['midpoint_ns'] == sample['start_ns']+(sample['end_ns']-sample['start_ns'])//2
                     and sample['half_width_ns'] == (sample['end_ns']-sample['start_ns'])/2
                     and 0 <= sample['q'] < 1 and 90 <= sample['spacing'] <= 120
                     and 440 <= sample['center'] <= 452, 'invalid_native_report')
            samples.append(sample)
        records.append(dict(row, model=model, samples=samples))
    return dict(value, records=records)


def _report(value, depth=0, *, require_motion_references=False, require_recovery=False):
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
        elif key == 'scene_changes':
            result[key] = _scene_changes(item)
        elif key == 'scene_change_details':
            result[key] = _scene_change_details(item)
        elif key == 'motion_wait':
            result[key] = _motion_wait(item)
        elif key == 'motion_references':
            _require(depth == 0, 'invalid_native_report')
            result[key] = _motion_references(item)
        elif key == 'recovery':
            _require(depth == 0, 'invalid_native_report')
            result[key] = _recovery(item)
        elif key == 'raster_samples':
            result[key] = _raster_samples(item)
        elif key == 'raster_samples_dropped':
            _require(_ns(item), 'invalid_native_report')
            result[key] = item
        elif key == 'capture_failure':
            result[key] = _capture_failure(item)
        elif key == 'dispatch_failure':
            result[key] = _dispatch_failure(item)
        elif key in ID_LIST_KEYS:
            _require(type(item) is list and len(item) <= MAX_CAPTURES
                     and all(type(v) is int and 0 <= v < 2**63 for v in item), 'invalid_native_report')
            result[key] = list(item)
        elif key in FIXED_TEXT:
            _require(item == FIXED_TEXT[key], 'invalid_native_report')
            result[key] = item
    for timing in (('start_ns', 'end_ns', 'decode_end_ns', 'analysis_start_ns', 'analysis_end_ns',
                    'observe_start_ns', 'observe_end_ns'),
                   ('capture_start_ns', 'capture_end_ns', 'decode_end_ns')):
        available = [result[key] for key in timing if key in result]
        _require(available == sorted(available), 'invalid_native_report')
    if depth == 0:
        _require(result.get('schema') == 'ngg2-native-v1' and _uuid(result.get('clock_id'))
                 and 'input_state' in result and 'device_now_ns' in result, 'invalid_native_report')
        _require(not require_motion_references or 'motion_references' in result, 'invalid_native_report')
        _require(not require_recovery or 'recovery' in result, 'invalid_native_report')
        if 'motion_references' in result:
            _motion_reference_events(result)
        if 'scene_change_details' in result and 'scene_changes' in result:
            ids = ('command_id','source_capture_id','observed_capture_id')
            _require([[row[key] for key in ids] for row in result['scene_changes']]
                     == [[row[key] for key in ids] for row in result['scene_change_details']],
                     'invalid_native_report')
    return result


def _status(value, run_id, *, require_motion_references=False, require_recovery=False,
            api_version=API_VERSION):
    _require(type(value) is dict and value.get('run_id') == run_id
             and value.get('profile') == PROFILE and type(value.get('state')) is str
             and value['state'] in STATES,
             'invalid_native_status')
    _require('api_version' not in value or value['api_version'] == api_version, 'invalid_native_status')
    return value['state'], _report(value.get('report'),
        require_motion_references=require_motion_references, require_recovery=require_recovery)


def _result_metadata(value, *, api_version=API_VERSION):
    selected = {key: item for key, item in value.items()
                if key in ('retained_images', 'exported_images', 'omitted_image_count')
                or key in ID_LIST_KEYS}
    result = _report(selected, depth=1)
    if 'api_version' in value:
        _require(value['api_version'] == api_version, 'invalid_native_status')
        result['api_version'] = api_version
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


def _manifest_images(value):
    _require(type(value) is list and len(value) <= MAX_IMAGES, 'invalid_native_images')
    selected = []
    for item in value:
        _require(type(item) is dict and 'data_base64' not in item
                 and type(item.get('byte_length')) is int, 'invalid_native_images')
        selected.append(dict(item, bytes=item['byte_length']))
    try:
        images = _stored_images(selected)
    except ProbeError:
        raise ProbeError('invalid_native_images') from None
    _require(len({item['capture_id'] for item in images}) == len(images), 'invalid_native_images')
    return images


def _export_checkpoint(value):
    keys = {'export_id', 'images', 'total_bytes', 'chunk_bytes', 'offsets', 'prefix_sha256'}
    _require(type(value) is dict and set(value) == keys and _uuid(value.get('export_id'))
             and type(value.get('chunk_bytes')) is int and value['chunk_bytes'] == CHUNK_BYTES
             and type(value.get('total_bytes')) is int
             and 0 <= value['total_bytes'] <= MAX_TOTAL_IMAGES,
             'native_journal_invalid')
    images = _stored_images(value['images'])
    _require(len({item['capture_id'] for item in images}) == len(images)
             and value['total_bytes'] == sum(item['bytes'] for item in images)
             and type(value.get('offsets')) is list and len(value['offsets']) == len(images)
             and type(value.get('prefix_sha256')) is list
             and len(value['prefix_sha256']) == len(images), 'native_journal_invalid')
    for item, offset, digest in zip(images, value['offsets'], value['prefix_sha256']):
        _require(type(offset) is int and 0 <= offset <= item['bytes']
                 and (offset == item['bytes'] or offset % CHUNK_BYTES == 0)
                 and type(digest) is str and re.fullmatch('[0-9a-f]{64}', digest)
                 and (offset != 0 or digest == hashlib.sha256(b'').hexdigest()),
                 'native_journal_invalid')
    return {key: images if key == 'images' else list(value[key]) if key in ('offsets', 'prefix_sha256')
            else value[key] for key in keys}


def _manifest(value, run_id, *, require_motion_references=False, require_recovery=False,
              api_version=API_VERSION):
    state, report = _status(value, run_id, require_motion_references=require_motion_references,
        require_recovery=require_recovery, api_version=api_version)
    _require(state in TERMINAL and value.get('result_mode') == 'manifest'
             and _uuid(value.get('export_id')) and type(value.get('chunk_bytes')) is int
             and value['chunk_bytes'] == CHUNK_BYTES, 'invalid_native_images')
    images = _manifest_images(value.get('images'))
    total = sum(item['bytes'] for item in images)
    _require(type(value.get('total_bytes')) is int and value['total_bytes'] == total,
             'invalid_native_images')
    checkpoint = {'export_id':value['export_id'], 'images':images, 'total_bytes':total,
                  'chunk_bytes':CHUNK_BYTES, 'offsets':[0]*len(images),
                  'prefix_sha256':[hashlib.sha256(b'').hexdigest()]*len(images)}
    return state, report, _result_metadata(value, api_version=api_version), checkpoint


def _read_fragment(path, image_path, offset, digest, byte_length):
    # A rename may have committed bytes just before the journal checkpoint.
    # Keep that uncommitted suffix to compare with the exact same-offset retry.
    selected = path if path.exists() else image_path
    try:
        with selected.open('rb') as handle:
            raw = handle.read(MAX_IMAGE+1)
    except FileNotFoundError:
        _require(offset == 0, 'invalid_native_images')
        raw = b''
    _require(offset <= len(raw) <= byte_length
             and hashlib.sha256(raw[:offset]).hexdigest() == digest,
             'invalid_native_images')
    return raw


def _chunk(value, run_id, export_id, item, offset):
    keys = {'run_id','result_mode','export_id','capture_id','offset','byte_length',
            'data_base64','sha256','chunk_bytes'}
    expected = min(CHUNK_BYTES, item['bytes']-offset)
    _require(type(value) is dict and set(value) == keys and value.get('run_id') == run_id
             and value.get('result_mode') == 'chunk' and value.get('export_id') == export_id
             and type(value.get('capture_id')) is int and value['capture_id'] == item['capture_id']
             and type(value.get('offset')) is int and value['offset'] == offset
             and type(value.get('byte_length')) is int and value['byte_length'] == item['bytes']
             and value.get('sha256') == item['sha256']
             and type(value.get('chunk_bytes')) is int and value['chunk_bytes'] == expected,
             'invalid_native_images')
    try:
        raw = b64(value.get('data_base64'), CHUNK_BYTES)
    except ProbeError:
        raise ProbeError('invalid_native_images') from None
    _require(len(raw) == expected and expected > 0, 'invalid_native_images')
    return raw


def _read_only_terminal(state, report):
    # Missing legacy diagnostics cannot establish a new, longer read-only lease.
    return (state in TERMINAL and report.get('terminal') == 1
            and report.get('input_state') in (0, 3)
            and report.get('workers_drained') is True
            and report.get('ui_frozen') is False
            and report.get('native_inflight') is False)


def _collect_paged(request, base, record, clock, deadline, rpc_seconds, client_timeout,
                   cancelled=lambda: False, progress=None, read_only_clock=None):
    run_id = record['run_id']
    def check():
        _require(not cancelled(), 'cancel_requested')
        remaining = (deadline-clock())/1e9
        _require(remaining >= .001, 'host_deadline')
        return remaining
    def call(params):
        remaining = check()
        return request('necro_native_results', params,
                       timeout=min(client_timeout, rpc_seconds, 8, remaining))
    def show_progress():
        if progress is not None:
            try:
                progress(len(record['images']), len(current['images']))
            except Exception:
                # Display is optional and cannot invalidate durable evidence.
                pass
            check()
    state, report, metadata, incoming = _manifest(call({'run_id':run_id, 'mode':'manifest'}), run_id,
        require_motion_references=record['revision'] in MOTION_REFERENCE_REVISIONS,
        require_recovery=record['revision'] in RECOVERY_REVISIONS,
        api_version=_revision_api(record['revision']))
    if read_only_clock is not None:
        # A terminal status grants time only to the same drained native run.
        # A contradictory manifest cannot spend that time transferring chunks.
        _require(_read_only_terminal(state, report) and report.get('cancel_requested') is not True
                 and report['clock_id'] == read_only_clock,
                 'native_input_unresolved')
    # Manifest validation and storage consume the same bounded export attempt.
    check()
    current = record.get('image_export')
    if current is not None:
        _require(all(current[key] == incoming[key]
                     for key in ('export_id','images','total_bytes','chunk_bytes')),
                 'invalid_native_images')
    else:
        current = incoming
        record['image_export'] = current
    record.update(state=state, native_state=state, native_report=report, result_metadata=metadata)
    _save(base, record)
    check()
    show_progress()
    image_folder = base/('native-'+run_id)/'images'
    image_folder.mkdir(mode=0o700, exist_ok=True)
    fragments = image_folder/'.parts'
    fragments.mkdir(mode=0o700, exist_ok=True)
    verified = {item['name']:item for item in record['images']}
    for index, item in enumerate(current['images']):
        image_path = image_folder/item['name']
        fragment = fragments/(item['name']+'.part')
        offset = current['offsets'][index]
        completed_before = offset == item['bytes'] and verified.get(item['name']) == item
        raw = _read_fragment(fragment, image_path, offset, current['prefix_sha256'][index], item['bytes'])
        prior_raw = raw
        check()
        pending_chunks = 0
        committed_offset = offset
        batch_chunks = EXPORT_BATCH_CHUNKS if record['revision'] in BATCHED_REVISIONS else 1
        def checkpoint():
            nonlocal pending_chunks, committed_offset
            if not pending_chunks:
                return
            # A failed IO propagates directly; never retry an uncertain write.
            # A previous rename can leave an authenticated suffix beyond this
            # cursor. Preserve it on disk until later same-offset replies have
            # also been compared, including across another interrupted replay.
            stored = raw+prior_raw[offset:] if batch_chunks > 1 else raw
            _atomic(fragment, stored)
            current['offsets'][index] = offset
            current['prefix_sha256'][index] = hashlib.sha256(raw).hexdigest()
            _save(base, record)
            committed_offset = offset
            pending_chunks = 0
        while offset < item['bytes']:
            try:
                part = _chunk(call({'run_id':run_id, 'mode':'chunk', 'export_id':current['export_id'],
                                    'capture_id':item['capture_id'], 'offset':offset}),
                              run_id, current['export_id'], item, offset)
                # Keep every renamed-but-uncheckpointed byte available for the
                # same-offset comparison throughout a replayed batched export.
                comparison = prior_raw if batch_chunks > 1 else raw
                suffix = comparison[offset:offset+len(part)]
                _require(part[:len(suffix)] == suffix, 'invalid_native_images')
                raw = raw[:offset]+part
                offset += len(part)
                pending_chunks += 1
                if batch_chunks > 1:
                    check()
                if (pending_chunks >= batch_chunks or offset-committed_offset >= EXPORT_BATCH_BYTES
                        or offset == item['bytes']):
                    checkpoint()
                check()
            except ProbeError:
                # A failed response, cancellation, or deadline still commits
                # only the already authenticated and verified pending prefix.
                checkpoint()
                raise
        _require(len(raw) == item['bytes'] and hashlib.sha256(raw).hexdigest() == item['sha256']
                 and raw[:16] == b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
                 and struct.unpack('>II', raw[16:24]) == (896,414), 'invalid_native_images')
        check()
        if completed_before:
            # Metadata and an end cursor do not prove that the published file
            # still exists. Compare its bounded bytes only after the complete
            # source/prefix/hash/PNG checks above. A fragment-only or changed
            # destination keeps the original atomic publication below.
            try:
                with image_path.open('rb') as handle:
                    published = handle.read(MAX_IMAGE+1)
            except FileNotFoundError:
                published = None
            check()
            if published == raw:
                try:
                    fragment.unlink()
                except FileNotFoundError:
                    pass
                check()
                continue
        _atomic(image_path, raw)
        verified[item['name']] = item
        record['images'] = [verified[entry['name']] for entry in current['images'] if entry['name'] in verified]
        _save(base, record)
        check()
        show_progress()
        try:
            fragment.unlink()
        except FileNotFoundError:
            pass
    check()
    return state, report


def run_session(client, output, *, cancelled=lambda: False, clock=time.monotonic_ns,
                sleep=time.sleep, poll_seconds=.25, max_seconds=185, recovery_seconds=6,
                results_seconds=8, export_seconds=90, lock_path=None, progress=None,
                recovery_notice=None, collection_seconds=300):
    """Start once; recover known work with read-only status and bounded cancel."""
    number(poll_seconds, .001, 1)
    number(max_seconds, .01, 200)
    number(recovery_seconds, .01, 10)
    number(results_seconds, .001, 8)
    number(export_seconds, .001, 90)
    number(collection_seconds, .001, 300)
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
        elif not record['start_attempted'] and record['revision'] != REVISION:
            # No native run exists yet. Its first start uses the current contract.
            record['revision'] = REVISION
            record.pop('preflight', None)
        recovering = record['start_attempted']
        run_id = record['run_id']
        invocation = uuid.uuid4().hex
        began = clock()
        deadline = began + int(max_seconds * 1e9)
        readiness_deadline = min(deadline, began + SCHEMA_BUDGET_NS)
        cleanup_deadline = None
        export_guard = None
        collection_deadline = None
        read_only_clock = None
        cancel_required = record['cancel_attempted']
        status_before_retry = False
        cancel_calls = 0

        def event(method, error=None, timings=None, stage=None):
            row = {'invocation': invocation, 'method': method, 'host_ns': clock(), 'error': error}
            if timings:
                row['host_timings'] = {key: value for key, value in timings.items()
                                       if key in HTTP_TIMING_KEYS and type(value) is int and 0 <= value < 2**63}
            if stage in RPC_STAGES:
                row['rpc_stage'] = stage
            record['events'].append(row)
            excess = max(0, len(record['events']) - MAX_HTTP_EVENTS)
            if excess:
                del record['events'][:excess]
                record['events_dropped'] += excess

        def request(method, params, timeout=None):
            try:
                reply = client.call(method, params, timeout=timeout)
                event(method, timings=reply.timings)
                return reply.result
            except ProbeError as exc:
                failure = getattr(client, 'last_failure', None) or {}
                event(method, _error(exc), timings=failure.get('host_timings'), stage=failure.get('stage'))
                raise

        def accept(value):
            nonlocal collection_deadline, read_only_clock
            state, report = _status(value, run_id,
                require_motion_references=record['revision'] in MOTION_REFERENCE_REVISIONS,
                require_recovery=record['revision'] in RECOVERY_REVISIONS,
                api_version=_revision_api(record['revision']))
            record.update(state=state, native_state=state, native_report=report)
            if state in TERMINAL or report.get('cancel_requested') is True:
                record['cancel_confirmed'] = True
            if (collection_deadline is None and record['revision'] in PAGED_REVISIONS
                    and _read_only_terminal(state, report) and not cancel_required
                    and not record['cancel_attempted'] and report.get('cancel_requested') is not True
                    and not cancelled()):
                # This freezes a separate collection deadline at the first
                # authenticated stop/drain observation, before journal IO.
                collection_deadline = clock() + int(collection_seconds*1e9)
                read_only_clock = report['clock_id']

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
            if recovering and recovery_notice is not None:
                try:
                    recovery_notice()
                except Exception:
                    # Optional display cannot discard the journal or change
                    # which run owns this read-only recovery invocation.
                    pass
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
                if collection_deadline is None:
                    if cancelled():
                        stop('cancel_requested')
                    if clock() >= deadline:
                        stop('host_deadline')
                if (cancel_required and record['state'] not in TERMINAL
                        and not status_before_retry):
                    cancel_attempt()
                if record['state'] in TERMINAL:
                    try:
                        # Mutable/unknown and legacy paths retain their original
                        # game/cleanup deadlines. Proven stop/drain cannot grant
                        # any new input authority, only a finite read-only export.
                        invocation_deadline = cleanup_deadline if cleanup_deadline is not None else deadline
                        if record['revision'] in PAGED_REVISIONS:
                            results_deadline = collection_deadline if collection_deadline is not None else min(
                                invocation_deadline, began+180_000_000_000,
                                clock()+int(export_seconds*1e9))
                            # Preserve the finite result cleanup for an already
                            # cancelled native run; a new cancel stops this export.
                            cancelled_before_export = False if collection_deadline is not None else cancelled()
                            export_cancelled = lambda: not cancelled_before_export and cancelled()
                            export_guard = (results_deadline, export_cancelled)
                            state, report = _collect_paged(request, base, record, clock,
                                results_deadline, results_seconds, client.timeout, export_cancelled,
                                progress, read_only_clock)
                        else:
                            # A started old journal keeps its original protocol.
                            results_deadline = min(invocation_deadline, clock()+int(results_seconds*1e9))
                            remaining = (results_deadline-clock())/1e9
                            _require(remaining >= .001, 'host_deadline')
                            value = request('necro_native_results', {'run_id': run_id},
                                            timeout=min(client.timeout, 8, remaining))
                            state, report = _status(value, run_id,
                                api_version=_revision_api(record['revision']))
                            _require(state in TERMINAL, 'invalid_native_status')
                            images = _images(value.get('images'))
                            image_folder = base/('native-'+run_id)/'images'
                            image_folder.mkdir(mode=0o700, exist_ok=True)
                            for image_metadata, raw in images:
                                _atomic(image_folder/image_metadata['name'], raw)
                            record.update(images=[metadata for metadata, _raw in images],
                                          result_metadata=_result_metadata(value,
                                              api_version=_revision_api(record['revision'])))
                        record.update(state=state, native_state=state, native_report=report,
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
        if export_guard is not None and record['resolved']:
            # A final fsync may finish after the collector's last check. Record
            # that expiry once while retaining every committed image and cursor.
            end, export_cancelled = export_guard
            reason = 'cancel_requested' if export_cancelled() else (
                'host_deadline' if end-clock() < 1_000_000 else None)
            if reason is not None:
                record.update(resolved=False, stop_reason=reason)
                _save(base, record)
        return record


def parser():
    ap = argparse.ArgumentParser(description='TEST061: 同期再取得と移動確認から商品到達を確認')
    ap.add_argument('--output', default='runtime/test-061')
    ap.add_argument('--token-store', default=str(Path.home()/'.loopctrl/token.json'))
    ap.add_argument('--store-key')
    ap.add_argument('--python-crypto', action='store_true')
    ap.add_argument('--check', action='store_true', help='軽量クライアントの版だけを確認')
    return ap


def main(argv=None, *, outcome=None, cancelled=lambda: False):
    args = parser().parse_args(argv)
    if args.check:
        print(REVISION + ' / ' + API_VERSION)
        return 0
    stopped = [False]
    def is_cancelled():
        return stopped[0] or cancelled()
    def stop(_signum, _frame):
        stopped[0] = True
    previous = {sig: signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        key, tok = load_pairing(args.token_store, args.store_key)
        with OwnedRpcTimer() as timer:
            client = NativeClient(HttpTransport(), key, tok, timeout=8,
                                  crypto=Crypto(native=not args.python_crypto), deadline_owner=timer)
            def progress(saved, total):
                print('画像回収中: 保存済み' + str(saved) + '/' + str(total)
                      + '枚。終了表示までお待ちください。', flush=True)
            recovering = [False]
            def recovery_notice():
                recovering[0] = True
                print('前回の結果の回収のみ行います。今回はゲームを起動しません。', flush=True)
            record = run_session(client, args.output, cancelled=is_cancelled, progress=progress,
                                 recovery_notice=recovery_notice)
        if outcome is not None:
            # A storage wrapper owns its completion display after publishing the
            # collected evidence. Preserve pairing, timers and signal handling.
            return outcome(record, is_cancelled())
        report = record['native_report'] or {}
        native_reason = report.get('reason_name') if record['native_state'] in TERMINAL else None
        print('NG-G2終了: ' + record['state'] + ' / '
              + (native_reason or record['stop_reason'] or 'none'))
        if record['native_state'] in TERMINAL:
            print('結果回収: ' + ('完了' if record['resolved'] else '未完了 / '
                  + (record['stop_reason'] or 'native_input_unresolved')))
        else:
            print('結果回収: 未実施')
        if recovering[0] and record['resolved']:
            print('前回の結果の回収完了。次回の実行から新しい試験を開始します。')
        print('保存先: ' + str(Path(args.output).resolve()/('native-'+record['run_id'])))
        if not record['start_attempted'] and record['stop_reason'] != 'cancel_requested':
            attempts = record.get('preflight', {}).get('attempts', [])
            kind = attempts[-1]['diagnostic']['kind'] if attempts else None
            if record['stop_reason'] == 'native_capability_missing':
                print('NG-G2の版・機能が一致しません。TEST054用の新IPAとLoopCtrlの起動状態を確認してください。')
            elif kind == 'refused':
                print('LoopCtrlへの接続が拒否されました。まだゲームの開始要求は送っていません。')
            elif record['stop_reason'] in ('rpc_deadline', 'host_deadline') or kind in ('timeout','deadline'):
                print('LoopCtrlの接続準備待ちが期限に達しました。まだゲームの開始要求は送っていません。')
            else:
                print('LoopCtrlの接続準備を確認できず停止しました。まだゲームの開始要求は送っていません。')
            print('LoopCtrlを開いて「Start Server」を押し、いつものVPN/ディスクイメージ接続を確認してから再実行してください。')
        if not record['resolved']:
            report = record['native_report'] or {}
            if record['native_state'] in TERMINAL and report.get('input_state') in (0,3) \
                    and report.get('workers_drained') is True and not report.get('native_inflight',False):
                print('端末側の停止は確認済みですが、結果の回収は未完了です。同じ実行IDを保持しています。')
            else:
                print('入力・終了結果は未確定です。同じ実行IDを保持しています。手動でゲームを確認してください。')
        return 0 if record['resolved'] and record['native_state'] == 'completed' else 2
    except (ProbeError, OSError) as exc:
        reason = exc.code if isinstance(exc, ProbeError) and exc.code in (
            'pairing_missing', 'pairing_ambiguous', 'invalid_pairing_record', 'already_running',
            'native_journal_invalid', 'timer_already_in_use', 'timer_handler_in_use',
            'timer_unusable', 'timer_setup_failed') else 'client_failed'
        print('TEST054停止: ' + reason, file=sys.stderr)
        return 2
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


if __name__ == '__main__':
    raise SystemExit(main())
