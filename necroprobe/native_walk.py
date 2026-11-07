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

REVISION = 'native-walk-v1'
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
    'native_results_unavailable'))


def _require(value, reason):
    if not value:
        raise ProbeError(reason)


def _uuid(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{32}', value) is not None


def _error(exc):
    return exc.code if isinstance(exc, ProbeError) and exc.code in ERROR_CODES else 'rpc_failed'


class NativeClient(Client):
    def _validate(self, method, params):
        if method == 'device_info' and params == {}:
            return
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
        optional = {'cancel_attempts', 'cancel_confirmed', 'events_dropped', 'result_metadata'}
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
        record['events'] = record['events'][excess:]
        _require(record['state'] in STATES | {'prepared', 'unknown'}
                 and record['native_state'] in STATES | {None}
                 and record['stop_reason'] in ERROR_CODES | {None}, 'native_journal_invalid')
        _require(record['native_report'] is None or _report(record['native_report']) == record['native_report'],
                 'native_journal_invalid')
        _require(_result_metadata(record['result_metadata']) == record['result_metadata'], 'native_journal_invalid')
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
        deadline = clock() + int(max_seconds * 1e9)
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

        try:
            _save(base, record)
            if not recovering:
                info = request('device_info', {})
                _require(info.get('server_version') == API_VERSION
                         and type(info.get('capabilities')) is list and CAPABILITY in info['capabilities'],
                         'native_capability_missing')
                if cancelled():
                    record.update(state='stopped', resolved=True, stop_reason='cancel_requested')
                    _save(base, record)
                    return record
                # A prepared journal with this bit false has never issued start.
                # The same UUID may make its first attempt after capability checks.
                record['start_attempted'] = True
                _save(base, record)
                try:
                    accept(request('necro_native_start', {'run_id': run_id, 'profile': PROFILE}))
                except ProbeError as exc:
                    record['state'] = 'unknown'
                    stop(_error(exc))
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
        except ProbeError as exc:
            record['stop_reason'] = _error(exc)
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
    ap = argparse.ArgumentParser(description='TEST043: NG-G2端末内制御の開始・取消・結果保存')
    ap.add_argument('--output', default='runtime/test-043')
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
        if not record['resolved']:
            print('入力・終了結果は未確定です。同じ実行IDを保持しています。手動でゲームを確認してください。')
        return 0 if record['resolved'] and record['native_state'] == 'completed' else 2
    except (ProbeError, OSError) as exc:
        reason = exc.code if isinstance(exc, ProbeError) and exc.code in (
            'pairing_missing', 'pairing_ambiguous', 'invalid_pairing_record', 'already_running',
            'native_journal_invalid', 'timer_already_in_use', 'timer_handler_in_use',
            'timer_unusable', 'timer_setup_failed') else 'client_failed'
        print('TEST043停止: ' + reason, file=sys.stderr)
        return 2
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


if __name__ == '__main__':
    raise SystemExit(main())
