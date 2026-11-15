"""TEST103 same known-ACK MOVE through transient Scene UNKNOWN.

Public C callbacks use procedural clocks/Scenes and later responses. They do
not replay missing device frames or claim physical arrival/recognition speed.
"""
import ctypes as C
from copy import deepcopy
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle


class Motion(C.Structure):
    _fields_ = [(name, C.c_int32) for name in ('kind', 'dx', 'dy')]


class NativeUnknownWait103Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cycle.NativeCycle094Tests.setUpClass()
        cls.lib = cycle.NativeCycle094Tests.lib
        cls.lib.ng2_motion.argtypes = [C.POINTER(native.Scene), C.POINTER(native.Scene),
                                      C.c_int32, C.POINTER(Motion)]

    @classmethod
    def tearDownClass(cls):
        cycle.NativeCycle094Tests.tearDownClass()

    def setUp(self):
        self.q = cycle.NativeCycle094Tests(methodName='runTest')
        self.q.setUp()
        self.addCleanup(self.q.doCleanups)
        self.h = self.q.h

    def armed(self, outcome=1):
        h = self.h
        terrain, command = h.continuous_walk(moves=1, direction=3)
        self.move_source = native.Scene.from_buffer_copy(bytes(h._last_fixture_scene))
        h.now = command.not_before_ns
        self.assertEqual(1, self.lib.ng2_controller_begin(h.engine, command.id, h.now, 1, 0, 1))
        appearing = deepcopy(terrain)
        appearing.goods = 'visible'
        h.now += 1
        self.assertEqual(0, h.observe(h.scene(2, 2, appearing, beat=True), stable=0),
                         'in-flight goods may latch but this capture has no completed-prefix authority')
        self.assertEqual((1, 0, 0), (self.q.cycle().pending,
            self.q.cycle().capture_id, self.q.cycle().worker_started_ns))
        h.now = command.not_before_ns + 50_000_000
        self.assertEqual(1, self.lib.ng2_controller_complete(h.engine, command.id, h.now, outcome))
        h.prefix = command.id
        event = next(e for e in h.events() if e.command.id == command.id)
        wait = h.motion_wait()
        if outcome == 1:
            self.assertEqual((3, command.id), (h.status().input_state, h.status().last_completed_id))
            self.assertEqual((2, 0, 1, command.id),
                (event.outcome, event.motion, wait.active, wait.command_id))
        else:
            self.assertEqual(4, h.status().input_state)
        return terrain, command, event, wait, h.status()

    def unknown(self, command, *, state=0, prefix=None, stable=1, at=None):
        h = self.h
        h.now = max(h.now + 2, command.target_ns + 80_000_000) if at is None else at
        frame = h.scene(state=state, gold=0)
        return h.observe(frame, prefix=prefix, stable=stable)

    def assert_same_wait(self, command, event, wait, status):
        h = self.h
        current, cycle_state, active = h.status(), self.q.cycle(), h.motion_wait()
        self.assertEqual((3, 0, 0), (current.input_state, current.terminal, cycle_state.status),
            'a fresh same-prefix UNKNOWN must preserve the known-ACK visual wait, not fail the cycle')
        self.assertEqual((1, 0, 0), (cycle_state.pending,
            cycle_state.capture_id, cycle_state.worker_started_ns))
        self.assertEqual((status.inputs, status.moves, status.last_completed_id),
            (current.inputs, current.moves, current.last_completed_id))
        preserved = next(e for e in h.events() if e.command.id == command.id)
        self.assertEqual(bytes(command), bytes(preserved.command), 'the old source/ticket is immutable')
        self.assertEqual((event.begin_ns, event.end_ns, event.outcome, event.motion, event.dx, event.dy),
            (preserved.begin_ns, preserved.end_ns, preserved.outcome,
             preserved.motion, preserved.dx, preserved.dy))
        self.assertEqual((wait.command_id, wait.source_capture_id, wait.deadline_ns, wait.attempts, 1),
            (active.command_id, active.source_capture_id, active.deadline_ns, active.attempts, active.active))
        self.assertEqual(0, current.next_target_ns, 'UNKNOWN revokes the previous next-slot authority')
        self.assertEqual(0, h.preparation_epoch(command))
        self.assertEqual(0, h.tick()[0], 'known ACK is never a resend/new input while visual proof is absent')

    def test_transient_unknown_preserves_ack_source_deadline_then_fresh_floor_resolves_same_move(self):
        terrain, command, event, wait, status = self.armed()
        records = self.h.recovery().record_count
        self.assertEqual(1, self.unknown(command))
        self.assertLess(self.h.now, wait.deadline_ns)
        self.assert_same_wait(command, event, wait, status)
        recovery = self.h.recovery()
        self.assertEqual(records + 1, recovery.record_count)
        trace = recovery.records[min(1, recovery.record_count - 1)]
        self.assertEqual((7, 1, command.id, self.h.number, self.h.now),
            (trace.reason, trace.clock, trace.command_id, trace.capture_id, trace.at_ns),
            'public VISUAL_PHASE trace revokes phase qualification independently of goods-latch slot cleanup')
        self.assertGreater(trace.model.period_ns, 0, 'the revoked phase is captured before resetting authority')
        after = native.translated(terrain, command.direction)
        after.goods = 'visible'
        self.h.now += 40_000_000
        self.assertLessEqual(self.h.now, wait.deadline_ns)
        self.assertEqual(1, self.h.observe(self.h.scene(2, 2, after, beat=True)))
        resolved = next(e for e in self.h.events() if e.command.id == command.id)
        self.assertEqual((1, 0, -1), (resolved.motion, resolved.dx, resolved.dy),
                         'the procedural later FLOOR must actually prove strict unit UP')
        self.assertEqual((status.inputs, status.moves + 1, 0),
            (self.h.status().inputs, self.h.status().moves, self.h.status().input_state))
        current = self.q.cycle()
        self.assertEqual((1, self.h.number, command.id),
            (current.pending, current.capture_id, current.prefix),
            'normal classification binds only the later qualified FLOOR source')
        ready, following = self.h.tick()
        self.assertFalse(ready and following.kind == 4,
                         'pending merchandise classification grants no new MOVE; its normal PAUSE may reserve')
        self.assertEqual(status.inputs, self.h.status().inputs)

    def test_repeated_unknown_uses_one_phase_failure_and_never_renews_visual_deadline_or_attempts(self):
        _, command, event, wait, status = self.armed()
        self.assertEqual(1, self.unknown(command))
        first = self.h.recovery().record_count
        for instant in (self.h.now + 40_000_000, wait.deadline_ns):
            with self.subTest(instant=instant):
                self.assertEqual(1, self.unknown(command, at=instant))
                self.assert_same_wait(command, event, wait, status)
                self.assertEqual(first, self.h.recovery().record_count,
                                 'the same unresolved MOVE records one phase failure, not a renewed episode')
        self.h.now = wait.deadline_ns + 1
        self.h.tick()
        self.assertNotEqual(3, self.h.status().input_state)
        self.assertNotEqual(0, self.q.cycle().status)
        self.assertEqual((status.inputs, status.moves), (self.h.status().inputs, self.h.status().moves))
        self.assertEqual(wait.deadline_ns, self.h.motion_wait().deadline_ns)
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, command.id, self.h.now, 1, 0, 1))

    def test_expired_unknown_pause_and_pre_ack_capture_keep_the_failure_path(self):
        for fault in ('expired', 'pause', 'pre_ack'):
            with self.subTest(fault=fault):
                self.setUp()
                terrain, command, event, wait, status = self.armed()
                if fault == 'expired':
                    self.assertEqual(1, self.unknown(command, at=wait.deadline_ns + 1))
                elif fault == 'pause':
                    self.assertEqual(1, self.unknown(command, state=1))
                else:
                    self.h.now = max(self.h.now + 2, command.target_ns + 80_000_000)
                    self.assertEqual(1, self.h.observe(self.h.scene(0, 0), start=event.end_ns - 1))
                self.assertEqual((0, 5, 17),
                    (self.h.status().input_state, self.q.cycle().status, self.h.status().reason),
                    'only an eligible current UNKNOWN may wait; PAUSE/expired/pre-ACK keep SCREEN failure')
                self.assertEqual(0, self.h.motion_wait().active)
                self.assertEqual((status.inputs, status.moves), (self.h.status().inputs, self.h.status().moves))
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, command.id, self.h.now, 1, 0, 1))
                later = native.translated(terrain, command.direction)
                later.goods = 'visible'
                self.h.now += 40_000_000
                self.h.observe(self.h.scene(2, 2, later, beat=True))
                ready, following = self.h.tick()
                self.assertFalse(ready and following.kind in (3, 4))
                self.assertEqual(status.moves, self.h.status().moves, 'late FLOOR cannot restore failed MOVE credit')

    def test_unstable_wrong_prefix_and_old_capture_do_not_mutate_the_ack_wait(self):
        for fault in ('unstable', 'prefix', 'old_capture'):
            with self.subTest(fault=fault):
                self.setUp()
                terrain, command, event, wait, status = self.armed()
                before = bytes(self.q.cycle()), self.h.recovery().record_count
                self.h.now = max(self.h.now + 2, command.target_ns + 80_000_000)
                options = ({'stable': 0} if fault == 'unstable' else
                           {'prefix': self.h.prefix + 1} if fault == 'prefix' else
                           {'number': command.source_capture_id})
                self.assertEqual(0, self.h.observe(self.h.scene(0, 0), **options))
                self.assertEqual(before, (bytes(self.q.cycle()), self.h.recovery().record_count))
                self.assert_same_wait(command, event, wait, status)
                later = native.translated(terrain, command.direction)
                later.goods = 'visible'
                self.h.now += 40_000_000
                self.assertEqual(1, self.h.observe(self.h.scene(2, 2, later, beat=True)))
                self.assertEqual(status.moves + 1, self.h.status().moves)
                self.assertEqual((1, self.h.number), (self.q.cycle().pending, self.q.cycle().capture_id))

    def test_cancel_foreground_lock_and_owner_guards_cannot_resume_after_unknown(self):
        for fault in ('cancel', 'foreground', 'locked', 'owner'):
            with self.subTest(fault=fault):
                self.setUp()
                terrain, command, _, _, status = self.armed()
                self.assertEqual(1, self.unknown(command))
                if fault == 'cancel':
                    self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 2)
                else:
                    self.h.tick(front=int(fault != 'foreground'), locked=int(fault == 'locked'),
                                owner=int(fault != 'owner'))
                self.assertEqual({'cancel': 2, 'foreground': 3, 'locked': 4, 'owner': 5}[fault],
                                 self.h.status().reason)
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, command.id, self.h.now, 1, 0, 1))
                later = native.translated(terrain, command.direction)
                later.goods = 'visible'
                self.h.now += 40_000_000
                self.h.observe(self.h.scene(2, 2, later, beat=True))
                ready, following = self.h.tick()
                self.assertFalse(ready and following.kind in (3, 4))
                self.assertEqual((status.inputs, status.moves), (self.h.status().inputs, self.h.status().moves))

    def test_unknown_synth_never_turns_an_unknown_screen_into_wait_or_new_input(self):
        terrain, command, _, _, status = self.armed(outcome=-1)
        self.assertEqual(0, self.unknown(command))
        self.assertEqual(4, self.h.status().input_state)
        self.assertEqual(0, self.q.cycle().capture_id)
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, command.id, self.h.now, 1, 0, 1))
        later = native.translated(terrain, command.direction)
        later.goods = 'visible'
        self.h.now += 40_000_000
        self.h.observe(self.h.scene(2, 2, later, beat=True))
        self.assertEqual(4, self.h.status().input_state)
        ready, following = self.h.tick()
        self.assertFalse(ready and following.kind in (3, 4))
        self.assertEqual((status.inputs, status.moves), (self.h.status().inputs, self.h.status().moves))
        self.assertEqual(0, self.q.cycle().capture_id)

    def test_later_full_floor_with_proven_unknown_motion_binds_fresh_candidate_without_old_credit(self):
        terrain, command, event, wait, status = self.armed()
        self.assertEqual(1, self.unknown(command))
        self.assert_same_wait(command, event, wait, status)
        later = deepcopy(terrain)
        later.goods = 'visible'
        later.signature = bytes([80]) * 23296
        self.h.now += 40_000_000
        self.assertLessEqual(self.h.now, wait.deadline_ns)
        frame = self.h.scene(2, 2, later, beat=True)
        motion = Motion()
        self.assertEqual(1, self.lib.ng2_motion(C.byref(self.move_source), C.byref(frame),
                                               command.direction, C.byref(motion)))
        self.assertEqual((0, 0, 0), (motion.kind, motion.dx, motion.dy),
                         'the procedural later FULL/FLOOR response must actually remain visual UNKNOWN')
        self.assertEqual(1, self.h.observe(frame))
        closed = next(e for e in self.h.events() if e.command.id == command.id)
        self.assertEqual((2, 0, 0, 0, self.h.number),
            (closed.outcome, closed.motion, closed.dx, closed.dy, closed.observed_capture_id))
        self.assertEqual((event.begin_ns, event.end_ns), (closed.begin_ns, closed.end_ns))
        self.assertEqual((status.inputs, status.moves, status.x, status.y, 0),
            (self.h.status().inputs, self.h.status().moves,
             self.h.status().x, self.h.status().y, self.h.status().input_state),
            'goods priority closes only known-ACK visual wait, with zero old displacement/input credit')
        current = self.q.cycle()
        self.assertEqual((1, self.h.number, command.id, 0, 1, 0),
            (current.pending, current.capture_id, current.prefix,
             current.partial, current.full_seen, current.worker_started_ns),
            'only the new qualified FULL/FLOOR raster becomes the normal worker source')
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, command.id, self.h.now, 1, 0, 1))
        self.q.assess(1, 1)
        self.assertEqual((1, 1, 1), (self.q.cycle().outcome,
            self.q.cycle().candidate_latched, self.q.cycle().completed_shops))
        ready, following = self.h.tick()
        self.assertFalse(ready and following.kind in (3, 4))
        self.assertEqual((status.inputs, status.moves), (self.h.status().inputs, self.h.status().moves))


if __name__ == '__main__':
    unittest.main()
