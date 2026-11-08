"""TEST054 closed motion-reference diagnostics over authenticated native HTTP."""
from copy import deepcopy
import base64
import json
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch

from necroprobe import native_walk as native
from necroprobe.crypto import mac, python_xor
from necroprobe.validation import ProbeError
from test_native_walk import NativeServer
from test_protocol import KEY
import test_native_paged_results as paged
from timer_support import TimerTestCase


def motion_event(command_id=5, **updates):
    value = dict(id=command_id, kind=4, outcome=2, direction=3,
        source_capture_id=101, source_start_ns=300, observed_capture_id=110,
        begin_ns=500, end_ns=550, target_ns=650, ordinal=3,
        motion=1, dx=0, dy=-1)
    value.update(updates)
    return value


def reference_row(command_id=5, **updates):
    value = dict(command_id=command_id, authority_capture_id=101,
        reference_capture_id=99, reference_start_ns=200, reference_prefix=2,
        observed_capture_id=110, reference_eligible=True, primary_motion=0,
        fallback_attempted=True, fallback_motion=1,
        selected_capture_id=99, selected_motion=1)
    value.update(updates)
    return value


def reference_report(**updates):
    first = motion_event(2, source_capture_id=34, observed_capture_id=62,
        source_start_ns=20, begin_ns=100, end_ns=150, target_ns=250, ordinal=1)
    first_row = reference_row(2, authority_capture_id=34, reference_capture_id=0,
        reference_start_ns=0, reference_prefix=0, observed_capture_id=62,
        reference_eligible=False, primary_motion=1, fallback_attempted=False,
        fallback_motion=0, selected_capture_id=34)
    value = dict(schema='ngg2-native-v1', clock_id='a'*32, device_now_ns=1000,
        input_state=0, goods=0, events=[
            motion_event(1, kind=1, source_capture_id=1, observed_capture_id=3,
                motion=0, dx=0, dy=0, ordinal=0),
            first,
            motion_event(3, outcome=3, observed_capture_id=0, motion=0, dx=0, dy=0),
            motion_event(4, outcome=3, observed_capture_id=0, motion=0, dx=0, dy=0),
            motion_event()], motion_references=[first_row, reference_row()])
    value.update(updates)
    return value


def add_reference_report(method, result):
    if method.startswith('necro_native_'):
        report = reference_report(clock_id=result['run_id'])
        result['report'].update(report)
    return result


class MotionReferenceTests(TimerTestCase):
    client = paged.PagedResultsTests.client
    execute = paged.PagedResultsTests.execute

    def test_client_054_revision_capability_and_output(self):
        self.assertEqual('native-walk-v12', native.REVISION)
        self.assertEqual('necrogold_native_v11', native.CAPABILITY)
        self.assertEqual('runtime/test-054', native.parser().parse_args([]).output)
        path = Path(native.__file__).resolve().parents[1]/'test_054.sh'
        self.assertEqual(0, subprocess.run(['sh','-n',str(path)], capture_output=True).returncode)
        self.assertIn('native-walk-v12 / 1.98.14-ngg2', path.read_text())
        self.assertIn('--output runtime/test-054', path.read_text())

    def test_fresh_start_requires_the_motion_reference_diagnostic(self):
        def missing(method, result):
            result['report'].pop('motion_references', None)
            return result
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True, transform=missing) as server:
            record = self.execute(server, folder)
            self.assertFalse(record['resolved'], 'new_capability_must_not_accept_a_disconnected_trace')
            self.assertEqual('invalid_native_report', record['stop_reason'])
            self.assertEqual(1, sum(m == 'necro_native_start' for m, p in server.calls))

    def test_fresh_native_v10_without_motion_reference_capability_never_starts(self):
        tags = ['necrogold_native_v'+str(version) for version in range(1,11)]
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True, capabilities=tags) as server:
            record = self.execute(server, folder)
            self.assertEqual(('native_capability_missing', False, 0),
                (record['stop_reason'], record['start_attempted'],
                 sum(m == 'necro_native_start' for m, p in server.calls)))
            self.assertEqual(['/schema'], server.schema_calls)
            self.assertEqual([], server.calls)

    def test_reference_selection_survives_encrypted_results_and_both_journals(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=add_reference_report) as server:
            record = self.execute(server, folder)
            self.assertTrue(record['resolved'], record['stop_reason'])
            expected = reference_report()['motion_references']
            self.assertEqual(expected, record['native_report']['motion_references'])
            self.assertEqual(99, expected[-1]['selected_capture_id'])
            self.assertNotEqual(expected[-1]['authority_capture_id'], expected[-1]['selected_capture_id'])
            self.assertEqual(record, native._load(Path(folder)))
            for path in (Path(folder)/'active.json',
                    Path(folder)/('native-'+record['run_id'])/'report.json'):
                self.assertEqual(expected, json.loads(path.read_text())['native_report']['motion_references'])

    def test_all_primary_and_fallback_motion_enums_keep_the_actual_selected_source(self):
        for primary in range(8):
            report = reference_report()
            row = report['motion_references'][-1]
            row.update(primary_motion=primary, fallback_attempted=primary == 0,
                fallback_motion=0, selected_capture_id=101, selected_motion=primary)
            report['events'][-1].update(motion=primary, dx=0, dy=0)
            with self.subTest(primary=primary):
                self.assertEqual(row, native._report(report)['motion_references'][-1])
        for fallback in range(8):
            report = reference_report()
            row = report['motion_references'][-1]
            row.update(fallback_motion=fallback, selected_capture_id=99 if fallback == 1 else 101,
                selected_motion=1 if fallback == 1 else 0)
            report['events'][-1].update(motion=row['selected_motion'], dx=0,
                dy=-1 if fallback == 1 else 0)
            with self.subTest(fallback=fallback):
                self.assertEqual(row, native._report(report)['motion_references'][-1])
        report = reference_report()
        report['motion_references'][-1].update(reference_eligible=False, fallback_attempted=False,
            fallback_motion=0, selected_capture_id=101, selected_motion=0)
        report['events'][-1].update(motion=0, dx=0, dy=0)
        self.assertFalse(native._report(report)['motion_references'][-1]['fallback_attempted'])

    def test_unassessed_ack_row_and_goods_frame_keep_distinct_observation_meanings(self):
        for reference in (False, True):
            for goods in (False, True):
                report = reference_report(goods=int(goods))
                row = report['motion_references'][-1]
                row.update(observed_capture_id=0, primary_motion=0, fallback_attempted=False,
                    fallback_motion=0, selected_capture_id=101, selected_motion=0)
                if not reference:
                    row.update(reference_capture_id=0, reference_start_ns=0, reference_prefix=0,
                        reference_eligible=False)
                report['events'][-1].update(observed_capture_id=111 if goods else 0, motion=0, dx=0, dy=0)
                with self.subTest(reference=reference, goods=goods):
                    self.assertEqual(row, native._report(report)['motion_references'][-1])
        report = reference_report(goods=1)
        report['motion_references'][-1].update(primary_motion=7, fallback_attempted=False,
            fallback_motion=0, selected_capture_id=101, selected_motion=7)
        report['events'][-1].update(observed_capture_id=111, motion=7, dx=0, dy=0)
        self.assertEqual(110, native._report(report)['motion_references'][-1]['observed_capture_id'])

    def test_motion_reference_rows_require_exact_keys_types_ranges_and_unique_ids(self):
        invalid = [None, {}, 'PRIVATE', [None], [reference_row()]*17]
        for key, original in reference_row().items():
            missing = reference_row()
            missing.pop(key)
            invalid.append([missing])
            bad_values = (0, 1, None, 'PRIVATE') if type(original) is bool else (
                True, False, None, -1, 2**63, 1.0, '1')
            if key in ('primary_motion', 'fallback_motion', 'selected_motion'):
                bad_values += (8,)
            invalid.extend([reference_row(**{key:value})] for value in bad_values)
        invalid.extend(([reference_row(private='PRIVATE')], [reference_row(), reference_row()]))
        for rows in invalid:
            with self.subTest(rows=rows), self.assertRaisesRegex(ProbeError, 'invalid_native_report'):
                native._report(reference_report(motion_references=rows))

    def test_event_source_prefix_observation_and_selection_relations_are_closed(self):
        row_changes = [dict(command_id=4), dict(authority_capture_id=5),
            dict(reference_capture_id=0), dict(reference_start_ns=301),
            dict(reference_prefix=4), dict(reference_prefix=5),
            dict(reference_capture_id=102), dict(observed_capture_id=109),
            dict(fallback_attempted=False), dict(primary_motion=2),
            dict(reference_eligible=False), dict(selected_capture_id=5),
            dict(selected_capture_id=101), dict(selected_motion=0)]
        for update in row_changes:
            report = reference_report()
            report['motion_references'][-1].update(update)
            with self.subTest(row=update), self.assertRaisesRegex(ProbeError, 'invalid_native_report'):
                native._report(report)
        for update in (dict(kind=3), dict(outcome=3), dict(outcome=4),
                dict(source_capture_id=100), dict(observed_capture_id=111),
                dict(motion=0), dict(direction=2), dict(dx=1), dict(dy=0)):
            report = reference_report()
            report['events'][-1].update(update)
            with self.subTest(event=update), self.assertRaisesRegex(ProbeError, 'invalid_native_report'):
                native._report(report)
        for missing in ('id', 'kind', 'outcome', 'source_capture_id', 'observed_capture_id', 'motion'):
            report = reference_report()
            report['events'][-1].pop(missing)
            with self.subTest(missing=missing), self.assertRaisesRegex(ProbeError, 'invalid_native_report'):
                native._report(report)
        for rows in ([], [reference_row()], list(reversed(reference_report()['motion_references']))):
            with self.subTest(rows=rows), self.assertRaisesRegex(ProbeError, 'invalid_native_report'):
                native._report(reference_report(motion_references=rows))

    def test_goods_exception_is_only_latest_pending_unknown_or_tween(self):
        for case in ('no_goods', 'older_ack', 'moved', 'blocked', 'reversed_capture'):
            report = reference_report(goods=1)
            if case == 'older_ack':
                report['events'][1]['observed_capture_id'] = 63
            else:
                row = report['motion_references'][-1]
                row.update(primary_motion=7, fallback_attempted=False, fallback_motion=0,
                    selected_capture_id=101, selected_motion=7)
                report['events'][-1].update(observed_capture_id=111, motion=7, dx=0, dy=0)
                if case == 'no_goods':
                    report['goods'] = 0
                elif case in ('moved', 'blocked'):
                    motion = 1 if case == 'moved' else 2
                    row.update(primary_motion=motion, selected_motion=motion)
                    report['events'][-1]['motion'] = motion
                elif case == 'reversed_capture':
                    report['events'][-1]['observed_capture_id'] = 109
            with self.subTest(case=case), self.assertRaisesRegex(ProbeError, 'invalid_native_report'):
                native._report(report)

    def test_prior_ack_prefix_skips_unsent_ids_and_sixteen_ack_rows_fit(self):
        parsed = native._report(reference_report())
        self.assertEqual(2, parsed['motion_references'][-1]['reference_prefix'])
        events, rows = [], []
        for index in range(16):
            command_id, authority = 3*index+2, 100+index
            events.extend([motion_event(command_id-1, outcome=3, observed_capture_id=0,
                    motion=0, dx=0, dy=0, begin_ns=0),
                motion_event(command_id, source_capture_id=authority, observed_capture_id=0,
                    motion=0, dx=0, dy=0)])
            rows.append(reference_row(command_id, authority_capture_id=authority,
                reference_capture_id=0, reference_start_ns=0, reference_prefix=0,
                observed_capture_id=0, reference_eligible=False, primary_motion=0,
                fallback_attempted=False, fallback_motion=0, selected_capture_id=authority,
                selected_motion=0))
        report = reference_report(events=events, motion_references=rows)
        self.assertEqual(rows, native._report(report)['motion_references'])
        report['events'].append(motion_event(50, source_capture_id=116, observed_capture_id=0,
            motion=0, dx=0, dy=0))
        report['motion_references'].append(reference_row(50, authority_capture_id=116,
            reference_capture_id=0, reference_start_ns=0, reference_prefix=0,
            observed_capture_id=0, reference_eligible=False, primary_motion=0,
            fallback_attempted=False, fallback_motion=0, selected_capture_id=116, selected_motion=0))
        with self.assertRaisesRegex(ProbeError, 'invalid_native_report'):
            native._report(report)

    def test_malformed_authenticated_results_do_not_replace_the_last_valid_report(self):
        changes = [dict(primary_motion=True), dict(private='PRIVATE_TRACE_TEXT'),
            dict(authority_capture_id=5), dict(reference_prefix=4),
            dict(selected_capture_id=101), dict(fallback_attempted=False)]
        for update in changes:
            def malformed(method, result):
                add_reference_report(method, result)
                if method == 'necro_native_results':
                    result['report']['motion_references'][-1].update(update)
                return result
            with self.subTest(update=update), tempfile.TemporaryDirectory() as folder, \
                    NativeServer(finish=True, transform=malformed) as server:
                record = self.execute(server, folder)
                self.assertFalse(record['resolved'])
                self.assertEqual('invalid_native_report', record['stop_reason'])
                self.assertEqual(reference_report()['motion_references'],
                    record['native_report']['motion_references'])
                self.assertNotIn('PRIVATE_TRACE_TEXT', json.dumps(record))

    def test_duplicate_motion_reference_json_key_is_rejected_after_authentication(self):
        with NativeServer(finish=True, transform=add_reference_report) as server:
            client = self.client(server)
            exchange = client.transport._exchange
            def duplicate(method, path, body, timeout, limit):
                raw = exchange(method, path, body, timeout, limit)
                nonce = bytes.fromhex(json.loads(body)['nonce'])
                envelope = json.loads(raw)
                plain = python_xor(mac(KEY, b'loopctrl-v1|enc-resp'+nonce), nonce,
                    base64.b64decode(envelope['ct']))
                self.assertIn(b'"command_id": 5', plain)
                plain = plain.replace(b'"command_id": 5', b'"command_id": 5, "command_id": 5', 1)
                cipher = python_xor(mac(KEY, b'loopctrl-v1|enc-resp'+nonce), nonce, plain)
                tag = mac(mac(KEY, b'loopctrl-v1|mac'+nonce), b'resp'+nonce+cipher).hex()
                return json.dumps(dict(ct=base64.b64encode(cipher).decode(), tag=tag)).encode()
            with patch.object(client.transport, '_exchange', side_effect=duplicate):
                with self.assertRaisesRegex(ProbeError, 'duplicate_json_key'):
                    client.call('necro_native_status', {'run_id':'a'*32, 'keepalive':False})
            self.assertEqual('result_json', client.last_failure['stage'])

    def test_fresh_journal_requires_trace_and_all_legacy_journals_validate_present_rows(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=add_reference_report) as server:
            original = self.execute(server, folder)
            self.assertTrue(original['resolved'])
            missing = deepcopy(original)
            missing['native_report'].pop('motion_references')
            native._save(Path(folder), missing)
            with self.assertRaisesRegex(ProbeError, 'native_journal_invalid'):
                native._load(Path(folder))
            for version in range(1,12):
                legacy = deepcopy(original)
                legacy['revision'] = 'native-walk-v'+str(version)
                if version < 9:
                    legacy.pop('image_export', None)
                native._save(Path(folder), legacy)
                self.assertEqual(legacy, native._load(Path(folder)))
                legacy['native_report']['motion_references'][-1]['reference_prefix'] = 4
                native._save(Path(folder), legacy)
                with self.subTest(version=version), self.assertRaisesRegex(ProbeError, 'native_journal_invalid'):
                    native._load(Path(folder))

    def test_literal_v11_started_recovery_allows_absent_trace_without_schema_or_start(self):
        with tempfile.TemporaryDirectory() as folder, NativeServer(finish=True,
                transform=add_reference_report) as server:
            seed = self.execute(server, folder)
            seed.update(revision='native-walk-v11', resolved=False)
            seed['native_report'].pop('motion_references')
            native._save(Path(folder), seed)
            def legacy(method, result):
                result['report'].pop('motion_references', None)
                return result
            server.transform = legacy
            server.capabilities = ['necrogold_native_v10']
            server.schema_calls.clear()
            before = len(server.calls)
            recovered = self.execute(server, folder)
            self.assertTrue(recovered['resolved'], recovered['stop_reason'])
            self.assertEqual('native-walk-v11', recovered['revision'])
            self.assertNotIn('motion_references', recovered['native_report'])
            self.assertEqual([], server.schema_calls)
            self.assertFalse(any(m in ('necro_native_start', 'necro_native_cancel')
                for m, p in server.calls[before:]))
