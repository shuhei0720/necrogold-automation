"""TEST041: 開幕候補を保持して歩行へ渡す。RPCは模擬、実機成功ではない。"""
from copy import deepcopy
import inspect
import unittest

from necroprobe import restart_loop as loop
from necroprobe.validation import ProbeError
import test_restart_loop as old


def collect(driver, callback):
    # Before the new optional argument exists, exercise the old public entry
    # rather than counting a missing-keyword TypeError as a behavioral Red.
    if 'candidate_handoff' in inspect.signature(loop.collect).parameters:
        return loop.collect(driver, candidate_handoff=callback)
    return loop.collect(driver)


class Driver(old.Driver):
    def __init__(self, frames, **kwargs):
        super().__init__(frames, **kwargs)
        self.last = None
        self.pending = False
        self.checkpoints = []

    def observe(self):
        self.last = super().observe()
        return self.last

    def checkpoint(self):
        self.checkpoints.append(deepcopy(self.report))


class CandidateHandoffTests(unittest.TestCase):
    def test_fresh_candidate_returns_without_pause_after_latching(self):
        driver = Driver([old.G, old.P])
        received = []

        def accept(frame):
            self.assertIs(driver.last, frame)
            self.assertEqual('floor', frame['state'])
            self.assertTrue(driver.report['candidate'])
            self.assertEqual('gold_candidate', driver.report['reason'])
            self.assertIn('found.jpg', driver.saved)
            self.assertTrue(driver.checkpoints[-1]['candidate'])
            received.append(frame)
            return True

        result = collect(driver, accept)
        self.assertEqual([], driver.actions)
        self.assertIs(result, driver.report)
        self.assertEqual(1, len(received))
        self.assertFalse(result['paused'])
        self.assertEqual(0, result['restarts_confirmed'])
        self.assertEqual(['candidate'], result['runs'])


    def test_all_three_floor_candidate_exits_keep_existing_run_accounting(self):
        for frames, actions, restarts, runs in (
                ([old.G, old.P], [], 0, ['candidate']),
                ([old.P, old.G, old.P], ['resume'], 0, ['candidate']),
                ([old.A, old.G, old.P], [], 0, ['clear']),
                ([old.A, old.A, old.P, old.G, old.P],
                 ['pause', 'restart'], 1, ['clear', 'candidate'])):
            with self.subTest(actions=actions, runs=runs):
                driver = Driver(frames)
                accepted = []
                def callback(frame):
                    self.assertIs(driver.last, frame)
                    self.assertEqual('floor', frame['state'])
                    self.assertEqual('candidate', frame['gold'])
                    self.assertTrue(driver.report['candidate'])
                    self.assertIn('found.jpg', driver.saved)
                    accepted.append(frame)
                    return True
                collect(driver, callback)
                self.assertEqual(actions, driver.actions)
                self.assertEqual(restarts, driver.report['restarts_confirmed'])
                self.assertEqual(runs, driver.report['runs'])
                self.assertEqual(1, len(accepted))
                self.assertFalse(driver.report['paused'])
                self.assertEqual('gold_candidate', driver.report['reason'])

    def test_post_restart_candidate_without_new_run_proof_is_not_counted_twice(self):
        candidate = deepcopy(old.G)
        candidate['fingerprint'] = deepcopy(old.A['fingerprint'])
        driver = Driver([old.A, old.A, old.P, candidate, old.P])
        received = []
        collect(driver, lambda frame: received.append(frame) or True)
        self.assertEqual(['pause', 'restart'], driver.actions)
        self.assertEqual(0, driver.report['restarts_confirmed'])
        self.assertEqual(['clear'], driver.report['runs'])
        self.assertEqual(1, len(received))
        self.assertTrue(driver.report['candidate'])
        self.assertFalse(driver.report['paused'])

    def test_only_strict_true_accepts_and_rejection_keeps_candidate_paused(self):
        for result in (False, None, 0, 1, 'yes', [], object()):
            with self.subTest(result=type(result).__name__):
                driver = Driver([old.G, old.P])
                calls = []
                def reject(frame):
                    calls.append(frame)
                    self.assertTrue(driver.report['candidate'])
                    return result
                collect(driver, reject)
                self.assertEqual(1, len(calls))
                self.assertEqual(['pause'], driver.actions)
                self.assertTrue(driver.report['candidate'])
                self.assertTrue(driver.report['paused'])
                self.assertEqual('gold_candidate', driver.report['reason'])
                self.assertEqual(0, driver.report['restarts_confirmed'])

    def test_default_none_preserves_legacy_pause_actions_and_checkpoints(self):
        frames = [old.P, old.A, old.A, old.P, old.G, old.P]
        direct = Driver(frames)
        explicit_none = Driver(frames)
        loop.collect(direct)
        collect(explicit_none, None)
        self.assertEqual(['resume', 'pause', 'restart', 'pause'], direct.actions)
        self.assertEqual(direct.actions, explicit_none.actions)
        self.assertEqual(direct.report, explicit_none.report)
        self.assertEqual(direct.saved, explicit_none.saved)
        self.assertEqual(direct.checkpoints, explicit_none.checkpoints)
        self.assertTrue(direct.report['paused'])

    def test_candidate_seen_after_pause_was_sent_never_invokes_handoff(self):
        driver = Driver([old.A, old.A, old.G, old.P])
        calls = []
        collect(driver, lambda frame: calls.append(frame) or True)
        self.assertEqual([], calls)
        self.assertEqual(['pause'], driver.actions)
        self.assertTrue(driver.report['candidate'])
        self.assertTrue(driver.report['paused'])
        self.assertIn('found.jpg', driver.saved)

    def test_unknown_resume_or_restart_input_never_reaches_handoff(self):
        for frames, fail, expected in (
                ([old.P, old.G], 1, ['resume']),
                ([old.A, old.A, old.P, old.G], 2, ['pause', 'restart'])):
            driver = Driver(frames, fail=fail)
            calls = []
            with self.subTest(expected=expected), self.assertRaises(ProbeError) as caught:
                collect(driver, lambda frame: calls.append(frame) or True)
            self.assertEqual('batch_unknown', caught.exception.code)
            self.assertEqual(expected, driver.actions)
            self.assertEqual([], calls)
            self.assertFalse(driver.report['candidate'])

    def test_callback_exception_propagates_after_latch_without_pause_or_restart(self):
        for exception in (ProbeError('cancelled'), RuntimeError('injected callback failure')):
            driver = Driver([old.G, old.P])
            def fail(_frame):
                raise exception
            with self.subTest(kind=type(exception).__name__), self.assertRaises(type(exception)):
                collect(driver, fail)
            self.assertTrue(driver.report['candidate'])
            self.assertEqual('gold_candidate', driver.report['reason'])
            self.assertIn('found.jpg', driver.saved)
            self.assertEqual([], driver.actions)
            self.assertFalse(driver.report['paused'])
            self.assertEqual(1, driver.reads)

    def test_latch_write_failure_does_not_call_handoff_or_send_input(self):
        driver = Driver([old.G, old.P])
        calls = []
        def fail_checkpoint():
            raise OSError('injected candidate checkpoint failure')
        driver.checkpoint = fail_checkpoint
        with self.assertRaises(OSError):
            collect(driver, lambda frame: calls.append(frame) or True)
        self.assertTrue(driver.report['candidate'])
        self.assertEqual([], calls)
        self.assertEqual([], driver.actions)

    def test_noncallable_callback_is_rejected_before_observation(self):
        for callback in (False, True, 0, 1, 'handoff', object()):
            driver = Driver([])
            with self.subTest(kind=type(callback).__name__), self.assertRaises(ProbeError) as caught:
                collect(driver, callback)
            self.assertEqual('method_not_allowed', caught.exception.code)
            self.assertEqual(0, driver.reads)
            self.assertEqual([], driver.actions)
            self.assertFalse(driver.report['candidate'])


if __name__ == '__main__':
    unittest.main()
