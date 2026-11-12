"""Priority export and local early assessment; encrypted HTTP is a fixture.

No native game execution or iSH speed/unknown-positive accuracy is claimed.
"""
import base64
from contextlib import ExitStack, contextmanager
from copy import deepcopy
import hashlib
import inspect
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from necroprobe import native_walk as native, ring_native as ring
from necroprobe import target_assessment as target, test069 as publication, test089
from necroprobe.protocol import HttpTransport
from tests.test_recover087 import seed
from tests.test_target_assessment087 import png, shop
from test_native_walk import NativeServer
from test_protocol import KEY, TOK
from timer_support import TimerTestCase

RUNNER_PREFIX = []


class RingEarly089Tests(TimerTestCase):
    @classmethod
    def setUpClass(cls):
        cls.pixels = png(shop())

    def setUp(self):
        super().setUp()
        self.temp = tempfile.TemporaryDirectory(prefix='ring-early089-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.user = self.root/'user'; self.user.mkdir()
        prototype = seed(self.root/'prototype', self.pixels)
        self.report = prototype['native_report']
        authority = prototype['images'][0]
        diagnostic = dict(authority, capture_id=1, name='capture-000001.png',
            capture_start_ns=1, capture_end_ns=2, decode_end_ns=3,
            completed_prefix=0, completed_prefix_start=0, completed_prefix_end=0)
        proof = dict(authority, capture_id=6, name='capture-000006.png',
            capture_start_ns=81, capture_end_ns=99, decode_end_ns=99)
        self.metadata = [diagnostic, proof, authority]
        self.data_by_capture = {item['capture_id']: self.pixels for item in self.metadata}
        self.base = self.root/'spool'
        self.output = self.root/'destination'; self.output.mkdir()

    def transform(self, method, result):
        if result.get('state') in native.TERMINAL:
            report = deepcopy(self.report)
            report['clock_id'] = result['run_id']
            result['report'] = report
        if method == 'necro_native_results':
            result['images'] = [dict(item, data_base64=base64.b64encode(self.data_by_capture[item['capture_id']]).decode())
                                for item in self.metadata]
        return result

    def execute(self, server, observer=None, **options):
        # The old public client remains executable for a behavioral Red.
        # Its missing priority handling must fail the chunk-order assertion,
        # never a missing keyword/import/compile error.
        if 'image_observer' in inspect.signature(native.run_session).parameters:
            options['image_observer'] = observer
        return native.run_session(server.client(self.timer), self.base,
            lock_path=self.root/'lock', max_seconds=8, poll_seconds=.001, **options)

    @contextmanager
    def compiled(self):
        with ExitStack() as stack:
            stack.enter_context(patch.object(Path, 'home', return_value=self.user))
            if RUNNER_PREFIX:
                launch = ring._popen
                stack.enter_context(patch.object(ring, '_popen', side_effect=
                    lambda argv, **kwargs: launch(list(RUNNER_PREFIX)+argv, **kwargs)))
            yield

    def chunks(self, server):
        return [params['capture_id'] for _method, params in server.calls if params.get('mode') == 'chunk']

    def test_public_client_exports_authority_first_without_changing_manifest_or_cursors(self):
        saved = []
        owner = self
        class Observer:
            def priority(self, record, images):
                return [7]
            def saved(self, base, record, item, cancelled):
                owner.assertFalse(cancelled())
                owner.assertEqual(record, native._load(base))
                path = base/('native-'+record['run_id'])/'images'/item['name']
                owner.assertEqual(item['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())
                saved.append((item['capture_id'], len(record['images'])))
            def failed(self):
                owner.fail('priority observer must not fail')
        with NativeServer(finish=True, transform=self.transform) as server:
            record = self.execute(server, Observer())
            self.assertTrue(record['resolved'], record['stop_reason'])
            self.assertEqual([7, 1, 6], self.chunks(server),
                             'ACK PAUSE authority must be obtained before bulk diagnostic images')
            self.assertEqual([(7, 1), (1, 2), (6, 3)], saved)
        self.assertEqual(self.metadata, record['images'])
        self.assertEqual(self.metadata, record['image_export']['images'])
        self.assertEqual([len(self.pixels)]*3, record['image_export']['offsets'])
        self.assertEqual([item['sha256'] for item in self.metadata], record['image_export']['prefix_sha256'])
        self.assertEqual(record, native._load(self.base))


    def test_compiled_provisional_result_precedes_diagnostics_and_final_publication_reuses_cache(self):
        from necroprobe.ring_early import EarlyAssessment
        notices = []
        def notice(message):
            saved = native._load(self.base)
            self.assertEqual([7], [item['capture_id'] for item in saved['images']])
            self.assertFalse((self.base/('native-'+saved['run_id'])/target.SIDECAR).exists())
            self.assertFalse(list(self.output.rglob('*.zip')))
            notices.append((message, self.chunks(server)))
        observer = EarlyAssessment(notice)
        self.base = self.user/'.necroprobe/runtime/test-089'
        # The real CLI owns its own timer; end the test's earlier isolated one.
        self.close_timer()
        with self.compiled(), NativeServer(finish=True, transform=self.transform) as server, \
                patch.object(target, 'classify_png', wraps=target.classify_png) as classifier, \
                patch.object(test089, 'EarlyAssessment', return_value=observer), \
                patch.object(Path, 'cwd', return_value=self.output), \
                patch.object(native, 'load_pairing', return_value=(KEY, TOK)), \
                patch.object(native, 'HttpTransport', return_value=HttpTransport(server.server.server_port)), \
                patch('sys.stdout', new_callable=io.StringIO) as output:
            code = test089.main(['--python-crypto'])
            self.assertEqual(0, code, output.getvalue())
            self.assertIn('保存・照合が完了', output.getvalue())
            record = native._load(self.base)
            archive = self.output/'runtime'/('test-089-'+record['run_id']+'.zip')
            self.assertEqual(1, classifier.call_count, 'final certificate must reuse the same validated pixels')
            self.assertEqual([7, 1, 6], self.chunks(server))
        self.assertEqual(1, len(notices)); self.assertEqual([7], notices[0][1])
        self.assertIn('暫定', notices[0][0]); self.assertIn('継続中', notices[0][0])
        self.assertIn('のろいのゆびわ', notices[0][0])
        self.assertTrue(archive.is_file())
        folder = self.base/('native-'+record['run_id'])
        sidecar = json.loads((folder/target.SIDECAR).read_bytes())
        self.assertEqual('target', sidecar['outcome']); self.assertEqual(1, len(sidecar['sources']))
        target.validate_assessment(sidecar, record=record,
            report_sha=hashlib.sha256((self.base/'active.json').read_bytes()).hexdigest())
        # A changed terminal selection must fail even when it selects no image,
        # so the normal classifier callback would otherwise never be invoked.
        for changed in ('run', 'export', 'eligibility', 'source'):
            mutated = deepcopy(record)
            if changed == 'run': mutated['run_id'] = 'f'*32
            elif changed == 'export': mutated['image_export']['export_id'] = 'f'*32
            elif changed == 'eligibility': mutated['native_report']['goods'] = 0
            else: mutated['images'][-1]['sha256'] = 'f'*64
            with self.subTest(changed=changed), self.assertRaisesRegex(target.AssessmentError, 'ring_early_changed'):
                observer.before_prepare(mutated)
        with self.assertRaisesRegex(target.AssessmentError, 'ring_early_changed'):
            observer.classify(record, target._selected(record)[0], self.pixels+b'changed', lambda: False)

    def test_nonconclusive_authority_prioritizes_proof_and_keeps_same_slot_target_semantics(self):
        from necroprobe.ring_early import EarlyAssessment
        candidate = png(shop(name=False))
        self.data_by_capture[7] = candidate
        self.metadata[-1].update(bytes=len(candidate), sha256=hashlib.sha256(candidate).hexdigest())
        notices = []
        observer = EarlyAssessment(notices.append)
        with self.compiled(), NativeServer(finish=True, transform=self.transform) as server, \
                patch.object(target, 'classify_png', wraps=target.classify_png) as classifier:
            record = self.execute(server, observer)
            self.assertTrue(record['resolved'], record['stop_reason'])
            self.assertEqual([7, 6, 1], self.chunks(server), 'proof is next only after authority is inconclusive')
            observer.before_prepare(record)
            report_sha = publication._certificate(self.base, record, lambda: False)
            value = target.prepare_assessment(self.base, record, report_sha, classify=observer.classify)
            self.assertEqual(2, classifier.call_count)
        self.assertEqual('target', value['outcome'])
        self.assertEqual(['candidate', 'target'], [source['outcome'] for source in value['sources']])
        self.assertEqual(2, len(notices)); self.assertIn('指輪候補', notices[0]); self.assertIn('のろいのゆびわ', notices[1])

    def test_interrupted_export_resumes_same_uuid_and_observes_completed_authority_without_redownload(self):
        from necroprobe.ring_early import EarlyAssessment
        first_observer = EarlyAssessment(lambda _message: None)
        recovered_notices = []
        def recovered_notice(message):
            recovered_notices.append((message, list(self.chunks(server))))
        next_observer = EarlyAssessment(recovered_notice)
        with self.compiled(), NativeServer(finish=True, transform=self.transform) as server:
            lost = [False]
            def interrupt(method, params, result):
                if params.get('mode') == 'chunk' and params['capture_id'] == 1 and not lost[0]:
                    lost[0] = True
                    server.lose.append(method)
                return result
            server.page_transform = interrupt
            first = self.execute(server, first_observer)
            self.assertFalse(first['resolved']); self.assertEqual([7], [item['capture_id'] for item in first['images']])
            authority = self.base/('native-'+first['run_id'])/'images'/'capture-000007.png'
            before = (authority.read_bytes(), authority.stat().st_mtime_ns)
            prior_calls = len(server.calls); server.calls.clear(); server.page_transform = None
            recovered = self.execute(server, next_observer)
            self.assertTrue(recovered['resolved'], recovered['stop_reason'])
            self.assertEqual(first['run_id'], recovered['run_id'])
            self.assertEqual([1, 6], self.chunks(server))
            self.assertFalse(any(method in ('necro_native_start', 'necro_native_cancel') for method, _params in server.calls))
            self.assertEqual('necro_native_status', server.calls[0][0]); self.assertFalse(server.calls[0][1]['keepalive'])
            self.assertGreater(prior_calls, 0)
        self.assertEqual(1, len(recovered_notices)); self.assertEqual([], recovered_notices[0][1])
        self.assertEqual(before, (authority.read_bytes(), authority.stat().st_mtime_ns))
        self.assertEqual(self.metadata, recovered['images'])

    def test_early_failures_finish_diagnostic_collection_then_keep_publication_pending(self):
        from necroprobe.ring_early import EarlyAssessment
        for fault in ('engine', 'observer'):
            with self.subTest(fault=fault), ExitStack() as stack:
                self.base = self.root/fault
                observer = EarlyAssessment(lambda _message: self.fail('failed engine cannot report a decision'))
                if fault == 'engine':
                    classifier = stack.enter_context(patch.object(target, 'classify_png',
                        side_effect=target.AssessmentError('ring_native_timeout')))
                    expected = 'ring_native_timeout'
                else:
                    stack.enter_context(patch.object(observer, 'saved', side_effect=OSError('private detail')))
                    expected = 'ring_early_failed'
                with NativeServer(finish=True, transform=self.transform) as server:
                    record = self.execute(server, observer)
                    self.assertTrue(record['resolved'], record['stop_reason'])
                    self.assertEqual([7, 1, 6], self.chunks(server))
                    self.assertFalse(any(method == 'necro_native_cancel' for method, _params in server.calls))
                self.assertEqual(self.metadata, record['images'])
                publication._certificate(self.base, record, lambda: False)
                if fault == 'engine': self.assertEqual(1, classifier.call_count, 'do not spend another timeout on final prepare')
                with self.assertRaisesRegex(target.AssessmentError, expected): observer.before_prepare(record)
                empty = deepcopy(record); empty['native_report']['goods'] = 0
                with self.assertRaisesRegex(target.AssessmentError, expected): observer.before_prepare(empty)
                self.assertFalse(list(self.base.rglob(target.SIDECAR)))
                self.assertFalse(list(self.output.rglob('*.zip')))

    def test_true_cancel_after_a_durable_early_image_preserves_cursor_and_sends_no_native_cancel(self):
        stopped = [False]
        class Observer:
            def priority(self, record, images): return [7]
            def saved(self, base, record, item, cancelled): stopped[0] = True
            def failed(self): raise AssertionError('cancellation is handled by collector check')
        with NativeServer(finish=True, transform=self.transform) as server:
            record = self.execute(server, Observer(), cancelled=lambda: stopped[0])
            self.assertFalse(record['resolved']); self.assertEqual('cancel_requested', record['stop_reason'])
            self.assertEqual([7], self.chunks(server))
            self.assertFalse(any(method == 'necro_native_cancel' for method, _params in server.calls))
        self.assertEqual([0, 0, len(self.pixels)], record['image_export']['offsets'])
        self.assertEqual([7], [item['capture_id'] for item in record['images']])
        self.assertEqual(record, native._load(self.base))


if __name__ == '__main__':
    unittest.main()
