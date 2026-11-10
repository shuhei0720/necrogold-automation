"""TEST073: bounded post-RESUME/RESTART permission for a PAUSE.

These procedural frames and device clocks verify controller transitions only.
The 200ms proposal is not a measured guarantee of the iPhone game's UI intake.
"""
import ctypes as C
from copy import deepcopy
import unittest

from tests import test_native_controller as fixture
from tests import test_native_recovery as mechanics
from tests import test_native_passage072 as passage

CORE = mechanics.CORE
SECOND = fixture.SECOND
PERIOD = fixture.PERIOD
SETTLE = 200_000_000


class NativeUI073Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = mechanics.CORE
        try:
            mechanics.CORE = CORE
            mechanics.NativeRecoveryTests.setUpClass.__func__(cls)
        finally:
            mechanics.CORE = previous

    tearDownClass = classmethod(mechanics.NativeRecoveryTests.tearDownClass.__func__)
    setUp = fixture.NativeControllerTests.setUp
    status = fixture.NativeControllerTests.status
    events = fixture.NativeControllerTests.events
    tick = fixture.NativeControllerTests.tick
    ack = fixture.NativeControllerTests.ack
    motion_wait = fixture.NativeControllerTests.motion_wait
    recovery = mechanics.NativeRecoveryTests.recovery
    recovery_samples = mechanics.NativeRecoveryTests.recovery_samples
    all_public_bytes = mechanics.NativeRecoveryTests.all_public_bytes
    reject_old_callbacks_without_mutation = mechanics.NativeRecoveryTests.reject_old_callbacks_without_mutation
    scene = passage.NativePassage072Tests.scene
    observe = passage.NativePassage072Tests.observe
    fit_clear = passage.NativePassage072Tests.fit_clear
    next_operation = passage.NativePassage072Tests.next_operation
    next_move = passage.NativePassage072Tests.next_move
    moved = passage.NativePassage072Tests.moved

    def new_uptime(self, uptime=32746*SECOND):
        self.engine = self.lib.ng2_controller_create(uptime)
        self.assertTrue(self.engine)
        self.addCleanup(self.lib.ng2_controller_destroy, self.engine)
        self.now = uptime+100_000_000
        self.number = self.prefix = 0

    def resumed(self, offset=71_289_375):
        self.new_uptime()
        terrain = passage.passage_room(mouth=None)
        self.observe(self.scene(terrain, state=1, gold=0))
        ready, resume = self.tick()
        self.assertEqual((1, 1), (ready, resume.kind))
        self.ack(resume)
        ack_ns = self.now
        self.now = ack_ns+offset
        self.observe(terrain)
        self.assertEqual((0, 0, 0),
            (self.status().inputs, self.status().moves, self.status().restarts))
        return terrain, resume, ack_ns

    def fresh_post_ui_floor(self, terrain, ack_ns, delta=0):
        self.now = max(self.now+2, ack_ns+SETTLE+delta+2)
        self.observe(terrain, start=ack_ns+SETTLE+delta, end=self.now)

    def test_resume_ack_is_not_immediate_permission_for_a_skip_pause(self):
        for offset in (71_289_375, 90_355_417, SETTLE-1):
            with self.subTest(offset=offset):
                terrain, resume, ack_ns = self.resumed(offset)
                ready, pause = self.tick()
                self.assertEqual((0, 0), (ready, pause.kind),
                    'a RESUME acknowledgement and early FLOOR must not immediately authorize PAUSE')
                self.assertEqual([1], [e.command.kind for e in self.events()])
                self.fresh_post_ui_floor(terrain, ack_ns)
                ready, pause = self.tick()
                self.assertEqual((1, 2), (ready, pause.kind))
                self.assertGreaterEqual(pause.source_start_ns-ack_ns, SETTLE)
                self.ack(pause)
                self.reject_old_callbacks_without_mutation(resume)

    def test_new_passage_during_ui_wait_revokes_skip_before_any_restart(self):
        for phase in ('waiting', 'pause_reserved', 'pause_ack'):
            with self.subTest(phase=phase):
                empty, _, ack_ns = self.resumed()
                old_pause = None
                if phase != 'waiting':
                    self.fresh_post_ui_floor(empty, ack_ns)
                    ready, old_pause = self.tick()
                    self.assertEqual((1, 2), (ready, old_pause.kind))
                    if phase == 'pause_ack':
                        self.ack(old_pause)
                terrain = passage.passage_room()
                self.now += 2
                self.observe(terrain)
                if phase == 'pause_ack':
                    self.assertEqual(12, self.status().reason,
                        'a passage exposed after PAUSE was sent must be held, never discarded by restart')
                    self.assertNotIn(self.tick()[1].kind, (3, 4))
                    continue
                self.assertEqual((0, 0, self.now),
                    (self.status().reason, self.status().input_state, self.status().walk_started_ns),
                    'a newly observed passage takes precedence over an unstarted skip')
                if old_pause is not None:
                    event = next(e for e in self.events() if e.command.id == old_pause.id)
                    self.assertEqual((3, 0), (event.outcome, event.begin_ns))
                    self.reject_old_callbacks_without_mutation(old_pause)
                self.fit_clear(terrain)
                following = self.next_move(terrain)
                self.assertEqual(3, following.direction)
                self.assertEqual(0, self.status().restarts)

    def test_elapsed_time_and_crossing_capture_do_not_replace_post_cutoff_floor(self):
        terrain, _, ack_ns = self.resumed()
        self.now = ack_ns+SETTLE
        self.assertEqual(0, self.tick()[0], 'a timer cannot make the old early FLOOR fresh enough')
        self.now += 2
        self.observe(terrain, start=ack_ns+SETTLE-1, end=self.now)
        self.assertEqual(0, self.tick()[0], 'the capture START must meet the inclusive cutoff')
        self.now += 2
        self.observe(terrain, start=ack_ns+SETTLE, end=self.now)
        ready, pause = self.tick()
        self.assertEqual((1, 2), (ready, pause.kind))
        self.assertEqual(ack_ns+SETTLE, pause.source_start_ns)
        self.assertEqual(0, self.tick()[0], 'one prepared PAUSE is not another reservation')

    def test_unstable_and_wrong_prefix_post_cutoff_frames_never_authorize_pause(self):
        for fault in ('unstable', 'prefix'):
            with self.subTest(fault=fault):
                terrain, _, ack_ns = self.resumed()
                self.now = ack_ns+SETTLE+2
                self.assertEqual(0, self.observe(terrain, start=ack_ns+SETTLE,
                    stable=0 if fault == 'unstable' else 1,
                    prefix=0 if fault == 'prefix' else self.prefix))
                self.assertEqual(0, self.tick()[0])
                self.assertEqual([1], [e.command.kind for e in self.events()])
                self.fresh_post_ui_floor(terrain, ack_ns, delta=4)
                ready, pause = self.tick()
                self.assertEqual((1, 2), (ready, pause.kind))
                self.assertEqual(self.number, pause.source_capture_id)

    def test_restart_ack_keeps_its_own_settle_boundary_after_level_reset(self):
        self.new_uptime()
        terrain = passage.passage_room(mouth=None)
        self.observe(terrain)
        ready, pause = self.tick()
        self.assertEqual((1, 2), (ready, pause.kind))
        self.ack(pause)
        self.now += SETTLE
        self.observe(self.scene(terrain, state=1, gold=0))
        ready, restart = self.tick()
        self.assertEqual((1, 3), (ready, restart.kind))
        self.ack(restart)
        ack_ns = self.now
        self.now += 71_289_375
        self.observe(self.scene(terrain, fingerprint=bytes([160])*48))
        self.assertEqual((1, 0, 0),
            (self.status().restarts, self.status().moves, self.status().inputs))
        self.assertEqual(0, self.tick()[0])
        self.fresh_post_ui_floor(terrain, ack_ns)
        ready, next_pause = self.tick()
        self.assertEqual((1, 2), (ready, next_pause.kind))
        self.assertEqual(self.number, next_pause.source_capture_id)
        self.assertGreaterEqual(next_pause.source_start_ns-ack_ns, SETTLE)
        self.reject_old_callbacks_without_mutation(restart)

    def test_goods_latch_immediately_while_physical_pause_waits_for_its_fresh_floor(self):
        for already_paused in (False, True):
            with self.subTest(already_paused=already_paused):
                terrain, _, ack_ns = self.resumed()
                visible = deepcopy(terrain)
                visible.goods = 'visible'
                self.now += 2
                self.observe(visible)
                self.assertEqual((1, 1, 0, 0),
                    (self.status().goods, self.status().reason,
                     self.status().inputs, self.status().restarts))
                self.assertEqual(0, self.tick()[0])
                self.assertEqual([1], [e.command.kind for e in self.events()])
                if already_paused:
                    self.now += 2
                    self.observe(self.scene(visible, state=1, gold=0))
                    self.assertEqual(0, self.tick()[0])
                    self.assertEqual((1, 1, 1),
                        (self.status().terminal, self.status().paused, self.status().goods))
                    self.assertEqual([1], [e.command.kind for e in self.events()])
                else:
                    self.fresh_post_ui_floor(visible, ack_ns)
                    ready, pause = self.tick()
                    self.assertEqual((1, 2), (ready, pause.kind))
                    self.ack(pause)
                    self.now += 2
                    self.observe(self.scene(visible, state=1, gold=0))
                    self.assertEqual((1, 1, 1),
                        (self.status().terminal, self.status().paused, self.status().goods))

    def test_already_floor_or_elapsed_ui_ack_adds_no_new_pause_delay(self):
        for mode in ('already_floor', 'old_resume'):
            with self.subTest(mode=mode):
                if mode == 'already_floor':
                    self.new_uptime()
                    terrain = passage.passage_room(mouth=None)
                    self.observe(terrain)
                else:
                    terrain, _, ack_ns = self.resumed()
                    self.now = ack_ns+2*SECOND
                    self.observe(terrain)
                    terrain.goods = 'visible'
                    self.now += 2
                    self.observe(terrain)
                current = self.now
                ready, pause = self.tick()
                self.assertEqual((1, 2, current), (ready, pause.kind, pause.not_before_ns))

    def test_final_begin_rechecks_latest_floor_and_live_control(self):
        for fault in ('pause_ui', 'owner', 'foreground', 'locked', 'cancel'):
            with self.subTest(fault=fault):
                terrain, _, ack_ns = self.resumed()
                self.fresh_post_ui_floor(terrain, ack_ns)
                ready, pause = self.tick()
                self.assertEqual((1, 2), (ready, pause.kind))
                self.now += 2
                if fault == 'pause_ui':
                    self.observe(self.scene(terrain, state=1, gold=0))
                elif fault == 'cancel':
                    self.lib.ng2_controller_cancel(self.engine, self.now, 2)
                accepted = self.lib.ng2_controller_begin(self.engine, pause.id, self.now,
                    0 if fault == 'foreground' else 1,
                    1 if fault == 'locked' else 0,
                    0 if fault == 'owner' else 1)
                self.assertEqual(0, accepted)
                event = next(e for e in self.events() if e.command.id == pause.id)
                self.assertEqual((3, 0), (event.outcome, event.begin_ns))
                self.assertEqual((0, 0), (self.status().inputs, self.status().restarts))
                self.reject_old_callbacks_without_mutation(pause)

    def test_ui_wait_preserves_source_session_and_unknown_input_limits(self):
        for fault in ('stale', 'session', 'unknown_resume', 'unknown_pause'):
            with self.subTest(fault=fault):
                if fault == 'unknown_resume':
                    self.new_uptime()
                    terrain = passage.passage_room(mouth=None)
                    self.observe(self.scene(terrain, state=1, gold=0))
                    ready, operation = self.tick()
                    self.assertEqual((1, 1), (ready, operation.kind))
                    self.assertEqual(1, self.lib.ng2_controller_begin(
                        self.engine, operation.id, self.now, 1, 0, 1))
                    self.now += 2
                    self.assertEqual(1, self.lib.ng2_controller_complete(self.engine, operation.id, self.now, -1))
                else:
                    terrain, _, ack_ns = self.resumed()
                    if fault == 'stale':
                        self.now = self.status().last_capture_start_ns+3*SECOND+1
                        self.tick()
                        self.assertEqual(7, self.status().reason)
                    elif fault == 'session':
                        self.now = self.status().started_ns+180*SECOND
                        self.tick()
                        self.assertEqual((1, 15), (self.status().terminal, self.status().reason))
                    else:
                        self.fresh_post_ui_floor(terrain, ack_ns)
                        ready, operation = self.tick()
                        self.assertEqual((1, 2), (ready, operation.kind))
                        self.assertEqual(1, self.lib.ng2_controller_begin(
                            self.engine, operation.id, self.now, 1, 0, 1))
                        self.now += 2
                        self.assertEqual(1, self.lib.ng2_controller_complete(
                            self.engine, operation.id, self.now, -1))
                if fault.startswith('unknown'):
                    self.assertEqual((1, 11, 4),
                        (self.status().terminal, self.status().reason, self.status().input_state))
                    before = self.all_public_bytes()
                    self.now += SECOND
                    self.observe(terrain)
                    self.assertEqual(before, self.all_public_bytes())
                self.assertNotIn(self.tick()[1].kind, (3, 4))
                self.assertEqual((0, 0), (self.status().inputs, self.status().restarts))

    def test_one_resumed_session_uses_fresh_ui_floor_and_reaches_all_goods(self):
        terrain, _, ack_ns = self.resumed()
        self.assertEqual(0, self.tick()[0])
        self.fresh_post_ui_floor(terrain, ack_ns)
        # Reuse the procedural route assertions without importing/inheriting
        # its unrelated methods. This is one native session and one C core.
        passage.NativePassage072Tests.test_one_native_session_restarts_searches_enters_and_completes_only_on_goods(self)


if __name__ == '__main__':
    unittest.main()
