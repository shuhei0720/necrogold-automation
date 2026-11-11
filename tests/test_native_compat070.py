"""TEST070 binds the expanded visual assessment count to one protocol revision.

Encrypted endpoint fixtures exercise status, manifest and durable recovery;
they make no assertion about game speed or unrecorded iPhone frames.
"""
from copy import deepcopy
from pathlib import Path
import tempfile

from necroprobe import native_walk as native
from necroprobe.validation import ProbeError
import test_native_paged_results as paged
from test_native_recovery_results import report
from test_native_results import motion_wait
from test_native_walk import NativeServer
from timer_support import TimerTestCase


OLD_API = '1.98.14-ngg2'
PREVIOUS_API = '1.98.15-ngg2'
NEW_API = '1.98.16-ngg2'


def api_for(version):
    return OLD_API if version < 14 else PREVIOUS_API if version == 14 else NEW_API


def envelope(api, attempts=3):
    return dict(run_id='a'*32, profile='normal-1-1-v1', state='completed',
        api_version=api, report=report(motion_wait=motion_wait(attempts=attempts)),
        result_mode='manifest', export_id='b'*32, chunk_bytes=native.CHUNK_BYTES,
        total_bytes=0, images=[])


def historical(record, version):
    record = deepcopy(record)
    record['revision'] = 'native-walk-v'+str(version)
    record['profile'] = 'normal-1-1-v1'
    if record.get('preflight', {}).get('server') is not None:
        record['preflight']['server']['server_version'] = api_for(version)
    if 'api_version' in record.get('result_metadata', {}):
        record['result_metadata']['api_version'] = api_for(version)
    if version < 9:
        record.pop('image_export', None)
    if version < 14:
        record['native_report'].pop('recovery', None)
    if version < 12:
        record['native_report'].pop('motion_references', None)
    return record


class NativeCompatibility070Tests(TimerTestCase):
    client = paged.PagedResultsTests.client
    execute = paged.PagedResultsTests.execute

    def evidence(self, attempts=3, api=NEW_API):
        def transform(method, value):
            if 'report' in value:
                value['api_version'] = api
                value['report']['motion_wait'] = motion_wait(attempts=attempts)
            return value
        return transform

    def test_version_map_and_feature_memberships_preserve_every_prior_revision(self):
        self.assertEqual(('native-walk-v16', NEW_API, 'necrogold_native_v15'),
            (native.REVISION, native.API_VERSION, native.CAPABILITY))
        for version in range(1, 17):
            with self.subTest(version=version):
                revision = 'native-walk-v'+str(version)
                self.assertEqual(api_for(version), native._revision_api(revision))
                for threshold, members in ((9, native.PAGED_REVISIONS),
                        (10, native.BATCHED_REVISIONS), (12, native.MOTION_REFERENCE_REVISIONS),
                        (14, native.RECOVERY_REVISIONS)):
                    self.assertEqual(version >= threshold, revision in members)
        for revision in ('native-walk-v0', 'native-walk-v17', '', None):
            with self.subTest(revision=revision), self.assertRaises(ProbeError):
                native._revision_api(revision)

    def test_unbound_diagnostics_keep_three_while_trusted_new_status_keeps_eight_recursively(self):
        self.assertEqual(3, native._report(report(motion_wait=motion_wait(attempts=3)))['motion_wait']['attempts'])
        for attempts in (4, 8):
            with self.subTest(attempts=attempts), self.assertRaises(ProbeError):
                native._report(report(motion_wait=motion_wait(attempts=attempts)))
        value = envelope(NEW_API, 8)
        value['report']['command'] = dict(motion_wait=motion_wait(attempts=8))
        parsed = native._status(value, 'a'*32, profile='normal-1-1-v1', api_version=NEW_API)[1]
        self.assertEqual((8, 8), (parsed['motion_wait']['attempts'], parsed['command']['motion_wait']['attempts']))
        value['api_version'] = PREVIOUS_API
        with self.assertRaises(ProbeError):
            native._status(value, 'a'*32, profile='normal-1-1-v1', api_version=NEW_API)

    def test_status_and_manifest_limits_are_bound_to_expected_api_and_reject_invalid_types(self):
        for api, limit in ((OLD_API, 3), (PREVIOUS_API, 3), (NEW_API, 8)):
            for attempts in (0, 3, 4, 8, 9, -1, True, 1.0):
                value = envelope(api, attempts)
                valid = type(attempts) is int and 0 <= attempts <= limit
                for parser in (native._status, native._manifest):
                    with self.subTest(api=api, attempts=attempts, parser=parser.__name__):
                        if valid:
                            self.assertEqual(attempts, parser(value, 'a'*32,
                                profile='normal-1-1-v1', api_version=api)[1]['motion_wait']['attempts'])
                        else:
                            with self.assertRaises(ProbeError):
                                parser(value, 'a'*32, profile='normal-1-1-v1', api_version=api)
            for wrong in ({OLD_API, PREVIOUS_API, NEW_API} - {api}):
                with self.subTest(api=api, wrong=wrong), self.assertRaises(ProbeError):
                    native._manifest(envelope(wrong), 'a'*32, profile='normal-1-1-v1', api_version=api)

    def test_encrypted_current_run_roundtrips_eight_in_status_manifest_and_both_journals(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=self.evidence(8)) as server:
            record = self.execute(server, folder)
            self.assertTrue(record['resolved'], record['stop_reason'])
            self.assertEqual('native-walk-v16', record['revision'])
            self.assertEqual(8, record['native_report']['motion_wait']['attempts'])
            self.assertEqual(NEW_API, record['result_metadata']['api_version'])
            self.assertEqual(record, native._load(Path(folder)))
            self.assertEqual((Path(folder)/'active.json').read_bytes(),
                (Path(folder)/('native-'+record['run_id'])/'report.json').read_bytes())
            methods = [method for method, _params in server.calls]
            self.assertEqual(1, methods.count('necro_native_start'))
            self.assertIn('necro_native_status', methods)
            self.assertIn(('necro_native_results', dict(run_id=record['run_id'], mode='manifest')), server.calls)

    def test_all_historical_journals_keep_their_api_limit_and_required_evidence(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=self.evidence()) as server:
            seed = self.execute(server, folder)
            self.assertTrue(seed['resolved'], seed['stop_reason'])
            for version in range(1, 16):
                record = historical(seed, version)
                with self.subTest(version=version):
                    native._save(Path(folder), record)
                    self.assertEqual(record, native._load(Path(folder)))
                    record['native_report']['motion_wait']['attempts'] = 8
                    native._save(Path(folder), record)
                    if version == 15:
                        self.assertEqual(8, native._load(Path(folder))['native_report']['motion_wait']['attempts'])
                    else:
                        with self.assertRaises(ProbeError):
                            native._load(Path(folder))
            for version in (14, 15):
                record = historical(seed, version)
                record['native_report'].pop('recovery')
                native._save(Path(folder), record)
                with self.subTest(missing_recovery=version), self.assertRaises(ProbeError):
                    native._load(Path(folder))

    def test_started_v14_recovers_same_uuid_and_original_api_without_a_new_start(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=self.evidence()) as server:
            seed = self.execute(server, folder)
            old = historical(seed, 14)
            old['resolved'] = False
            server.profiles[seed['run_id']] = old['profile']
            native._save(Path(folder), old)
            server.version = PREVIOUS_API
            server.transform = self.evidence(api=PREVIOUS_API)
            server.calls.clear(); server.schema_calls.clear()
            recovered = self.execute(server, folder)
            self.assertTrue(recovered['resolved'], recovered['stop_reason'])
            self.assertEqual(('native-walk-v14', seed['run_id'], PREVIOUS_API),
                (recovered['revision'], recovered['run_id'], recovered['result_metadata']['api_version']))
            self.assertEqual(seed['native_report']['clock_id'], recovered['native_report']['clock_id'])
            self.assertEqual([], server.schema_calls)
            self.assertTrue(server.calls)
            for method, params in server.calls:
                self.assertIn(method, ('necro_native_status', 'necro_native_results'))
                self.assertEqual(seed['run_id'], params['run_id'])
                self.assertFalse(params.get('keepalive', False))

    def test_never_started_v14_upgrades_only_its_first_start_and_rejects_an_old_ipa(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=self.evidence()) as server:
            seed = self.execute(server, folder)
            old = historical(seed, 14)
            old.update(resolved=False, state='prepared', native_state=None, native_report=None,
                start_attempted=False, result_metadata={}, images=[])
            old.pop('image_export', None)
            native._save(Path(folder), old)
            server.calls.clear(); server.schema_calls.clear()
            fresh = self.execute(server, folder)
            self.assertTrue(fresh['resolved'], fresh['stop_reason'])
            self.assertEqual(('native-walk-v16', seed['run_id']), (fresh['revision'], fresh['run_id']))
            self.assertEqual(['/schema'], server.schema_calls)
            self.assertEqual(1, sum(method == 'necro_native_start' for method, _ in server.calls))
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                version=PREVIOUS_API, capabilities=['necrogold_native_v13']) as server:
            rejected = self.execute(server, folder)
            self.assertEqual(('native_capability_missing', False),
                (rejected['stop_reason'], rejected['start_attempted']))
            self.assertEqual([], server.calls)

    def test_persisted_preflight_and_result_api_cannot_cross_revision_boundaries(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=self.evidence()) as server:
            seed = self.execute(server, folder)
            for version in (13, 14, 15):
                for wrong in ({OLD_API, PREVIOUS_API, NEW_API} - {api_for(version)}):
                    for field in ('preflight', 'result_metadata'):
                        record = historical(seed, version)
                        if field == 'preflight':
                            record[field]['server']['server_version'] = wrong
                        else:
                            record[field]['api_version'] = wrong
                        native._save(Path(folder), record)
                        with self.subTest(version=version, wrong=wrong, field=field), self.assertRaises(ProbeError):
                            native._load(Path(folder))
