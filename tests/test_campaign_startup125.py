"""Opt-in startup readiness: procedural replies/clocks, not an iPhone replay."""
import copy
import io
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from necroprobe import campaign116 as campaign
from necroprobe import native_cycle as cycle
from necroprobe.validation import ProbeError
import test_continuous_client125 as prior


class Clock:
    def __init__(self):
        self.ns = 10_000_000_000
        self.sleeps = []

    def __call__(self):
        return self.ns

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.ns += int(seconds * 1_000_000_000)


def prepared(*, ready=False, notification='authorized', scan='pending', ids=()):
    reason = ('recovery_scan_failed' if scan == 'failed' else
        'recovery_scan_pending' if scan == 'pending' else
        'unpublished_cycle' if ids else
        'none' if ready else 'need_open_loopctrl_notifications')
    return dict(ready=ready, notification_authorization=notification,
        recovery_scan=scan, unpublished_run_ids=list(ids), reason=reason)


class StartupServer(prior.ContinuousServer125):
    wait_for_startup_ready = True

    def __init__(self, base, sequence):
        super().__init__(base)
        self.sequence = copy.deepcopy(sequence)
        self.prepares = 0
        self.on_prepare = None

    def call(self, method, params):
        if method == cycle.IRREGULAR_PROTOCOL.query and params.get('mode') == 'prepare':
            self.initial_validator._validate(method, params)
            self.calls.append((method, copy.deepcopy(params)))
            index = min(self.prepares, len(self.sequence) - 1)
            self.prepares += 1
            value = copy.deepcopy(self.sequence[index])
            if self.on_prepare is not None:
                self.on_prepare(self.prepares)
            if isinstance(value, Exception):
                raise value
            return self.wrap(params['run_id'], 'prepare', value)
        return super().call(method, params)


class CampaignStartup125Tests(unittest.TestCase):
    def run_campaign(self, server, base, destination, clock, **options):
        original = cycle.device_lock
        notice = options.pop('notice', lambda _text: None)
        with patch('necroprobe.native_cycle.device_lock',
                lambda path=None: original(path or destination/'device.lock')):
            return campaign.run(server, destination, spool=base, test_number='125',
                notice=notice, clock=clock, sleep=clock.sleep, **options)

    def assert_no_start(self, server):
        self.assertFalse(any(method == 'necro_native_start' for method, _ in server.calls))

    def test_actual_pending_then_scan_ready_starts_once_after_prepare(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary)
            base = destination/'test-125'
            base.mkdir()
            sequence = [prepared(notification='pending'), prepared(), prepared(),
                prepared(ready=True, scan='ready')]
            server = StartupServer(base, sequence)
            clock = Clock()
            result = failure = None
            try:
                result = self.run_campaign(server, base, destination, clock)
            except ProbeError as error:
                failure = error.code
            self.assertIsNone(failure,
                'authorized notification and pending recovery scan must wait, not stop as '+str(failure))
            self.assertIsNotNone(result)
            self.assertTrue(result['ledger']['collection_complete'])
            self.assertEqual(4, server.prepares)
            self.assertEqual(1, sum(method == 'necro_native_start' for method, _ in server.calls))
            startup = [(method, params) for method, params in server.calls
                if method == 'necro_native_start' or params.get('mode') == 'prepare']
            self.assertEqual(['prepare']*4+['start'],
                ['start' if method == 'necro_native_start' else params['mode']
                    for method, params in startup])
            self.assertEqual(1, len({params['run_id'] for _, params in startup[:-1]}))
            self.assertTrue(all(params['request_authorization'] is False
                for _, params in startup[:-1]))
            self.assertEqual([.25]*3, clock.sleeps[:3])

    def test_pending_stops_at_original_admission_deadline_without_a_journal_or_post(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary); base = destination/'test-125'; base.mkdir()
            server = StartupServer(base, [prepared()]); clock = Clock(); notices = []
            with self.assertRaisesRegex(ProbeError, 'cycle_recovery_scan_pending'):
                self.run_campaign(server, base, destination, clock, notice=notices.append)
            self.assertEqual(18_000_000_000, clock.ns)
            self.assertEqual(32, server.prepares)
            self.assertEqual(1, len(notices))
            self.assertIn('保存記録', notices[0]); self.assertIn('再起動せず', notices[0])
            self.assertFalse((base/'continuous-campaign.json').exists())
            self.assert_no_start(server)

    def test_ready_reply_at_or_after_original_deadline_never_admits_a_start(self):
        for duration in (250_000_000, 500_000_000):
            with self.subTest(duration=duration), tempfile.TemporaryDirectory() as temporary:
                destination = Path(temporary); base = destination/'test-125'; base.mkdir()
                server = StartupServer(base, [prepared()]*31+[prepared(ready=True, scan='ready')])
                clock = Clock()
                server.on_prepare = lambda count: setattr(clock, 'ns', clock.ns+duration) if count == 32 else None
                with self.assertRaisesRegex(ProbeError, 'cycle_prepare_timeout'):
                    self.run_campaign(server, base, destination, clock)
                self.assertEqual(32, server.prepares)
                self.assertGreaterEqual(clock.ns, 18_000_000_000)
                self.assert_no_start(server)

    def test_sole_post_guard_reuses_the_first_prepare_deadline_after_durable_intent(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary); base = destination/'test-125'; base.mkdir()
            server = StartupServer(base, [prepared()]*31+[prepared(ready=True, scan='ready')])
            clock = Clock()
            server.before_post = lambda: setattr(clock, 'ns', clock.ns+500_000_000)
            result = self.run_campaign(server, base, destination, clock)
            self.assertEqual('host_deadline', result['ledger']['last_error'])
            self.assertFalse(result['ledger']['start_intent'])
            self.assertEqual(1, len(server.start_requests))  # Logical attempt stopped before transport.
            self.assert_no_start(server)

    def test_explicit_failure_states_are_not_all_notification_errors(self):
        cases = (
            (prepared(scan='failed'), 'cycle_recovery_scan_failed'),
            (prepared(notification='denied'), 'cycle_notification_permission'),
            (prepared(notification='not_determined'), 'cycle_notification_permission'),
            (prepared(notification='unavailable'), 'cycle_notification_permission'),
            (prepared(scan='ready', notification='pending'), 'cycle_notification_pending'),
            (prepared(scan='ready'), 'cycle_prepare_not_ready'),
        )
        for value, expected in cases:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as temporary:
                destination = Path(temporary); base = destination/'test-125'; base.mkdir()
                server = StartupServer(base, [value]); clock = Clock()
                with self.assertRaisesRegex(ProbeError, expected):
                    self.run_campaign(server, base, destination, clock)
                self.assert_no_start(server)

    def test_late_explicit_failure_is_reported_before_admission_expiry(self):
        cases = ((prepared(notification='denied'), 'cycle_notification_permission'),
            (prepared(scan='failed'), 'cycle_recovery_scan_failed'))
        for value, expected in cases:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as temporary:
                destination = Path(temporary); base = destination/'test-125'; base.mkdir()
                server = StartupServer(base, [prepared()]*31+[value]); clock = Clock()
                server.on_prepare = lambda count: setattr(clock, 'ns', clock.ns+250_000_000) if count == 32 else None
                with self.assertRaisesRegex(ProbeError, expected):
                    self.run_campaign(server, base, destination, clock)
                self.assertEqual(18_000_000_000, clock.ns)
                self.assert_no_start(server)

    def test_read_connection_failure_is_not_replayed_and_does_not_write_start_intent(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary); base = destination/'test-125'; base.mkdir()
            server = StartupServer(base, [prepared(), ProbeError('connection_error')]); clock = Clock()
            with self.assertRaisesRegex(ProbeError, 'connection_error'):
                self.run_campaign(server, base, destination, clock)
            self.assertEqual(2, server.prepares)
            self.assertEqual([.25], clock.sleeps)
            self.assertFalse((base/'continuous-campaign.json').exists())
            self.assert_no_start(server)

    def test_uncertain_post_after_prepare_wait_is_never_posted_again(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary); base = destination/'test-125'; base.mkdir()
            server = StartupServer(base, [prepared(), prepared(ready=True, scan='ready')])
            server.start_failure = True; clock = Clock()
            first = self.run_campaign(server, base, destination, clock)
            root = first['ledger']['campaign_id']
            self.assertFalse(first['ledger']['collection_complete'])
            self.assertEqual(2, server.prepares)
            self.assertEqual(1, len(server.start_requests))
            server.calls.clear()
            second = self.run_campaign(server, base, destination, clock,
                until_target=False, recovery_only=True)
            self.assertTrue(second['ledger']['collection_complete'])
            self.assertEqual(root, second['ledger']['campaign_id'])
            self.assertEqual(1, len(server.start_requests))
            self.assert_no_start(server)
            self.assertFalse(any(params.get('keepalive') for _, params in server.calls))

    def test_cancellation_after_a_read_or_wait_never_admits_or_retries(self):
        for where in ('read', 'wait'):
            with self.subTest(where=where), tempfile.TemporaryDirectory() as temporary:
                destination = Path(temporary); base = destination/'test-125'; base.mkdir()
                server = StartupServer(base, [prepared()]); clock = Clock(); cancelled = [False]
                if where == 'read':
                    server.on_prepare = lambda _count: cancelled.__setitem__(0, True)
                else:
                    original_sleep = clock.sleep
                    def sleep(seconds):
                        original_sleep(seconds); cancelled[0] = True
                    clock.sleep = sleep
                with self.assertRaisesRegex(ProbeError, 'cancel_requested'):
                    self.run_campaign(server, base, destination, clock, cancelled=lambda: cancelled[0])
                self.assertEqual(1, server.prepares)
                self.assert_no_start(server)

    def test_late_authenticated_unpublished_ids_still_enter_only_old_recovery(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary); base = destination/'test-125'; base.mkdir()
            root, child = prior.baseline.ROOT, prior.baseline.SECOND
            server = StartupServer(base, [prepared()]*31+[
                prepared(scan='ready', ids=(root, child))])
            server.root = root
            server.models = {root:prior.baseline.campaign_model(root, root, 0, None, child),
                child:prior.baseline.campaign_model(child, root, 1, root, None)}
            clock = Clock()
            server.on_prepare = lambda count: setattr(clock, 'ns', clock.ns+500_000_000) if count == 32 else None
            result = self.run_campaign(server, base, destination, clock)
            self.assertTrue(result['ledger']['collection_complete'])
            self.assertEqual(root, result['ledger']['campaign_id'])
            self.assertEqual([root, child], result['ledger']['recovery_ids'])
            self.assert_no_start(server)
            self.assertFalse(any(params.get('keepalive') for _, params in server.calls))

    def test_recovery_only_waits_for_complete_scan_before_reporting_no_records(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary); base = destination/'test-125'; base.mkdir()
            server = StartupServer(base, [prepared(), prepared(ready=True, scan='ready')]); clock = Clock()
            with self.assertRaisesRegex(ProbeError, 'campaign_recovery_record_missing'):
                self.run_campaign(server, base, destination, clock, until_target=False, recovery_only=True)
            self.assertEqual(2, server.prepares)
            self.assert_no_start(server)

    def test_only_125_continuous_client_opts_in_and_false_flag_keeps_single_query(self):
        self.assertIs(True, prior.clients()[0].wait_for_startup_ready)
        self.assertFalse(getattr(prior.clients()[1], 'wait_for_startup_ready', False))
        self.assertFalse(getattr(prior.previous.DeviceClient124, 'wait_for_startup_ready', False))
        for flag, expected, count in ((False, 'cycle_notification_permission', 1),
                (1, 'cycle_protocol_invalid', 0)):
            with self.subTest(flag=flag), tempfile.TemporaryDirectory() as temporary:
                destination = Path(temporary); base = destination/'test-125'; base.mkdir()
                server = StartupServer(base, [prepared(), prepared(ready=True, scan='ready')])
                server.wait_for_startup_ready = flag
                with self.assertRaisesRegex(ProbeError, expected):
                    self.run_campaign(server, base, destination, Clock())
                self.assertEqual(count, server.prepares)
                self.assert_no_start(server)

    def test_malformed_ready_cannot_be_repaired_or_used_to_start(self):
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary); base = destination/'test-125'; base.mkdir()
            server = StartupServer(base, [prepared(ready=True)]); clock = Clock()
            with self.assertRaises(ProbeError):
                self.run_campaign(server, base, destination, clock)
            self.assertEqual(1, server.prepares)
            self.assert_no_start(server)

    def test_source_fix_banner_and_error_details_do_not_change_check_identity(self):
        shared = prior.shared_entry
        for number, entry in (('125', prior.entry), ('116', shared)):
            with self.subTest(number=number), tempfile.TemporaryDirectory() as temporary:
                home = Path(temporary); output = io.StringIO()
                with patch.object(Path, 'home', return_value=home), \
                        patch.object(shared, 'load_pairing', return_value=(prior.KEY, prior.TOK)), \
                        patch.object(campaign, 'run', side_effect=ProbeError('cycle_recovery_scan_pending')), \
                        redirect_stdout(output):
                    self.assertEqual(2, entry.main(['--until-target', '--python-crypto']))
                if number == '125':
                    self.assertIn('TEST-125: 起動準備修正1', output.getvalue())
                    self.assertIn('保存記録の確認が開始期限内に終わりませんでした', output.getvalue())
                    self.assertNotIn('通知拒否ではありません', output.getvalue())
                else:
                    self.assertNotIn('起動準備修正1', output.getvalue())
                    self.assertNotIn('保存記録の確認が開始期限内に終わりませんでした', output.getvalue())
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(0, prior.entry.main(['--check']))
        self.assertEqual('native-device-failures-trial-v125 / '+cycle.API_VERSION+'\n', output.getvalue())


if __name__ == '__main__':
    unittest.main()
