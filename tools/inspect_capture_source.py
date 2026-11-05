"""P1.4/P1.5の取得元を1回だけ照会。画像・位置情報・ゲーム操作は扱わない。"""
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

FIELDS = ('server_version', 'build', 'protocol_version', 'point_width', 'point_height',
          'pixel_width', 'pixel_height', 'scale')
CAPABILITIES = ('run_steps', 'wait_for', 'screenshot_stream', 'video_stream', 'stream_ticket', 'screenshot_image_geometry_v1')


def sanitize(result):
    result = result if isinstance(result, dict) else {}
    values, issues = {}, []
    for name in FIELDS:
        if name not in result:
            issues.append(name + '_missing')
            continue
        value = result[name]
        if name in ('server_version', 'build'):
            valid = isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9._:+ -]{1,64}', value) is not None
        elif name == 'protocol_version':
            valid = type(value) is int and 1 <= value <= 10000
        elif name.startswith('pixel_'):
            valid = type(value) is int and 1 <= value <= 8192
        else:
            limit = 8 if name == 'scale' else 4096
            valid = type(value) in (int, float) and 0 < value <= limit and math.isfinite(value)
        if valid:
            values[name] = value
        else:
            issues.append(name + '_invalid')
    caps = result.get('capabilities')
    caps = caps if isinstance(caps, list) else []
    return {'values': values, 'issues': issues, 'known_capabilities': [x for x in CAPABILITIES if x in caps]}


def probe_device():
    # カレントは既存 /mnt/necro_p14。ペアリングの内容を出力しない。
    sys.path.insert(0, os.getcwd())
    from necroprobe import VERSION
    if VERSION not in ('P1.4', 'P1.5'):
        return {'error': 'requires_P1.4'}
    from necroprobe.crypto import Crypto
    from necroprobe.deadlines import OwnedRpcTimer
    from necroprobe.protocol import Client, HttpTransport, load_pairing
    key, token = load_pairing(str(Path.home() / '.loopctrl/token.json'), None)
    crypto = Crypto()
    with OwnedRpcTimer() as timer:
        client = Client(HttpTransport(), key, token, timeout=8, allow_launch=False,
                        crypto=crypto, deadline_owner=timer)
        reply = client.call('device_info')
    return {'server': sanitize(reply.result), 'crypto_engine': crypto.engine}


def run_query(command=None, timeout=15):
    process = None
    previous = {}
    cancelled = False
    deadline = time.monotonic() + timeout
    def interrupted(_signal, _frame):
        nonlocal cancelled
        cancelled = True
    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            previous[signum] = signal.signal(signum, interrupted)
        process = subprocess.Popen(command or [sys.executable, str(Path(__file__).resolve()), '--worker'],
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        # handlerでは例外を投げず、起動/回収境界でも停止要求を保持する。
        while True:
            if cancelled:
                return {'error': 'source_info_cancelled'}
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return {'error': 'source_info_deadline'}
            try:
                raw, _ = process.communicate(timeout=min(.1, remaining))
                break
            except subprocess.TimeoutExpired:
                continue
        if cancelled:
            return {'error': 'source_info_cancelled'}
        if process.returncode:
            return {'error': 'source_info_worker_failed', 'returncode': process.returncode}
        if len(raw) > 4096:
            return {'error': 'source_info_invalid_output'}
        try:
            result = json.loads(raw)
            if result == {'error': 'requires_P1.4'}:
                return result
            if not isinstance(result, dict) or set(result) != {'server', 'crypto_engine'}:
                raise ValueError()
            server = result['server']
            if not isinstance(server, dict) or set(server) != {'values', 'issues', 'known_capabilities'}:
                raise ValueError()
            if not isinstance(server['values'], dict) or result['crypto_engine'] not in ('python', 'native_i386'):
                raise ValueError()
            checked = sanitize(dict(server['values'], capabilities=server['known_capabilities']))
            # 型不正を生値なしで保持する。未知理由や任意文字列は出さない。
            allowed_issues = {x + suffix for x in FIELDS for suffix in ('_missing', '_invalid')}
            if not isinstance(server['issues'], list) or len(server['issues']) > len(FIELDS):
                raise ValueError()
            if any(type(x) is not str or x not in allowed_issues for x in server['issues']):
                raise ValueError()
            issue_fields = [x.rsplit('_', 1)[0] for x in server['issues']]
            if len(set(issue_fields)) != len(issue_fields) or set(issue_fields) != set(FIELDS) - set(server['values']):
                raise ValueError()
            if checked['values'] != server['values'] or checked['known_capabilities'] != server['known_capabilities']:
                raise ValueError()
            checked['issues'] = server['issues']
            return {'server': checked, 'crypto_engine': result['crypto_engine']}
        except (ValueError, TypeError, UnicodeError, RecursionError):
            return {'error': 'source_info_invalid_output'}
    except subprocess.TimeoutExpired:
        return {'error': 'source_info_deadline'}
    except KeyboardInterrupt:
        return {'error': 'source_info_cancelled'}
    except OSError:
        return {'error': 'source_info_start_failed'}
    finally:
        cleanup_failed = False
        try:
            # 連続した停止要求が子の回収を中断しないようにする。
            for signum in previous:
                signal.signal(signum, signal.SIG_IGN)
            if process is not None and process.poll() is None:
                process.kill()
                process.communicate(timeout=1)
        except (OSError, subprocess.TimeoutExpired):
            cleanup_failed = True
        finally:
            for signum, handler in previous.items():
                signal.signal(signum, handler)
        if cleanup_failed:
            return {'error': 'source_info_cleanup_failed'}


def main():
    is_worker = sys.argv[1:] == ['--worker']
    if is_worker:
        try:
            result = probe_device()
        except Exception:
            return 2  # 例外本文には秘密値が含まれ得るため表示しない。
    else:
        result = run_query()
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    # 想定エラーJSONの出力完了と子のプロセス異常を区別する。
    return 0 if is_worker else 2 if 'error' in result else 0


if __name__ == '__main__':
    raise SystemExit(main())
