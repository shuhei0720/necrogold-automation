"""TEST112 explicit extra capability/start flag; no device or native compiler."""
import importlib.util
import inspect
import io
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from necroprobe import native_cycle as cycle
from necroprobe import test110, test111
from necroprobe.deadlines import OwnedRpcTimer
from necroprobe.validation import ProbeError
from tests.test_client111 import SchemaTransport, support_reply, KEY, TOKEN

if importlib.util.find_spec('necroprobe.test112') is not None:
    from necroprobe import test112
else:
    test112 = None

YIELD_CAP = 'necrogold_native_restart_yield_v1'


def client_type():
    return test112.RestartYieldClient112 if test112 is not None else test111.ImagePriceClient111


def reply(value, *, enabled=False, protocol=cycle.IRREGULAR_PROTOCOL):
    options = dict(protocol_spec=protocol)
    if 'yield_after_restart' in inspect.signature(cycle.start_reply).parameters:
        options['yield_after_restart'] = enabled
    return cycle.start_reply(value, 'a' * 32, **options)


class YieldServer:
    protocol_spec = cycle.IRREGULAR_PROTOCOL
    yield_after_restart = True
    allow_restarted_budget = True

    def __init__(self): self.calls = []
    def check_schema(self): return {}
    def call(self, method, params):
        self.calls.append((method, dict(params)))
        if method in ('necro_native_start', 'necro_native_cancel'):
            return dict(run_id=params['run_id'], profile=self.protocol_spec.profile,
                state='accepted', api_version=cycle.API_VERSION, report={}, yield_after_restart=True)
        if params['mode'] == 'prepare':
            return dict(schema=self.protocol_spec.schema, run_id=params['run_id'],
                profile=self.protocol_spec.profile, mode='prepare', payload=dict(ready=True,
                notification_authorization='authorized', recovery_scan='ready', unpublished_run_ids=[], reason='none'))
        raise ProbeError('test_collection_interrupted')


class RestartYieldClient112Tests(unittest.TestCase):
    def test_image_price_ipa_without_restart_yield_cap_is_rejected_before_support(self):
        transport = SchemaTransport([cycle.CAPABILITY, cycle.IRREGULAR_PROTOCOL.capability,
                                     test111.IMAGE_PRICE_CAPABILITY])
        with OwnedRpcTimer() as timer:
            client = client_type()(transport, KEY, TOKEN, deadline_owner=timer)
            with patch.object(cycle, '_call', side_effect=support_reply) as calls:
                with self.assertRaisesRegex(ProbeError, 'native_capability_missing'): client.check_schema()
                calls.assert_not_called()
        self.assertEqual(1, transport.schema_calls)

    def test_both_new_capabilities_are_required_by_the_same_schema_request(self):
        required = [cycle.CAPABILITY, cycle.IRREGULAR_PROTOCOL.capability,
                    test111.IMAGE_PRICE_CAPABILITY, YIELD_CAP]
        for missing in (None, test111.IMAGE_PRICE_CAPABILITY, YIELD_CAP):
            transport = SchemaTransport([v for v in required if v != missing])
            with OwnedRpcTimer() as timer:
                client = client_type()(transport, KEY, TOKEN, deadline_owner=timer)
                with self.subTest(missing=missing), patch.object(cycle, '_call', side_effect=support_reply) as calls:
                    if missing is None:
                        client.check_schema(); self.assertEqual(1, calls.call_count)
                    else:
                        with self.assertRaises(ProbeError): client.check_schema()
                        calls.assert_not_called()
            self.assertEqual(1, transport.schema_calls)

    def test_only_optin_irregular_client_admits_literal_true_start_flag(self):
        with OwnedRpcTimer() as timer:
            client = client_type()(SchemaTransport([]), KEY, TOKEN, deadline_owner=timer)
            good = dict(run_id='a' * 32, profile=cycle.IRREGULAR_PROTOCOL.profile, yield_after_restart=True)
            failure = None
            try: client._validate('necro_native_start', good)
            except ProbeError as error: failure = error.code
            self.assertIsNone(failure, 'new explicit optin start must be admitted')
            for value in (False, 0, 1, 'true', None):
                with self.subTest(value=value), self.assertRaises(ProbeError):
                    client._validate('necro_native_start', dict(good, yield_after_restart=value))
            for params in (dict(run_id='a' * 32, profile=cycle.IRREGULAR_PROTOCOL.profile),
                           dict(good, profile=cycle.PROFILE)):
                with self.assertRaises(ProbeError): client._validate('necro_native_start', params)
            for method, params in (('necro_native_cancel', dict(run_id='a' * 32, yield_after_restart=True)),
                    (cycle.IRREGULAR_PROTOCOL.query, dict(run_id='a' * 32, mode='prepare', request_authorization=False, yield_after_restart=True))):
                with self.assertRaises(ProbeError): client._validate(method, params)

    def test_legacy_clients_keep_flag_omission_and_refuse_any_extra_flag(self):
        with OwnedRpcTimer() as timer:
            for cls in (cycle.CycleClient, cycle.IrregularCycleClient, test111.ImagePriceClient111):
                client = cls(SchemaTransport([]), KEY, TOKEN, deadline_owner=timer)
                base = dict(run_id='a' * 32, profile=client.protocol_spec.profile)
                client._validate('necro_native_start', base)
                for value in (True, False, 0, 1):
                    with self.subTest(client=cls.__name__, value=value), self.assertRaises(ProbeError):
                        client._validate('necro_native_start', dict(base, yield_after_restart=value))

    def test_actual_start_post_has_flag_and_uncertain_recovery_never_posts_again(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); server = YieldServer()
            first = cycle.run_session(server, base, notice=lambda _: None, protocol_spec=cycle.IRREGULAR_PROTOCOL)
            posts = [p for m,p in server.calls if m == 'necro_native_start']
            self.assertEqual(1, len(posts)); self.assertIs(posts[0].get('yield_after_restart'), True)
            self.assertTrue(first['start_intent']); self.assertFalse(first['resolved'])
            second = cycle.run_session(server, base, notice=lambda _: None, protocol_spec=cycle.IRREGULAR_PROTOCOL)
            self.assertEqual(first['run_id'], second['run_id'])
            self.assertEqual(1, sum(m == 'necro_native_start' for m,_ in server.calls))

    def test_start_reply_flag_is_explicit_exact_and_never_selects_its_own_context(self):
        old = dict(run_id='a' * 32, profile=cycle.IRREGULAR_PROTOCOL.profile,
                   state='accepted', api_version=cycle.API_VERSION, report={})
        new = dict(old, yield_after_restart=True)
        failure = None
        try: result = reply(new, enabled=True)
        except ProbeError as error: failure = error.code; result = None
        self.assertIsNone(failure); self.assertEqual('accepted', result)
        self.assertEqual('accepted', reply(old))
        with self.assertRaises(ProbeError): reply(new)
        for value in (old, dict(new, yield_after_restart=False), dict(new, yield_after_restart=1), dict(new, extra=True)):
            with self.subTest(value=value), self.assertRaises(ProbeError): reply(value, enabled=True)
        with self.assertRaises(ProbeError): reply(dict(new, profile=cycle.PROFILE), enabled=True, protocol=cycle.STANDARD_PROTOCOL)

    def test_entry_identifies_explicit_client_and_keeps_110_111_labels(self):
        self.assertIsNotNone(test112)
        for main, label in ((test112.main, 'native-restart-yield-trial-v1'),
                            (test111.main, 'native-image-price-trial-v1'),
                            (test110.main, 'native-irregular-trial-v1')):
            output = io.StringIO()
            with self.subTest(label=label), redirect_stdout(output): self.assertEqual(0, main(['--check']))
            self.assertEqual(label + ' / 1.98.16-ngg2\n', output.getvalue())
        with patch.object(test112, 'device_main', return_value=7) as main:
            self.assertEqual(7, test112.main(['--recovery']))
        self.assertIs(main.call_args.kwargs['client_class'], test112.RestartYieldClient112)
        self.assertIs(main.call_args.kwargs['protocol_spec'], cycle.IRREGULAR_PROTOCOL)
        self.assertEqual('112', main.call_args.kwargs['test_number'])


if __name__ == '__main__': unittest.main()
