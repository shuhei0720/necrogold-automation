"""TEST052 encrypted export checkpoint batches and interrupted-prefix recovery."""
import base64
import hashlib
import json
from pathlib import Path
import tempfile
import time
from unittest.mock import patch

from necroprobe import native_walk as native
import test_native_paged_results as paged
from test_native_walk import NativeServer, image_item
from timer_support import TimerTestCase


class ExportBatchTests(TimerTestCase):
    client = paged.PagedResultsTests.client
    execute = paged.PagedResultsTests.execute

    def test_four_chunk_batches_reduce_durable_fragment_and_journal_writes(self):
        image = image_item(size=512*1024)
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=paged.page_images(image)) as server:
            atomic = native._atomic
            fragments = []
            journals = []
            def trace(path, raw):
                atomic(path, raw)
                if path.name.endswith('.part'):
                    fragments.append(len(raw))
                elif path.name in ('report.json', 'active.json'):
                    row = json.loads(raw)
                    if 'image_export' in row:
                        journals.append((path.name, row['image_export']['offsets'][0]))
            with patch.object(native, '_atomic', side_effect=trace):
                record = self.execute(server, folder)
            self.assertTrue(record['resolved'], record['stop_reason'])
            self.assertEqual([262144, 524288], fragments,
                'eight_chunks_require_two_durable_fragment_checkpoints')
            changed = []
            for name, offset in journals:
                if name == 'active.json' and offset and offset not in changed:
                    changed.append(offset)
            self.assertEqual([262144, 524288], changed)
            self.assertEqual(image['sha256'], record['images'][0]['sha256'])
            self.assertEqual(8, sum(p.get('mode') == 'chunk' for m, p in server.calls))

    def test_slow_storage_clock_completes_within_the_original_ninety_second_attempt(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=paged.page_images(image_item(size=512*1024))) as server:
            now = [0]
            exporting = [False]
            atomic = native._atomic
            def mark_manifest(method, params, result):
                if params.get('mode') == 'manifest':
                    exporting[0] = True
                return result
            server.page_transform = mark_manifest
            def slow_storage(path, raw):
                atomic(path, raw)
                if exporting[0]:
                    now[0] += 5_000_000_000
            with patch.object(native, '_atomic', side_effect=slow_storage):
                record = self.execute(server, folder, clock=lambda: now[0],
                    max_seconds=180, export_seconds=90)
            self.assertTrue(record['resolved'],
                'bounded_batches_must_finish_the_slow_storage_model_within_90s: '
                + str(record['stop_reason']))
            self.assertEqual([524288], record['image_export']['offsets'])
            self.assertLess(now[0], 90_000_000_000)

    def test_checkpoint_order_and_partial_last_batch_stay_within_four_chunks(self):
        image = image_item(size=4*65536+17)
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=paged.page_images(image)) as server:
            atomic = native._atomic
            writes = []
            def trace(path, raw):
                if path.name.endswith('.part'):
                    writes.append(('fragment', len(raw)))
                elif path.name in ('report.json', 'active.json'):
                    row = json.loads(raw)
                    if 'image_export' in row:
                        writes.append((path.name, row['image_export']['offsets'][0]))
                atomic(path, raw)
            with patch.object(native, '_atomic', side_effect=trace):
                record = self.execute(server, folder)
            self.assertTrue(record['resolved'])
            self.assertEqual([('fragment', 262144), ('fragment', 262161)],
                [row for row in writes if row[0] == 'fragment'])
            for index, row in enumerate(writes):
                if row[0] == 'fragment':
                    self.assertEqual([row, ('report.json', row[1]), ('active.json', row[1])],
                        writes[index:index+3])

    def test_three_four_five_chunk_and_image_boundaries_have_separate_bounded_checkpoints(self):
        cases = [([3*65536], [196608]), ([4*65536], [262144]),
                 ([5*65536], [262144, 327680]), ([4*65536+17], [262144, 262161]),
                 ([3*65536, 2*65536+17], [196608, 131089])]
        for sizes, expected in cases:
            with self.subTest(sizes=sizes), tempfile.TemporaryDirectory() as folder:
                images = [dict(image_item(name='frame-'+str(i)+'.png', size=size), capture_id=i)
                          for i, size in enumerate(sizes)]
                with NativeServer(finish=True, transform=paged.page_images(*images)) as server:
                    atomic = native._atomic
                    fragments = []
                    def trace(path, raw):
                        atomic(path, raw)
                        if path.name.endswith('.part'):
                            fragments.append(len(raw))
                    with patch.object(native, '_atomic', side_effect=trace):
                        record = self.execute(server, folder)
                    self.assertTrue(record['resolved'], record['stop_reason'])
                    self.assertEqual(expected, fragments)
                    self.assertEqual(sizes, record['image_export']['offsets'])
                    self.assertEqual(len(sizes), len(record['images']))

    def test_one_two_or_three_valid_chunks_flush_before_error_cancel_or_deadline(self):
        for valid in (1, 2, 3):
            for failure in ('invalid', 'base64', 'lost', 'timeout', 'cancel', 'deadline'):
                with self.subTest(valid=valid, failure=failure), tempfile.TemporaryDirectory() as folder, \
                        NativeServer(finish=True, transform=paged.page_images(
                            image_item(size=4*65536+17))) as server:
                    now = [0]
                    stopped = [False]
                    def interrupt(method, params, result):
                        if params.get('mode') != 'chunk':
                            return result
                        if failure in ('cancel', 'deadline') and params['offset'] == (valid-1)*65536:
                            if failure == 'cancel':
                                stopped[0] = True
                            else:
                                now[0] = 500_000_000
                        elif params['offset'] == valid*65536:
                            if failure == 'invalid':
                                result['offset'] += 1
                            elif failure == 'base64':
                                result['data_base64'] = '!!'
                            elif failure == 'lost':
                                server.lose.append(method)
                            elif failure == 'timeout':
                                time.sleep(.15)
                        return result
                    server.page_transform = interrupt
                    first = self.execute(server, folder, clock=lambda: now[0],
                        cancelled=lambda: stopped[0], export_seconds=.5, results_seconds=.1)
                    self.assertFalse(first['resolved'])
                    expected_error = {'invalid':'invalid_native_images', 'base64':'invalid_native_images',
                        'lost':'connection_error',
                        'timeout':'rpc_deadline', 'cancel':'cancel_requested',
                        'deadline':'host_deadline'}[failure]
                    self.assertEqual(expected_error, first['stop_reason'])
                    self.assertEqual([valid*65536], first['image_export']['offsets'])
                    self.assertEqual(first, native._load(Path(folder)))
                    self.assertEqual([], first['images'])
                    self.assertFalse(any(m == 'necro_native_cancel' for m, p in server.calls))
                    calls = [p['offset'] for m, p in server.calls if p.get('mode') == 'chunk']
                    self.assertEqual(list(range(0, (valid+(failure not in ('cancel', 'deadline')))*65536,
                        65536)), calls)
                    server.page_transform = None
                    server.schema_calls.clear()
                    before = len(server.calls)
                    recovered = self.execute(server, folder)
                    self.assertTrue(recovered['resolved'], recovered['stop_reason'])
                    self.assertEqual(first['run_id'], recovered['run_id'])
                    self.assertEqual([], server.schema_calls)
                    later = server.calls[before:]
                    self.assertEqual('necro_native_status', later[0][0])
                    self.assertFalse(later[0][1]['keepalive'])
                    self.assertFalse(any(m in ('necro_native_start', 'necro_native_cancel') for m, p in later))
                    chunks = [p for m, p in later if p.get('mode') == 'chunk']
                    self.assertEqual(valid*65536, chunks[0]['offset'])
                    self.assertTrue(all(p['export_id'] == first['image_export']['export_id'] for p in chunks))

    def test_failed_fragment_or_either_journal_io_is_never_retried(self):
        for target in ('fragment', 'report.json', 'active.json'):
            for after_rename in (False, True):
                with self.subTest(target=target, after_rename=after_rename), \
                        tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                            transform=paged.page_images(image_item(size=512*1024))) as server:
                    atomic = native._atomic
                    failures = []
                    def uncertain_io(path, raw):
                        selected = path.name.endswith('.part') if target == 'fragment' else path.name == target
                        offset = len(raw) if path.name.endswith('.part') else (
                            json.loads(raw).get('image_export', {}).get('offsets', [0])[0]
                            if path.name in ('report.json', 'active.json') else 0)
                        if selected and offset == 524288:
                            failures.append(path.name)
                            if after_rename:
                                atomic(path, raw)
                            raise OSError('uncertain_export_io')
                        atomic(path, raw)
                    with patch.object(native, '_atomic', side_effect=uncertain_io):
                        with self.assertRaisesRegex(OSError, 'uncertain_export_io'):
                            self.execute(server, folder)
                    self.assertEqual(1, len(failures), 'failed_IO_must_not_trigger_a_second_flush')
                    first = native._load(Path(folder))
                    durable = 524288 if target == 'active.json' and after_rename else 262144
                    self.assertEqual([durable], first['image_export']['offsets'])
                    self.assertEqual([], first['images'])
                    self.assertFalse(any(m == 'necro_native_cancel' for m, p in server.calls))
                    server.schema_calls.clear()
                    before = len(server.calls)
                    recovered = self.execute(server, folder)
                    self.assertTrue(recovered['resolved'], recovered['stop_reason'])
                    self.assertEqual([], server.schema_calls)
                    chunks = [p for m, p in server.calls[before:] if p.get('mode') == 'chunk']
                    self.assertEqual(list(range(durable, 524288, 65536)), [p['offset'] for p in chunks])

    def test_probe_error_flush_io_failure_is_not_retried_and_keeps_the_previous_cursor(self):
        for after_rename in (False, True):
            with self.subTest(after_rename=after_rename), tempfile.TemporaryDirectory() as folder, \
                    NativeServer(finish=True, transform=paged.page_images(image_item(size=4*65536))) as server:
                def bad_third_chunk(method, params, result):
                    if params.get('mode') == 'chunk' and params['offset'] == 2*65536:
                        result['offset'] += 1
                    return result
                server.page_transform = bad_third_chunk
                atomic = native._atomic
                attempts = []
                def fail_flush(path, raw):
                    if path.name.endswith('.part'):
                        attempts.append(len(raw))
                        if after_rename:
                            atomic(path, raw)
                        raise OSError('prefix_flush_io')
                    atomic(path, raw)
                with patch.object(native, '_atomic', side_effect=fail_flush):
                    with self.assertRaisesRegex(OSError, 'prefix_flush_io'):
                        self.execute(server, folder)
                self.assertEqual([131072], attempts)
                first = native._load(Path(folder))
                self.assertEqual([0], first['image_export']['offsets'])
                self.assertFalse(any(m == 'necro_native_cancel' for m, p in server.calls))
                server.page_transform = None
                before = len(server.calls)
                recovered = self.execute(server, folder)
                self.assertTrue(recovered['resolved'], recovered['stop_reason'])
                self.assertEqual([0, 65536, 131072, 196608],
                    [p['offset'] for m, p in server.calls[before:] if p.get('mode') == 'chunk'])

    def test_crash_after_fragment_or_either_journal_rename_resumes_the_durable_cursor(self):
        class Crash(Exception):
            pass
        for target in ('fragment', 'report.json', 'active.json'):
            with self.subTest(target=target), tempfile.TemporaryDirectory() as folder, \
                    NativeServer(finish=True, transform=paged.page_images(image_item(size=512*1024))) as server:
                atomic = native._atomic
                def crash_after_rename(path, raw):
                    atomic(path, raw)
                    selected = path.name.endswith('.part') if target == 'fragment' else path.name == target
                    offset = len(raw) if path.name.endswith('.part') else (
                        json.loads(raw).get('image_export', {}).get('offsets', [0])[0]
                        if path.name in ('report.json', 'active.json') else 0)
                    if selected and offset == 262144:
                        raise Crash('after_rename')
                with patch.object(native, '_atomic', side_effect=crash_after_rename):
                    with self.assertRaises(Crash):
                        self.execute(server, folder)
                first = native._load(Path(folder))
                durable = 262144 if target == 'active.json' else 0
                self.assertEqual([durable], first['image_export']['offsets'])
                server.schema_calls.clear()
                before = len(server.calls)
                recovered = self.execute(server, folder)
                self.assertTrue(recovered['resolved'], recovered['stop_reason'])
                self.assertEqual([], server.schema_calls)
                later = server.calls[before:]
                self.assertEqual(list(range(durable, 524288, 65536)),
                    [p['offset'] for m, p in later if p.get('mode') == 'chunk'])
                self.assertFalse(any(m in ('necro_native_start', 'necro_native_cancel') for m, p in later))

    def test_replayed_second_third_and_fourth_chunk_must_match_the_renamed_suffix(self):
        class Crash(Exception):
            pass
        for changed_chunk in (2, 3, 4):
            with self.subTest(changed_chunk=changed_chunk), tempfile.TemporaryDirectory() as folder, \
                    NativeServer(finish=True, transform=paged.page_images(image_item(size=512*1024))) as server:
                atomic = native._atomic
                def crash_after_fragment(path, raw):
                    atomic(path, raw)
                    if path.name.endswith('.part'):
                        raise Crash()
                with patch.object(native, '_atomic', side_effect=crash_after_fragment):
                    with self.assertRaises(Crash):
                        self.execute(server, folder)
                self.assertEqual([0], native._load(Path(folder))['image_export']['offsets'])
                def conflicting_suffix(method, params, result):
                    if params.get('mode') == 'chunk' and params['offset'] == (changed_chunk-1)*65536:
                        raw = base64.b64decode(result['data_base64'])
                        result['data_base64'] = base64.b64encode(bytes([raw[0]^1])+raw[1:]).decode()
                    return result
                server.page_transform = conflicting_suffix
                first = self.execute(server, folder)
                self.assertFalse(first['resolved'])
                self.assertEqual('invalid_native_images', first['stop_reason'])
                self.assertEqual([(changed_chunk-1)*65536], first['image_export']['offsets'])
                self.assertEqual([], first['images'])
                server.page_transform = None
                recovered = self.execute(server, folder)
                self.assertTrue(recovered['resolved'], recovered['stop_reason'])

    def test_unverified_suffix_survives_partial_replay_flush_and_later_conflicts(self):
        self.assert_unverified_suffix_survives_partial_replay(native.REVISION)

    def test_literal_v10_suffix_survives_repeated_interruption_and_read_only_recovery(self):
        self.assert_unverified_suffix_survives_partial_replay('native-walk-v10')

    def test_literal_v11_suffix_survives_repeated_interruption_and_read_only_recovery(self):
        self.assert_unverified_suffix_survives_partial_replay('native-walk-v11', legacy_trace=True)

    def test_literal_v12_suffix_survives_repeated_interruption_and_read_only_recovery(self):
        self.assert_unverified_suffix_survives_partial_replay('native-walk-v12')

    def assert_unverified_suffix_survives_partial_replay(self, revision, legacy_trace=False):
        class Crash(Exception):
            pass
        for replayed in (1, 2, 3):
            with self.subTest(replayed=replayed), tempfile.TemporaryDirectory() as folder, \
                    NativeServer(finish=True, transform=paged.page_images(image_item(size=512*1024))) as server:
                atomic = native._atomic
                def crash_after_four_chunks(path, raw):
                    atomic(path, raw)
                    if path.name.endswith('.part'):
                        raise Crash()
                with patch.object(native, '_atomic', side_effect=crash_after_four_chunks):
                    with self.assertRaises(Crash):
                        self.execute(server, folder)
                seed = native._load(Path(folder))
                seed['revision'] = revision
                if legacy_trace:
                    seed['native_report'].pop('motion_references')
                    transform = server.transform
                    def without_trace(method, result):
                        result = transform(method, result)
                        result['report'].pop('motion_references', None)
                        return result
                    server.transform = without_trace
                native._save(Path(folder), seed)
                server.schema_calls.clear()
                recovery_start = len(server.calls)
                fragment = Path(folder)/('native-'+seed['run_id'])/'images'/'.parts'/'initial.png.part'
                original_fragment = fragment.read_bytes()
                stopped = [False]
                def cancel_partial_replay(method, params, result):
                    if params.get('mode') == 'chunk' and params['offset'] == (replayed-1)*65536:
                        stopped[0] = True
                    return result
                server.page_transform = cancel_partial_replay
                partial = self.execute(server, folder, cancelled=lambda: stopped[0])
                self.assertEqual('cancel_requested', partial['stop_reason'])
                self.assertEqual([replayed*65536], partial['image_export']['offsets'])
                retained = fragment.read_bytes()
                self.assertEqual(hashlib.sha256(retained[:replayed*65536]).hexdigest(),
                    partial['image_export']['prefix_sha256'][0])
                def conflict_after_partial_replay(method, params, result):
                    if params.get('mode') == 'chunk' and params['offset'] == replayed*65536:
                        raw = base64.b64decode(result['data_base64'])
                        result['data_base64'] = base64.b64encode(bytes([raw[0]^1])+raw[1:]).decode()
                    return result
                server.page_transform = conflict_after_partial_replay
                before = len(server.calls)
                rejected = self.execute(server, folder)
                self.assertFalse(rejected['resolved'])
                self.assertEqual('invalid_native_images', rejected['stop_reason'])
                self.assertEqual([replayed*65536], rejected['image_export']['offsets'],
                    'a_second_invocation_must_compare_the_still_unverified_suffix_before_advancing')
                self.assertEqual(262144, len(retained), 'partial_flush_must_keep_unverified_renamed_tail')
                self.assertEqual(original_fragment, retained)
                self.assertEqual([replayed*65536],
                    [p['offset'] for m, p in server.calls[before:] if p.get('mode') == 'chunk'])
                self.assertEqual([], rejected['images'])
                server.page_transform = None
                recovered = self.execute(server, folder)
                self.assertTrue(recovered['resolved'], recovered['stop_reason'])
                self.assertEqual(revision, recovered['revision'])
                self.assertEqual([], server.schema_calls)
                self.assertEqual({seed['run_id']},
                    {p['run_id'] for m, p in server.calls[recovery_start:]})
                self.assertFalse(any(m in ('necro_native_start', 'necro_native_cancel')
                    for m, p in server.calls[recovery_start:]))

    def test_literal_v10_nonzero_checkpoint_keeps_four_chunk_saves_and_read_only_recovery(self):
        self.assert_batched_nonzero_checkpoint('native-walk-v10')

    def test_literal_v11_nonzero_checkpoint_keeps_four_chunk_saves_and_read_only_recovery(self):
        self.assert_batched_nonzero_checkpoint('native-walk-v11', legacy_trace=True)

    def test_literal_v12_nonzero_checkpoint_keeps_four_chunk_saves_and_read_only_recovery(self):
        self.assert_batched_nonzero_checkpoint('native-walk-v12')

    def assert_batched_nonzero_checkpoint(self, revision, legacy_trace=False):
        image = image_item(size=512*1024)
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=paged.page_images(image)) as server:
            stopped = [False]
            def cancel_first_chunk(method, params, result):
                if params.get('mode') == 'chunk':
                    stopped[0] = True
                return result
            server.page_transform = cancel_first_chunk
            first = self.execute(server, folder, cancelled=lambda: stopped[0])
            self.assertEqual([65536], first['image_export']['offsets'])
            first['revision'] = revision
            if legacy_trace:
                first['native_report'].pop('motion_references')
                transform = server.transform
                def without_trace(method, result):
                    result = transform(method, result)
                    result['report'].pop('motion_references', None)
                    return result
                server.transform = without_trace
            native._save(Path(folder), first)
            server.page_transform = None
            server.schema_calls.clear()
            atomic = native._atomic
            fragments = []
            def trace(path, raw):
                atomic(path, raw)
                if path.name.endswith('.part'):
                    fragments.append(len(raw))
            before = len(server.calls)
            with patch.object(native, '_atomic', side_effect=trace):
                recovered = self.execute(server, folder)
            self.assertTrue(recovered['resolved'], recovered['stop_reason'])
            self.assertEqual(revision, recovered['revision'])
            self.assertEqual([327680, 524288], fragments)
            self.assertEqual(image['sha256'], recovered['images'][0]['sha256'])
            self.assertEqual([], server.schema_calls)
            later = server.calls[before:]
            self.assertEqual({first['run_id']}, {p['run_id'] for m, p in later})
            self.assertFalse(any(m in ('necro_native_start', 'necro_native_cancel') for m, p in later))
            self.assertEqual(list(range(65536, 524288, 65536)),
                [p['offset'] for m, p in later if p.get('mode') == 'chunk'])
            self.assertEqual(recovered, native._load(Path(folder)))

    def test_literal_v9_nonzero_checkpoint_keeps_per_chunk_saves_and_read_only_recovery(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=paged.page_images(image_item(size=4*65536+17))) as server:
            stopped = [False]
            def cancel_first_chunk(method, params, result):
                if params.get('mode') == 'chunk':
                    stopped[0] = True
                return result
            server.page_transform = cancel_first_chunk
            first = self.execute(server, folder, cancelled=lambda: stopped[0])
            self.assertEqual([65536], first['image_export']['offsets'])
            first['revision'] = 'native-walk-v9'
            native._save(Path(folder), first)
            server.page_transform = None
            server.schema_calls.clear()
            atomic = native._atomic
            fragments = []
            def trace(path, raw):
                atomic(path, raw)
                if path.name.endswith('.part'):
                    fragments.append(len(raw))
            before = len(server.calls)
            with patch.object(native, '_atomic', side_effect=trace):
                recovered = self.execute(server, folder)
            self.assertTrue(recovered['resolved'], recovered['stop_reason'])
            self.assertEqual('native-walk-v9', recovered['revision'])
            self.assertEqual([131072, 196608, 262144, 262161], fragments)
            self.assertEqual([], server.schema_calls)
            later = server.calls[before:]
            self.assertFalse(any(m in ('necro_native_start', 'necro_native_cancel') for m, p in later))
            self.assertEqual([65536, 131072, 196608, 262144],
                [p['offset'] for m, p in later if p.get('mode') == 'chunk'])
            self.assertEqual(recovered, native._load(Path(folder)))

    def test_progress_is_bounded_and_default_off_and_display_failures_are_harmless(self):
        images = [dict(image_item(name='frame-'+str(i)+'.png'), capture_id=i) for i in range(20)]
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=paged.page_images(*images)) as server:
            messages = []
            record = self.execute(server, folder, progress=lambda saved, total: messages.append((saved, total)))
            self.assertTrue(record['resolved'])
            self.assertEqual([(saved, 20) for saved in range(21)], messages)
        for error in (OSError('pipe'), ValueError('closed'), RuntimeError('display')):
            with self.subTest(error=type(error)), tempfile.TemporaryDirectory() as folder, \
                    NativeServer(finish=True, transform=paged.page_images(image_item())) as server:
                with patch('builtins.print') as output:
                    record = self.execute(server, folder)
                self.assertTrue(record['resolved'])
                output.assert_not_called()
                def broken_display(saved, total):
                    raise error
                record = self.execute(server, folder, progress=broken_display)
                self.assertTrue(record['resolved'], record['stop_reason'])

    def test_progress_io_still_checks_deadline_and_cancellation_after_committed_image(self):
        for failure in ('host_deadline', 'cancel_requested'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as folder, \
                    NativeServer(finish=True, transform=paged.page_images(image_item())) as server:
                now = [0]
                stopped = [False]
                def late_display(saved, total):
                    if saved:
                        if failure == 'host_deadline':
                            now[0] = 500_000_000
                        else:
                            stopped[0] = True
                first = self.execute(server, folder, progress=late_display, clock=lambda: now[0],
                    cancelled=lambda: stopped[0], export_seconds=.5)
                self.assertFalse(first['resolved'])
                self.assertEqual(failure, first['stop_reason'])
                self.assertEqual(1, len(first['images']))
                self.assertEqual([32], first['image_export']['offsets'])
                self.assertEqual(first, native._load(Path(folder)))

    def test_recovery_progress_starts_with_the_durably_verified_image_count(self):
        images = [image_item(), dict(image_item(name='terminal.png', size=65553), capture_id=2)]
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=paged.page_images(*images)) as server:
            stopped = [False]
            def cancel_partial_second_image(method, params, result):
                if params.get('mode') == 'chunk' and params['capture_id'] == 2:
                    stopped[0] = True
                return result
            server.page_transform = cancel_partial_second_image
            first = self.execute(server, folder, cancelled=lambda: stopped[0])
            self.assertEqual(1, len(first['images']))
            self.assertEqual([32, 65536], first['image_export']['offsets'])
            server.page_transform = None
            progress = []
            recovered = self.execute(server, folder,
                progress=lambda saved, total: progress.append((saved, total)))
            self.assertTrue(recovered['resolved'], recovered['stop_reason'])
            self.assertEqual((1, 2), progress[0])
            self.assertEqual((2, 2), progress[-1])
            self.assertLessEqual(len(progress), 3)

