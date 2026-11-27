"""Read TEST125 startup readiness once, without requesting gameplay actions.

Run from the TEST125 source directory with: python3 diagnose_startup125.py
The existing local pairing record is read only after the public schema passes.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
import uuid

from necroprobe import native_cycle as cycle
from necroprobe.crypto import Crypto
from necroprobe.deadlines import OwnedRpcTimer
from necroprobe.protocol import HttpTransport, load_pairing
from necroprobe.test125 import DeviceClient125
from necroprobe.validation import ProbeError


SCHEMA = 'necroprobe-startup-diagnostic125-v1'
REASONS = frozenset(('none', 'recovery_scan_failed', 'recovery_scan_pending',
    'unpublished_cycle', 'need_open_loopctrl_notifications'))
ERROR_CODES = frozenset(('connection_error', 'native_capability_missing',
    'cycle_schema_unavailable', 'pairing_missing', 'pairing_ambiguous',
    'invalid_pairing_record', 'invalid_cycle_response', 'cycle_evidence_storage_unavailable',
    'rpc_error', 'rpc_deadline', 'http_body_limit', 'http_body_truncated',
    'response_mac_mismatch', 'invalid_response_tag', 'response_id_mismatch',
    'rpc_result_type', 'timer_owner_required', 'timer_already_in_use', 'timer_unusable',
    'posix_timer_required', 'timer_handler_in_use', 'timer_setup_failed', 'timer_cleanup_failed',
    'method_not_allowed', 'json_size', 'invalid_json', 'duplicate_json_key',
    'nonfinite_json', 'base64_size_or_type', 'invalid_base64'))
TRANSPORT_KINDS = frozenset(('ok', 'timeout', 'refused', 'reset', 'unreachable',
    'disconnected', 'body_truncated', 'protocol_error', 'io_error', 'deadline',
    'body_limit', 'http_status'))
TRANSPORT_STAGES = frozenset(('connect', 'request', 'headers', 'body', 'complete'))


class DiagnosticClient125(DeviceClient125):
    """An authenticated client whose entire RPC allowlist is read-only prepare."""

    def check_schema(self):
        # TrialClient099 adds a trial_support RPC. Use its unchanged public
        # schema validator with this subclass's complete TEST125 cap set.
        return cycle.CycleClient.check_schema(self)

    def _validate(self, method, params):
        cycle.closed(params, ('run_id', 'mode', 'request_authorization'), 'method_not_allowed')
        cycle.require(method == cycle.IRREGULAR_PROTOCOL.query
            and cycle.identifier(params['run_id']) and params['mode'] == 'prepare'
            and params['request_authorization'] is False, 'method_not_allowed')


def _error_code(error):
    if isinstance(error, KeyboardInterrupt):
        return 'interrupted'
    if isinstance(error, ProbeError):
        code = error.code
        if type(code) is str and code in ERROR_CODES:
            return code
        if type(code) is str and code.startswith('http_status_') \
                and code[12:].isdigit() and len(code[12:]) == 3:
            return 'http_status'
    if isinstance(error, OSError):
        return 'local_io_error'
    return 'diagnostic_failed'


def _transport_diagnostic(transport):
    value = getattr(transport, 'last_diagnostic', None)
    value = value if type(value) is dict else {}
    kind, stage = value.get('kind'), value.get('stage')
    number, status = value.get('errno'), value.get('status')
    return dict(kind=kind if type(kind) is str and kind in TRANSPORT_KINDS else 'unknown',
        stage=stage if type(stage) is str and stage in TRANSPORT_STAGES else 'unknown',
        errno=number if type(number) is int and 0 <= number <= 4095 else None,
        status=status if type(status) is int and 100 <= status <= 599 else None)


def _sample(prepared):
    return dict(ready=prepared['ready'],
        notification_authorization=prepared['notification_authorization'],
        recovery_scan=prepared['recovery_scan'],
        reason=prepared['reason'] if prepared['reason'] in REASONS else 'unknown',
        unpublished_count=len(prepared['unpublished_run_ids']))


def collect_diagnostic(*, client_factory=DiagnosticClient125, transport_factory=HttpTransport,
        pairing_loader=load_pairing, timer_factory=OwnedRpcTimer, sleep=time.sleep, probe_id=None):
    """Return a bounded report; injected fakes need no network or pairing file."""
    report = dict(schema=SCHEMA, phase='initialize', code='diagnostic_failed',
        ready=False, samples=[], transport=_transport_diagnostic(None))
    transport = None
    try:
        with timer_factory() as timer:
            transport = transport_factory()
            client = client_factory(transport, timeout=8, crypto=Crypto(native=False), deadline_owner=timer)
            report['phase'] = 'schema'
            client.check_schema()
            report['phase'] = 'pairing'
            client.key, client.tok = pairing_loader(Path.home()/'.loopctrl'/'token.json')
            probe = uuid.uuid4().hex if probe_id is None else probe_id
            cycle.require(cycle.identifier(probe), 'invalid_cycle_response')
            report['phase'] = 'prepare'
            for index in range(3):
                if index:
                    sleep(.5)
                prepared = cycle.prepare(cycle._call(client, cycle.IRREGULAR_PROTOCOL.query,
                    dict(run_id=probe, mode='prepare', request_authorization=False)),
                    probe, protocol_spec=cycle.IRREGULAR_PROTOCOL)
                report['samples'].append(_sample(prepared))
            report['phase'] = 'complete'
        report['ready'] = report['samples'][-1]['ready']
        report['code'] = 'ready' if report['ready'] else 'not_ready'
    except (Exception, KeyboardInterrupt) as error:
        report['code'] = _error_code(error)
    report['transport'] = _transport_diagnostic(transport)
    return report


def save_report(report, *, output_dir=None, now=None, pid=None):
    """Create one private report exclusively; never replace or delete a file."""
    current = datetime.now(timezone.utc) if now is None else now
    stamp = current.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    process = os.getpid() if pid is None else pid
    filename = 'startup-diagnostic125-'+stamp+'-'+str(process)+'.json'
    destination = (Path.cwd() if output_dir is None else Path(output_dir))/filename
    raw = json.dumps(report, ensure_ascii=False, allow_nan=False,
        sort_keys=True, indent=2).encode('utf-8') + b'\n'
    descriptor = os.open(str(destination), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'wb') as output:
        output.write(raw)
        output.flush()
        os.fsync(output.fileno())
    return destination


def main(argv=None, *, collector=collect_diagnostic, report_writer=save_report, notice=print):
    parser = argparse.ArgumentParser(description='TEST125 起動前の状態を3回読み、診断JSONを保存します。')
    parser.parse_args(argv)
    report = collector()
    notice('TEST125 起動診断: phase='+report['phase']+' code='+report['code']
        +' ready='+str(report['ready']).lower())
    for index, sample in enumerate(report['samples'], 1):
        notice('prepare['+str(index)+']: '+', '.join(name+'='+str(value).lower()
            for name, value in sample.items()))
    transport = report['transport']
    notice('transport: '+', '.join(name+'='+str(value).lower() for name, value in transport.items()))
    try:
        destination = report_writer(report)
    except (Exception, KeyboardInterrupt):
        notice('診断JSON: 保存できませんでした / report_save_failed')
        return 2
    notice('診断JSON: '+destination.name)
    return 0 if report['ready'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
