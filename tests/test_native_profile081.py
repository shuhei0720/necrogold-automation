"""TEST081 opt-in evidence profile: encrypted RPC and durable byte boundaries.

These fixtures test client/export contracts, not game progress or iPhone timing.
"""
import base64
from copy import deepcopy
import hashlib
from pathlib import Path
import tempfile
import zipfile

from necroprobe import native_walk as native
from necroprobe import test069 as publication
from necroprobe.validation import ProbeError
from test_native_walk import NativeServer, image_item
import test_native_paged_results as paged
from test_native_recovery_results import report
from timer_support import TimerTestCase


V1 = 'normal-1-1-v1'
V2 = 'normal-1-1-evidence-v2'
OLD_BYTES = 4 * 1024 * 1024
NEW_BYTES = 20 * 512 * 1024


def api_for(version):
    return '1.98.14-ngg2' if version < 14 else '1.98.15-ngg2' if version == 14 else '1.98.16-ngg2'


def journal(version, *, started=True, images=()):
    return dict(schema='ngg2-host-v1', revision='native-walk-v'+str(version),
        run_id='a'*32, profile=V2 if version == 16 else V1,
        state='stopped' if started else 'prepared', resolved=False,
        start_attempted=started, cancel_attempted=False, cancel_attempts=0,
        cancel_confirmed=False, stop_reason=None, native_state='stopped' if started else None,
        native_report=report(terminal=1, workers_drained=True, ui_frozen=False,
            native_inflight=False) if started else None,
        images=list(images), result_metadata={}, host_clock_domain='python.monotonic_ns',
        native_clock_domain='device.monotonic_ns', events=[], events_dropped=0)


def metadata(count, size=512*1024):
    return [dict(name='capture-%06d.png'%index, format='png', pixel_width=896,
        pixel_height=414, sha256='b'*64, bytes=size, capture_id=index,
        capture_start_ns=2, capture_end_ns=3) for index in range(1, count+1)]


def checkpoint(images):
    return dict(export_id='b'*32, images=deepcopy(images),
        total_bytes=sum(item['bytes'] for item in images), chunk_bytes=65536,
        offsets=[0]*len(images), prefix_sha256=[hashlib.sha256(b'').hexdigest()]*len(images))


def response(profile=V2, api='1.98.16-ngg2', images=()):
    rows = [dict(item, byte_length=item['bytes']) for item in images]
    for item in rows:
        item.pop('bytes')
    return dict(run_id='a'*32, profile=profile, state='completed', api_version=api,
        report=report(terminal=1, workers_drained=True, ui_frozen=False,
            native_inflight=False), result_mode='manifest', export_id='b'*32,
        chunk_bytes=65536, total_bytes=sum(item['byte_length'] for item in rows), images=rows)


def transform(profile=V2, api='1.98.16-ngg2', images=()):
    def apply(method, value):
        value['profile'] = profile
        value['api_version'] = api
        value['report'].update(terminal=int(value['state'] in native.TERMINAL),
            workers_drained=value['state'] in native.TERMINAL, ui_frozen=False,
            native_inflight=False)
        if method == 'necro_native_results':
            value['images'] = deepcopy(list(images))
        return value
    return apply


class NativeEvidenceProfile081Tests(TimerTestCase):
    client = paged.PagedResultsTests.client
    execute = paged.PagedResultsTests.execute

    def test_fresh_cap15_start_uses_v16_evidence_profile_and_existing_paged_wire(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                capabilities=['necrogold_native_v14', 'necrogold_native_v15'],
                transform=transform()) as server:
            value = self.execute(server, folder)
            starts = [params for method, params in server.calls if method == 'necro_native_start']
            self.assertEqual([V2], [params['profile'] for params in starts],
                'fresh_cap15_run_must_opt_into_all_restart_evidence_profile')
            self.assertEqual(('native-walk-v16', V2, True),
                (value['revision'], value['profile'], value['resolved']))
            self.assertEqual({'run_id', 'profile'}, set(starts[0]))
            results = [params for method, params in server.calls if method == 'necro_native_results']
            self.assertEqual(['manifest'], [params.get('mode') for params in results])
            self.assertEqual(value, native._load(Path(folder)))

    def test_fresh_client_rejects_cap14_only_app_before_any_start(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                capabilities=['necrogold_native_v14']) as server:
            value = self.execute(server, folder)
            self.assertEqual(('native_capability_missing', False),
                (value['stop_reason'], value['start_attempted']))
            self.assertEqual([], server.calls)

    def test_every_revision_binds_profile_api_and_aggregate_without_wire_upgrade(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            for version in range(1, 17):
                with self.subTest(version=version):
                    self.assertEqual(api_for(version), native._revision_api('native-walk-v'+str(version)))
                    limit = NEW_BYTES if version == 16 else OLD_BYTES
                    rows = metadata(limit//(512*1024))
                    value = journal(version, images=rows)
                    native._save(base, value)
                    self.assertEqual(limit, sum(item['bytes'] for item in native._load(base)['images']))
                    over = deepcopy(value)
                    over['images'] = rows+[dict(metadata(1, 24)[0], name='extra.png', capture_id=100)]
                    native._save(base, over)
                    with self.assertRaisesRegex(ProbeError, 'native_journal_invalid'):
                        native._load(base)
                    wrong = deepcopy(value)
                    wrong['profile'] = V1 if version == 16 else V2
                    native._save(base, wrong)
                    with self.assertRaisesRegex(ProbeError, 'native_journal_invalid'):
                        native._load(base)
            for invalid in ('native-walk-v0', 'native-walk-v17', True, None):
                with self.subTest(invalid=invalid), self.assertRaises(ProbeError):
                    native._revision_api(invalid)

    def test_manifest_checkpoint_and_image_bounds_are_selected_by_trusted_profile(self):
        with self.assertRaisesRegex(ProbeError, 'invalid_native_images'):
            native._images([image_item()], profile=V2)
        for profile, count in ((V1, 8), (V2, 20)):
            rows = metadata(count)
            parsed = native._manifest(response(profile, images=rows), 'a'*32,
                profile=profile)[3]
            self.assertEqual(count*512*1024, parsed['total_bytes'])
            self.assertEqual(checkpoint(rows), native._export_checkpoint(checkpoint(rows), profile=profile))
            for invalid in (rows+[dict(metadata(1, 24)[0], name='extra.png', capture_id=100)],
                    [dict(rows[0], bytes=512*1024+1)]):
                with self.subTest(profile=profile, count=len(invalid)), self.assertRaises(ProbeError):
                    native._manifest(response(profile, images=invalid), 'a'*32, profile=profile)
                with self.assertRaises(ProbeError):
                    native._export_checkpoint(checkpoint(invalid), profile=profile)
        for api in ('1.98.14-ngg2', '1.98.15-ngg2'):
            with self.subTest(api=api), self.assertRaises(ProbeError):
                native._manifest(response(V2, api), 'a'*32, profile=V2, api_version=api)
        with self.assertRaises(ProbeError):
            native._manifest(response(V2, images=metadata(9)), 'a'*32, profile=V1)
        with self.assertRaises(ProbeError):
            native._manifest(response(V1), 'a'*32, profile='normal-1-1-v3')

    def test_started_v1_recovery_preserves_all_fifteen_uuid_api_and_no_new_start(self):
        for version in range(1, 16):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as folder, \
                    NativeServer(finish=True, transform=transform(V1, api_for(version))) as server:
                seed = journal(version)
                native._save(Path(folder), seed)
                value = self.execute(server, folder)
                self.assertEqual((seed['revision'], seed['run_id'], V1, True),
                    (value['revision'], value['run_id'], value['profile'], value['resolved']))
                self.assertEqual([], server.schema_calls)
                self.assertNotIn('necro_native_start', [method for method, params in server.calls])
                self.assertEqual('necro_native_status', server.calls[0][0])
                self.assertFalse(server.calls[0][1]['keepalive'])

    def test_never_started_v1_migrates_both_contract_fields_once_with_same_uuid(self):
        for version in (1, 14, 15):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as folder, \
                    NativeServer(finish=True, transform=transform()) as server:
                seed = journal(version, started=False)
                native._save(Path(folder), seed)
                value = self.execute(server, folder)
                self.assertEqual(('native-walk-v16', V2, seed['run_id'], True),
                    (value['revision'], value['profile'], value['run_id'], value['resolved']))
                starts = [params for method, params in server.calls if method == 'necro_native_start']
                self.assertEqual([dict(run_id=seed['run_id'], profile=V2)], starts)
                self.assertEqual(['/schema'], server.schema_calls)

    def test_v1_wire_start_remains_allowed_and_claimed_v2_status_cannot_upgrade_v15(self):
        with NativeServer(finish=True, transform=transform(V1)) as server:
            value = self.client(server).call('necro_native_start',
                dict(run_id='a'*32, profile=V1)).result
            self.assertEqual(V1, value['profile'])
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=transform(V2, images=())) as server:
            seed = journal(15)
            native._save(Path(folder), seed)
            value = self.execute(server, folder)
            self.assertEqual(('native-walk-v15', V1, False),
                (value['revision'], value['profile'], value['resolved']))
            self.assertEqual('invalid_native_status', value['stop_reason'])
            self.assertNotIn('necro_native_start', [method for method, params in server.calls])

    def test_paged_v2_above_four_mib_verifies_every_png_cursor_and_published_zip(self):
        images = [dict(image_item('capture-%06d.png'%index, 512*1024 if index < 9 else 24),
            capture_id=index) for index in range(1, 10)]
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=transform(images=images)) as server:
            base = Path(folder)/'spool'
            destination = Path(folder)/'output'
            value, archive = publication.run(destination, spool=base, test_number='081',
                notice=lambda _: None, session=lambda output: self.execute(server, output))
            self.assertTrue(value['resolved'], value['stop_reason'])
            self.assertEqual(OLD_BYTES+24, value['image_export']['total_bytes'])
            self.assertEqual(9, len(value['images']))
            self.assertEqual([row['bytes'] for row in value['images']], value['image_export']['offsets'])
            self.assertEqual([row['sha256'] for row in value['images']],
                value['image_export']['prefix_sha256'])
            with zipfile.ZipFile(archive) as zipped:
                for item, original in zip(value['images'], images):
                    raw = (base/('native-'+value['run_id'])/'images'/item['name']).read_bytes()
                    self.assertEqual(base64.b64decode(original['data_base64']), raw)
                    self.assertEqual(item['sha256'], hashlib.sha256(raw).hexdigest())
                    self.assertEqual(raw, zipped.read('test-081/native-'+value['run_id']+'/images/'+item['name']))
            self.assertTrue(all(params.get('mode') in ('manifest', 'chunk')
                for method, params in server.calls if method == 'necro_native_results'))
            self.assertEqual(value, native._load(base))
