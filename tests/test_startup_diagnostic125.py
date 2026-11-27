"""Focused startup diagnostics using fakes, never an iPhone or real socket."""
import base64
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import stat
import tempfile
import unittest

import diagnose_startup125 as diagnostic
from necroprobe import native_cycle as cycle
from necroprobe.crypto import Crypto, mac, python_xor
from necroprobe.protocol import HttpTransport, RpcReply
from necroprobe.validation import ProbeError


KEY = bytes(range(32))
TOK = hashlib.sha256(KEY).digest()[:4].hex()
PROBE = 'a'*32
UNPUBLISHED = ['b'*32, 'c'*32]
FIXED_TIME = datetime(2026, 11, 27, tzinfo=timezone.utc)


def payload(**changes):
    result = dict(ready=True, notification_authorization='authorized', recovery_scan='ready',
        unpublished_run_ids=[], reason='none')
    result.update(changes)
    return result


def envelope(prepared, run_id=PROBE):
    return dict(schema=cycle.IRREGULAR_PROTOCOL.schema, run_id=run_id,
        profile=cycle.IRREGULAR_PROTOCOL.profile, mode='prepare', payload=prepared)


class Harness:
    def __init__(self, *actions, schema_error=None):
        self.events, self.calls, self.sleeps = [], [], []
        self.actions = list(actions) if actions else [payload()]*3
        self.schema_error = schema_error
        self.transport = type('FakeTransport', (), {})()
        self.transport.last_diagnostic = dict(kind='ok', stage='complete', errno=None, status=200)
        harness = self

        class FakeTimer:
            def __enter__(self):
                harness.events.append('timer_enter')
                return self

            def __exit__(self, *_args):
                harness.events.append('timer_exit')
                return False

        class FakeClient:
            def __init__(self, transport, key=None, tok=None, **options):
                harness.events.append('client')
                self.transport, self.key, self.tok = transport, key, tok
                harness.client = self
                harness.options = options

            def check_schema(self):
                harness.events.append('schema')
                if self.key is not None or self.tok is not None:
                    raise AssertionError('schema must precede pairing')
                if harness.schema_error is not None:
                    raise harness.schema_error
                return {'api_version': cycle.API_VERSION, 'capability': cycle.IRREGULAR_PROTOCOL.capability}

            def call(self, method, params):
                diagnostic.DiagnosticClient125._validate(self, method, params)
                harness.events.append('prepare')
                harness.calls.append((method, dict(params)))
                action = harness.actions.pop(0)
                if isinstance(action, BaseException):
                    raise action
                return RpcReply(envelope(action, params['run_id']), {})

        self.timer_factory, self.client_factory = FakeTimer, FakeClient

    def pairing_loader(self, path):
        self.events.append('pairing')
        self.pairing_path = path
        return KEY, TOK

    def sleep(self, seconds):
        self.sleeps.append(seconds)

    def collect(self):
        return diagnostic.collect_diagnostic(client_factory=self.client_factory,
            transport_factory=lambda: self.transport, pairing_loader=self.pairing_loader,
            timer_factory=self.timer_factory, sleep=self.sleep, probe_id=PROBE)


class AuthenticatedTransport(HttpTransport):
    """The real authenticated client talks only to this procedural fixture."""
    def __init__(self, events, *, missing_capability=False):
        super().__init__()
        self.events, self.calls = events, []
        caps = {cycle.CAPABILITY, cycle.IRREGULAR_PROTOCOL.capability} \
            | diagnostic.DiagnosticClient125.required_capabilities
        if missing_capability:
            caps.remove('necrogold_native_device_fixes125_v1')
        self.metadata = dict(server_version=cycle.API_VERSION, protocol_version=1,
            capability_tags=sorted(caps))

    def _exchange(self, method, path, body, timeout, limit):
        self.events.append(method+' '+path)
        self.last_diagnostic = dict(kind='ok', stage='complete', errno=None, status=200)
        if method == 'GET':
            if path != '/schema' or body is not None:
                raise AssertionError('the public schema must have no body')
            return cycle.canonical(self.metadata)
        sealed = json.loads(body)
        nonce = bytes.fromhex(sealed['nonce'])
        request = json.loads(python_xor(mac(KEY, b'loopctrl-v1|enc-req'+nonce), nonce,
            base64.b64decode(sealed['ct'])))
        self.calls.append(request)
        result = envelope(payload(), request['params']['run_id'])
        response = dict(jsonrpc='2.0', id=request['id'], result=result)
        cipher = python_xor(mac(KEY, b'loopctrl-v1|enc-resp'+nonce), nonce, cycle.canonical(response))
        tag = mac(mac(KEY, b'loopctrl-v1|mac'+nonce), b'resp'+nonce+cipher).hex()
        return cycle.canonical(dict(ct=base64.b64encode(cipher).decode(), tag=tag))


class StartupDiagnostic125Tests(unittest.TestCase):
    def test_ready_prepare_is_sampled_three_times_without_a_start(self):
        harness = Harness()
        report = harness.collect()
        self.assertEqual(3, len(report['samples']),
            'the read-only diagnostic must preserve all three readiness observations')
        self.assertTrue(report['ready'])
        self.assertEqual('complete', report['phase'])
        self.assertEqual('ready', report['code'])
        self.assertEqual([cycle.IRREGULAR_PROTOCOL.query]*3, [row[0] for row in harness.calls])
        self.assertEqual([dict(run_id=PROBE, mode='prepare', request_authorization=False)]*3,
            [row[1] for row in harness.calls])
        self.assertEqual([.5, .5], harness.sleeps)
        self.assertEqual(['timer_enter', 'client', 'schema', 'pairing',
            'prepare', 'prepare', 'prepare', 'timer_exit'], harness.events)
        self.assertEqual(Path.home()/'.loopctrl'/'token.json', harness.pairing_path)
        self.assertEqual('python', harness.options['crypto'].engine)
        self.assertIsNone(harness.options['crypto'].native)
        self.assertIsInstance(harness.options['deadline_owner'], harness.timer_factory)
        self.assertEqual({'schema', 'phase', 'code', 'ready', 'samples', 'transport'}, set(report))

    def test_pending_denied_failed_scan_and_unpublished_are_distinct(self):
        cases = (
            payload(ready=False, notification_authorization='pending', reason='need_open_loopctrl_notifications'),
            payload(ready=False, recovery_scan='pending', reason='recovery_scan_pending'),
            payload(ready=False, notification_authorization='denied', reason='need_open_loopctrl_notifications'),
            payload(ready=False, recovery_scan='failed', reason='recovery_scan_failed'),
            payload(ready=False, unpublished_run_ids=UNPUBLISHED, reason='unpublished_cycle'))
        for prepared in cases:
            with self.subTest(reason=prepared['reason'], authorization=prepared['notification_authorization']):
                report = Harness(*[prepared]*3).collect()
                self.assertFalse(report['ready'])
                self.assertEqual('not_ready', report['code'])
                self.assertEqual(3, len(report['samples']))
                expected = {name: prepared[name] for name in
                    ('ready', 'notification_authorization', 'recovery_scan', 'reason')}
                expected['unpublished_count'] = len(prepared['unpublished_run_ids'])
                self.assertEqual([expected]*3, report['samples'])
                self.assertNotIn('unpublished_run_ids', json.dumps(report))

    def test_final_ready_sample_controls_exit_after_pending_samples(self):
        harness = Harness(payload(ready=False, notification_authorization='pending'),
            payload(ready=False, recovery_scan='pending'), payload())
        report = harness.collect()
        self.assertEqual([False, False, True], [sample['ready'] for sample in report['samples']])
        self.assertTrue(report['ready'])

    def test_schema_refusal_reads_no_pairing_and_sends_no_rpc(self):
        harness = Harness(schema_error=ProbeError('connection_error'))
        harness.transport.last_diagnostic = dict(kind='refused', stage='connect', errno=111, status=None,
            raw='PRIVATE_RAW_REPLY', path='/PRIVATE_PATH')
        report = harness.collect()
        self.assertEqual('schema', report['phase'])
        self.assertEqual('connection_error', report['code'])
        self.assertEqual([], report['samples'])
        self.assertEqual([], harness.calls)
        self.assertNotIn('pairing', harness.events)
        self.assertIsNone(harness.client.key)
        self.assertIsNone(harness.client.tok)
        self.assertEqual(dict(kind='refused', stage='connect', errno=111, status=None), report['transport'])

    def test_real_125_schema_gate_precedes_pairing_and_authenticated_prepare(self):
        for missing in (True, False):
            with self.subTest(missing_capability=missing):
                events = []
                transport = AuthenticatedTransport(events, missing_capability=missing)
                def pairing(_path):
                    events.append('pairing')
                    return KEY, TOK
                report = diagnostic.collect_diagnostic(transport_factory=lambda: transport,
                    pairing_loader=pairing, sleep=lambda _seconds: None, probe_id=PROBE)
                if missing:
                    self.assertEqual('native_capability_missing', report['code'])
                    self.assertEqual(['GET /schema'], events)
                    self.assertEqual([], transport.calls)
                else:
                    self.assertTrue(report['ready'])
                    self.assertEqual(['GET /schema', 'pairing']+['POST /rpc']*3, events)
                    self.assertEqual([cycle.IRREGULAR_PROTOCOL.query]*3,
                        [request['method'] for request in transport.calls])
                    self.assertEqual([dict(run_id=PROBE, mode='prepare', request_authorization=False)]*3,
                        [request['params'] for request in transport.calls])

    def test_later_rpc_failure_preserves_and_saves_first_sample(self):
        harness = Harness(payload(), ProbeError('connection_error'))
        report = harness.collect()
        self.assertEqual('prepare', report['phase'])
        self.assertEqual('connection_error', report['code'])
        self.assertFalse(report['ready'])
        self.assertEqual(1, len(report['samples']))
        self.assertTrue(report['samples'][0]['ready'])
        self.assertEqual(2, len(harness.calls))
        self.assertEqual([.5], harness.sleeps)
        with tempfile.TemporaryDirectory() as temporary:
            writer = lambda value: diagnostic.save_report(value, output_dir=temporary, now=FIXED_TIME, pid=42)
            messages = []
            self.assertEqual(2, diagnostic.main([], collector=lambda: report, report_writer=writer, notice=messages.append))
            files = list(Path(temporary).iterdir())
            self.assertEqual(1, len(files))
            self.assertEqual(report, json.loads(files[0].read_text()))
            self.assertIn('診断JSON: '+files[0].name, messages)
            self.assertNotIn(temporary, '\n'.join(messages))

    def test_connection_failure_also_writes_a_diagnostic(self):
        report = Harness(schema_error=ProbeError('connection_error')).collect()
        with tempfile.TemporaryDirectory() as temporary:
            writer = lambda value: diagnostic.save_report(value, output_dir=temporary, now=FIXED_TIME, pid=42)
            self.assertEqual(2, diagnostic.main([], collector=lambda: report, report_writer=writer, notice=lambda _text: None))
            self.assertEqual(report, json.loads(next(Path(temporary).iterdir()).read_text()))

    def test_prepare_schema_is_validated_without_repairing_raw_packets(self):
        cases = (payload(ready=True, notification_authorization='denied'),
            payload(ready=True, recovery_scan='pending'), payload(extra='PRIVATE_RAW_REPLY'))
        for prepared in cases:
            with self.subTest(keys=sorted(prepared)):
                harness = Harness(prepared)
                report = harness.collect()
                self.assertEqual('invalid_cycle_response', report['code'])
                self.assertEqual([], report['samples'])
                self.assertFalse(report['ready'])
                self.assertEqual(1, len(harness.calls))

    def test_no_raw_identifiers_tokens_paths_or_exception_text_reach_outputs(self):
        harness = Harness(payload(ready=False, unpublished_run_ids=UNPUBLISHED, reason=TOK),
            ProbeError('/PRIVATE_PATH/PRIVATE_EXCEPTION_'+KEY.hex()))
        harness.transport.last_diagnostic = dict(kind=TOK, stage=PROBE, errno=True,
            status='/PRIVATE_PATH', raw_reply='PRIVATE_RAW_REPLY', token=TOK, key=KEY.hex())
        report = harness.collect()
        self.assertEqual('diagnostic_failed', report['code'])
        self.assertEqual('unknown', report['samples'][0]['reason'])
        self.assertEqual(dict(kind='unknown', stage='unknown', errno=None, status=None), report['transport'])
        with tempfile.TemporaryDirectory() as temporary:
            messages = []
            writer = lambda value: diagnostic.save_report(value, output_dir=temporary, now=FIXED_TIME, pid=42)
            diagnostic.main([], collector=lambda: report, report_writer=writer, notice=messages.append)
            serialized = next(Path(temporary).iterdir()).read_text()+'\n'+'\n'.join(messages)
            for private in (KEY.hex(), TOK, PROBE, *UNPUBLISHED, '/PRIVATE_PATH',
                    'PRIVATE_EXCEPTION', 'PRIVATE_RAW_REPLY', temporary, 'token.json'):
                self.assertNotIn(private, serialized)

    def test_os_errors_and_unknown_transport_values_are_sanitized(self):
        harness = Harness(schema_error=OSError(5, 'PRIVATE_EXCEPTION', '/PRIVATE_PATH'))
        report = harness.collect()
        self.assertEqual('local_io_error', report['code'])
        self.assertNotIn('PRIVATE_', json.dumps(report))
        for value in ({'errno': -1, 'status': 600}, {'errno': 4096, 'status': True}):
            harness = Harness()
            harness.transport.last_diagnostic = value
            self.assertEqual(dict(kind='unknown', stage='unknown', errno=None, status=None),
                harness.collect()['transport'])

    def test_pairing_failure_does_not_send_prepare(self):
        harness = Harness()
        def missing(_path):
            raise ProbeError('pairing_missing')
        harness.pairing_loader = missing
        report = harness.collect()
        self.assertEqual('pairing', report['phase'])
        self.assertEqual('pairing_missing', report['code'])
        self.assertEqual([], harness.calls)

    def test_prepare_is_the_only_allowed_rpc_and_requires_authorization_false(self):
        calls = []
        client = diagnostic.DiagnosticClient125(lambda *args: calls.append(args), KEY, TOK,
            crypto=Crypto(native=False))
        allowed = dict(run_id=PROBE, mode='prepare', request_authorization=False)
        client._validate(cycle.IRREGULAR_PROTOCOL.query, allowed)
        refused = [
            ('necro_native_start', dict(run_id=PROBE, profile=cycle.IRREGULAR_PROTOCOL.profile,
                continuous_campaign=True, initial_restart=True)),
            ('necro_native_cancel', dict(run_id=PROBE)),
            (cycle.STANDARD_PROTOCOL.query, allowed),
            (cycle.IRREGULAR_PROTOCOL.query, dict(allowed, request_authorization=True)),
            (cycle.IRREGULAR_PROTOCOL.query, dict(allowed, request_authorization=0)),
            (cycle.IRREGULAR_PROTOCOL.query, dict(allowed, keepalive=False)),
            (cycle.IRREGULAR_PROTOCOL.query, dict(run_id=PROBE, mode='prepare')),
            (cycle.IRREGULAR_PROTOCOL.query, dict(allowed, run_id='invalid')),
            ('tap', {'x': 1, 'y': 2}), ('run_steps', {}), ('launch_app', {}),
            ('device_info', {}), ('screenshot', {})]
        refused.extend((cycle.IRREGULAR_PROTOCOL.query, dict(run_id=PROBE, mode=mode, keepalive=False))
            for mode in ('status', 'campaign_status', 'manifest', 'chunk', 'batch', 'record',
                'published', 'trial_support'))
        for method, params in refused:
            with self.subTest(method=method, mode=params.get('mode')):
                with self.assertRaises(ProbeError) as caught:
                    client.call(method, params)
                self.assertEqual('method_not_allowed', caught.exception.code)
        self.assertEqual([], calls)

    def test_report_file_is_exclusive_private_and_never_overwrites(self):
        report = Harness().collect()
        with tempfile.TemporaryDirectory() as temporary:
            path = diagnostic.save_report(report, output_dir=temporary, now=FIXED_TIME, pid=42)
            before = path.read_bytes()
            self.assertEqual('startup-diagnostic125-20261127T000000.000000Z-42.json', path.name)
            self.assertEqual(0o600, stat.S_IMODE(path.stat().st_mode))
            with self.assertRaises(FileExistsError):
                diagnostic.save_report(dict(report, code='not_ready'), output_dir=temporary, now=FIXED_TIME, pid=42)
            self.assertEqual(before, path.read_bytes())
            self.assertEqual([path], list(Path(temporary).iterdir()))

    def test_main_ready_exit_and_save_error_are_one_shot_and_sanitized(self):
        report = Harness().collect()
        messages, saved = [], []
        def writer(value):
            saved.append(value)
            return Path('startup-diagnostic125-safe.json')
        self.assertEqual(0, diagnostic.main([], collector=lambda: report, report_writer=writer, notice=messages.append))
        self.assertEqual([report], saved)
        def failing_writer(_value):
            raise OSError(5, 'PRIVATE_EXCEPTION', '/PRIVATE_PATH')
        messages = []
        self.assertEqual(2, diagnostic.main([], collector=lambda: report, report_writer=failing_writer, notice=messages.append))
        self.assertIn('report_save_failed', messages[-1])
        self.assertNotIn('PRIVATE_', '\n'.join(messages))


if __name__ == '__main__':
    unittest.main()
