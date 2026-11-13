"""Separate a completed local assessment from unavailable product evidence.

The public display paths use synthetic metadata and a mocked pixel result.
No classifier/kernel, phone image or native game input is executed here.
"""
from copy import deepcopy
import hashlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from necroprobe import ring_early, target_assessment as target, test087


class RingStatus092Tests(unittest.TestCase):
    def displayed(self, value):
        original = deepcopy(value)
        output = io.StringIO()
        with patch.object(test087, 'prepare_assessment', return_value=value) as prepare:
            with patch('sys.stdout', output):
                actual = test087._prepare(Path('/unused'), {}, 'a'*64, lambda: False)
        self.assertIs(actual, value)
        self.assertEqual(original, value, 'display must not modify the assessment')
        prepare.assert_called_once()
        return output.getvalue()

    def test_completed_and_unavailable_assessment_have_distinct_execution_status(self):
        evaluated = dict(outcome='unknown', reason='no_target_evidence',
                         sources=[dict(row=[301, 117], reason='no_target_evidence')])
        missing = dict(outcome='unknown', reason='no_authority', sources=[])
        completed = self.displayed(evaluated)
        unavailable = self.displayed(missing)
        self.assertIn('実施済み', completed,
                      'a scored product image must be visibly different from an unassessed stop')
        self.assertNotIn('未実施', completed)
        self.assertIn('未実施', unavailable)
        self.assertNotIn('実施済み', unavailable)
        self.assertIn('商品画像', unavailable)
        self.assertNotEqual(completed, unavailable)

    def test_target_candidate_and_unknown_keep_their_existing_meaning(self):
        for outcome, expected in (
                ('target', 'のろいのゆびわ（アイコンと名前が一致）'),
                ('candidate', '指輪候補（保持して目視確認してください）'),
                ('unknown', 'のろいのゆびわとの一致は未確認（対象なしとは未確定）')):
            with self.subTest(outcome=outcome):
                text = self.displayed(dict(outcome=outcome, sources=[dict(outcome=outcome)]))
                self.assertIn('実施済み', text)
                self.assertIn(expected, text)
                self.assertNotIn('対象なし', text.replace(expected, '', 1))

    def test_unreadable_product_row_is_evaluated_but_never_confirmed_absent(self):
        text = self.displayed(dict(outcome='unknown', reason='no_target_evidence',
                                   sources=[dict(row=None, reason='no_complete_row')]))
        self.assertIn('実施済み', text)
        expected = 'のろいのゆびわとの一致は未確認（対象なしとは未確定）'
        self.assertIn(expected, text)
        self.assertNotIn('対象なし', text.replace(expected, '', 1))
        self.assertNotIn('未実施', text)

    def test_early_and_final_display_share_the_completed_label_without_extra_work(self):
        pixels = b'synthetic display fixture, not an encoded product image'
        digest = hashlib.sha256(pixels).hexdigest()
        source = dict(role='authority', capture_id=7, sha256=digest)
        item = dict(source, name='capture-000007.png', bytes=len(pixels))
        result = dict(outcome='unknown', reason='no_target_evidence', row=[100, 60],
                      slots=[], word=None)
        record = dict(run_id='a'*32, images=[item], image_export=dict(
            images=[item], offsets=[len(pixels)], prefix_sha256=[digest]))
        notices = []
        observer = ring_early.EarlyAssessment(notices.append)
        observer._began = 100.
        # Qualification/cache publication have their own existing integration
        # tests. Here only the already-qualified display boundary is isolated.
        with tempfile.TemporaryDirectory(prefix='ring-status092-') as directory:
            base = Path(directory)
            folder = base/('native-'+record['run_id'])/'images'
            folder.mkdir(parents=True)
            (folder/item['name']).write_bytes(pixels)
            with patch.object(observer, '_plan', return_value=[source]), \
                    patch.object(target, 'classify_png', return_value=result) as classify, \
                    patch.object(ring_early.time, 'monotonic', return_value=100.01):
                observer.saved(base, record, item, lambda: False)
            classify.assert_called_once()
            self.assertEqual(1, len(notices))
            self.assertIn('暫定', notices[0])
            self.assertIn('継続中', notices[0])
            self.assertIn('実施済み', notices[0])
            self.assertEqual([folder/item['name']], list(base.rglob('*.*')),
                             'display must not publish a sidecar or archive')
        final = self.displayed(dict(outcome='unknown', reason='no_target_evidence',
                                    sources=[dict(source, **result)]))
        label = '実施済み・のろいのゆびわとの一致は未確認（対象なしとは未確定）'
        self.assertIn(label, notices[0])
        self.assertIn(label, final)

    def test_engine_failure_never_reports_a_completed_or_absent_result(self):
        output = io.StringIO()
        with patch.object(test087, 'prepare_assessment', side_effect=target.AssessmentError('ring_native_failed')):
            with patch('sys.stdout', output), self.assertRaisesRegex(target.AssessmentError, 'ring_native_failed'):
                test087._prepare(Path('/unused'), {}, 'a'*64, lambda: False)
        self.assertIn('完了できませんでした', output.getvalue())
        self.assertIn('元データを保持', output.getvalue())
        self.assertNotIn('実施済み', output.getvalue())
        self.assertNotIn('対象なし', output.getvalue())


if __name__ == '__main__':
    unittest.main()
