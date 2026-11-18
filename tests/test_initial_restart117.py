"""TEST117 root-only initial reset: closed wire and unique client POST.

Transport fixtures are procedural. They neither implement screen decisions
nor prove that an iPhone performed the initial reset.
"""
import copy
from pathlib import Path
import tempfile
import unittest

from necroprobe import native_cycle as cycle
from necroprobe import campaign116 as campaign
from necroprobe import test117 as entry
from necroprobe.crypto import Crypto
from necroprobe.test116 import DeviceClient116, FiniteClient116
from necroprobe.validation import ProbeError
from tests.test_protocol import KEY, TOK
import test_continuous_client116 as baseline
from test_native_irregular_client110 import IrregularServer, store_model
from test_restart_yield112 import restart_yield_model, revise


ROOT = baseline.ROOT
SPEC = cycle.IRREGULAR_PROTOCOL


def admitted(selected, params):
    client = selected(lambda *_: b'', KEY, TOK, crypto=Crypto(native=False))
    try:
        client._validate('necro_native_start', params)
        return True
    except ProbeError:
        return False


class ContinuousInitialServer117(baseline.ContinuousServer116):
    initial_restart = True

    def __init__(self, base):
        super().__init__(base); self.start_requests = []
        self.initial_validator = entry.DeviceClient117(lambda *_: b'', KEY, TOK, crypto=Crypto(native=False))

    def call(self, method, params):
        self.initial_validator._validate(method, params)
        if method == 'necro_native_start': self.start_requests.append(copy.deepcopy(params))
        wire = copy.deepcopy(params); wire.pop('initial_restart', None)
        value = super().call(method, wire)
        if method in ('necro_native_start', 'necro_native_cancel'): value['initial_restart'] = True
        return value


class FiniteInitialServer117(IrregularServer):
    initial_restart = True
    yield_after_restart = True

    def call(self, method, params):
        if method == 'necro_native_start':
            entry.FiniteClient117(lambda *_: b'', KEY, TOK, crypto=Crypto(native=False))._validate(method, params)
        value = super().call(method, params)
        if method in ('necro_native_start', 'necro_native_cancel'):
            value['yield_after_restart'] = True; value['initial_restart'] = True
        return value


class InitialRestartClient117Tests(unittest.TestCase):
    def test_both_117_modes_explicitly_request_initial_restart(self):
        for selected in (entry.DeviceClient117, entry.FiniteClient117):
            with self.subTest(selected=selected.__name__):
                self.assertIs(True, getattr(selected, 'initial_restart', False),
                    'the 117 root must discard its first floor once in both modes')

    def test_117_true_only_closed_start_shape_is_admitted(self):
        for selected, extras in ((entry.DeviceClient117, dict(continuous_campaign=True)),
                (entry.FiniteClient117, dict(yield_after_restart=True))):
            params = dict(run_id=ROOT, profile=SPEC.profile, initial_restart=True, **extras)
            with self.subTest(selected=selected.__name__):
                self.assertTrue(admitted(selected, params),
                    '117 must send a typed initial restart in its one closed start request')

    def test_117_does_not_silently_omit_the_initial_reset(self):
        for selected, extras in ((entry.DeviceClient117, dict(continuous_campaign=True)),
                (entry.FiniteClient117, dict(yield_after_restart=True))):
            with self.subTest(selected=selected.__name__):
                self.assertFalse(admitted(selected, dict(run_id=ROOT, profile=SPEC.profile, **extras)),
                    'an omitted initial mode is a different request and must fail closed')

    def test_continuous_pipeline_posts_the_flag_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary); base = destination/'test-117'; base.mkdir()
            server = ContinuousInitialServer117(base)
            result = baseline.ContinuousClientRun116Tests.run_client(self, server, base, destination, test_number='117')
            self.assertEqual(1, len(server.start_requests))
            self.assertIs(True, server.start_requests[0].get('initial_restart'),
                'the unique continuous native POST must carry the initial reset mode')
            self.assertTrue(result['ledger']['complete'])

    def test_finite_pipeline_posts_the_flag_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); server = FiniteInitialServer117(base, 'normal:unknown')
            record = cycle.run_session(server, base, protocol_spec=SPEC, clock=lambda:100, sleep=lambda _:None, notice=lambda _:None)
            starts = [params for method, params in server.calls if method == 'necro_native_start']
            self.assertEqual(1, len(starts))
            self.assertIs(True, starts[0].get('initial_restart'),
                'the unique finite native POST must carry the initial reset mode')
            self.assertTrue(record['resolved'])

    def test_116_keeps_omitting_and_rejecting_the_new_mode(self):
        for selected, extras in ((DeviceClient116, dict(continuous_campaign=True)),
                (FiniteClient116, dict(yield_after_restart=True))):
            params = dict(run_id=ROOT, profile=SPEC.profile, **extras)
            self.assertTrue(admitted(selected, params))
            self.assertFalse(admitted(selected, dict(params, initial_restart=True)))
            self.assertIs(False, getattr(selected, 'initial_restart', False))

    def test_false_untyped_flags_other_profiles_and_extra_fields_are_rejected(self):
        for selected, extras in ((entry.DeviceClient117, dict(continuous_campaign=True)),
                (entry.FiniteClient117, dict(yield_after_restart=True))):
            for flag in (False, 0, 1, None, 'true', []):
                with self.subTest(selected=selected.__name__, flag=flag):
                    self.assertFalse(admitted(selected, dict(run_id=ROOT, profile=SPEC.profile,
                        initial_restart=flag, **extras)))
            for extra in ({'profile':cycle.STANDARD_PROTOCOL.profile}, {'unexpected':True}):
                params = dict(run_id=ROOT, profile=SPEC.profile, initial_restart=True, **extras); params.update(extra)
                self.assertFalse(admitted(selected, params))

    def test_start_and_cancel_reply_mode_must_match_exactly(self):
        for continuous in (False, True):
            original = dict(run_id=ROOT, profile=SPEC.profile, state='accepted', api_version=cycle.API_VERSION, report={})
            original['continuous_campaign' if continuous else 'yield_after_restart'] = True
            parse = (lambda value, **kw:campaign.start_reply(value, ROOT, **kw)) if continuous else (
                lambda value, **kw:cycle.start_reply(value, ROOT, protocol_spec=SPEC, yield_after_restart=True, **kw))
            self.assertEqual('accepted', parse(original))
            valid = dict(original, initial_restart=True)
            self.assertEqual('accepted', parse(valid, initial_restart=True))
            with self.assertRaises(ProbeError): parse(valid)
            with self.assertRaises(ProbeError): parse(original, initial_restart=True)
            for flag in (False, 0, 1, None, 'true', []):
                with self.subTest(continuous=continuous, flag=flag), self.assertRaises(ProbeError):
                    parse(dict(original, initial_restart=flag), initial_restart=True)

    def test_trait_is_boolean_and_only_uses_the_irregular_protocol(self):
        class Client:
            protocol_spec = SPEC
            initial_restart = True
        self.assertTrue(cycle.initial_restart_enabled(Client()))
        for flag in (0, 1, None, 'true', []):
            client = Client(); client.initial_restart = flag
            with self.subTest(flag=flag), self.assertRaises(ProbeError): cycle.initial_restart_enabled(client)
        client = Client(); client.protocol_spec = cycle.STANDARD_PROTOCOL
        with self.assertRaises(ProbeError): cycle.initial_restart_enabled(client)

    def test_uncertain_initial_start_is_never_resent_in_either_pipeline(self):
        for continuous in (False, True):
            with self.subTest(continuous=continuous), tempfile.TemporaryDirectory() as temporary:
                dest = Path(temporary); base = dest/'test-117'; base.mkdir()
                if continuous:
                    server = ContinuousInitialServer117(base); server.start_failure = True
                    first = baseline.ContinuousClientRun116Tests.run_client(self, server, base, dest, test_number='117')
                    second = baseline.ContinuousClientRun116Tests.run_client(self, server, base, dest,
                        test_number='117', until_target=False, recovery_only=True)
                    self.assertEqual(first['ledger']['campaign_id'], second['ledger']['campaign_id'])
                    self.assertEqual(1, len(server.start_requests))
                else:
                    server = FiniteInitialServer117(base, 'normal:unknown'); server.fail_start = True
                    first = cycle.run_session(server, base, protocol_spec=SPEC, clock=lambda:100, notice=lambda _:None)
                    second = cycle.run_session(server, base, protocol_spec=SPEC, clock=lambda:100, notice=lambda _:None)
                    self.assertEqual(first['run_id'], second['run_id'])
                    self.assertEqual(1, sum(method=='necro_native_start' for method, _ in server.calls))

    def test_provenance_true_is_read_only_and_false_numeric_or_foreign_is_rejected(self):
        cases = [(flag, SPEC.profile) for flag in (True, False, 0, 1, None, 'true')]
        cases.append((True, cycle.STANDARD_PROTOCOL.profile))
        for flag, profile in cases:
            with self.subTest(flag=flag, profile=profile), tempfile.TemporaryDirectory() as temporary:
                model = restart_yield_model()
                revise(model, 0, lambda body:body['provenance'].update(initial_restart=flag, native_profile=profile))
                base = Path(temporary); record = store_model(base, model, protocol=SPEC)
                if flag is True and profile == SPEC.profile:
                    cycle.verify_evidence(base, record, protocol_spec=SPEC)
                else:
                    with self.assertRaisesRegex(ProbeError, 'cycle_record_identity'):
                        cycle.verify_evidence(base, record, protocol_spec=SPEC)


if __name__ == '__main__':
    unittest.main()
