"""TEST068: finish read-only collection without republishing verified images.

The public encrypted endpoint fixture supplies bounded PNG-header samples and
terminal native records. Storage-clock tests describe durable IO costs, not
iPhone performance or a successful game run. Existing cursor, digest, deadline
and same-run recovery authority remain the oracle.
"""
import base64
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from necroprobe import native_walk as native
from necroprobe.crypto import Crypto
from necroprobe.deadlines import OwnedRpcTimer
from necroprobe.protocol import HttpTransport
import test_native_paged_results as paged
from test_native_walk import NativeServer, image_item, bind_legacy_api
from test_protocol import KEY, TOK
from timer_support import TimerTestCase


def completed_image_path(folder, record, name='initial.png'):
    return Path(folder)/('native-'+record['run_id'])/'images'/name


def mark_unresolved(folder, record):
    record = deepcopy(record)
    record.update(resolved=False, stop_reason='host_deadline')
    native._save(Path(folder), record)
    return record


class NativeCollection068Tests(TimerTestCase):
    client = paged.PagedResultsTests.client
    execute = paged.PagedResultsTests.execute

    def seed(self, server, folder):
        record = self.execute(server, folder)
        self.assertTrue(record['resolved'], record['stop_reason'])
        return mark_unresolved(folder, record)

    def assert_read_only_recovery(self, server, before, original, recovered):
        calls = server.calls[before:]
        self.assertEqual(original['run_id'], recovered['run_id'])
        self.assertEqual(original['native_report']['clock_id'], recovered['native_report']['clock_id'])
        self.assertEqual([], server.schema_calls)
        self.assertNotIn('necro_native_start', [method for method, _params in calls])
        self.assertNotIn('necro_native_cancel', [method for method, _params in calls])
        self.assertTrue(all(params.get('run_id') == original['run_id'] for _method, params in calls))

    def test_verified_complete_images_are_revalidated_without_image_or_per_image_journal_writes(self):
        images = [image_item(), dict(image_item('terminal.png', 65553), capture_id=2)]
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=paged.page_images(*images)) as server:
            original = self.seed(server, folder)
            before = len(server.calls);server.schema_calls.clear()
            atomic, save = native._atomic, native._save
            image_writes, saves = [], []
            def trace_atomic(path, raw):
                if path.suffix == '.png':image_writes.append(path.name)
                atomic(path, raw)
            def trace_save(base, record):
                saves.append(deepcopy(record));save(base, record)
            with patch.object(native, '_atomic', side_effect=trace_atomic), \
                    patch.object(native, '_save', side_effect=trace_save):
                recovered = self.execute(server, folder)
            self.assertTrue(recovered['resolved'], recovered['stop_reason'])
            self.assertEqual([], image_writes,
                'authenticated completed images with identical bytes must not be republished')
            self.assertEqual(3, len(saves),
                'only invocation, manifest and terminal journals change during a complete replay')
            self.assertEqual(original['images'], recovered['images'])
            self.assertEqual(original['image_export'], recovered['image_export'])
            self.assertEqual(original['events'], recovered['events'][:len(original['events'])])
            self.assertEqual(recovered, native._load(Path(folder)))
            self.assert_read_only_recovery(server, before, original, recovered)
            self.assertEqual(['necro_native_status', 'necro_native_results'],
                [method for method, _params in server.calls[before:]])

    def test_slow_complete_replay_fits_the_original_attempt_by_avoiding_unchanged_writes(self):
        images = [image_item(), dict(image_item('terminal.png'), capture_id=2)]
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=paged.page_images(*images)) as server:
            original = self.seed(server, folder)
            before = len(server.calls);server.schema_calls.clear()
            now = [0];atomic = native._atomic
            def slow_atomic(path, raw):
                atomic(path, raw);now[0] += 1_000_000_000
            with patch.object(native, '_atomic', side_effect=slow_atomic):
                recovered = self.execute(server, folder, clock=lambda:now[0],
                    max_seconds=180, export_seconds=5.5)
            self.assertTrue(recovered['resolved'],
                'unchanged replay IO must fit the existing 5.5s export model: '+str(recovered['stop_reason']))
            self.assertLess(now[0], 7_500_000_000)
            self.assert_read_only_recovery(server, before, original, recovered)

    def test_completed_metadata_never_replaces_validation_of_saved_bytes_or_the_full_cursor(self):
        for fault in ('changed_image', 'missing_image', 'bad_fragment', 'bad_cursor'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as folder, \
                    NativeServer(finish=True, transform=paged.page_images(image_item())) as server:
                original = self.seed(server, folder)
                image = completed_image_path(folder, original)
                if fault == 'missing_image':image.unlink()
                elif fault == 'changed_image':
                    raw=bytearray(image.read_bytes());raw[-1]^=1;image.write_bytes(raw)
                elif fault == 'bad_fragment':
                    fragment=image.parent/'.parts'/(image.name+'.part')
                    fragment.write_bytes(b'x'*original['images'][0]['bytes'])
                else:
                    original['image_export']['prefix_sha256'][0]='0'*64
                    native._save(Path(folder), original)
                before=len(server.calls);server.schema_calls.clear()
                recovered=self.execute(server, folder)
                self.assertFalse(recovered['resolved'])
                self.assertEqual('invalid_native_images', recovered['stop_reason'])
                self.assert_read_only_recovery(server,before,original,recovered)

    def test_complete_png_header_and_geometry_are_checked_even_with_a_matching_full_digest(self):
        for fault in ('magic','width','height'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as folder:
                item=image_item();raw=bytearray(base64.b64decode(item['data_base64']))
                raw[0 if fault=='magic' else 19 if fault=='width' else 23]^=1
                item.update(data_base64=base64.b64encode(raw).decode(),
                    sha256=hashlib.sha256(raw).hexdigest())
                with NativeServer(finish=True,transform=paged.page_images(item)) as server:
                    seed=self.execute(server,folder)
                    self.assertFalse(seed['resolved'])
                    self.assertEqual('invalid_native_images',seed['stop_reason'])
                    # A stored journal's metadata is not proof that the PNG
                    # bytes are valid. Force that claim with a coherent SHA.
                    seed['images']=deepcopy(seed['image_export']['images'])
                    image=completed_image_path(folder,seed);image.write_bytes(raw)
                    native._save(Path(folder),seed)
                    before=len(server.calls);server.schema_calls.clear()
                    recovered=self.execute(server,folder)
                    self.assertFalse(recovered['resolved'])
                    self.assertEqual('invalid_native_images',recovered['stop_reason'])
                    self.assert_read_only_recovery(server,before,seed,recovered)

    def test_complete_fragment_without_identical_published_image_uses_the_existing_publish_order(self):
        for fault in ('part_only','missing_image','changed_image','partial_cursor'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as folder, \
                    NativeServer(finish=True,transform=paged.page_images(image_item())) as server:
                original=self.seed(server,folder);image=completed_image_path(folder,original)
                raw=image.read_bytes();fragment=image.parent/'.parts'/(image.name+'.part')
                fragment.write_bytes(raw)
                if fault=='changed_image':image.write_bytes(b'x'*len(raw))
                elif fault!='partial_cursor':image.unlink()
                if fault=='part_only':original['images']=[];native._save(Path(folder),original)
                if fault=='partial_cursor':
                    fragment.unlink()
                    original['image_export']['offsets'][0]=0
                    original['image_export']['prefix_sha256'][0]=hashlib.sha256(b'').hexdigest()
                    native._save(Path(folder),original)
                before=len(server.calls);server.schema_calls.clear()
                atomic=native._atomic;writes=[]
                def trace(path,body):
                    writes.append(path.name);atomic(path,body)
                with patch.object(native,'_atomic',side_effect=trace):
                    recovered=self.execute(server,folder)
                self.assertTrue(recovered['resolved'],recovered['stop_reason'])
                self.assertIn(image.name,writes,
                    'an already stored metadata row without an end cursor is not a completed replay')
                where=writes.index(image.name)
                self.assertEqual([image.name,'report.json','active.json'],writes[where:where+3])
                self.assertEqual(raw,image.read_bytes())
                self.assertFalse(fragment.exists())
                self.assertEqual(1,len(recovered['images']))
                self.assert_read_only_recovery(server,before,original,recovered)
                self.assertEqual([0] if fault=='partial_cursor' else [],
                    [p['offset'] for _m,p in server.calls[before:] if p.get('mode')=='chunk'])

    def test_complete_revalidation_checks_deadline_and_cancel_after_reading_without_republishing(self):
        for failure in ('host_deadline','cancel_requested'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as folder, \
                    NativeServer(finish=True,transform=paged.page_images(image_item())) as server:
                original=self.seed(server,folder);before=len(server.calls);server.schema_calls.clear()
                read=native._read_fragment;atomic=native._atomic;now=[0];cancelled=[False];images=[]
                def late_read(*args):
                    raw=read(*args)
                    if failure=='host_deadline':now[0]=500_000_000
                    else:cancelled[0]=True
                    return raw
                def trace(path,raw):
                    if path.suffix=='.png':images.append(path.name)
                    atomic(path,raw)
                with patch.object(native,'_read_fragment',side_effect=late_read), \
                        patch.object(native,'_atomic',side_effect=trace):
                    recovered=self.execute(server,folder,clock=lambda:now[0],
                        cancelled=lambda:cancelled[0],export_seconds=.5)
                self.assertFalse(recovered['resolved'])
                self.assertEqual(failure,recovered['stop_reason'])
                self.assertEqual([],images)
                self.assertEqual(original['images'],recovered['images'])
                self.assertEqual(original['image_export'],recovered['image_export'])
                self.assert_read_only_recovery(server,before,original,recovered)

    def test_literal_legacy_recovery_keeps_its_api_uuid_clock_and_complete_image_evidence(self):
        for revision in ('native-walk-v9','native-walk-v10','native-walk-v13','native-walk-v14',native.REVISION):
            served_api=[native.API_VERSION];pages=paged.page_images(image_item())
            def response(method,result):
                result=pages(method,result);result['api_version']=served_api[0]
                return result
            with self.subTest(revision=revision),tempfile.TemporaryDirectory() as folder, \
                    NativeServer(finish=True,transform=response) as server:
                original=self.seed(server,folder);original['revision']=revision
                bind_legacy_api(original);native._save(Path(folder),original)
                served_api[0]=native._revision_api(revision)
                before=len(server.calls);server.schema_calls.clear();writes=[];atomic=native._atomic
                def trace(path,raw):
                    if path.suffix=='.png':writes.append(path.name)
                    atomic(path,raw)
                with patch.object(native,'_atomic',side_effect=trace):recovered=self.execute(server,folder)
                self.assertTrue(recovered['resolved'],recovered['stop_reason'])
                self.assertEqual(revision,recovered['revision'])
                self.assertEqual(served_api[0],recovered['result_metadata']['api_version'])
                self.assertEqual(original['preflight'],recovered['preflight'])
                self.assertEqual([],writes)
                self.assert_read_only_recovery(server,before,original,recovered)


class NativeCollection068CliTests(unittest.TestCase):
    def seed(self,server,folder):
        with OwnedRpcTimer() as timer:
            client=native.NativeClient(HttpTransport(server.server.server_port),KEY,TOK,
                deadline_owner=timer,crypto=Crypto(native=False),timeout=8)
            record=native.run_session(client,folder,lock_path=Path(folder)/'lock',
                max_seconds=8,poll_seconds=.001)
        self.assertTrue(record['resolved'],record['stop_reason'])
        return mark_unresolved(folder,record)

    def invoke_main(self,server,folder,output,returned=None):
        original=native.run_session
        def bounded(client,base,**options):
            if returned is not None:
                return deepcopy(returned)
            return original(client,base,lock_path=Path(folder)/'lock',
                max_seconds=8,poll_seconds=.001,**options)
        with patch.object(native,'HttpTransport',return_value=HttpTransport(server.server.server_port)), \
                patch.object(native,'load_pairing',return_value=(KEY,TOK)), \
                patch.object(native,'Crypto',return_value=Crypto(native=False)), \
                patch.object(native,'run_session',side_effect=bounded),redirect_stdout(output):
            return native.main(['--output',folder])

    def goods(self,method,result):
        if 'report' in result:result['report'].update(reason=1,reason_name='goods',goods=1,paused=1)
        if method=='necro_native_results':result['images']=[image_item()]
        return result

    def test_cli_announces_read_only_recovery_before_status_and_separates_goods_from_old_collection_timeout(self):
        with tempfile.TemporaryDirectory() as folder,NativeServer(finish=True,transform=self.goods) as server:
            original=self.seed(server,folder);before=len(server.calls);server.schema_calls.clear()
            output=io.StringIO();seen=[]
            def transform(method,result):
                if method=='necro_native_status':seen.append(output.getvalue())
                return self.goods(method,result)
            server.transform=transform
            self.assertEqual(0,self.invoke_main(server,folder,output))
            text=output.getvalue();record=native._load(Path(folder))
            self.assertTrue(seen)
            self.assertIn('回収のみ',seen[0],
                'explain the lack of game launch before the first read-only recovery request')
            self.assertIn('今回はゲームを起動しません',seen[0])
            self.assertIn('NG-G2終了: completed / goods',text)
            self.assertIn('結果回収: 完了',text)
            self.assertIn('次回',text)
            self.assertNotIn('completed / host_deadline',text)
            self.assertEqual('host_deadline',record['stop_reason'],
                'the persisted prior failure remains historical evidence, separate from current display')
            self.assertEqual(original['run_id'],record['run_id'])
            self.assertEqual([],server.schema_calls)
            self.assertNotIn('necro_native_start',[m for m,_p in server.calls[before:]])
            # Presentation-only case: a failed status read can leave the last
            # valid native state running/none while the host has timed out.
            # That stale native reason must not hide the current host cause.
            uncertain=deepcopy(original)
            uncertain.update(state='unknown',native_state='running',resolved=False,
                stop_reason='host_deadline')
            uncertain['native_report'].update(reason_name='none',input_state=4,
                terminal=0,goods=0,paused=0,workers_drained=False,ui_frozen=True)
            unknown_output=io.StringIO()
            self.assertEqual(2,self.invoke_main(server,folder,unknown_output,returned=uncertain))
            self.assertIn('NG-G2終了: unknown / host_deadline',unknown_output.getvalue())
            self.assertNotIn('unknown / none',unknown_output.getvalue())
            # Finishing collection never launches a second game in that call.
            # A separate explicit invocation is the first fresh start.
            after=len(server.calls);server.schema_calls.clear();next_output=io.StringIO()
            self.assertEqual(0,self.invoke_main(server,folder,next_output))
            fresh=native._load(Path(folder))
            self.assertNotEqual(record['run_id'],fresh['run_id'])
            self.assertEqual(1,sum(m=='necro_native_start' for m,_p in server.calls[after:]))
            self.assertEqual(1,len(server.schema_calls))

    def test_cli_incomplete_recovery_reports_collection_failure_without_claiming_a_new_game(self):
        with tempfile.TemporaryDirectory() as folder,NativeServer(finish=True,transform=self.goods) as server:
            original=self.seed(server,folder);image=completed_image_path(folder,original)
            raw=bytearray(image.read_bytes());raw[-1]^=1;image.write_bytes(raw)
            before=len(server.calls);server.schema_calls.clear();output=io.StringIO()
            self.assertEqual(2,self.invoke_main(server,folder,output))
            text=output.getvalue();record=native._load(Path(folder))
            self.assertIn('回収のみ',text)
            self.assertIn('今回はゲームを起動しません',text)
            self.assertIn('NG-G2終了: completed / goods',text)
            self.assertIn('結果回収: 未完了',text)
            self.assertNotIn('結果回収: 完了',text)
            self.assertEqual(original['run_id'],record['run_id'])
            self.assertFalse(record['resolved'])
            self.assertEqual('invalid_native_images',record['stop_reason'])
            self.assertEqual([],server.schema_calls)
            self.assertNotIn('necro_native_start',[m for m,_p in server.calls[before:]])
