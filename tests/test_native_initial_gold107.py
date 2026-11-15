"""TEST107 initial GOLD reacquisition after a non-stationary fade source.

Procedural native scenes exercise the first-step authority boundary. The
recorded phone pair 40/107 remains UNKNOWN; these textures do not stand in for
that pair, and no actual game response is fabricated.
"""
import ctypes as C
from copy import deepcopy
import unittest

from tests import test_native_controller as native
from tests import test_native_passage072 as passage
from tests import test_native_view074 as view
from tests.test_native_stop099 import stop_detail
from tests.test_native_motion067 import Motion


class NativeInitialGold107Tests(unittest.TestCase):
    setUpClass = classmethod(view.NativeView074Tests.setUpClass.__func__)
    tearDownClass = classmethod(view.NativeView074Tests.tearDownClass.__func__)
    setUp = view.NativeView074Tests.setUp
    status = view.NativeView074Tests.status
    events = view.NativeView074Tests.events
    tick = view.NativeView074Tests.tick
    ack = view.NativeView074Tests.ack
    fresh_engine = view.NativeView074Tests.fresh_engine
    scene = view.NativeView074Tests.scene
    observe = view.NativeView074Tests.observe
    fit_clear = view.NativeView074Tests.fit_clear
    next_operation = view.NativeView074Tests.next_operation
    next_move = view.NativeView074Tests.next_move
    moved = view.NativeView074Tests.moved
    recovery = view.NativeView074Tests.recovery
    recovery_samples = view.NativeView074Tests.recovery_samples
    all_public_bytes = view.NativeView074Tests.all_public_bytes
    reject_old_callbacks_without_mutation = view.NativeView074Tests.reject_old_callbacks_without_mutation
    new_uptime = view.NativeView074Tests.new_uptime

    def detail(self):
        return stop_detail(self.lib, self.engine)

    def later(self, terrain, amount=20_000_000, **kwargs):
        self.now += amount
        return self.observe(terrain, **kwargs)

    def bound_wait(self, terrain):
        # StopDetail exposes the long horizon until the first model fixes D.
        # The finite two-beat deadline, rather than that fallback, is required.
        for _ in range(60):
            remaining = self.detail().deadline_ns-self.now
            if self.status().beat_period_ns and 0 < remaining <= 2*self.status().beat_period_ns:
                return self.detail()
            self.later(terrain, amount=40_000_000)
        self.fail('the normal beat model must fix the original two-beat wait deadline')

    def fade_wait(self, faded=True):
        empty = self.fit_clear(passage.passage_room(mouth=None))
        old = self.next_operation(empty)
        self.assertEqual(2, old.kind)
        bright = native.textured()
        fade = deepcopy(bright)
        if faded:
            fade.signature = bytes([40])*23296
        self.later(fade)
        if faded:
            self.bound_wait(fade)
        first = self.detail()
        self.assertEqual((3, 0, 0, 0), (first.wait_kind, self.status().inputs,
            self.status().moves, self.status().lead_confirmed))
        self.assertGreater(first.deadline_ns, self.now)
        self.assertEqual((3, 0), (self.events()[-1].outcome, self.events()[-1].begin_ns))
        return bright, old, first

    def fresh_pair(self, bright):
        self.later(bright)
        first_id = self.number
        self.assertEqual(0, self.tick()[0], 'the first new data frame grants no step')
        self.later(bright)
        return first_id, self.number

    def test_fade_anchor_retires_before_latest_independent_pair_gets_a_new_ticket(self):
        bright, old, original = self.fade_wait()
        epoch = self.status().walk_started_ns
        self.later(bright)
        first = self.detail()
        self.assertEqual(self.number, first.anchor_capture_id,
            'a new data anchor must replace the unusable fade, without claiming old zero motion')
        self.assertEqual(original.deadline_ns, first.deadline_ns)
        self.assertEqual(0, self.tick()[0])
        self.reject_old_callbacks_without_mutation(old)
        self.later(bright)
        self.assertEqual(0, self.detail().wait_kind,
            'only the independent latest pair may retire the GOLD wait')
        command = self.next_move(bright)
        self.assertGreater(command.id, old.id)
        self.assertGreater(command.source_capture_id, original.anchor_capture_id)
        self.assertEqual((0, 0, 0, epoch), (self.status().inputs, self.status().moves,
            self.status().restarts, self.status().walk_started_ns))
        self.reject_old_callbacks_without_mutation(old)
        shifted = self.moved(bright, command)
        self.assertEqual((1, 1, 1), (self.status().inputs, self.status().moves,
            self.status().lead_confirmed))
        self.assertTrue(shifted.gold)

    def test_data_anchor_changes_keep_original_wait_deadline_and_do_not_skip_a_pair(self):
        bright, old, original = self.fade_wait()
        for value in (61, 83, 106):
            changed = deepcopy(bright)
            changed.signature = bytes([value])*23296
            self.later(changed)
            self.assertEqual(original.deadline_ns, self.detail().deadline_ns)
            self.assertEqual(0, self.tick()[0])
            self.assertEqual((0, 0), (self.status().inputs, self.status().moves))
        self.fresh_pair(bright)
        self.assertEqual(0, self.detail().wait_kind)
        self.assertEqual(4, self.next_move(bright).kind)
        self.reject_old_callbacks_without_mutation(old)

    def test_post_restart_first_fade_gold_uses_only_latest_pair_for_its_first_move(self):
        empty, _, _ = view.NativeView074Tests.resumed(self)
        view.NativeView074Tests.after_first_floor(self, empty)
        self.fit_clear(empty)
        pause = self.next_operation(empty)
        self.assertEqual(2, pause.kind)
        self.ack(pause)
        self.later(self.scene(empty, state=1))
        self.now += 200_000_000
        restart = self.next_operation(empty)
        self.assertEqual(3, restart.kind)
        self.ack(restart)
        # A completed RESTART is followed by a new floor before GOLD becomes
        # readable. No skip PAUSE has been issued for this new level.
        self.later(self.scene(empty, fingerprint=bytes([160])*48))
        self.assertEqual((1, 0), (self.status().restarts, self.status().input_state))
        bright = native.textured()
        fade = deepcopy(bright)
        fade.signature = bytes([40])*23296
        self.later(self.scene(fade, fingerprint=bytes([160])*48))
        self.assertEqual((1, 0, 0), (self.status().restarts, self.status().inputs,
            self.status().moves))
        self.assertEqual(3, self.detail().wait_kind)
        original = self.bound_wait(fade)
        self.assertGreater(self.status().beat_period_ns, 0)
        self.assertGreater(original.deadline_ns, self.now)
        self.later(bright)
        self.assertEqual(original.deadline_ns, self.detail().deadline_ns)
        self.assertEqual(0, self.tick()[0])
        self.later(bright)
        self.assertEqual(0, self.detail().wait_kind,
            'the initial post-RESTART fade cannot remain the fixed motion anchor')
        command = self.next_move(bright)
        self.assertGreater(command.id, restart.id)
        self.assertEqual(restart.id, self.prefix)
        self.assertGreater(command.source_capture_id, original.anchor_capture_id)
        self.assertEqual((0, 0, 1), (self.status().inputs, self.status().moves,
            self.status().restarts))

    def test_nonindependent_stale_and_foreign_prefix_frames_never_supply_the_second_proof(self):
        for fault in ('prefix', 'unstable', 'overlap', 'old_id', 'stale'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                bright, _, original = self.fade_wait()
                self.later(bright)
                first_id = self.number
                first_end = self.now
                self.now += 20_000_000
                kwargs = ({'prefix': self.prefix+1} if fault == 'prefix' else
                    {'stable': 0} if fault == 'unstable' else
                    {'start': first_end-1} if fault == 'overlap' else
                    {'number': first_id} if fault == 'old_id' else
                    {'start': self.now-3*native.SECOND-1})
                self.observe(bright, **kwargs)
                self.assertEqual(3, self.detail().wait_kind)
                self.assertEqual(0, self.tick()[0])
                self.assertEqual((0, 0), (self.status().inputs, self.status().moves))
                self.assertEqual(original.deadline_ns, self.detail().deadline_ns)

    def test_goods_protection_cancellation_and_moved_evidence_never_recover_an_initial_ticket(self):
        for fault in ('partial', 'visible', 'protected', 'cancel', 'moved'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                bright, _, original = self.fade_wait()
                changed = deepcopy(bright)
                if fault == 'partial': changed.goods = 'partial'
                elif fault == 'visible': changed.goods = 'visible'
                elif fault == 'protected': changed.protected.add((8, 3))
                elif fault == 'cancel':
                    self.lib.ng2_controller_cancel(self.engine, self.now, 2)
                else:
                    self.later(bright)
                    changed = native.translated(bright, 3)
                self.later(changed)
                self.later(changed)
                self.assertEqual((0, 0), (self.status().inputs, self.status().moves))
                self.assertNotEqual(4, self.tick()[1].kind)
                self.now = original.deadline_ns+1
                self.observe(changed)
                self.assertNotEqual(4, self.tick()[1].kind)

    def test_moved_before_a_reanchor_episode_cannot_be_forgotten_by_unknown_views(self):
        bright, _, _ = self.fade_wait(faded=False)
        moved = native.translated(bright, 3)
        self.later(moved)
        self.assertEqual(1, self.detail().motion_kind,
            'known MOVED is established before any data-reanchor episode')
        original = self.bound_wait(moved)
        unknown = deepcopy(moved)
        unknown.signature = bytes([61])*23296
        a, b = self.scene(bright, beat=False), self.scene(unknown, beat=False)
        motion = Motion()
        self.lib.ng2_motion.argtypes = [C.POINTER(native.Scene), C.POINTER(native.Scene),
            C.c_int32, C.POINTER(Motion)]
        self.assertEqual(1, self.lib.ng2_motion(C.byref(a), C.byref(b), 3, C.byref(motion)))
        self.assertEqual((0, 0, 0), (motion.kind, motion.dx, motion.dy),
            'the later UNKNOWN would otherwise qualify for data reacquisition')
        self.later(unknown)
        self.assertEqual(original.anchor_capture_id, self.detail().anchor_capture_id,
            'a later UNKNOWN cannot erase a previously observed real displacement')
        self.assertEqual(original.deadline_ns, self.detail().deadline_ns)
        self.later(moved)
        self.later(moved)
        self.assertEqual((3, 0, 0), (self.detail().wait_kind, self.status().inputs,
            self.status().moves))
        self.assertNotEqual(4, self.tick()[1].kind)

    def test_original_wait_and_sync_limits_are_not_renewed_by_fade_observations(self):
        for which in ('wait', 'sync', 'walk', 'session'):
            with self.subTest(which=which):
                self.fresh_engine()
                bright, _, original = self.fade_wait()
                epoch = self.status().walk_started_ns
                self.later(bright)
                self.now = (original.deadline_ns if which == 'wait' else
                    epoch+12*native.SECOND if which == 'sync' else
                    epoch+45*native.SECOND if which == 'walk' else
                    self.status().started_ns+180*native.SECOND)
                self.observe(bright)
                self.assertEqual((0, 0, epoch), (self.status().inputs, self.status().moves,
                    self.status().walk_started_ns))
                self.assertNotEqual(4, self.tick()[1].kind)
                self.assertNotEqual(0, self.status().reason)


if __name__ == '__main__':
    unittest.main()
