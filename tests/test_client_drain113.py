"""TEST113: current native drain status through the real Python client flow.

Transport and game results are procedural fixtures. Journal, collection,
publication, and campaign code are production; these are not phone tests.
"""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from necroprobe import campaign099 as campaign
from necroprobe import cycle_publication as publication
from necroprobe import native_cycle as cycle
from necroprobe import native_walk
from necroprobe.irregular import STATUS_NUMBERS
from necroprobe.validation import ProbeError
from tests.test_native_cycle_client094 import Server, RUN
from tests.test_restart_yield112 import RestartYieldServer112, SPEC


def draining(server, **changes):
    # NG2Runtime.cyclePayload: terminal && lease => draining;
    # cycleWorkersDrainedLocked includes !lease, so workers_drained is false.
    value = server.status(state='draining', terminal=True,
        workers_drained=False, native_inflight=False)
    value.update(changes)
    return value


def wrap(value, protocol=cycle.STANDARD_PROTOCOL):
    return dict(schema=protocol.schema, profile=protocol.profile, run_id=RUN,
        mode='status', payload=value)


class DrainCampaignServer(RestartYieldServer112):
    def __init__(self, base):
        super().__init__(base)
        self.drain_replies = 2

    def call(self, method, params):
        value = super().call(method, params)
        if params.get('mode') == 'status' and self.drain_replies:
            self.drain_replies -= 1
            value = copy.deepcopy(value)
            value['payload'].update(state='draining', terminal=True,
                workers_drained=False, native_inflight=False)
        return value


class ClientDrain113Tests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='client113-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.base = self.root/'local'/'test-113'
        self.base.mkdir(parents=True)
        self.destination = self.root/'mounted'
        self.destination.mkdir()

    def test_actual_terminal_draining_projection_is_readonly_for_both_protocols(self):
        for protocol in (cycle.STANDARD_PROTOCOL, cycle.IRREGULAR_PROTOCOL):
            payload = draining(Server())
            if protocol.irregular:
                status = {key: 0 for key in STATUS_NUMBERS}
                status.update(abi_version=1, enabled=True, kind='none',
                    stage='idle', held_reason='none')
                payload['irregular'] = status
            with self.subTest(protocol=protocol.profile):
                failure = None
                try:
                    value = cycle.status(wrap(payload, protocol), RUN,
                        protocol_spec=protocol)
                except ProbeError as error:
                    failure = error.code
                self.assertIsNone(failure,
                    'native terminal+lease is a valid waiting response')
                self.assertEqual('draining', value['state'])
                self.assertFalse(value['workers_drained'])

    def test_incoherent_draining_and_changed_closed_fields_fail_closed(self):
        good = draining(Server())
        for change in (dict(terminal=False), dict(workers_drained=True),
                dict(terminal=1), dict(workers_drained=0), dict(input_state=True),
                dict(state='running'), dict(extra=True)):
            with self.subTest(change=change), self.assertRaises(ProbeError):
                cycle.status(wrap(dict(good, **change)), RUN)

    def test_repeated_draining_waits_before_manifest_without_cancel_or_resend(self):
        server = Server(self.base)
        server.status_queue = [draining(server, native_inflight=True),
            draining(server), server.status()]
        result = cycle.run_session(server, self.base, sleep=lambda _: None,
            notice=lambda _: None)
        self.assertTrue(result['resolved'], 'wait for native leases before collection')
        self.assertFalse(result['cancel_intent'])
        self.assertIsNone(result['last_error'])
        calls = server.calls
        modes = [params.get('mode') for _, params in calls]
        self.assertEqual(['status']*3 + ['manifest'],
            [mode for mode in modes if mode in ('status', 'manifest')])
        self.assertEqual(1, sum(method == 'necro_native_start' for method, _ in calls))
        self.assertFalse(any(method == 'necro_native_cancel' for method, _ in calls))

    def test_explicit_cancel_during_draining_is_not_replaced_by_continuation(self):
        server = Server(self.base)
        server.status_queue = [draining(server)]
        cancelled = lambda: any(params.get('mode') == 'status'
            for _, params in server.calls)
        result = cycle.run_session(server, self.base, cancelled=cancelled,
            sleep=lambda _: None, notice=lambda _: None)
        self.assertTrue(result['cancel_intent'])
        self.assertEqual('cancel_requested', result['last_error'])
        self.assertFalse(result['resolved'])
        self.assertEqual(1, sum(method == 'necro_native_start' for method, _ in server.calls))
        self.assertEqual(1, sum(method == 'necro_native_cancel' for method, _ in server.calls))
        self.assertFalse(any(params.get('mode') in ('manifest', 'published')
            for _, params in server.calls))

    def test_unknown_input_still_waits_for_drain_and_remains_diagnostic_only(self):
        for input_state in (3, 4):
            with self.subTest(input_state=input_state), tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                server = Server(base)
                server.status_queue = [draining(server, input_state=input_state,
                    ui_frozen=True, native_inflight=True),
                    server.status(input_state=input_state, ui_frozen=True)]
                server.manifest.update(input_state=input_state, ui_frozen=True)
                result = cycle.run_session(server, base, sleep=lambda _: None,
                    notice=lambda _: None)
                self.assertTrue(result['resolved'])
                self.assertFalse(result['cancel_intent'])
                self.assertEqual(1, sum(m == 'necro_native_start' for m, _ in server.calls))
                self.assertFalse(any(m == 'necro_native_cancel' for m, _ in server.calls))
                manifest = cycle.verify_evidence(base, result)
                self.assertEqual(input_state, manifest['input_state'])
                self.assertTrue(manifest['ui_frozen'])

    def test_campaign_publishes_drained_predecessor_before_new_uuid(self):
        server = DrainCampaignServer(self.base)
        original = native_walk.device_lock
        with patch.object(cycle, 'device_lock',
                lambda path=None: original(path or self.root/'device.lock')):
            result = campaign.run(server, self.destination, spool=self.base,
                until_target=True, notice=lambda _: None, protocol_spec=SPEC)
        self.assertEqual('target', result['stop_reason'])
        starts = [(i, params) for i, (method, params) in enumerate(server.calls)
            if method == 'necro_native_start']
        self.assertEqual(2, len(starts))
        first, second = starts[0][1]['run_id'], starts[1][1]['run_id']
        self.assertNotEqual(first, second)
        self.assertFalse(any(method == 'necro_native_cancel' for method, _ in server.calls))
        first_calls = [(i, params) for i, (_, params) in enumerate(server.calls)
            if params.get('run_id') == first]
        statuses = [i for i, params in first_calls if params.get('mode') == 'status']
        manifests = [i for i, params in first_calls if params.get('mode') == 'manifest']
        images = [i for i, params in first_calls if params.get('mode') == 'batch']
        publications = [i for i, params in first_calls if params.get('mode') == 'published']
        self.assertEqual(3, len(statuses))
        self.assertTrue(manifests and images and publications)
        self.assertLess(max(statuses), min(manifests))
        self.assertLess(max(images), publications[-1])
        self.assertLess(publications[-1], starts[1][0])
        row = result['ledger']['runs'][0]
        self.assertEqual(('handoff', 'unassessed', False),
            (row['stop_reason'], row['outcome'], row['assessment_adopted']))
        self.assertEqual('restarted_budget', row['handoff']['kind'])

    def test_cancelled_recovery_keeps_failure_in_collection_archive_and_publication(self):
        server = Server(self.base)
        # A truly malformed response still cancels; successful read-only
        # recovery must not erase why that client stopped.
        server.status_queue = [server.status(state='running')]
        first = cycle.run_session(server, self.base, sleep=lambda _: None,
            notice=lambda _: None)
        self.assertEqual('invalid_cycle_response', first['last_error'])
        self.assertTrue(first['cancel_intent'])
        second = cycle.run_session(server, self.base, sleep=lambda _: None,
            notice=lambda _: None)
        self.assertTrue(second['resolved'])
        self.assertEqual('invalid_cycle_response', second['last_error'])
        archive = publication.publish(server, self.base, self.destination, second,
            notice=lambda _: None)
        self.assertTrue(second['published'])
        self.assertEqual('invalid_cycle_response', second['last_error'])
        with zipfile.ZipFile(archive) as saved:
            import json
            name = 'test-113/cycle-'+second['run_id']+'/archive-journal.json'
            journal = json.loads(saved.read(name))
        self.assertTrue(journal['cancel_intent'])
        self.assertEqual('invalid_cycle_response', journal['last_error'])
        self.assertEqual(1, sum(m == 'necro_native_start' for m, _ in server.calls))

    def test_non_cancelled_success_clears_old_retry_error(self):
        server = Server(self.base)
        record = cycle.fresh_record(RUN)
        record.update(start_intent=True, state='unknown', last_error='connection_error')
        cycle._journal(self.base, record)
        result = cycle.run_session(server, self.base, sleep=lambda _: None,
            notice=lambda _: None)
        self.assertTrue(result['resolved'])
        self.assertFalse(result['cancel_intent'])
        self.assertIsNone(result['last_error'])
        publication.publish(server, self.base, self.destination, result,
            notice=lambda _: None)
        self.assertTrue(result['published'])
        self.assertIsNone(result['last_error'])
        self.assertFalse(any(m == 'necro_native_start' for m, _ in server.calls))


if __name__ == '__main__':
    unittest.main()
