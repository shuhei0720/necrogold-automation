"""Saved-run progress/cancellation, with procedural images and no device calls."""
from contextlib import ExitStack
import io
from pathlib import Path
import signal
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from necroprobe import native_walk as native
from necroprobe import target_assessment as target
from necroprobe import test069 as publication, test087, test088
from tests.test_recover087 import seed
from tests.test_target_assessment087 import png


class TargetProgress088Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = png(bytes((12, 8, 7, 255))*(896*414))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='target-progress088-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.user = self.root/'user'; self.user.mkdir()
        self.base = self.user/'.necroprobe/runtime/test-088'
        self.destination = self.root/'new-source'; self.destination.mkdir()
        self.record = seed(self.base, self.data)
        self.output = io.StringIO(); self.clock = [100.]

    def sources(self):
        return {p.relative_to(self.base).as_posix(): p.read_bytes()
                for p in self.base.rglob('*') if p.is_file()}

    def invoke(self, prepare):
        with ExitStack() as stack:
            stack.enter_context(patch.object(Path, 'home', return_value=self.user))
            stack.enter_context(patch.object(Path, 'cwd', return_value=self.destination))
            stack.enter_context(patch('sys.stdout', self.output))
            stack.enter_context(patch('time.monotonic', side_effect=lambda: self.clock[0]))
            stack.enter_context(patch.object(test087, 'prepare_assessment', side_effect=prepare))
            for name in ('main', 'run_session', 'Client', 'NativeClient', 'HttpTransport'):
                stack.enter_context(patch.object(native, name,
                    side_effect=AssertionError('saved progress must not call '+name)))
            return test088.main([])

    def test_saved_run_reports_before_work_and_keeps_progress_without_changing_the_snapshot(self):
        before = self.sources(); actual = test087.prepare_assessment
        certificate = publication._certificate
        def checked_certificate(*args):
            self.assertIn('照合', self.output.getvalue(),
                          'the saved-run stage must be visible before integrity work starts')
            return certificate(*args)
        def slow_prepare(base, record, digest, cancelled):
            self.assertIn('指輪判定中', self.output.getvalue(),
                          'a long local assessment must announce itself before work')
            for stamp in (103., 105.1, 109., 110.2):
                self.clock[0] = stamp
                self.assertFalse(cancelled())
            self.assertEqual(3, self.output.getvalue().count('指輪判定中'),
                             'long work must keep reporting while limiting console output')
            return actual(base, record, digest, cancelled)
        with patch.object(publication, '_certificate', side_effect=checked_certificate):
            self.assertEqual(0, self.invoke(slow_prepare))
        after = self.sources()
        self.assertEqual(before, {name: after[name] for name in before})
        self.assertEqual(self.record, native._load(self.base))
        archive = self.destination/'runtime'/('test-088-'+self.record['run_id']+'.zip')
        with zipfile.ZipFile(archive) as saved:
            self.assertIsNone(saved.testzip())
            for name, data in before.items(): self.assertEqual(data, saved.read('test-088/'+name))

    def test_progress_preserves_signal_cancellation_and_never_publishes_an_incomplete_result(self):
        before = self.sources()
        for sig in (signal.SIGINT, signal.SIGTERM):
            with self.subTest(signal=sig):
                self.output = io.StringIO(); previous = signal.getsignal(sig)
                def interrupted(_base, _record, _digest, cancelled):
                    self.assertIn('指輪判定中', self.output.getvalue())
                    self.clock[0] += 6
                    signal.getsignal(sig)(sig, None)
                    self.assertTrue(cancelled(), 'progress must not swallow the caller cancellation')
                    raise target.AssessmentError('target_cancelled')
                self.assertEqual(2, self.invoke(interrupted))
                self.assertIs(previous, signal.getsignal(sig))
                self.assertEqual(before, self.sources())
                self.assertFalse(list(self.destination.rglob('*.zip')))
                self.assertNotIn('保存・照合が完了', self.output.getvalue())


if __name__ == '__main__':
    unittest.main()
