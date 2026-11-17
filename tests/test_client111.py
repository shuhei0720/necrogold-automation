"""TEST111 extra capability gate and explicit entry; no device traffic."""
from contextlib import redirect_stdout
import io
from pathlib import Path
import unittest
from unittest.mock import patch

from necroprobe import native_cycle as cycle
from necroprobe import test099, test110, test111
from necroprobe.deadlines import OwnedRpcTimer
from necroprobe.protocol import HttpTransport
from necroprobe.trial_evidence099 import IrregularTrialClient110, SUPPORT, TrialClient099
from necroprobe.validation import ProbeError

KEY = bytes(range(32))
TOKEN = 'test111-token'


class SchemaTransport(HttpTransport):
    def __init__(self, caps):
        super().__init__()
        self.caps = caps
        self.schema_calls = 0

    def schema(self, _timeout):
        self.schema_calls += 1
        return cycle.canonical(dict(server_version=cycle.API_VERSION, protocol_version=1,
                                    capability_tags=self.caps))


def support_reply(client, method, params):
    return dict(schema=client.protocol_spec.schema, run_id=client.trial_probe_id,
                profile=client.protocol_spec.profile, mode='trial_support', payload=SUPPORT)


class ImagePriceClient111Tests(unittest.TestCase):
    def test_old_ipa_is_rejected_before_trial_support_or_game_start(self):
        transport = SchemaTransport([cycle.CAPABILITY, cycle.IRREGULAR_PROTOCOL.capability])
        with OwnedRpcTimer() as timer:
            client = test111.ImagePriceClient111(transport, KEY, TOKEN, deadline_owner=timer)
            with patch.object(cycle, '_call', side_effect=support_reply) as calls:
                with self.assertRaisesRegex(ProbeError, 'native_capability_missing'):
                    client.check_schema()
                calls.assert_not_called()
        self.assertEqual(1, transport.schema_calls)

    def test_new_cap_is_additional_and_uses_one_schema_request(self):
        caps = [cycle.CAPABILITY, cycle.IRREGULAR_PROTOCOL.capability,
                test111.IMAGE_PRICE_CAPABILITY, 'unrelated-future-tag']
        transport = SchemaTransport(caps)
        with OwnedRpcTimer() as timer:
            client = test111.ImagePriceClient111(transport, KEY, TOKEN, deadline_owner=timer)
            with patch.object(cycle, '_call', side_effect=support_reply) as calls:
                self.assertEqual(dict(api_version=cycle.API_VERSION,
                                      capability=cycle.IRREGULAR_PROTOCOL.capability), client.check_schema())
                self.assertEqual(1, calls.call_count)
                self.assertEqual(cycle.IRREGULAR_PROTOCOL.query, calls.call_args.args[1])
        self.assertEqual(1, transport.schema_calls)

    def test_old_clients_keep_their_default_capability_contract(self):
        caps = [cycle.CAPABILITY, cycle.IRREGULAR_PROTOCOL.capability]
        with OwnedRpcTimer() as timer:
            for client_type in (TrialClient099, IrregularTrialClient110):
                client = client_type(SchemaTransport(caps), KEY, TOKEN, deadline_owner=timer)
                with self.subTest(client=client_type.__name__), patch.object(cycle, '_call', side_effect=support_reply):
                    self.assertEqual(client.protocol_spec.capability, client.check_schema()['capability'])

    def test_entry_check_identifies_new_client_and_keeps_test110_default(self):
        for main, expected in ((test111.main, 'native-image-price-trial-v1'),
                               (test110.main, 'native-irregular-trial-v1')):
            output = io.StringIO()
            with self.subTest(entry=main.__module__), redirect_stdout(output):
                self.assertEqual(0, main(['--check']))
            self.assertEqual(expected + ' / 1.98.16-ngg2\n', output.getvalue())

    def test_entry_client_must_match_explicit_protocol_identity(self):
        for client_type in (TrialClient099, object, lambda: None):
            with self.subTest(client=repr(client_type)), self.assertRaisesRegex(ValueError, 'invalid trial client'):
                test099.main(['--check'], protocol_spec=cycle.IRREGULAR_PROTOCOL,
                             client_class=client_type)

    def test_entry_selects_only_new_explicit_client(self):
        with patch.object(test111, 'device_main', return_value=7) as main:
            self.assertEqual(7, test111.main(['--recovery']))
        self.assertEqual(dict(test_number='111', protocol_spec=cycle.IRREGULAR_PROTOCOL,
                              client_class=test111.ImagePriceClient111), main.call_args.kwargs)
        self.assertEqual(['--recovery'], main.call_args.args[0])

    def test_capability_is_advertised_without_changing_api_or_profile(self):
        source = (Path(__file__).resolve().parents[1] / 'patches/loopctrl/ngg2.patch').read_text()
        self.assertEqual(1, source.count('"' + test111.IMAGE_PRICE_CAPABILITY + '"'))
        self.assertEqual('1.98.16-ngg2', cycle.API_VERSION)
        self.assertIs(cycle.IRREGULAR_PROTOCOL, test111.ImagePriceClient111.protocol_spec)


if __name__ == '__main__':
    unittest.main()
