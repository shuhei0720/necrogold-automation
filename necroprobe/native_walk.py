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
    'started_prefix', 'inflight', 'generation', 'sequence', 'timeout_ns', 'last_heartbeat_ns'))
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
        expected = {'run_id', 'profile'} if method == 'necro_native_start' else {'run_id'}
        if (method not in ('necro_native_start', 'necro_native_status',
                           'necro_native_cancel', 'necro_native_results')
                or type(params) is not dict or set(params) != expected
                or type(params.get('run_id')) is not str
                or not re.fullmatch('[0-9a-f]{32}', params['run_id'])
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
        raw = path.read_bytes()
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
        _require(set(record) == set(allowed), 'native_journal_invalid')
        _require(record['state'] in STATES | {'prepared', 'unknown'}
                 and record['native_state'] in STATES | {None}
                 and record['stop_reason'] in ERROR_CODES | {None}, 'native_journal_invalid')
        _require(record['native_report'] is None or _report(record['native_report']) == record['native_report'],
                 'native_journal_invalid')
        return record
    except (OSError, ProbeError, ValueError, TypeError, RecursionError):
        raise ProbeError('native_journal_invalid') from None


def _report(value, depth=0):
    _require(type(value) is dict and depth <= 3 and len(value) <= 96, 'invalid_native_report')
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
        elif key in ('cancel_requested', 'stable', 'timed_out', 'draining', 'capture_outstanding',
                     'capture_timed_out', 'workers_drained'):
            _require(type(item) is bool, 'invalid_native_report')
            result[key] = item
        elif key == 'backend':
            result[key] = item if item in ('daemon_direct', 'daemon', 'none') else 'none'
        elif key in ('capture', 'command'):
            result[key] = _report(item, depth+1)
        elif key == 'events':
            _require(type(item) is list and len(item) <= 128, 'invalid_native_report')
            result[key] = [_report(event, depth+1) for event in item]
    if depth == 0:
        _require(result.get('schema') == 'ngg2-native-v1' and _uuid(result.get('clock_id'))
                 and 'input_state' in result and 'device_now_ns' in result, 'invalid_native_report')
    return result


def _status(value, run_id):
    _require(type(value) is dict and value.get('run_id') == run_id
             and value.get('profile') == PROFILE and type(value.get('state')) is str
             and value['state'] in STATES,
             'invalid_native_status')
    return value['state'], _report(value.get('report'))


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
        _require(meta['capture_start_ns'] <= meta['capture_end_ns'], 'invalid_native_images')
        images.append((meta, raw))
    return images


def run_session(client, output, *, cancelled=lambda: False, clock=time.monotonic_ns,
                sleep=time.sleep, poll_seconds=.25, max_seconds=185, recovery_seconds=6,
                lock_path=None):
    """Start once; any uncertainty is recovered using only this durable run ID."""
    number(poll_seconds, .001, 1)
    number(max_seconds, .01, 200)
    number(recovery_seconds, .01, 10)
    base = Path(output).resolve()
    base.mkdir(mode=0o700, parents=True, exist_ok=True)
    with device_lock(lock_path):
        record = _load(base)
        recovering = record is not None and not record['resolved']
        if not recovering:
            record = {'schema': 'ngg2-host-v1', 'revision': REVISION, 'run_id': uuid.uuid4().hex,
                      'profile': PROFILE, 'state': 'prepared', 'resolved': False,
                      'start_attempted': False, 'cancel_attempted': False, 'stop_reason': None,
                      'native_state': None, 'native_report': None, 'images': [],
                      'host_clock_domain': 'python.monotonic_ns',
                      'native_clock_domain': 'device.monotonic_ns', 'events': []}
        run_id = record['run_id']
        invocation = uuid.uuid4().hex
        began = clock()
        deadline = began + int(max_seconds * 1e9)
        cleanup_deadline = None

        def event(method, error=None, timings=None):
            if len(record['events']) >= 1024:
                raise ProbeError('native_journal_invalid')
            row = {'invocation': invocation, 'method': method, 'host_ns': clock(), 'error': error}
            if timings:
                row['host_timings'] = {key: value for key, value in timings.items()
                                       if key.endswith('_ns') and type(value) is int and 0 <= value < 2**63}
            record['events'].append(row)

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

        def cancel_once(reason):
            nonlocal cleanup_deadline
            record['stop_reason'] = record['stop_reason'] or reason
            cleanup_deadline = cleanup_deadline or min(deadline + int(recovery_seconds*1e9),
                                                       clock() + int(recovery_seconds*1e9))
            if record['start_attempted'] and not record['cancel_attempted']:
                record['cancel_attempted'] = True
                _save(base, record)
                try:
                    accept(request('necro_native_cancel', {'run_id': run_id}))
                except ProbeError:
                    record['state'] = 'unknown'

        _save(base, record)
        try:
            info = request('device_info', {})
            _require(info.get('server_version') == API_VERSION
                     and type(info.get('capabilities')) is list and CAPABILITY in info['capabilities'],
                     'native_capability_missing')
            if not recovering:
                if cancelled():
                    record.update(state='stopped', resolved=True, stop_reason='cancel_requested')
                    _save(base, record)
                    return record
                # This durable bit precedes the first and only start attempt.
                record['start_attempted'] = True
                _save(base, record)
                try:
                    accept(request('necro_native_start', {'run_id': run_id, 'profile': PROFILE}))
                except ProbeError as exc:
                    record['state'] = 'unknown'
                    cancel_once(_error(exc))
                _save(base, record)
            else:
                # Recovery never restarts or silently continues an old walk.
                try:
                    accept(request('necro_native_status', {'run_id': run_id}))
                except ProbeError as exc:
                    record['state'] = 'unknown'
                    cancel_once(_error(exc))
                if record['state'] not in TERMINAL:
                    cancel_once('cancel_requested')

            while True:
                if cancelled():
                    cancel_once('cancel_requested')
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
                        record.update(state=state, native_state=state, native_report=report,
                                      images=[metadata for metadata, _raw in images],
                                      resolved=report['input_state'] in (0, 3))
                        if not record['resolved']:
                            record['stop_reason'] = 'native_input_unresolved'
                    except ProbeError as exc:
                        record['stop_reason'] = _error(exc)
                        record['resolved'] = False
                    break
                now = clock()
                if now >= deadline:
                    cancel_once('host_deadline')
                if cleanup_deadline is not None and now >= cleanup_deadline:
                    break
                sleep(poll_seconds)
                try:
                    accept(request('necro_native_status', {'run_id': run_id}))
                except ProbeError as exc:
                    record['state'] = 'unknown'
                    cancel_once(_error(exc))
                _save(base, record)
        except ProbeError as exc:
            record['stop_reason'] = _error(exc)
            if not record['start_attempted']:
                record.update(state='stopped', resolved=True)
            else:
                record.update(state='unknown', resolved=False)
        except OSError:
            # A failed journal must prevent new work, but cannot block cancellation.
            # The start-attempt record was committed before any native start.
            if record['start_attempted'] and not record['cancel_attempted']:
                record['cancel_attempted'] = True
                try:
                    request('necro_native_cancel', {'run_id': run_id})
                except ProbeError:
                    pass
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
