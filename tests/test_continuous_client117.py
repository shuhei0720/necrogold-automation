"""TEST117 namespaces and capability gates over procedural client transports.

These contracts cover durable collection and preflight, not iPhone gameplay.
The missing 117 entry deliberately falls back to the actual 116 client for
the pre-implementation semantic Red.
"""
import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from necroprobe import campaign116 as campaign
from necroprobe import native_cycle as cycle
from necroprobe import test116 as shared_entry
from necroprobe.crypto import Crypto
from necroprobe.deadlines import OwnedRpcTimer
from necroprobe.protocol import HttpTransport
from necroprobe.test116 import DeviceClient116
from necroprobe.validation import ProbeError
from tests.test_protocol import KEY, TOK
import test_continuous_client116 as baseline
from test_forensic_orphan116 import OrphanServer116


VISIBLE_GOODS_CAPABILITY = 'necrogold_native_visible_goods_v1'
entry = (importlib.import_module('necroprobe.test117')
    if importlib.util.find_spec('necroprobe.test117') is not None else shared_entry)


def subject_client():
    if importlib.util.find_spec('necroprobe.test117') is None:
        return DeviceClient116
    from necroprobe.test117 import DeviceClient117
    return DeviceClient117


class ContinuousClientNamespace117Tests(unittest.TestCase):
    run_client = baseline.ContinuousClientRun116Tests.run_client

    def test_117_schema_is_a_distinct_supported_collection_namespace(self):
        ledger = campaign._fresh('a' * 32)
        ledger['schema'] = 'necroprobe-continuous-campaign117-v1'
        accepted = None
        try:
            accepted = campaign._validate(ledger)
        except ProbeError:
            pass
        self.assertIs(ledger, accepted,
            '117 collection must accept its own namespace without posing as 116')

    def test_old_default_retains_116_schema_and_number_is_a_closed_set(self):
        self.assertEqual('necroprobe-continuous-campaign116-v1', campaign._fresh()['schema'])
        self.assertEqual('necroprobe-continuous-campaign117-v1', campaign._fresh(test_number='117')['schema'])
        for value in ('120', '0117', '../117', '', 117, True, None, ['117']):
            with self.subTest(value=value), self.assertRaisesRegex(ProbeError, 'campaign_test_number_invalid'):
                campaign._fresh(test_number=value)
        for schema in ('necroprobe-continuous-campaign120-v1', [], None):
            ledger = campaign._fresh(); ledger['schema'] = schema
            with self.subTest(schema=schema), self.assertRaisesRegex(ProbeError, 'campaign_ledger_invalid'):
                campaign._validate(ledger)

    def test_selector_and_selectorless_history_refuse_another_requested_number(self):
        for selector in (True, False):
            with self.subTest(selector=selector), tempfile.TemporaryDirectory() as temporary:
                base = Path(temporary)
                ledger = campaign._fresh(test_number='117'); ledger['start_intent'] = True
                campaign._save(base, ledger)
                if not selector:
                    (base/'continuous-campaign.json').unlink()
                with self.assertRaisesRegex(ProbeError, 'campaign_test_number_mismatch'):
                    campaign._load(base)
                self.assertEqual(ledger, campaign._load(base, test_number='117'))

    def test_selected_history_cannot_swap_to_another_schema_at_the_same_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary); ledger = campaign._fresh(test_number='117')
            campaign._save(base, ledger)
            ledger['schema'] = campaign.LEDGER_SCHEMAS['116']
            cycle._atomic(base/'continuous-campaigns'/(ledger['campaign_id']+'.json'), cycle.canonical(ledger))
            with self.assertRaisesRegex(ProbeError, 'campaign_test_number_mismatch'):
                campaign._load(base, test_number='117')

    def test_number_mismatch_and_wrong_spool_make_no_native_requests(self):
        for wrong_spool in (False, True):
            with self.subTest(wrong_spool=wrong_spool), tempfile.TemporaryDirectory() as temporary:
                dest = Path(temporary); base = dest/'spool'/('test-116' if wrong_spool else 'test-117')
                base.mkdir(parents=True)
                if not wrong_spool:
                    campaign._save(base, campaign._fresh())
                server = baseline.ContinuousServer116(base)
                with self.assertRaisesRegex(ProbeError, 'campaign_test_number_mismatch'):
                    self.run_client(server, base, dest, test_number='117')
                self.assertEqual([], server.calls)

    def test_117_live_chain_uses_117_names_and_retains_every_published_child(self):
        with tempfile.TemporaryDirectory() as temporary:
            dest = Path(temporary); base = dest/'spool'/'test-117'; base.mkdir(parents=True)
            server = baseline.ContinuousServer116(base)
            result = self.run_client(server, base, dest, test_number='117')
            ledger = result['ledger']
            self.assertTrue(ledger['complete'])
            self.assertEqual(campaign.LEDGER_SCHEMAS['117'], ledger['schema'])
            self.assertEqual([], server.exports_while_live)
            self.assertTrue(result['campaign_archive'].name.startswith('test-117-campaign-'))
            for row in ledger['runs']:
                self.assertEqual('test-117-'+row['run_id']+'.zip', row['archive_name'])
                with zipfile.ZipFile(dest/'runtime'/row['archive_name']) as archive:
                    self.assertTrue(all(name.startswith('test-117/') for name in archive.namelist()))
            with zipfile.ZipFile(result['campaign_archive']) as archive:
                self.assertEqual(ledger, json.loads(archive.read('campaign-index.json')))
                self.assertEqual(['campaign-index.json', 'last-run/'+ledger['runs'][-1]['archive_name']], archive.namelist())
            self.assertEqual([], list((dest/'runtime').glob('test-116*')))
            self.assertEqual(1, sum(method=='necro_native_start' for method, _ in server.calls))

    def test_117_uncertain_start_recovers_same_root_without_another_post(self):
        with tempfile.TemporaryDirectory() as temporary:
            dest = Path(temporary); base = dest/'spool'/'test-117'; base.mkdir(parents=True)
            server = baseline.ContinuousServer116(base); server.start_failure = True
            first = self.run_client(server, base, dest, test_number='117')
            root = first['ledger']['campaign_id']
            self.assertTrue(first['ledger']['start_intent'])
            result = self.run_client(server, base, dest, test_number='117', until_target=False, recovery_only=True)
            self.assertEqual(root, result['ledger']['campaign_id'])
            self.assertTrue(result['ledger']['complete'])
            self.assertEqual(1, sum(method=='necro_native_start' for method, _ in server.calls))
            self.assertTrue(all(not params['keepalive'] for method, params in server.calls
                if params.get('mode')=='campaign_status'))

    def test_117_orphan_remains_diagnostic_and_retains_original_scope(self):
        with tempfile.TemporaryDirectory() as temporary:
            dest = Path(temporary); base = dest/'spool'/'test-117'; base.mkdir(parents=True)
            server = OrphanServer116(base, header=False, artifacts=True)
            result = self.run_client(server, base, dest, test_number='117')
            self.assertTrue(result['ledger']['collection_complete'])
            self.assertFalse(result['ledger']['complete'])
            row = result['ledger']['runs'][-1]
            self.assertEqual('test-117-'+row['run_id']+'.zip', row['archive_name'])
            self.assertTrue(row['diagnostic_only']); self.assertFalse(row['verified'])
            self.assertEqual('device_retained_not_transferred', row['diagnostic_collection']['opaque_uncommitted_bytes'])
            native = result['ledger']['native_status']
            self.assertEqual(4, native['input_state']); self.assertTrue(native['ui_frozen'])
            self.assertEqual(1, sum(method=='necro_native_start' for method, _ in server.calls))

    def test_117_closed_recovery_rechecks_saved_publication_without_new_start(self):
        with tempfile.TemporaryDirectory() as temporary:
            dest = Path(temporary); base = dest/'spool'/'test-117'; base.mkdir(parents=True)
            server = baseline.ContinuousServer116(base)
            first = self.run_client(server, base, dest, test_number='117')
            (base/'continuous-campaign.json').unlink()
            result = self.run_client(server, base, dest, test_number='117', until_target=False, recovery_only=True)
            self.assertEqual(first['ledger']['campaign_id'], result['ledger']['campaign_id'])
            self.assertTrue(result['ledger']['complete'])
            self.assertEqual(1, sum(method=='necro_native_start' for method, _ in server.calls))


class ContinuousClientCapability117Tests(unittest.TestCase):
    def test_117_client_requires_visible_goods_implementation(self):
        self.assertIn(VISIBLE_GOODS_CAPABILITY, subject_client().required_capabilities,
            'the same API version with the old IPA cannot start TEST117')

    def test_both_modes_require_new_capability_without_changing_old_client(self):
        self.assertNotIn(VISIBLE_GOODS_CAPABILITY, DeviceClient116.required_capabilities)
        self.assertEqual(DeviceClient116.required_capabilities | {VISIBLE_GOODS_CAPABILITY},
            entry.DeviceClient117.required_capabilities)
        self.assertIn(VISIBLE_GOODS_CAPABILITY, entry.FiniteClient117.required_capabilities)
        self.assertFalse(entry.DeviceClient117.yield_after_restart)
        self.assertFalse(entry.DeviceClient117.allow_restarted_budget)

    def test_old_ipa_schema_blocks_before_continuous_native_start(self):
        class Transport(HttpTransport):
            def schema(self, _timeout):
                return cycle.canonical(self.metadata)
            def _exchange(self, *args):
                raise AssertionError('this schema gate fixture must never send an RPC')
        for selected in (entry.DeviceClient117, entry.FiniteClient117):
            with self.subTest(selected=selected.__name__), tempfile.TemporaryDirectory() as temporary, OwnedRpcTimer() as timer:
                dest = Path(temporary); base = dest/'test-117'; base.mkdir()
                transport = Transport()
                transport.metadata = dict(server_version=cycle.API_VERSION, protocol_version=1,
                    capability_tags=list({cycle.CAPABILITY, cycle.IRREGULAR_PROTOCOL.capability} |
                        selected.required_capabilities - {VISIBLE_GOODS_CAPABILITY}))
                client = selected(transport, KEY, TOK, deadline_owner=timer, crypto=Crypto(native=False))
                server = baseline.ContinuousServer116(base); server.check_schema = client.check_schema
                with self.assertRaisesRegex(ProbeError, 'native_capability_missing'):
                    baseline.ContinuousClientRun116Tests.run_client(self, server, base, dest, test_number='117')
                self.assertEqual([], server.calls)
                transport.metadata['capability_tags'].append(VISIBLE_GOODS_CAPABILITY)
                self.assertEqual(cycle.IRREGULAR_PROTOCOL.capability,
                    cycle.CycleClient.check_schema(client)['capability'])


class ContinuousClientEntry117Tests(unittest.TestCase):
    def test_check_and_finite_routing_have_117_identity(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(0, entry.main(['--check']))
        self.assertEqual('native-device-failures-trial-v117 / '+cycle.API_VERSION+'\n', output.getvalue())
        with tempfile.TemporaryDirectory() as temporary, patch.object(Path, 'home', return_value=Path(temporary)), \
                patch.object(shared_entry, 'device_main', return_value=7) as finite:
            self.assertEqual(7, entry.main([]))
        self.assertEqual('117', finite.call_args.kwargs['test_number'])
        self.assertIs(entry.FiniteClient117, finite.call_args.kwargs['client_class'])

    def test_continuous_and_saved_recovery_pass_exact_namespace_and_no_mode_mix(self):
        for recovery in (False, True):
            with self.subTest(recovery=recovery), tempfile.TemporaryDirectory() as temporary:
                home = Path(temporary); spool = home/'.necroprobe'/'runtime'/'test-117'
                if recovery:
                    spool.mkdir(parents=True); (spool/'continuous-campaign.json').write_text('{}')
                ledger = campaign._fresh(test_number='117')
                result = dict(ledger=ledger, campaign_archive=None, stop_reason=None, record=None)
                with patch.object(Path, 'home', return_value=home), \
                        patch.object(shared_entry, 'load_pairing', return_value=(KEY,TOK)), \
                        patch.object(campaign, 'run', return_value=result) as run, redirect_stdout(io.StringIO()):
                    self.assertEqual(2, entry.main(['--recovery' if recovery else '--until-target', '--python-crypto']))
                self.assertIsInstance(run.call_args.args[0], entry.DeviceClient117)
                self.assertEqual('117', run.call_args.kwargs['test_number'])
                self.assertEqual(spool, run.call_args.kwargs['spool'])
                self.assertIs(recovery, run.call_args.kwargs['recovery_only'])
                self.assertIs(not recovery, run.call_args.kwargs['until_target'])


if __name__ == '__main__':
    unittest.main()
