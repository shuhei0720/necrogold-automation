"""TEST077: local palette changes cannot grant passage input authority.

TEST076's first stopped run motivates an off-step FLOOR/DIRT observation in
the origin/next neighbourhood. All maps, signatures, future frames and clocks
below are procedural public-C fixtures, not missing phone observations.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from tests import test_native_controller as fixture
from tests import test_native_recovery as mechanics
from tests import test_native_passage072 as passage
from tests import test_native_observation072 as observation
from tests import test_native_stationary_wait076 as stationary

CORE = mechanics.CORE
SECOND = fixture.SECOND


class NativePassagePalette077Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = mechanics.CORE
        cls.baseline_directory = None
        try:
            mechanics.CORE = CORE
            baseline = os.environ.get('NECRO_TEST077_BASELINE_CONTROLLER')
            if baseline:
                cls.baseline_directory = tempfile.TemporaryDirectory(prefix='test077-palette-baseline-')
                directory = Path(cls.baseline_directory.name)
                for path in CORE.glob('NG2*'):
                    if path.suffix in ('.c', '.h'):
                        shutil.copyfile(path, directory / path.name)
                shutil.copyfile(baseline, directory / 'NG2Controller.c')
                mechanics.CORE = directory
            mechanics.NativeRecoveryTests.setUpClass.__func__(cls)
        finally:
            mechanics.CORE = previous
        cls.lib.ng2_motion.argtypes = [C.POINTER(fixture.Scene), C.POINTER(fixture.Scene),
                                      C.c_int32, C.POINTER(observation.Motion)]
        cls.lib.ng2_choose.argtypes = [C.POINTER(fixture.Scene), C.c_int32, C.c_int32,
            C.POINTER(C.c_uint16), C.c_size_t, C.POINTER(observation.Entrance),
            C.POINTER(observation.Decision)]
        cls.lib.ng2_choose_passage.argtypes = [C.POINTER(fixture.Scene), C.c_int32,
            C.c_int32, C.c_int32, C.c_int32, C.POINTER(observation.Decision)]

    @classmethod
    def tearDownClass(cls):
        mechanics.NativeRecoveryTests.tearDownClass.__func__(cls)
        if cls.baseline_directory:
            cls.baseline_directory.cleanup()

    setUp = fixture.NativeControllerTests.setUp
    scene = fixture.NativeControllerTests.scene
    tick = fixture.NativeControllerTests.tick
    status = fixture.NativeControllerTests.status
    events = fixture.NativeControllerTests.events
    ack = fixture.NativeControllerTests.ack
    fit = fixture.NativeControllerTests.fit
    next_move = fixture.NativeControllerTests.next_move
    publish_procedural_candidate = fixture.NativeControllerTests.publish_procedural_candidate
    fresh_engine = fixture.NativeControllerTests.fresh_engine
    recovery = mechanics.NativeRecoveryTests.recovery
    recovery_samples = mechanics.NativeRecoveryTests.recovery_samples
    all_public_bytes = mechanics.NativeRecoveryTests.all_public_bytes
    reject_old_callbacks_without_mutation = mechanics.NativeRecoveryTests.reject_old_callbacks_without_mutation
    motion_wait = fixture.NativeControllerTests.motion_wait
    credit = observation.NativeObservation072Tests.credit
    choice = observation.NativeObservation072Tests.choice
    observed_vantage = observation.NativeObservation072Tests.observed_vantage
    observed_result = observation.NativeObservation072Tests.observed_result
    preparation_epoch = fixture.NativeControllerTests.preparation_epoch
    frame = stationary.NativeStationaryWait076Tests.frame
    observe = stationary.NativeStationaryWait076Tests.observe
    observe_actual = stationary.NativeStationaryWait076Tests.observe_actual
    uncertain = stationary.NativeStationaryWait076Tests.uncertain
    motion = stationary.NativeStationaryWait076Tests.motion
    assert_waiting = stationary.NativeStationaryWait076Tests.assert_waiting
    future_ticket = stationary.NativeStationaryWait076Tests.future_ticket

    def passage_choice(self, terrain):
        choice = observation.Decision()
        frame = self.frame(terrain)
        self.assertGreater(self.lib.ng2_choose_passage(C.byref(frame), self.status().x,
            self.status().y, 0, -3, C.byref(choice)), 0)
        return tuple(getattr(choice, key) for key, _ in choice._fields_)

    def armed_palette(self, initial='floor'):
        terrain = passage.passage_room()
        # The camera moves UP once before the tested ticket. This inboard
        # off-route cell then appears at (1,-1), as in the reported rejection.
        if initial == 'unknown':
            del terrain.tiles[(1, -2)]
        else:
            terrain.tiles[(1, -2)] = initial
        for _ in range(27):
            self.now += 100_000_000
            self.observe(terrain)
        first = passage.NativePassage072Tests.next_operation(self, terrain)
        self.assertEqual((4, 3), (first.kind, first.direction))
        self.ack(first)
        terrain = fixture.translated(terrain, first.direction)
        self.now = max(self.now, first.target_ns + 80_000_002)
        self.observe(terrain)
        self.assertEqual((1, 1, 1), (self.status().inputs, self.status().moves,
                                  self.status().lead_confirmed))
        self.verified_ns = self.now
        old = passage.NativePassage072Tests.next_operation(self, terrain)
        self.assertEqual((4, 3, 1), (old.kind, old.direction, self.status().input_state))
        self.original_period = self.status().beat_period_ns
        self.parent_deadline = min(old.source_start_ns + 3 * SECOND,
            old.phase_sample_ns + 3 * SECOND, self.verified_ns + 12 * SECOND,
            self.status().walk_started_ns + 45 * SECOND,
            self.status().started_ns + 180 * SECOND)
        return terrain, old

    def palette_wait(self, initial='floor', latest='dirt'):
        terrain, old = self.armed_palette(initial)
        changed = self.uncertain(terrain)
        if latest == 'unknown':
            changed.tiles.pop((1, -1), None)
        else:
            changed.tiles[(1, -1)] = latest
        self.assertEqual(self.passage_choice(terrain), self.passage_choice(changed))
        self.assertEqual((0, 0, 0), self.motion(terrain, changed, old.direction))
        self.assertEqual((2, 0, 0), self.motion(changed, changed, old.direction))
        self.saved_credit = self.credit()
        self.now = old.deadline_ns - 30_000_000
        self.trigger_commit = self.trigger_end = self.now
        self.wait_deadline = min(self.parent_deadline, self.now + 2 * self.original_period)
        self.observe(changed)
        self.trigger_id = self.number
        self.assert_waiting(old)
        return terrain, changed, old

    def test_off_step_local_palette_retires_ticket_and_later_strict_proof_moves(self):
        for initial in ('unknown', 'floor', 'dirt', 'stone'):
            for latest in ('unknown', 'floor', 'dirt', 'stone'):
                if initial == latest:
                    continue
                with self.subTest(initial=initial, latest=latest):
                    self.fresh_engine()
                    terrain, changed, old = self.palette_wait(initial, latest)
                    self.reject_old_callbacks_without_mutation(old)
                    # A later independent image retains the changed palette;
                    # only the public motion proof returns to the old anchor.
                    proven = deepcopy(changed)
                    proven.signature = terrain.signature
                    self.assertEqual((2, 0, 0), self.motion(terrain, proven, old.direction))
                    new = self.future_ticket(proven)
                    self.assertGreater(new.id, old.id)
                    self.assertGreater(new.target_ns, old.target_ns)
                    self.assertEqual((old.direction, old.ordinal), (new.direction, new.ordinal))
                    self.assertLessEqual(new.deadline_ns + self.status().lead_ns + 50_000_000,
                                         self.parent_deadline)
                    self.ack(new)
                    self.now = max(self.now, new.target_ns + 80_000_002)
                    self.observe(fixture.translated(proven, new.direction))
                    self.assertEqual((0, 2, 2, 0, -2),
                        (self.status().reason, self.status().inputs, self.status().moves,
                         self.status().x, self.status().y))

    def test_adjacent_blocked_palette_frames_cannot_replace_original_anchor(self):
        terrain, changed, old = self.palette_wait()
        for _ in range(3):
            self.now += 100_000_000
            self.observe(changed)
            self.assert_waiting(old)
        self.assertEqual((0, 0, 0), self.motion(terrain, changed, old.direction))
        self.assertEqual((2, 0, 0), self.motion(changed, changed, old.direction))
        self.reject_old_callbacks_without_mutation(old)
        proven = deepcopy(changed)
        proven.signature = terrain.signature
        self.assertEqual((2, 0, 0), self.motion(terrain, proven, old.direction))
        self.future_ticket(proven)

    def test_local_change_is_still_rejected_for_shop_wait(self):
        terrain, old = stationary.NativeStationaryWait076Tests.armed(self)
        changed = self.uncertain(terrain, True)
        changed.tiles[(1, 0)] = 'dirt'
        self.now = old.deadline_ns - 30_000_000
        self.observe(changed)
        self.assertEqual((17, 1, 1),
            (self.status().reason, self.status().inputs, self.status().moves))
        self.assertEqual(0, self.lib.ng2_controller_begin(
            self.engine, old.id, old.not_before_ns, 1, 0, 1))

    def test_origin_next_protected_route_goods_and_unsafe_materials_remain_guards(self):
        for fault in ('origin', 'next', 'protected', 'item', 'door', 'gold', 'route',
                      'visible', 'partial', 'nonfloor', 'expired'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                terrain, old = self.armed_palette()
                changed = self.uncertain(terrain)
                changed.tiles[(1, -1)] = 'dirt'
                if fault == 'origin': changed.tiles[(0, 0)] = 'dirt'
                elif fault == 'next': changed.tiles[(0, -1)] = 'dirt'
                elif fault == 'protected': changed.protected.add((1, -1))
                elif fault == 'item': changed.tiles[(1, -1)] = 'item'
                elif fault == 'door': changed.tiles[(1, -1)] = 'door'
                elif fault == 'gold':
                    changed.tiles[(1, -1)] = 'gold'; changed.gold.add((1, -1))
                elif fault == 'route': changed.tiles[(0, -3)] = 'dirt'
                elif fault in ('visible', 'partial'): changed.goods = fault
                self.now = old.deadline_ns + 1 if fault == 'expired' else old.deadline_ns - 30_000_000
                frame = self.frame(changed)
                if fault == 'nonfloor': frame.state = 1
                self.observe(frame)
                self.assertNotEqual((0, 0, 4, 0), (self.status().reason,
                    self.status().terminal, self.status().phase, self.status().input_state))
                self.assertEqual((1, 1), (self.status().inputs, self.status().moves))
                self.assertEqual(0, self.lib.ng2_controller_begin(
                    self.engine, old.id, old.not_before_ns, 1, 0, 1))

    def test_palette_wait_uses_fixed_wait_and_parent_deadlines(self):
        for bound in ('wait', 'parent'):
            with self.subTest(bound=bound):
                self.fresh_engine()
                terrain, changed, old = self.palette_wait()
                if bound == 'parent':
                    self.future_ticket(terrain)
                    self.assertEqual(self.parent_deadline,
                                     self.recovery().records[0].sync_deadline_ns)
                else:
                    self.now += 100_000_000
                    self.observe(changed)
                    self.assert_waiting(old)
                self.now = self.wait_deadline if bound == 'wait' else self.parent_deadline
                self.observe(terrain)
                self.assertEqual((8, 1, 1),
                    (self.status().reason, self.status().inputs, self.status().moves))
                self.assertNotEqual(4, self.tick()[1].kind)

    def test_palette_proof_still_requires_stable_current_prefix_and_new_capture(self):
        for fault in ('prefix', 'unstable', 'id', 'overlap'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                terrain, _, old = self.palette_wait()
                self.now += 2
                options = {'prefix': self.prefix - 1} if fault == 'prefix' else (
                    {'stable': 0} if fault == 'unstable' else
                    {'number': self.trigger_id} if fault == 'id' else
                    {'start': self.trigger_end - 1})
                self.observe(terrain, **options)
                self.assertNotEqual(4, self.tick()[1].kind)
                self.assertEqual((1, 1), (self.status().inputs, self.status().moves))
                self.assertEqual(0, self.lib.ng2_controller_begin(
                    self.engine, old.id, old.not_before_ns, 1, 0, 1))


if __name__ == '__main__':
    unittest.main()
