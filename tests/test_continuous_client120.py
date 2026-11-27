"""TEST120 client identity, implementation gate and isolated durable collection.

Transport fixtures are procedural; these checks do not prove iPhone gameplay.
The existing 119 entry is the runnable subject before the 120 implementation.
"""
import importlib
import importlib.util
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from necroprobe import campaign116 as campaign
from necroprobe import native_cycle as cycle
from necroprobe import test116 as shared_entry
from necroprobe import test119 as previous
from necroprobe.crypto import Crypto
from necroprobe.deadlines import OwnedRpcTimer
from necroprobe.protocol import HttpTransport
from necroprobe.validation import ProbeError
from tests.test_protocol import KEY, TOK
import test_continuous_client116 as baseline
from test_initial_restart117 import ContinuousInitialServer117, FiniteInitialServer117


ROOT = Path(__file__).resolve().parents[1]
IMPLEMENTATION_CAPABILITY = 'necrogold_native_device_fixes120_v1'
entry = (importlib.import_module('necroprobe.test120')
    if importlib.util.find_spec('necroprobe.test120') is not None else previous)


def clients():
    return (getattr(entry, 'DeviceClient120', previous.DeviceClient119),
        getattr(entry, 'FiniteClient120', previous.FiniteClient119))


class ContinuousServer120(ContinuousInitialServer117):
    def __init__(self, base):
        super().__init__(base)
        selected = clients()[0]
        self.initial_restart = selected.initial_restart
        self.initial_validator = selected(lambda *_: b'', KEY, TOK, crypto=Crypto(native=False))


class FiniteServer120(FiniteInitialServer117):
    def __init__(self, base):
        super().__init__(base, 'normal:unknown')
        selected = clients()[1]
        self.initial_restart = selected.initial_restart
        self.initial_validator = selected(lambda *_: b'', KEY, TOK, crypto=Crypto(native=False))

    def call(self, method, params):
        self.initial_validator._validate(method, params)
        return super().call(method, params)


class ContinuousClient120Tests(unittest.TestCase):
    run_client = baseline.ContinuousClientRun116Tests.run_client

    def fresh120(self):
        try:
            ledger = campaign._fresh(test_number='120')
        except ProbeError as error:
            self.fail('the TEST120 collection namespace was rejected: '+error.code)
        return ledger

    def run120(self, server, base, destination, **options):
        try:
            return self.run_client(server, base, destination, test_number='120', **options)
        except ProbeError as error:
            self.fail('the TEST120 client pipeline was rejected: '+error.code)

    def test_both_modes_require_120_implementation_without_changing_old_clients(self):
        for selected, old in zip(clients(), (previous.DeviceClient119, previous.FiniteClient119)):
            with self.subTest(selected=selected.__name__):
                self.assertEqual(old.required_capabilities | {IMPLEMENTATION_CAPABILITY},
                    selected.required_capabilities,
                    'an unchanged API number must not admit the old TEST119 IPA')
                self.assertNotIn(IMPLEMENTATION_CAPABILITY, old.required_capabilities)
                self.assertIs(True, selected.initial_restart)
        self.assertEqual('1.98.16-ngg2', cycle.API_VERSION)
        self.assertFalse(clients()[0].yield_after_restart)
        self.assertFalse(clients()[0].allow_restarted_budget)

    def test_old_ipa_is_blocked_before_either_pipeline_sends_native_requests(self):
        class Transport(HttpTransport):
            def schema(self, _timeout):
                return cycle.canonical(self.metadata)

            def _exchange(self, *args):
                raise AssertionError('the schema fixture cannot send an RPC')

        for continuous, selected in zip((True, False), clients()):
            with self.subTest(continuous=continuous), tempfile.TemporaryDirectory() as temporary, OwnedRpcTimer() as timer:
                destination = Path(temporary); base = destination/'test-120'; base.mkdir()
                transport = Transport()
                transport.metadata = dict(server_version=cycle.API_VERSION, protocol_version=1,
                    capability_tags=list(({cycle.CAPABILITY, cycle.IRREGULAR_PROTOCOL.capability}
                        | selected.required_capabilities) - {IMPLEMENTATION_CAPABILITY}))
                client = selected(transport, KEY, TOK, deadline_owner=timer, crypto=Crypto(native=False))
                server = ContinuousServer120(base) if continuous else FiniteServer120(base)
                server.check_schema = client.check_schema
                if continuous:
                    with self.assertRaisesRegex(ProbeError, 'native_capability_missing'):
                        self.run_client(server, base, destination, test_number='120')
                else:
                    record = cycle.run_session(server, destination, protocol_spec=cycle.IRREGULAR_PROTOCOL,
                        clock=lambda:100, sleep=lambda _:None, notice=lambda _:None)
                    self.assertEqual('native_capability_missing', record['last_error'])
                    self.assertFalse(record['start_intent'])
                self.assertEqual([], server.calls)
                transport.metadata['capability_tags'].append(IMPLEMENTATION_CAPABILITY)
                self.assertEqual(cycle.IRREGULAR_PROTOCOL.capability,
                    cycle.CycleClient.check_schema(client)['capability'])

    def test_120_schema_is_distinct_and_only_supported_numbers_are_admitted(self):
        ledger = self.fresh120()
        self.assertEqual('necroprobe-continuous-campaign120-v1', ledger['schema'])
        self.assertIs(ledger, campaign._validate(ledger, test_number='120'))
        self.assertEqual('necroprobe-continuous-campaign116-v1', campaign._fresh()['schema'])
        self.assertEqual('necroprobe-continuous-campaign117-v1', campaign._fresh(test_number='117')['schema'])
        self.assertEqual('necroprobe-continuous-campaign118-v1', campaign._fresh(test_number='118')['schema'])
        self.assertEqual('necroprobe-continuous-campaign119-v1', campaign._fresh(test_number='119')['schema'])
        for number in ('126', '0120', '../120', '', 120, True, None, ['120']):
            with self.subTest(number=number), self.assertRaisesRegex(ProbeError, 'campaign_test_number_invalid'):
                campaign._fresh(test_number=number)
        for schema in ('necroprobe-continuous-campaign126-v1', [], None):
            bad = dict(ledger, schema=schema)
            with self.subTest(schema=schema), self.assertRaisesRegex(ProbeError, 'campaign_ledger_invalid'):
                campaign._validate(bad)

    def test_116_117_118_119_120_histories_remain_isolated_with_or_without_selector(self):
        self.fresh120()
        for number in ('116', '117', '118', '119', '120'):
            for selector in (True, False):
                with self.subTest(number=number, selector=selector), tempfile.TemporaryDirectory() as temporary:
                    base = Path(temporary); ledger = campaign._fresh(test_number=number)
                    ledger['start_intent'] = True; campaign._save(base, ledger)
                    if not selector:
                        (base/'continuous-campaign.json').unlink()
                    self.assertEqual(ledger, campaign._load(base, test_number=number))
                    for wrong in {'116', '117', '118', '119', '120'} - {number}:
                        with self.subTest(wrong=wrong), self.assertRaisesRegex(ProbeError, 'campaign_test_number_mismatch'):
                            campaign._load(base, test_number=wrong)

    def test_wrong_history_or_spool_makes_no_native_request(self):
        self.fresh120()
        for prior in ('116', '117', '118', '119'):
            for wrong_spool in (False, True):
                with self.subTest(prior=prior, wrong_spool=wrong_spool), tempfile.TemporaryDirectory() as temporary:
                    destination = Path(temporary)
                    base = destination/'spool'/('test-'+prior if wrong_spool else 'test-120')
                    base.mkdir(parents=True)
                    if not wrong_spool:
                        campaign._save(base, campaign._fresh(test_number=prior))
                    server = ContinuousServer120(base)
                    refused = None
                    try:
                        self.run_client(server, base, destination, test_number='120')
                    except (ProbeError, OSError) as error:
                        refused = error
                    self.assertEqual([], server.calls)
                    self.assertIsInstance(refused, ProbeError)
                    self.assertEqual('campaign_test_number_mismatch', refused.code)

    def test_live_chain_keeps_120_archives_and_posts_initial_restart_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary); base = destination/'spool'/'test-120'; base.mkdir(parents=True)
            server = ContinuousServer120(base)
            result = self.run120(server, base, destination)
            ledger = result['ledger']
            self.assertTrue(ledger['complete'])
            self.assertEqual('necroprobe-continuous-campaign120-v1', ledger['schema'])
            self.assertEqual([], server.exports_while_live)
            self.assertEqual(1, len(server.start_requests))
            self.assertIs(True, server.start_requests[0].get('initial_restart'))
            self.assertTrue(result['campaign_archive'].name.startswith('test-120-campaign-'))
            for row in ledger['runs']:
                self.assertEqual('test-120-'+row['run_id']+'.zip', row['archive_name'])
                with zipfile.ZipFile(destination/'runtime'/row['archive_name']) as archive:
                    self.assertTrue(all(name.startswith('test-120/') for name in archive.namelist()))
            with zipfile.ZipFile(result['campaign_archive']) as archive:
                self.assertEqual(ledger, json.loads(archive.read('campaign-index.json')))
            self.assertFalse(any((destination/'runtime').glob('test-116*')))
            self.assertFalse(any((destination/'runtime').glob('test-117*')))
            self.assertFalse(any((destination/'runtime').glob('test-118*')))
            self.assertFalse(any((destination/'runtime').glob('test-119*')))

    def test_uncertain_start_recovers_same_root_without_a_second_post(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary); base = destination/'spool'/'test-120'; base.mkdir(parents=True)
            server = ContinuousServer120(base); server.start_failure = True
            first = self.run120(server, base, destination)
            root = first['ledger']['campaign_id']
            second = self.run120(server, base, destination, until_target=False, recovery_only=True)
            self.assertEqual(root, second['ledger']['campaign_id'])
            self.assertTrue(second['ledger']['complete'])
            self.assertEqual(1, len(server.start_requests))
            self.assertTrue(all(not params['keepalive'] for method, params in server.calls
                if params.get('mode')=='campaign_status'))

    def test_finite_mode_keeps_the_single_initial_restart_post(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary); server = FiniteServer120(destination)
            record = cycle.run_session(server, destination, protocol_spec=cycle.IRREGULAR_PROTOCOL,
                clock=lambda:100, sleep=lambda _:None, notice=lambda _:None)
            starts = [params for method, params in server.calls if method=='necro_native_start']
            self.assertEqual(1, len(starts))
            self.assertIs(True, starts[0].get('initial_restart'))
            self.assertTrue(record['resolved'])

    def test_check_and_finite_entry_use_120_identity(self):
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(0, entry.main(['--check']))
        self.assertEqual('native-device-failures-trial-v120 / '+cycle.API_VERSION+'\n', output.getvalue())
        with tempfile.TemporaryDirectory() as temporary, patch.object(Path, 'home', return_value=Path(temporary)), \
                patch.object(shared_entry, 'device_main', return_value=7) as finite:
            self.assertEqual(7, entry.main([]))
        self.assertEqual('120', finite.call_args.kwargs['test_number'])
        self.assertIs(clients()[1], finite.call_args.kwargs['client_class'])

    def test_continuous_and_saved_recovery_entry_keep_120_namespace(self):
        for recovery in (False, True):
            with self.subTest(recovery=recovery), tempfile.TemporaryDirectory() as temporary:
                home = Path(temporary); spool = home/'.necroprobe'/'runtime'/'test-120'
                if recovery:
                    spool.mkdir(parents=True); (spool/'continuous-campaign.json').write_text('{}')
                result = dict(ledger=self.fresh120(), campaign_archive=None, stop_reason=None, record=None)
                with patch.object(Path, 'home', return_value=home), \
                        patch.object(shared_entry, 'load_pairing', return_value=(KEY, TOK)), \
                        patch.object(campaign, 'run', return_value=result) as run, redirect_stdout(io.StringIO()):
                    self.assertEqual(2, entry.main(['--recovery' if recovery else '--until-target', '--python-crypto']))
                self.assertIsInstance(run.call_args.args[0], clients()[0])
                self.assertEqual('120', run.call_args.kwargs['test_number'])
                self.assertEqual(spool, run.call_args.kwargs['spool'])
                self.assertIs(recovery, run.call_args.kwargs['recovery_only'])
                self.assertIs(not recovery, run.call_args.kwargs['until_target'])

    def test_shell_has_120_identity_and_rejects_conflicting_modes_before_device_use(self):
        shell = ROOT/'test_120.sh'
        if not shell.exists():
            shell = ROOT/'test_119.sh'
        syntax = subprocess.run(['sh', '-n', str(shell)], capture_output=True, text=True)
        self.assertEqual(0, syntax.returncode, syntax.stderr)
        refused = subprocess.run(['sh', str(shell), '--until-target', '--recovery'], capture_output=True, text=True)
        self.assertEqual(2, refused.returncode)
        self.assertIn('TEST-120:', refused.stderr)
        self.assertIn('--until-target と --recovery', refused.stderr)
        for arguments in (('--forged',), ('--recovery', '--until-target', '--python-crypto', '--forged')):
            with self.subTest(arguments=arguments):
                refused = subprocess.run(['sh', str(shell), *arguments], capture_output=True, text=True)
                self.assertEqual(2, refused.returncode)
                self.assertIn('TEST-120:', refused.stderr)


if __name__ == '__main__':
    unittest.main()
