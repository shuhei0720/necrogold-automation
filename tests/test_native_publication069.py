"""TEST069 publication preserves local authority across interrupted copies."""
import hashlib
import io
from pathlib import Path
import signal
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch
import zipfile

from necroprobe import native_walk as native
from necroprobe import test069 as publication
from necroprobe.crypto import Crypto
from necroprobe.protocol import HttpTransport
from test_native_walk import NativeServer, image_item
from test_protocol import KEY, TOK


def seed(base, run_id='a'*32):
    metadata, raw = native._images([image_item(size=65553)])[0]
    # Native clock identity is independent of the native run UUID on device.
    report = dict(schema='ngg2-native-v1', clock_id='c'*32, device_now_ns=10,
        input_state=0, terminal=1, reason_name='goods', goods=1, paused=1,
        workers_drained=True, native_inflight=False, ui_frozen=False,
        events=[], motion_references=[], recovery=dict(initial_reacquisitions=0,
        post_move_reacquisitions=0, episode_id=0, mode=0, schedule_deadline_ns=0,
        visual_deadline_ns=0, ack_ns=0, record_count=0, dropped_records=0, records=[]))
    record = dict(schema='ngg2-host-v1', revision=native.REVISION, run_id=run_id,
        profile=native.PROFILE, state='completed', resolved=True, start_attempted=True,
        cancel_attempted=False, cancel_attempts=0, cancel_confirmed=True,
        stop_reason=None, native_state='completed', native_report=report,
        images=[metadata], result_metadata={}, events=[], events_dropped=0,
        host_clock_domain='python.monotonic_ns', native_clock_domain='device.monotonic_ns',
        image_export=dict(export_id=run_id, images=[metadata], total_bytes=len(raw),
        chunk_bytes=native.CHUNK_BYTES, offsets=[len(raw)], prefix_sha256=[metadata['sha256']]))
    base.mkdir(parents=True, exist_ok=True)
    native._save(base, record)
    images = base/('native-'+run_id)/'images'
    images.mkdir()
    (images/metadata['name']).write_bytes(raw)
    (images/'.parts').mkdir()
    return native._load(base)


class Publication069Tests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.spool = self.root/'local'/'test-069'
        self.destination = self.root/'mounted'
        self.destination.mkdir()
        self.messages = []

    def invoke(self, session=None, cancelled=lambda: False):
        return publication.run(self.destination, spool=self.spool,
            session=session or Mock(side_effect=AssertionError('must not start a new native run')),
            cancelled=cancelled, notice=self.messages.append)

    def test_resolved_without_receipt_publishes_only_and_archive_contains_exact_snapshot(self):
        record = seed(self.spool)
        record_path = self.spool/('native-'+record['run_id'])/'report.json'
        user_note = self.spool/'operator-note.txt'
        user_note.write_bytes(b'preserve local evidence')
        session = Mock(side_effect=AssertionError('resolved publication must not start'))
        returned, archive = self.invoke(session)
        self.assertIsNotNone(archive, 'a resolved journal alone is not a published result')
        self.assertEqual(record['run_id'], returned['run_id'])
        self.assertEqual(self.destination/'runtime'/('test-069-'+record['run_id']+'.zip'), archive)
        session.assert_not_called()
        self.assertEqual(b'preserve local evidence', user_note.read_bytes())
        with zipfile.ZipFile(archive) as result:
            self.assertIsNone(result.testzip())
            self.assertEqual(record_path.read_bytes(), result.read('test-069/'+record_path.relative_to(self.spool).as_posix()))
            self.assertTrue(all(info.compress_type == zipfile.ZIP_STORED for info in result.infolist()))
            self.assertNotIn('test-069/operator-note.txt', result.namelist())

    def test_only_a_separate_invocation_after_verified_publication_can_start(self):
        first = seed(self.spool)
        self.invoke()
        def fresh(base):
            return seed(base, 'b'*32)
        session = Mock(side_effect=fresh)
        second, archive = self.invoke(session)
        session.assert_called_once_with(self.spool)
        self.assertNotEqual(first['run_id'], second['run_id'])
        self.assertTrue(archive.is_file())
        self.assertTrue((archive.parent/('test-069-'+first['run_id']+'.zip')).is_file())
        with zipfile.ZipFile(archive) as result:
            self.assertFalse(any('native-'+first['run_id'] in name for name in result.namelist()))
        self.assertTrue((self.spool/('native-'+first['run_id'])/'report.json').is_file())

    def test_missing_png_or_incomplete_cursor_cannot_be_published_or_start_fresh(self):
        for fault in ('missing', 'cursor', 'prefix', 'metadata', 'geometry', 'unresolved_input'):
            with self.subTest(fault=fault):
                base = self.spool/fault
                record = seed(base)
                image = base/('native-'+record['run_id'])/'images'/'initial.png'
                if fault == 'missing': image.unlink()
                elif fault == 'cursor': record['image_export']['offsets'][0] = 0
                elif fault == 'prefix': record['image_export']['prefix_sha256'][0] = '0'*64
                elif fault == 'metadata': record['images'] = []
                elif fault == 'unresolved_input': record['native_report']['input_state'] = 4
                else:
                    raw = bytearray(image.read_bytes()); raw[19] ^= 1
                    image.write_bytes(raw)
                    digest = hashlib.sha256(raw).hexdigest()
                    record['images'][0]['sha256'] = digest
                    record['image_export']['images'][0]['sha256'] = digest
                    record['image_export']['prefix_sha256'][0] = digest
                if fault == 'cursor': record['image_export']['prefix_sha256'][0] = hashlib.sha256(b'').hexdigest()
                native._save(base, record)
                with self.assertRaises((OSError, native.ProbeError, ValueError)):
                    publication.run(self.destination, spool=base,
                        session=Mock(side_effect=AssertionError('must not start')), notice=self.messages.append)
        self.assertEqual([], list(self.destination.rglob('*.zip')))

    def test_failure_before_receipt_retries_publication_without_a_native_call(self):
        record = seed(self.spool)
        atomic = native._atomic
        def fail_receipt(path, raw):
            if path.name.endswith('.receipt.json'): raise OSError('interrupted before receipt')
            return atomic(path, raw)
        with patch.object(native, '_atomic', side_effect=fail_receipt):
            with self.assertRaisesRegex(OSError, 'before receipt'): self.invoke()
        final = self.destination/'runtime'/('test-069-'+record['run_id']+'.zip')
        self.assertTrue(final.is_file())
        before = final.read_bytes()
        returned, archive = self.invoke()
        self.assertEqual(record['run_id'], returned['run_id'])
        self.assertEqual(before, archive.read_bytes())

    def test_interrupted_provider_rename_retains_local_and_retries_without_start(self):
        record = seed(self.spool)
        original = self.spool/'active.json'
        before = original.read_bytes()
        replace = publication.os.replace
        def fail_rename(source, target):
            if Path(target).suffix == '.zip' and self.destination in Path(target).parents:
                raise OSError('provider rename interrupted')
            return replace(source, target)
        with patch.object(publication.os, 'replace', side_effect=fail_rename):
            with self.assertRaisesRegex(OSError, 'rename interrupted'): self.invoke()
        self.assertEqual(before, original.read_bytes())
        self.assertTrue(list(self.destination.rglob('*.part')))
        returned, archive = self.invoke()
        self.assertEqual(record['run_id'], returned['run_id'])
        self.assertTrue(archive.is_file())

    def test_interrupted_or_corrupted_provider_copy_is_never_published_and_can_retry(self):
        record = seed(self.spool)
        original = (self.spool/'active.json').read_bytes()
        def interrupted(source, target, cancelled):
            target.write_bytes(source.read_bytes()[:137])
            raise OSError('copy interrupted')
        with patch.object(publication, '_copy', side_effect=interrupted):
            with self.assertRaisesRegex(OSError, 'copy interrupted'): self.invoke()
        self.assertFalse(list(self.destination.rglob('*.zip')))
        self.assertEqual(original, (self.spool/'active.json').read_bytes())
        copy = publication._copy
        def corrupted(source, target, cancelled):
            copy(source, target, cancelled)
            raw = bytearray(target.read_bytes()); raw[-1] ^= 1
            target.write_bytes(raw)
        with patch.object(publication, '_copy', side_effect=corrupted):
            with self.assertRaisesRegex(ValueError, 'copy_changed'): self.invoke()
        self.assertFalse(list(self.destination.rglob('*.zip')))
        recovered, archive = self.invoke()
        self.assertEqual(record['run_id'], recovered['run_id'])
        self.assertTrue(archive.is_file())

    def test_existing_different_final_is_never_overwritten(self):
        record = seed(self.spool)
        folder = self.destination/'runtime'; folder.mkdir()
        final = folder/('test-069-'+record['run_id']+'.zip')
        final.write_bytes(b'previous user artifact')
        with self.assertRaises((OSError, native.ProbeError, ValueError)): self.invoke()
        self.assertEqual(b'previous user artifact', final.read_bytes())

    def test_changed_mount_or_deleted_zip_is_publication_only_even_with_local_receipt(self):
        record = seed(self.spool)
        _returned, final = self.invoke()
        final.unlink()
        recovered, archive = self.invoke()
        self.assertEqual(record['run_id'], recovered['run_id'])
        self.assertTrue(archive.is_file())

    def test_preflight_failure_is_not_a_completed_result(self):
        for start_intent in (False, True):
            with self.subTest(start_intent=start_intent):
                base = self.spool/str(start_intent)
                record = seed(base)
                record.update(start_attempted=start_intent, native_state=None, native_report=None,
                    state='stopped', images=[], stop_reason='host_deadline')
                record.pop('image_export')
                native._save(base, record)
                session = Mock(return_value=record)
                returned, archive = publication.run(self.destination, spool=base,
                    session=session, notice=self.messages.append)
                session.assert_called_once_with(base)
                self.assertIsNone(archive)
                fresh = Mock(side_effect=lambda output: seed(output, 'b'*32))
                _returned, archive = publication.run(self.destination, spool=base,
                    session=fresh, notice=self.messages.append)
                fresh.assert_called_once_with(base)
                self.assertTrue(archive.is_file())

    def test_cancellation_and_old_runtime_leave_every_source_byte_intact(self):
        record = seed(self.spool)
        old = self.destination/'runtime'/'test-068'/'operator.txt'
        old.parent.mkdir(parents=True); old.write_bytes(b'old data')
        before = (self.spool/'active.json').read_bytes()
        with self.assertRaises((OSError, native.ProbeError, ValueError)):
            self.invoke(cancelled=lambda: True)
        self.assertEqual(before, (self.spool/'active.json').read_bytes())
        self.assertEqual(b'old data', old.read_bytes())
        self.assertEqual([], list(self.destination.rglob('*.zip')))
        # A cancellation arriving during the previous ZIP verification must
        # still prevent admission to the next native session.
        self.invoke()
        stopped = [False]
        published = publication._published
        def late_cancel(*args, **kwargs):
            result = published(*args, **kwargs)
            stopped[0] = True
            return result
        session = Mock(return_value=record)
        with patch.object(publication, '_published', side_effect=late_cancel):
            with self.assertRaisesRegex(ValueError, 'cancel_requested'):
                self.invoke(session, cancelled=lambda: stopped[0])
        session.assert_not_called()
        # Publishing a durable receipt does not erase a concurrent cancel.
        fresh_base = self.spool/'receipt-cancel'
        seed(fresh_base, 'b'*32)
        atomic = native._atomic
        stopped[0] = False
        def receipt_cancel(path, raw):
            atomic(path, raw)
            if path.name.endswith('.receipt.json'): stopped[0] = True
        with patch.object(native, '_atomic', side_effect=receipt_cancel):
            with self.assertRaisesRegex(ValueError, 'cancel_requested'):
                publication.run(self.destination, spool=fresh_base,
                    session=Mock(side_effect=AssertionError('must not start')),
                    cancelled=lambda: stopped[0], notice=self.messages.append)
        # A previous cancellation is historical evidence. Once all results are
        # durable and input is resolved, it must not wedge publication forever.
        for state, run_id, following_id in (('completed','d'*32,'f'*32), ('stopped','e'*32,'9'*32)):
            with self.subTest(historical_cancel=state):
                base = self.spool/('historical-'+state)
                previous = seed(base, run_id)
                previous.update(state=state, native_state=state,
                    cancel_attempted=True, cancel_attempts=1, stop_reason='cancel_requested')
                previous['native_report']['cancel_requested'] = True
                native._save(base, previous)
                session = Mock(side_effect=AssertionError('publication must not start'))
                published = None
                try:
                    published = publication.run(self.destination, spool=base, session=session,
                        notice=self.messages.append)
                except publication.PublicationError:
                    pass
                self.assertIsNotNone(published, 'historical cancellation must allow a safe result ZIP')
                session.assert_not_called()
                self.assertTrue(published[1].is_file())
                next_session = Mock(side_effect=lambda output: seed(output, following_id))
                following, _archive = publication.run(self.destination, spool=base,
                    session=next_session, notice=self.messages.append)
                next_session.assert_called_once_with(base)
                self.assertEqual(following_id, following['run_id'])

    def test_wrapper_uses_stable_local_output_and_honors_the_native_outcome_cancel(self):
        for cancelled in (False, True):
            with self.subTest(cancelled=cancelled):
                phone_home = self.root/str(cancelled)
                calls = []
                def client_main(options, *, outcome, **kwargs):
                    calls.append(options)
                    self.assertFalse(kwargs['cancelled']())
                    base = Path(options[options.index('--output')+1])
                    return outcome(seed(base), cancelled)
                output = io.StringIO()
                with patch.object(publication.Path, 'home', return_value=phone_home), \
                        patch.object(publication.Path, 'cwd', return_value=self.destination), \
                        patch.object(native, 'main', side_effect=client_main), \
                        patch('sys.stdout', output):
                    result = publication.main(['--python-crypto'])
                self.assertEqual(['--output', str(phone_home/'.necroprobe'/'runtime'/'test-069'),
                    '--python-crypto'], calls[0])
                self.assertEqual(2 if cancelled else 0, result)
                self.assertEqual(not cancelled, 'TEST-069: 終了。' in output.getvalue())
                self.assertEqual(not cancelled, 'このZIPを返してください:' in output.getvalue())
        # The wrapper checks cancellation again before its final completion
        # display, even if it arrives just as run() returns a verified ZIP.
        output = io.StringIO()
        record = seed(self.root/'late-display')
        def cancelled_return(*_args, **_kwargs):
            signal.raise_signal(signal.SIGTERM)
            return record, self.destination/'runtime'/'previously-verified.zip'
        with patch.object(publication, 'run', side_effect=cancelled_return), patch('sys.stdout', output):
            self.assertEqual(2, publication.main([]))
        self.assertNotIn('TEST-069: 終了。', output.getvalue())
        self.assertNotIn('このZIPを返してください:', output.getvalue())
        # Exercise the actual CLI/timer/client/outcome/publication boundary once
        # with authenticated HTTP; the server fixture does not perform a game.
        def terminal_images(method, result):
            if 'report' in result:
                result['report'].update(clock_id='c'*32,
                    terminal=int(result['state'] in native.TERMINAL),
                    workers_drained=True, native_inflight=False, ui_frozen=False)
            if method == 'necro_native_results': result['images'] = [image_item()]
            return result
        actual_main = native.main
        for handoff_cancel in (False, True):
            phone_home = self.root/('http-client-'+str(handoff_cancel))
            destination = self.root/('http-mounted-'+str(handoff_cancel)); destination.mkdir()
            output = io.StringIO()
            def client_handoff(options, **kwargs):
                if handoff_cancel: signal.raise_signal(signal.SIGTERM)
                return actual_main(options, **kwargs)
            with NativeServer(finish=True, transform=terminal_images) as server, \
                    patch.object(publication.Path, 'home', return_value=phone_home), \
                    patch.object(publication.Path, 'cwd', return_value=destination), \
                    patch.object(native, 'main', side_effect=client_handoff), \
                    patch.object(native, 'HttpTransport', return_value=HttpTransport(server.server.server_port)), \
                    patch.object(native, 'load_pairing', return_value=(KEY,TOK)), \
                    patch.object(native, 'Crypto', return_value=Crypto(native=False)), \
                    patch('sys.stdout', output):
                self.assertEqual(2 if handoff_cancel else 0, publication.main(['--python-crypto']))
                self.assertEqual(0 if handoff_cancel else 1,
                    sum(method == 'necro_native_start' for method, _params in server.calls))
            self.assertEqual(not handoff_cancel, 'TEST-069: 終了。' in output.getvalue())
            self.assertEqual(0 if handoff_cancel else 1, len(list(destination.rglob('*.zip'))))

    def test_provider_part_symlink_cannot_modify_an_unrelated_file(self):
        record = seed(self.spool)
        outside = self.root/'unrelated'; outside.write_bytes(b'private unchanged')
        folder = self.destination/'runtime'; folder.mkdir()
        part = folder/('test-069-'+record['run_id']+'.zip.part')
        part.symlink_to(outside)
        with self.assertRaisesRegex(ValueError, 'symlink'): self.invoke()
        self.assertEqual(b'private unchanged', outside.read_bytes())

    def test_mutation_between_certificate_and_inventory_is_not_certified_as_a_snapshot(self):
        record = seed(self.spool)
        image = self.spool/('native-'+record['run_id'])/'images'/'initial.png'
        inventory = publication._inventory
        def changed(*args, **kwargs):
            raw = bytearray(image.read_bytes()); raw[-1] ^= 1
            image.write_bytes(raw)
            return inventory(*args, **kwargs)
        with patch.object(publication, '_inventory', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'changed'): self.invoke()
        self.assertFalse(list(self.destination.rglob('*.zip')))
        # The certificate also binds the exact loaded journal, rather than
        # accepting a different active/report pair read after admission.
        base = self.spool/'journal-race'
        seed(base, 'b'*32)
        certificate = publication._certificate
        def changed_journal(folder, previous, cancelled):
            updated = dict(previous); updated['resolved'] = False
            native._save(folder, updated)
            return certificate(folder, previous, cancelled)
        with patch.object(publication, '_certificate', side_effect=changed_journal):
            with self.assertRaisesRegex(ValueError, 'changed'):
                publication.run(self.destination, spool=base,
                    session=Mock(side_effect=AssertionError('must not start')),
                    notice=self.messages.append)
        self.assertFalse(list(self.destination.rglob('*.zip')))

    def test_missing_drain_safety_fields_cannot_certify_publication(self):
        for field in ('workers_drained', 'native_inflight', 'ui_frozen'):
            with self.subTest(field=field):
                base = self.spool/field
                record = seed(base)
                del record['native_report'][field]
                native._save(base, record)
                with self.assertRaisesRegex(ValueError, 'native_incomplete'):
                    publication.run(self.destination/field, spool=base,
                        session=Mock(side_effect=AssertionError('must not start')),
                        notice=self.messages.append)

    def test_launcher_delegates_completion_to_the_verified_local_publication_wrapper(self):
        launcher = Path(__file__).resolve().parents[1]/'test_069.sh'
        self.assertEqual(0, subprocess.run(['sh', '-n', str(launcher)], capture_output=True).returncode)
        text = launcher.read_text()
        self.assertIn('python3 -m necroprobe.test069 "$@"', text)
        self.assertNotIn('--output runtime/', text)
        self.assertNotIn('終了。', text)


if __name__ == '__main__':
    unittest.main()
