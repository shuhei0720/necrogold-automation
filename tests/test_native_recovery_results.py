"""TEST061 recovery snapshots and revision-bound encrypted result collection."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import tempfile

from necroprobe import native_walk as native
from necroprobe.validation import ProbeError
from test_native_walk import NativeServer
import test_native_paged_results as paged
from timer_support import TimerTestCase


OLD_API = '1.98.14-ngg2'
PREVIOUS_API = '1.98.15-ngg2'


def recovery(**updates):
    value = dict(initial_reacquisitions=0, post_move_reacquisitions=0, episode_id=0,
        mode=0, schedule_deadline_ns=0, visual_deadline_ns=0, ack_ns=0,
        record_count=0, dropped_records=0, records=[])
    value.update(updates)
    return value


def model(**updates):
    value = dict(period_ns=520_000_000, epoch_ns=10, first_ns=100,
        last_ns=2_100_000_100, gap_ns=500_000_000, prediction_span_ns=3_000_000_000,
        sample_count=5, mode=1, candidate_count=1, residual=.002, maximum=.004,
        alternate=-1., alias_gap=-1., half_width_max_ns=5_000_000.,
        tracking_error=-1., extrapolation_budget=-1.)
    value.update(updates)
    return value


def sample(**updates):
    value = dict(start_ns=100, end_ns=200, midpoint_ns=150,
        half_width_ns=50., q=.25, spacing=104., center=446.)
    value.update(updates)
    return value


def trace(**updates):
    value = dict(sequence=1, episode_id=1, reason=1, clock=1, at_ns=250,
        capture_id=8, command_id=2, abandoned_target_ns=600,
        sync_deadline_ns=12_000_000_000, model=model(), samples=[sample()])
    value.update(updates)
    return value


def recorded_recovery():
    return recovery(initial_reacquisitions=1, post_move_reacquisitions=1,
        episode_id=2, mode=2, schedule_deadline_ns=600, visual_deadline_ns=3000,
        ack_ns=550, record_count=3, dropped_records=1,
        records=[trace(), trace(sequence=3, episode_id=2, reason=6, clock=2, at_ns=800)])


def report(**updates):
    value = dict(schema='ngg2-native-v1', clock_id='a'*32,
        device_now_ns=1000, input_state=0, events=[], motion_references=[], recovery=recovery())
    value.update(updates)
    return value


def old_journal(value, version):
    """Build an actual old API journal, rather than relabel a new API preflight."""
    value = deepcopy(value)
    value['revision'] = 'native-walk-v'+str(version)
    api = OLD_API if version < 14 else PREVIOUS_API if version == 14 else native.API_VERSION
    if value.get('preflight', {}).get('server') is not None:
        value['preflight']['server']['server_version'] = api
    if 'api_version' in value.get('result_metadata', {}):
        value['result_metadata']['api_version'] = api
    if version < 9:
        value.pop('image_export', None)
    return value


class RecoveryResultsTests(TimerTestCase):
    client = paged.PagedResultsTests.client
    execute = paged.PagedResultsTests.execute

    def test_recovery_snapshot_survives_the_report_projection(self):
        expected = recorded_recovery()
        parsed = native._report(report(recovery=expected))
        self.assertIn('recovery', parsed, 'native_recovery_snapshot_must_not_be_dropped')
        self.assertEqual(expected, parsed['recovery'])

    def test_current_revision_requires_new_api_capability_and_test061_output(self):
        self.assertEqual(('native-walk-v15', '1.98.16-ngg2', 'necrogold_native_v14'),
            (native.REVISION, native.API_VERSION, native.CAPABILITY))
        path = Path(native.__file__).resolve().parents[1]/'test_061.sh'
        self.assertEqual(0, subprocess.run(['sh', '-n', str(path)], capture_output=True).returncode)
        self.assertIn('native-walk-v14 / 1.98.15-ngg2', path.read_text())
        self.assertIn('--output runtime/test-061', path.read_text())

    def test_never_started_old_journal_uses_v15_contract_for_its_first_start(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True) as server:
            seed = self.execute(server, folder)
            seed = old_journal(seed, 13)
            seed.update(resolved=False, state='prepared', native_state=None, native_report=None,
                start_attempted=False, result_metadata={}, images=[])
            seed.pop('image_export', None)
            native._save(Path(folder), seed)
            server.calls.clear()
            server.schema_calls.clear()
            value = self.execute(server, folder)
            self.assertEqual('native-walk-v15', value['revision'],
                'a_first_start_requires_the_current_full_report_contract')
            self.assertEqual(seed['run_id'], value['run_id'])
            self.assertTrue(value['resolved'], value['stop_reason'])
            self.assertEqual(['/schema'], server.schema_calls)
            self.assertEqual(1, sum(method == 'necro_native_start' for method,params in server.calls))
            self.assertEqual(value, native._load(Path(folder)))

    def test_old_ipa_is_rejected_before_any_native_start(self):
        for version, tags in ((OLD_API, [native.CAPABILITY]),
                (native.API_VERSION, ['necrogold_native_v12'])):
            with self.subTest(version=version, tags=tags), tempfile.TemporaryDirectory() as folder, \
                    NativeServer(finish=True, version=version, capabilities=tags) as server:
                result = self.execute(server, folder)
                self.assertEqual(('native_capability_missing', False),
                    (result['stop_reason'], result['start_attempted']))
                self.assertEqual(['/schema'], server.schema_calls)
                self.assertEqual([], server.calls)

    def test_new_full_reports_require_recovery_in_start_status_results_and_journal(self):
        for endpoint in ('necro_native_start', 'necro_native_status', 'necro_native_results'):
            def missing(method, value):
                if method == endpoint:
                    value['report'].pop('recovery')
                return value
            with self.subTest(endpoint=endpoint), tempfile.TemporaryDirectory() as folder, \
                    NativeServer(finish=True, transform=missing) as server:
                result = self.execute(server, folder)
                self.assertEqual('invalid_native_report', result['stop_reason'])
                self.assertTrue(any(method == endpoint for method, params in server.calls))
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True) as server:
            value = self.execute(server, folder)
            value['native_report'].pop('recovery')
            native._save(Path(folder), value)
            with self.assertRaisesRegex(ProbeError, 'native_journal_invalid'):
                native._load(Path(folder))

    def test_recovery_reaches_encrypted_results_and_both_journals_without_aliases(self):
        expected = recorded_recovery()
        def diagnostics(method, value):
            value['report']['recovery'] = deepcopy(expected)
            return value
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=diagnostics) as server:
            result = self.execute(server, folder)
            self.assertTrue(result['resolved'], result['stop_reason'])
            self.assertEqual(expected, result['native_report']['recovery'])
            self.assertEqual(result, native._load(Path(folder)))
            for path in (Path(folder)/'active.json',
                    Path(folder)/('native-'+result['run_id'])/'report.json'):
                self.assertEqual(expected, json.loads(path.read_text())['native_report']['recovery'])
        raw = report(recovery=expected)
        parsed = native._report(raw)
        parsed['recovery']['records'][0]['model']['residual'] = .5
        parsed['recovery']['records'][0]['samples'][0]['q'] = .75
        self.assertEqual(.002, raw['recovery']['records'][0]['model']['residual'])
        self.assertEqual(.25, raw['recovery']['records'][0]['samples'][0]['q'])

    def test_closed_recovery_keys_and_nonboolean_unsigned_counters(self):
        for base in (recovery(), recorded_recovery()):
            for key in base:
                for change in ('missing', 'extra') if key == 'records' else ('missing', True, False, -1, 2**63, 1., '0', None):
                    bad = deepcopy(base)
                    if change == 'missing':
                        bad.pop(key)
                    elif change == 'extra':
                        bad['private'] = 'PRIVATE'
                    else:
                        bad[key] = change
                    with self.subTest(key=key, change=change), self.assertRaisesRegex(ProbeError, 'invalid_native_report'):
                        native._report(report(recovery=bad))
        for value in (None, [], {'private': 'PRIVATE'}, recovery(mode=3), recovery(records=None)):
            with self.subTest(value=value), self.assertRaisesRegex(ProbeError, 'invalid_native_report'):
                native._report(report(recovery=value))

    def test_first_and_latest_sequences_and_overwrite_counts_are_coherent(self):
        for count in (0, 1, 2, 3, 100):
            rows = [] if count == 0 else [trace()]
            if count > 1:
                rows.append(trace(sequence=count))
            value = recovery(episode_id=1, record_count=count,
                dropped_records=max(count-2, 0), records=rows)
            self.assertEqual(value, native._report(report(recovery=value))['recovery'])
        invalid = [recovery(record_count=1), recovery(dropped_records=1),
            recovery(episode_id=1, record_count=1, records=[trace(sequence=2)]),
            recovery(episode_id=1, record_count=1, records=[trace(episode_id=2)]),
            recovery(episode_id=1, record_count=3, dropped_records=1,
                records=[trace(), trace(sequence=2)]),
            recovery(episode_id=1, record_count=3, records=[trace(), trace(sequence=3)]),
            recovery(episode_id=1, record_count=3, records=[trace(), trace(sequence=2), trace(sequence=3)])]
        for value in invalid:
            with self.subTest(value=value), self.assertRaisesRegex(ProbeError, 'invalid_native_report'):
                native._report(report(recovery=value))
        value = recovery(record_count=1, records=[trace(episode_id=0, reason=7)])
        self.assertEqual(value, native._report(report(recovery=value))['recovery'])

    def test_record_fields_are_closed_and_all_reason_clock_modes_are_checked(self):
        for key in trace():
            bad = trace()
            bad.pop(key)
            with self.subTest(missing=key), self.assertRaisesRegex(ProbeError, 'invalid_native_report'):
                native._report(report(recovery=recovery(episode_id=1, record_count=1, records=[bad])))
        for key in tuple(trace())[:-2]:
            for value in (True, False, -1, 2**63, 1., '1', None):
                bad = trace(**{key:value})
                with self.subTest(key=key, value=value), self.assertRaisesRegex(ProbeError, 'invalid_native_report'):
                    native._report(report(recovery=recovery(episode_id=1, record_count=1, records=[bad])))
        for reason in range(1,9):
            for clock in range(1,4):
                value = recovery(episode_id=1, record_count=1, records=[trace(reason=reason, clock=clock)])
                self.assertEqual(value, native._report(report(recovery=value))['recovery'])
        for updates in (dict(reason=0), dict(reason=9), dict(clock=0), dict(clock=4), dict(private='PRIVATE')):
            with self.subTest(updates=updates), self.assertRaisesRegex(ProbeError, 'invalid_native_report'):
                native._report(report(recovery=recovery(episode_id=1, record_count=1, records=[trace(**updates)])))

    def test_model_all_fields_numeric_finite_modes_and_sample_counts(self):
        for key, original in model().items():
            bad_values = (True, False, None, 'PRIVATE', float('nan'), float('inf'), -float('inf'), 2**2000)
            if type(original) is int:
                bad_values += (-1, 2**63, 1.)
            for value in bad_values:
                bad_model = model(**{key:value})
                with self.subTest(key=key, value=value), self.assertRaisesRegex(ProbeError, 'invalid_native_report'):
                    native._report(report(recovery=recovery(episode_id=1, record_count=1, records=[trace(model=bad_model)])))
            missing = model()
            missing.pop(key)
            with self.subTest(missing=key), self.assertRaisesRegex(ProbeError, 'invalid_native_report'):
                native._report(report(recovery=recovery(episode_id=1, record_count=1, records=[trace(model=missing)])))
        for changes in (dict(mode=3), dict(sample_count=14), dict(private='PRIVATE')):
            with self.subTest(changes=changes), self.assertRaisesRegex(ProbeError, 'invalid_native_report'):
                native._report(report(recovery=recovery(episode_id=1, record_count=1, records=[trace(model=model(**changes))])))
        for mode in range(3):
            value = recovery(episode_id=1, record_count=1, records=[trace(model=model(mode=mode, sample_count=13))])
            self.assertEqual(value, native._report(report(recovery=value))['recovery'])

    def test_samples_require_seven_fields_finite_values_ranges_and_thirteen_limit(self):
        invalid = [None, {}, [sample()]*14, [sample(private='PRIVATE')]]
        for key, original in sample().items():
            missing = sample()
            missing.pop(key)
            invalid.append([missing])
            values = (True, False, None, 'PRIVATE', float('nan'), float('inf'), -float('inf'), 2**2000)
            if type(original) is int:
                values += (-1, 2**63, 1.)
            invalid.extend([sample(**{key:value})] for value in values)
        invalid.extend([sample(**changes)] for changes in (dict(start_ns=200), dict(end_ns=100),
            dict(midpoint_ns=151), dict(half_width_ns=49), dict(q=-.1), dict(q=1.),
            dict(spacing=89.9), dict(spacing=120.1), dict(center=439.9), dict(center=452.1)))
        for samples in invalid:
            with self.subTest(samples=samples), self.assertRaisesRegex(ProbeError, 'invalid_native_report'):
                native._report(report(recovery=recovery(episode_id=1, record_count=1, records=[trace(samples=samples)])))
        value = recovery(episode_id=1, record_count=1, records=[trace(samples=[sample()]*13)])
        self.assertEqual(value, native._report(report(recovery=value))['recovery'])

    def test_authenticated_malformed_recovery_keeps_the_last_valid_report(self):
        def invalid(method, value):
            value['report']['recovery'] = recorded_recovery()
            if method == 'necro_native_results':
                value['report']['recovery']['records'][1]['private'] = 'PRIVATE_RECOVERY'
            return value
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True, transform=invalid) as server:
            result = self.execute(server, folder)
            self.assertFalse(result['resolved'])
            self.assertEqual('invalid_native_report', result['stop_reason'])
            self.assertEqual(recorded_recovery(), result['native_report']['recovery'])
            self.assertNotIn('PRIVATE_RECOVERY', json.dumps(result))

    def test_literal_v1_through_v13_recover_ready_old_api_journals_with_no_get_or_start(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True) as server:
            seed = self.execute(server, folder)
            self.assertTrue(seed['resolved'], seed['stop_reason'])
            for version in range(1,14):
                value = old_journal(seed, version)
                value.update(resolved=False, state='unknown')
                value['native_report'].pop('recovery')
                if version < 12:
                    value['native_report'].pop('motion_references')
                value['result_metadata']['api_version'] = OLD_API
                native._save(Path(folder), value)
                def legacy(method, result):
                    result['api_version'] = OLD_API
                    result['report'].pop('recovery')
                    if version < 12:
                        result['report'].pop('motion_references')
                    return result
                server.transform = legacy
                server.exports.clear()
                server.schema_calls.clear()
                before = len(server.calls)
                with self.subTest(version=version):
                    recovered = self.execute(server, folder)
                    self.assertTrue(recovered['resolved'], recovered['stop_reason'])
                    self.assertEqual(value['revision'], recovered['revision'])
                    self.assertEqual(value['run_id'], recovered['run_id'])
                    self.assertEqual([], server.schema_calls)
                    calls = server.calls[before:]
                    self.assertEqual(['necro_native_status', 'necro_native_results'], [m for m,p in calls])
                    self.assertEqual({value['run_id']}, {p['run_id'] for m,p in calls})
                    self.assertEqual(version >= 9, calls[-1][1].get('mode') == 'manifest')
                    self.assertEqual(OLD_API, recovered['result_metadata']['api_version'])
                    self.assertEqual(recovered, native._load(Path(folder)))

    def test_each_revision_binds_preflight_status_and_result_metadata_to_one_api(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True) as server:
            seed = self.execute(server, folder)
            for version in range(1,16):
                value = old_journal(seed, version)
                expected = OLD_API if version < 14 else PREVIOUS_API if version == 14 else native.API_VERSION
                wrong = native.API_VERSION if version < 15 else OLD_API
                for key in ('preflight', 'result_metadata'):
                    bad = deepcopy(value)
                    if key == 'preflight':
                        bad[key]['server']['server_version'] = wrong
                    else:
                        bad[key]['api_version'] = wrong
                    native._save(Path(folder), bad)
                    with self.subTest(version=version, key=key), self.assertRaisesRegex(ProbeError, 'native_journal_invalid'):
                        native._load(Path(folder))
                reply = dict(run_id=seed['run_id'], profile=native.PROFILE,
                    state='stopped', api_version=expected, report=seed['native_report'])
                self.assertEqual('stopped', native._status(reply, seed['run_id'], api_version=expected)[0])
                reply['api_version'] = wrong
                with self.subTest(version=version, key='status'), self.assertRaisesRegex(ProbeError, 'invalid_native_status'):
                    native._status(reply, seed['run_id'], api_version=expected)

    def test_old_revisions_allow_absent_recovery_but_validate_every_present_snapshot(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True) as server:
            seed = self.execute(server, folder)
            for version in range(1,14):
                value = old_journal(seed, version)
                value['native_report'].pop('recovery')
                native._save(Path(folder), value)
                self.assertEqual(value, native._load(Path(folder)))
                value['native_report']['recovery'] = recorded_recovery()
                native._save(Path(folder), value)
                self.assertEqual(value, native._load(Path(folder)))
                value['native_report']['recovery']['records'][0]['samples'] *= 14
                native._save(Path(folder), value)
                with self.subTest(version=version), self.assertRaisesRegex(ProbeError, 'native_journal_invalid'):
                    native._load(Path(folder))
