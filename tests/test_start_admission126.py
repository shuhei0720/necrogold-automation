"""Bounded TEST126 start-refusal diagnostics; procedural, not iPhone acceptance."""
import copy
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from necroprobe import campaign116 as campaign
from necroprobe import native_cycle as cycle
from necroprobe import test116 as shared_entry
from necroprobe import test125 as previous
from necroprobe import test126 as entry
from necroprobe.crypto import Crypto
from necroprobe.rpc_diagnostics import remote_error
from necroprobe.validation import ProbeError
from test_campaign_startup125 import Clock, StartupServer, prepared
from test_protocol import KEY, TOK
from test_rpc_diagnostics import seal
from timer_support import TimerTestCase


ROOT = '0123456789abcdef0123456789abcdef'
PRIVATE = 'PRIVATE_START_SECRET'
MESSAGES = (
    ('owner_paused', 'Owner paused native control before campaign admission.'),
    ('storage_unavailable', 'Campaign storage quota is unavailable.'),
    ('evidence_unpublished', 'Native cycle evidence must be recovered and publication acknowledged before a new start.'),
    ('notification_permission', 'Prepare native cycle notifications before starting gameplay.'),
    ('publication_pending', 'Previous native cycle publication is not acknowledged.'),
    ('input_unknown', 'Unknown native input prevents campaign admission.'),
    ('run_draining', 'Previous native run is still draining before campaign admission.'),
    ('campaign_draining', 'Previous native campaign is still draining.'),
    ('export_pending', 'Previous native export prevents campaign admission.'),
    ('capture_pending', 'Previous capture prevents campaign admission.'),
    ('identity_limit', 'Run identity or process limit prevents campaign admission.'),
)


def start_params():
    return dict(run_id=ROOT, profile=cycle.IRREGULAR_PROTOCOL.profile,
        continuous_campaign=True, initial_restart=True)


def refusal(message, *, params=None, method='necro_native_start', code=-32095, malformed=False):
    response = dict(error=dict(code=code, message=message, data={'secret': PRIVATE}))
    if malformed:
        response['result'] = {}
    return remote_error(response, method, start_params() if params is None else params)


class StartAdmissionProtocol126Tests(TimerTestCase):
    def encrypted_error(self, message, *, method='necro_native_start', params=None,
            code=-32095, fields=None, **options):
        payload = dict(error=dict(code=code, message=message, data={'secret': PRIVATE}))
        payload.update(fields or {})
        client = entry.DeviceClient126(lambda body, timeout: seal(body, payload, **options),
            KEY, TOK, crypto=Crypto(native=False), deadline_owner=self.timer)
        with self.assertRaises(ProbeError) as caught:
            client.call(method, start_params() if params is None else params)
        return caught.exception

    def test_authenticated_exact_native_messages_have_fixed_safe_reason_codes(self):
        for reason, message in MESSAGES:
            with self.subTest(reason=reason):
                error = self.encrypted_error(message)
                self.assertEqual('cycle_start_'+reason, getattr(error, 'admission_reason', None),
                    'the authenticated native refusal must retain its fixed cause')
                self.assertEqual('rpc_error', error.code)
                self.assertEqual(-32095, getattr(error, 'rpc_code', None))
                self.assertIs(True, getattr(error, 'error_shape_valid', None))
                self.assertEqual('unclassified', getattr(error, 'category', None))
                self.assertNotIn(PRIVATE, repr(vars(error))+repr(error.args)+str(error))
                self.assertNotIn(message, repr(vars(error))+repr(error.args)+str(error))

    def test_suffix_prefix_unknown_text_and_other_codes_have_no_specific_reason(self):
        message = MESSAGES[1][1]
        cases = [(message+' '+PRIVATE, -32095), (PRIVATE+' '+message, -32095),
            (message.lower(), -32095), (PRIVATE, -32095), (message, -32004),
            (message, -32602), (message, True), (message, '-32095')]
        for text, code in cases:
            with self.subTest(text=text, code=code):
                error = self.encrypted_error(text, code=code)
                self.assertIsNone(getattr(error, 'admission_reason', None))
                self.assertNotIn(PRIVATE, repr(vars(error))+repr(error.args)+str(error))

    def test_only_exact_typed_initial_continuous_irregular_start_is_classified(self):
        valid = start_params()
        cases = [('necro_native_cancel', dict(run_id=ROOT)),
            (cycle.IRREGULAR_PROTOCOL.query, dict(run_id=ROOT, mode='prepare', request_authorization=False))]
        for key in valid:
            params = dict(valid); del params[key]
            cases.append(('necro_native_start', params))
        for key in ('continuous_campaign', 'initial_restart'):
            for flag in (False, 0, 1, None, 'true'):
                cases.append(('necro_native_start', dict(valid, **{key: flag})))
        for changed in ({'profile': cycle.STANDARD_PROTOCOL.profile}, {'extra': True},
                {'yield_after_restart': True}, {'run_id': 'A'*32}, {'run_id': ''}, {'run_id': 1}):
            cases.append(('necro_native_start', dict(valid, **changed)))
        for method, params in cases:
            with self.subTest(method=method, params=params):
                self.assertIsNone(getattr(refusal(MESSAGES[1][1], method=method, params=params),
                    'admission_reason', None))

    def test_bad_mac_wrong_id_and_malformed_error_never_reveal_a_reason(self):
        for options, expected in (({'corrupt_mac': True}, 'response_mac_mismatch'),
                ({'wrong_id': True}, 'response_id_mismatch')):
            with self.subTest(options=options):
                error = self.encrypted_error(MESSAGES[1][1], **options)
                self.assertEqual(expected, error.code)
                self.assertIsNone(getattr(error, 'admission_reason', None))
                self.assertFalse(hasattr(error, 'rpc_code'))
        for fields, message in (({'result': {}}, MESSAGES[1][1]), ({}, None)):
            with self.subTest(fields=fields, message=message):
                error = self.encrypted_error(message, fields=fields)
                self.assertIs(False, getattr(error, 'error_shape_valid', None))
                self.assertIsNone(getattr(error, 'admission_reason', None))

    def test_full_protocol_nonstart_rpc_keeps_its_original_generic_error(self):
        error = self.encrypted_error(MESSAGES[1][1], method='necro_native_cancel', params=dict(run_id=ROOT))
        self.assertIsNone(getattr(error, 'admission_reason', None))
        self.assertEqual('rpc_error', error.code)
        self.assertIs(True, getattr(error, 'error_shape_valid', None))


class StartupServer126(StartupServer):
    """Use real refusal classification after the actual campaign sole-POST guard."""
    def __init__(self, base, sequence, *, message=MESSAGES[1][1], selected=entry.DeviceClient126):
        super().__init__(base, sequence)
        self.initial_validator = selected(lambda *_: b'', KEY, TOK, crypto=Crypto(native=False))
        self.start_admission_diagnostics = getattr(selected, 'start_admission_diagnostics', False)
        self.refusal_message = message
        self.refusal_remaining = 1
        self.malformed_refusal = False
        self.injected_reason = None

    def call(self, method, params):
        if method == 'necro_native_start' and self.refusal_remaining:
            self.initial_validator._validate(method, params)
            self.start_requests.append(copy.deepcopy(params))
            if self.before_post is not None:
                self.before_post()
            guard = getattr(self, '_before_start_post', None)
            if guard is not None:
                guard()
            saved = json.loads((self.base/'continuous-campaign.json').read_bytes())
            assert saved['start_intent'] and saved['campaign_id'] == params['run_id']
            self.calls.append((method, copy.deepcopy(params)))
            self.refusal_remaining -= 1
            error = refusal(self.refusal_message, params=params, malformed=self.malformed_refusal)
            if self.injected_reason is not None:
                error.admission_reason = self.injected_reason
            raise error
        return super().call(method, params)


class StartAdmissionCampaign126Tests(unittest.TestCase):
    def run_campaign(self, server, base, destination, clock, *, test_number='126', **options):
        original = cycle.device_lock
        with patch.object(cycle, 'device_lock', lambda path=None: original(path or destination/'device.lock')):
            return campaign.run(server, destination, spool=base, test_number=test_number,
                notice=lambda _text: None, clock=clock, sleep=clock.sleep, **options)

    def test_only_126_continuous_client_enables_start_admission_diagnostics(self):
        self.assertIs(True, getattr(entry.DeviceClient126, 'start_admission_diagnostics', False))
        for selected in (previous.DeviceClient125, previous.FiniteClient125,
                shared_entry.DeviceClient116, entry.FiniteClient126):
            with self.subTest(selected=selected.__name__):
                self.assertFalse(getattr(selected, 'start_admission_diagnostics', False))

    def test_pending_then_ready_refusal_stores_fixed_cause_without_repost_or_cancel(self):
        for reason, message in MESSAGES:
            with self.subTest(reason=reason), tempfile.TemporaryDirectory() as temporary:
                destination = Path(temporary); base = destination/'test-126'; base.mkdir()
                server = StartupServer126(base, [prepared(notification='pending'),
                    prepared(ready=True, scan='ready')], message=message)
                result = self.run_campaign(server, base, destination, Clock())
                ledger = result['ledger']; expected = 'cycle_start_'+reason
                self.assertEqual(expected, ledger['last_error'],
                    'ready is not a native admission promise; preserve the actual refusal cause')
                self.assertEqual(expected, result['stop_reason'])
                self.assertFalse(ledger['start_intent'])
                self.assertFalse(ledger['cancel_intent'])
                self.assertIsNone(result['campaign_archive'])
                self.assertEqual(2, server.prepares)
                self.assertEqual(1, len(server.start_requests))
                self.assertEqual(1, sum(method == 'necro_native_start' for method, _ in server.calls))
                self.assertFalse(any(method == 'necro_native_cancel' for method, _ in server.calls))
                for path in (base/'continuous-campaign.json',
                        base/'continuous-campaigns'/(ledger['campaign_id']+'.json')):
                    saved = json.loads(path.read_bytes())
                    self.assertEqual(expected, saved['last_error'])
                    self.assertFalse(saved['start_intent'])
                    self.assertNotIn(PRIVATE, path.read_text())
                    self.assertNotIn(message, path.read_text())

    def test_manual_next_invocation_rechecks_prepare_and_reuses_the_unconsumed_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary); base = destination/'test-126'; base.mkdir()
            server = StartupServer126(base, [prepared(ready=True, scan='ready')])
            first = self.run_campaign(server, base, destination, Clock())
            root = first['ledger']['campaign_id']; server.calls.clear()
            second = self.run_campaign(server, base, destination, Clock())
            self.assertEqual(root, second['ledger']['campaign_id'])
            self.assertEqual('schema', server.calls[0][0])
            self.assertEqual('prepare', server.calls[1][1]['mode'])
            self.assertEqual(root, server.start_requests[0]['run_id'])
            self.assertEqual(root, server.start_requests[1]['run_id'])
            self.assertEqual(1, sum(method == 'necro_native_start' for method, _ in server.calls))
            self.assertTrue(second['ledger']['complete'])

    def test_unknown_refusal_and_unrecognized_injected_detail_remain_generic(self):
        for injected in (None, PRIVATE, 'cycle_start_'+PRIVATE, [], {'code': 'cycle_start_storage_unavailable'}):
            with self.subTest(injected=injected), tempfile.TemporaryDirectory() as temporary:
                destination = Path(temporary); base = destination/'test-126'; base.mkdir()
                server = StartupServer126(base, [prepared(ready=True, scan='ready')], message=PRIVATE)
                server.injected_reason = injected
                result = self.run_campaign(server, base, destination, Clock())
                self.assertEqual('cycle_start_not_admitted', result['stop_reason'])
                self.assertFalse(result['ledger']['start_intent'])
                self.assertEqual(1, len(server.start_requests))
                self.assertFalse(any(method == 'necro_native_cancel' for method, _ in server.calls))
                self.assertNotIn(PRIVATE, (base/'continuous-campaign.json').read_text())

    def test_old_client_keeps_generic_refusal_even_when_parser_knows_the_cause(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary); base = destination/'test-125'; base.mkdir()
            server = StartupServer126(base, [prepared(ready=True, scan='ready')], selected=previous.DeviceClient125)
            server.injected_reason = 'cycle_start_storage_unavailable'
            result = self.run_campaign(server, base, destination, Clock(), test_number='125')
            self.assertEqual('cycle_start_not_admitted', result['stop_reason'])
            self.assertFalse(result['ledger']['start_intent'])

    def test_untrusted_refusal_cannot_clear_intent_even_with_a_known_injected_reason(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary); base = destination/'test-126'; base.mkdir()
            server = StartupServer126(base, [prepared(ready=True, scan='ready')])
            server.malformed_refusal = True; server.injected_reason = 'cycle_start_storage_unavailable'
            result = self.run_campaign(server, base, destination, Clock())
            self.assertTrue(result['ledger']['start_intent'])
            self.assertEqual('rpc_error', result['stop_reason'])
            self.assertEqual(1, len(server.start_requests))
            self.assertNotIn('cycle_start_storage_unavailable', (base/'continuous-campaign.json').read_text())

    def test_uncertain_transport_start_still_recovers_the_original_root_without_repost(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary); base = destination/'test-126'; base.mkdir()
            server = StartupServer126(base, [prepared(ready=True, scan='ready')])
            server.refusal_remaining = 0; server.start_failure = True
            first = self.run_campaign(server, base, destination, Clock())
            root = first['ledger']['campaign_id']
            self.assertTrue(first['ledger']['start_intent'])
            second = self.run_campaign(server, base, destination, Clock(), until_target=False, recovery_only=True)
            self.assertEqual(root, second['ledger']['campaign_id'])
            self.assertEqual(1, len(server.start_requests))
            self.assertTrue(second['ledger']['collection_complete'])


class StartAdmissionEntry126Tests(unittest.TestCase):
    def output_for(self, code, *, selected=entry):
        number = '126' if selected is entry else '125'
        ledger = campaign._fresh(test_number=number); ledger.update(state='pending', last_error=code)
        result = dict(ledger=ledger, campaign_archive=None, stop_reason=code, record=None)
        output = io.StringIO()
        with tempfile.TemporaryDirectory() as temporary, patch.object(Path, 'home', return_value=Path(temporary)), \
                patch.object(shared_entry, 'load_pairing', return_value=(KEY, TOK)), \
                patch.object(campaign, 'run', return_value=result), redirect_stdout(output):
            self.assertEqual(2, selected.main(['--until-target', '--python-crypto']))
        return output.getvalue()

    def test_storage_cause_is_explained_without_blind_retry_or_recovery_advice(self):
        output = self.output_for('cycle_start_storage_unavailable')
        self.assertIn('ゲームは開始していません', output)
        self.assertIn('保存', output)
        self.assertTrue('容量' in output or '領域' in output,
            'explain the storage refusal instead of only echoing its enum')
        self.assertNotIn('通常コマンドを再実行', output)
        self.assertNotIn('--recovery', output)

    def test_generic_diagnostic_refusal_explicitly_keeps_its_cause_unknown(self):
        output = self.output_for('cycle_start_not_admitted')
        self.assertIn('ゲームは開始していません', output)
        self.assertIn('原因', output)
        self.assertTrue('未特定' in output or '特定でき' in output)
        self.assertNotIn('通常コマンドを再実行', output)
        self.assertNotIn('--recovery', output)
        self.assertNotIn('通知が拒否', output)

    def test_old_entry_advice_and_check_identity_are_unchanged(self):
        self.assertIn('通常コマンドを再実行', self.output_for('cycle_start_not_admitted', selected=previous))
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(0, entry.main(['--check']))
        self.assertEqual('native-device-failures-trial-v126 / '+cycle.API_VERSION+'\n', output.getvalue())


if __name__ == '__main__':
    unittest.main()
