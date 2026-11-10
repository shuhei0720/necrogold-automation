"""TEST069: terminal evidence collection has no authority to extend gameplay.

Encrypted HTTP fixtures exercise the public client and durable journals. The
storage clock models slow file-provider IO; it is not an iPhone speed result.
"""
from copy import deepcopy
from contextlib import redirect_stdout
import io
from pathlib import Path
import signal
import tempfile
import unittest
from unittest.mock import patch

from necroprobe import native_walk as native
from necroprobe.crypto import Crypto
from necroprobe.protocol import HttpTransport
import test_native_paged_results as paged
from test_native_walk import NativeServer, image_item
from test_protocol import KEY, TOK
from timer_support import TimerTestCase


def terminal_images(*items):
    def transform(method, result):
        if result.get('state') in native.TERMINAL:
            result['report'].update(terminal=1, workers_drained=True,
                native_inflight=False, ui_frozen=False)
        if method == 'necro_native_results':
            result['images'] = deepcopy(list(items))
        return result
    return transform


class NativeCollection069Tests(TimerTestCase):
    client = paged.PagedResultsTests.client
    execute = paged.PagedResultsTests.execute

    def assert_only_results_after_terminal(self, server):
        methods = [method for method, _params in server.calls]
        self.assertEqual(1, methods.count('necro_native_start'))
        self.assertEqual(0, methods.count('necro_native_cancel'))
        terminal = methods.index('necro_native_status')
        self.assertTrue(all(method == 'necro_native_results' for method in methods[terminal+1:]))
        self.assertEqual(1, len({params['run_id'] for _method, params in server.calls}))

    def test_slow_stopped_collection_finishes_after_game_and_old_export_deadlines(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=terminal_images(image_item(size=512*1024))) as server:
            now = [0]
            exporting = [False]
            atomic = native._atomic
            def terminal_near_game_deadline(method, params, result):
                if method == 'necro_native_status':
                    result['state'] = 'stopped'
                    now[0] = 179_000_000_000
                    exporting[0] = True
                if params.get('mode') == 'manifest':result['state'] = 'stopped'
                return result
            server.page_transform = terminal_near_game_deadline
            def slow_storage(path, raw):
                atomic(path, raw)
                if exporting[0]:now[0] += 10_000_000_000
            with patch.object(native, '_atomic', side_effect=slow_storage):
                record = self.execute(server, folder, clock=lambda:now[0], max_seconds=185)
            self.assertTrue(record['resolved'],
                'fully drained native stop must not lose read-only collection to the old game deadline: '
                + str(record['stop_reason']))
            self.assertEqual('stopped', record['native_state'])
            self.assertEqual([512*1024], record['image_export']['offsets'])
            self.assertEqual(1, len(record['images']))
            self.assertGreater(now[0], 179_000_000_000 + 90_000_000_000)
            self.assertLess(now[0], 179_000_000_000 + 300_000_000_000)
            self.assertEqual(record, native._load(Path(folder)))
            self.assert_only_results_after_terminal(server)

    def test_missing_or_unsafe_terminal_fields_keep_the_original_export_deadline(self):
        faults = ({'workers_drained':False}, {'ui_frozen':True}, {'native_inflight':True},
            {'input_state':4}, {'terminal':0}, {'workers_drained':None},
            {'ui_frozen':None}, {'native_inflight':None})
        for fault in faults:
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as folder, \
                    NativeServer(finish=True, transform=terminal_images(image_item())) as server:
                now = [0]
                def unsafe(method, params, result):
                    if 'report' in result:
                        for key, value in fault.items():
                            if value is None:result['report'].pop(key, None)
                            else:result['report'][key] = value
                    if method == 'necro_native_status':now[0] = 180_000_000_000
                    return result
                server.page_transform = unsafe
                record = self.execute(server, folder, clock=lambda:now[0], max_seconds=185)
                self.assertFalse(record['resolved'])
                self.assertEqual('host_deadline', record['stop_reason'])
                self.assertEqual(['necro_native_start','necro_native_status'],
                    [method for method, _params in server.calls])

    def test_unsafe_manifest_cannot_borrow_the_trusted_status_collection_budget(self):
        faults = ({'workers_drained':False}, {'ui_frozen':True}, {'native_inflight':True},
            {'input_state':4}, {'terminal':0}, {'workers_drained':None},
            {'ui_frozen':None}, {'native_inflight':None}, {'clock_id':'c'*32},
            {'cancel_requested':True})
        for fault in faults:
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as folder, \
                    NativeServer(finish=True, transform=terminal_images(image_item())) as server:
                def unsafe(method, params, result):
                    if params.get('mode') == 'manifest':
                        for key, value in fault.items():
                            if value is None:result['report'].pop(key, None)
                            else:result['report'][key] = value
                    return result
                server.page_transform = unsafe
                record = self.execute(server, folder)
                self.assertFalse(record['resolved'])
                self.assertEqual('native_input_unresolved', record['stop_reason'])
                self.assertEqual([], [params for _method, params in server.calls
                    if params.get('mode') == 'chunk'])
                self.assert_only_results_after_terminal(server)

    def test_nonterminal_unknown_input_still_uses_the_bounded_cancel_cleanup(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(input_state=4) as server:
            now = [0]
            def late_status(method, params, result):
                if method == 'necro_native_status':now[0] = 185_000_000_000
                return result
            server.page_transform = late_status
            record = self.execute(server, folder, clock=lambda:now[0], max_seconds=185)
            self.assertFalse(record['resolved'])
            self.assertEqual('host_deadline', record['stop_reason'])
            self.assertEqual(['necro_native_start','necro_native_status','necro_native_cancel'],
                [method for method, _params in server.calls])

    def test_cancel_during_trusted_read_only_collection_sends_no_native_cancel(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=terminal_images(image_item())) as server:
            stopped = [False]
            def cancel_at_manifest(method, params, result):
                if params.get('mode') == 'manifest':stopped[0] = True
                return result
            server.page_transform = cancel_at_manifest
            record = self.execute(server, folder, cancelled=lambda:stopped[0])
            self.assertFalse(record['resolved'])
            self.assertEqual('cancel_requested', record['stop_reason'])
            self.assertEqual([], [params for _method, params in server.calls
                if params.get('mode') == 'chunk'])
            self.assert_only_results_after_terminal(server)

    def test_cancel_before_terminal_confirmation_keeps_the_short_cleanup_budget(self):
        for cancellation in ('signal','host_failure','persisted_cancel','native_cancel_requested'):
            with self.subTest(cancellation=cancellation), tempfile.TemporaryDirectory() as folder, \
                    NativeServer(finish=cancellation in ('persisted_cancel','native_cancel_requested'),
                        lose=['necro_native_start'] if cancellation == 'host_failure' else (),
                        transform=terminal_images(image_item())) as server:
                if cancellation == 'persisted_cancel':
                    def lose_initial_chunk(method, params, result):
                        if params.get('mode') == 'chunk':server.lose.append(method)
                        return result
                    server.page_transform = lose_initial_chunk
                    seed = self.execute(server, folder)
                    self.assertFalse(seed['resolved'])
                    self.assertEqual([0], seed['image_export']['offsets'])
                    seed.update(resolved=False, cancel_attempted=True, cancel_attempts=1)
                    native._save(Path(folder), seed)
                stopped = [False]
                collecting = [False]
                now = [0]
                atomic = native._atomic
                def cancel_after_start(method, params, result):
                    if cancellation == 'signal' and method == 'necro_native_start':stopped[0] = True
                    if cancellation == 'native_cancel_requested' and 'report' in result:
                        result['report']['cancel_requested'] = True
                    if method == 'necro_native_cancel' or method == 'necro_native_status':
                        collecting[0] = True
                    return result
                server.page_transform = cancel_after_start
                def slow_storage(path, raw):
                    atomic(path, raw)
                    if collecting[0]:
                        now[0] += (1 if cancellation in ('signal','host_failure') else 10)*1_000_000_000
                with patch.object(native, '_atomic', side_effect=slow_storage):
                    record = self.execute(server, folder, clock=lambda:now[0],
                        cancelled=lambda:stopped[0], max_seconds=185, recovery_seconds=6)
                self.assertFalse(record['resolved'],
                    'existing signal, host or native cancellation cannot gain the new 300s collection phase')
                self.assertEqual('host_deadline', record['stop_reason'])
                self.assertEqual(1 if cancellation in ('signal','host_failure') else 0,
                    sum(method == 'necro_native_cancel' for method, _params in server.calls))

    def test_storage_failure_after_trusted_stop_has_no_emergency_native_cancel(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=terminal_images(image_item())) as server:
            save = native._save
            def fail_stopped(base, record):
                if record['state'] in native.TERMINAL:raise OSError('storage failed')
                save(base, record)
            with patch.object(native, '_save', side_effect=fail_stopped):
                with self.assertRaises(OSError):self.execute(server, folder)
            self.assert_only_results_after_terminal(server)

    def test_collection_deadline_starts_at_trusted_observation_before_journal_io(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=terminal_images(image_item())) as server:
            now = [0]
            trusted = [False]
            atomic = native._atomic
            def observe_stop(method, params, result):
                if method == 'necro_native_status':trusted[0] = True
                return result
            server.page_transform = observe_stop
            def slow_journal(path, raw):
                atomic(path, raw)
                if trusted[0]:now[0] += 1_000_000_000
            with patch.object(native, '_atomic', side_effect=slow_journal):
                record = self.execute(server, folder, clock=lambda:now[0], collection_seconds=1)
            self.assertFalse(record['resolved'])
            self.assertEqual('host_deadline', record['stop_reason'])
            self.assertEqual([], [params for method, params in server.calls
                if method == 'necro_native_results'])
            self.assert_only_results_after_terminal(server)

    def test_interrupted_export_recovers_same_uuid_export_and_cursor_with_no_keepalive(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True, input_state=3,
                transform=terminal_images(image_item(size=512*1024))) as server:
            def lose_after_first_checkpoint(method, params, result):
                if params.get('mode') == 'chunk' and params['offset'] == 262144:
                    server.lose.append(method)
                return result
            server.page_transform = lose_after_first_checkpoint
            original = self.execute(server, folder)
            self.assertFalse(original['resolved'])
            self.assertEqual([262144], original['image_export']['offsets'])
            before = len(server.calls)
            now = [0]
            atomic = native._atomic
            def late_recovery(method, params, result):
                if method == 'necro_native_status':now[0] = 179_000_000_000
                return result
            server.page_transform = late_recovery
            def slow_storage(path, raw):
                atomic(path, raw)
                now[0] += 1_000_000_000
            with patch.object(native, '_atomic', side_effect=slow_storage):
                recovered = self.execute(server, folder, clock=lambda:now[0], max_seconds=185)
            self.assertTrue(recovered['resolved'], recovered['stop_reason'])
            self.assertEqual(original['run_id'], recovered['run_id'])
            self.assertEqual(original['image_export']['export_id'], recovered['image_export']['export_id'])
            calls = server.calls[before:]
            self.assertEqual('necro_native_status', calls[0][0])
            self.assertFalse(calls[0][1]['keepalive'])
            self.assertTrue(all(method == 'necro_native_results' for method, _params in calls[1:]))
            self.assertEqual([262144,327680,393216,458752],
                [params['offset'] for _method, params in calls if params.get('mode') == 'chunk'])
            self.assertEqual(1, sum(method == 'necro_native_start' for method, _params in server.calls))
            self.assertFalse(any(method == 'necro_native_cancel' for method, _params in server.calls))
            self.assertEqual({original['run_id']}, {params['run_id'] for _method, params in server.calls})

    def test_final_journal_over_collection_deadline_keeps_complete_evidence_unresolved(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=terminal_images(image_item())) as server:
            now = [0]
            atomic = native._atomic
            def expire_final_journal(path, raw):
                atomic(path, raw)
                if path.name == 'active.json' and b'"resolved":true' in raw:
                    now[0] = 300_000_000_000
            with patch.object(native, '_atomic', side_effect=expire_final_journal):
                record = self.execute(server, folder, clock=lambda:now[0])
            self.assertFalse(record['resolved'])
            self.assertEqual('host_deadline', record['stop_reason'])
            self.assertEqual([32], record['image_export']['offsets'])
            self.assertEqual(1, len(record['images']))
            self.assertEqual(record, native._load(Path(folder)))
            self.assert_only_results_after_terminal(server)


class NativeCollection069CliTests(unittest.TestCase):
    def test_outcome_receives_record_and_cancel_state_before_any_completion_display(self):
        record = {'run_id':'a'*32, 'resolved':False}
        output = io.StringIO()
        observed = []
        previous = signal.getsignal(signal.SIGTERM)
        def run(*_args, **_options):
            signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
            return record
        def outcome(received, cancelled):
            observed.append((received is record, cancelled, output.getvalue()))
            return record
        with patch.object(native, 'load_pairing', return_value=(KEY,TOK)), \
                patch.object(native, 'Crypto', return_value=Crypto(native=False)), \
                patch.object(native, 'run_session', side_effect=run), redirect_stdout(output):
            returned = native.main(['--output','unused'], outcome=outcome)
        self.assertIs(record, returned)
        self.assertEqual([(True, True, '')], observed)
        self.assertEqual('', output.getvalue())
        self.assertEqual(previous, signal.getsignal(signal.SIGTERM))
        with self.subTest(cancellation='outer_handoff'), tempfile.TemporaryDirectory() as folder, \
                NativeServer(finish=True, transform=terminal_images(image_item())) as server:
            output = io.StringIO()
            session = native.run_session
            def execute(client, base, **options):
                return session(client, base, lock_path=Path(folder)/'lock', **options)
            with patch.object(native, 'load_pairing', return_value=(KEY,TOK)), \
                    patch.object(native, 'Crypto', return_value=Crypto(native=False)), \
                    patch.object(native, 'HttpTransport', return_value=HttpTransport(server.server.server_port)), \
                    patch.object(native, 'run_session', side_effect=execute), \
                    redirect_stdout(output):
                record, cancelled = native.main(['--output',folder], cancelled=lambda:True,
                    outcome=lambda record, cancelled:(record,cancelled))
            self.assertFalse(record['start_attempted'],
                'wrapper cancellation before native signal installation must prohibit native start')
            self.assertTrue(cancelled)
            self.assertEqual([], server.calls)
            self.assertEqual('', output.getvalue())
