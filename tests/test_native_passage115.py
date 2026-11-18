"""TEST115 bounded passage source refresh and unlocalized stationary evidence.

All maps, images and clocks here are procedural public-C fixtures. Recorded
TEST114 images calibrate the design privately; no missing future phone capture
or callback is claimed to exist. Normal Motion always remains authoritative.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from tests import test_native_controller as native
from tests import test_native_stationary_wait076 as stationary
from tests import test_native_passage072 as passage
from tests import test_native_passage_navigation072 as geometry
from tests import test_native_plural_wait103 as plural
from tests import test_native_plural_stationary103 as scalar
from tests import test_native_motion075 as motion
from tests.test_native_beat import NativeSample


CORE = Path(os.environ.get('NECRO115_PASSAGE_CORE', native.CORE))
CELL = geometry.offset
MOUTH = (-2, -3)


def floor_fringe():
    """Observed full boundary and an exterior FLOOR; the mouth stays dark."""
    scene = geometry.room()
    geometry.set_cell(scene, -2, -3, 0)
    geometry.set_cell(scene, -2, -4, 0)
    geometry.set_cell(scene, -3, -4, 1)
    return scene


class Passage115Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        old = native.CORE
        try:
            native.CORE = CORE
            native.NativeControllerTests.setUpClass.__func__(cls)
        finally:
            native.CORE = old
        cls.lib.ng2_passage_candidates.argtypes = [C.POINTER(native.Scene)]
        cls.lib.ng2_passage_candidates.restype = C.c_uint32
        cls.lib.ng2_choose_passage.argtypes = [C.POINTER(native.Scene), C.c_int32,
            C.c_int32, C.c_int32, C.c_int32, C.POINTER(geometry.Decision)]
        cls.lib.ng2_motion.argtypes = [C.POINTER(native.Scene), C.POINTER(native.Scene),
            C.c_int32, C.POINTER(motion.Motion)]
        cls.lib.ng2_controller_recovery_samples.argtypes = [C.c_void_p, C.c_size_t,
            C.POINTER(NativeSample), C.c_size_t]
        cls.lib.ng2_controller_recovery_samples.restype = C.c_size_t

    tearDownClass = classmethod(native.NativeControllerTests.tearDownClass.__func__)


class NativePassageFringe115Tests(Passage115Base):
    def candidates(self, scene):
        original = bytes(scene)
        mask = self.lib.ng2_passage_candidates(C.byref(scene))
        self.assertEqual(original, bytes(scene), 'a hypothesis cannot relabel unknown tiles')
        return mask

    def choose(self, scene, x=0, y=0):
        value = geometry.Decision()
        length = self.lib.ng2_choose_passage(C.byref(scene), x, y, *MOUTH, C.byref(value))
        return length, value

    def test_observed_floor_fringe_adds_only_upper_left_dark_mouth(self):
        scene = floor_fringe()
        self.assertEqual((0, 0, 1), tuple(scene.tiles[CELL(*p)]
            for p in (MOUTH, (-2, -4), (-3, -4))))
        self.assertEqual(1, self.candidates(scene),
            'an observed exterior FLOOR with full roof/left support merits an inside FLOOR view')
        length, choice = self.choose(scene)
        self.assertGreater(length, 0)
        self.assertEqual((10, 1), (choice.reason, choice.obstacle))
        dx, dy = native.DIRS[choice.direction]
        self.assertEqual(1, scene.tiles[CELL(dx, dy)])
        self.assertEqual((0, 0), (scene.tiles[CELL(*MOUTH)], scene.tiles[CELL(-2, -4)]))

    def test_fringe_needs_full_observed_support_and_positive_inside_floor(self):
        required = tuple((x, -3) for x in range(-1, 3)) + tuple((-3, y) for y in range(-3, 4))
        for point in required:
            for tile in (0, 1, 2, 5, 6):
                with self.subTest(point=point, tile=tile):
                    scene = floor_fringe(); geometry.set_cell(scene, *point, tile)
                    self.assertEqual(0, self.candidates(scene) & 1)
        for point in ((-3, -4), (-1, -1), (0, -1), (-1, 0), (0, 0)):
            for tile in (0, 2, 3, 4, 5, 6):
                if point == (-3, -4) and tile in (3, 4):
                    continue  # The independent historical wall-corner hypothesis remains valid.
                with self.subTest(point=point, tile=tile):
                    scene = floor_fringe(); geometry.set_cell(scene, *point, tile)
                    self.assertEqual(0, self.candidates(scene) & 1)

    def test_fringe_rejects_nonclear_goods_protection_and_no_floor_vantage(self):
        for field, value in (('state', 1), ('gold_state', 0), ('gold_state', 2),
                             ('gold_state', 3), ('goods', 1), ('goods', 2)):
            scene = floor_fringe(); setattr(scene, field, value)
            self.assertEqual(0, self.candidates(scene) & 1)
        scene = floor_fringe(); scene.protected_cells[CELL(8, 2)] = 1
        self.assertEqual(0, self.candidates(scene) & 1)
        scene = floor_fringe()
        for point in ((-1, -2), (-2, -1), (-2, -2)):
            geometry.set_cell(scene, *point, 0)
        self.assertEqual(0, self.candidates(scene) & 1)
        length, choice = self.choose(scene)
        if length:
            # A pure chooser may still name another observed inside vantage;
            # the new candidate cannot grant it or an UNKNOWN mouth as input.
            dx, dy = native.DIRS[choice.direction]
            self.assertEqual(1, scene.tiles[CELL(dx, dy)])
            self.assertNotEqual(MOUTH, (dx, dy))


class NativePassageSource115Tests(Passage115Base):
    setUp = native.NativeControllerTests.setUp
    scene = native.NativeControllerTests.scene
    tick = native.NativeControllerTests.tick
    status = native.NativeControllerTests.status
    events = native.NativeControllerTests.events
    ack = native.NativeControllerTests.ack
    motion_wait = native.NativeControllerTests.motion_wait
    preparation_epoch = native.NativeControllerTests.preparation_epoch
    fresh_engine = native.NativeControllerTests.fresh_engine
    fit = native.NativeControllerTests.fit
    publish_procedural_candidate = native.NativeControllerTests.publish_procedural_candidate
    next_move = native.NativeControllerTests.next_move
    credit = stationary.NativeStationaryWait076Tests.credit
    armed = stationary.NativeStationaryWait076Tests.armed
    next_operation = passage.NativePassage072Tests.next_operation
    frame = stationary.NativeStationaryWait076Tests.frame
    observe = stationary.NativeStationaryWait076Tests.observe

    def direct_motion(self, before, after, direction):
        first, second = self.frame(before), self.frame(after)
        value = motion.Motion()
        self.assertEqual(1, self.lib.ng2_motion(C.byref(first), C.byref(second), direction, C.byref(value)))
        return value.kind, value.dx, value.dy

    def pending_refresh(self):
        terrain, old = self.armed('passage')
        self.assertEqual((1, 1, 1),
            (self.status().inputs, self.status().moves, self.status().lead_confirmed))
        changed = deepcopy(terrain)
        changed.tiles[(-3, 3)] = 'stone'
        self.assertEqual('dirt', terrain.tiles[(-3, 3)])
        self.assertEqual((2, 0, 0), self.direct_motion(terrain, changed, old.direction))
        return terrain, changed, old

    def test_clear_passage_presend_refresh_reissues_same_physical_ticket_and_epoch(self):
        _, changed, old = self.pending_refresh()
        epoch, credit = self.preparation_epoch(old), self.credit()
        original_wait = bytes(self.motion_wait())
        self.assertGreater(epoch, 0)
        self.now += 2
        self.assertEqual(1, self.observe(changed))
        source = self.number
        prior = self.events()[-1]
        self.assertEqual((old.id, 3, 0, 0),
            (prior.command.id, prior.outcome, prior.begin_ns, prior.motion),
            'the stale before-image must be retired while it is definitely unsent')
        ready, new = self.tick()
        self.assertEqual((1, 4), (ready, new.kind))
        self.assertGreater(new.id, old.id)
        self.assertEqual(source, new.source_capture_id)
        self.assertEqual((old.target_ns, old.not_before_ns, old.deadline_ns, old.ordinal, old.direction),
            (new.target_ns, new.not_before_ns, new.deadline_ns, new.ordinal, new.direction))
        self.assertEqual(epoch, self.preparation_epoch(new))
        self.assertEqual(0, self.preparation_epoch(old))
        self.assertEqual(credit, self.credit())
        wait = self.motion_wait()
        original = native.MotionWait.from_buffer_copy(original_wait)
        self.assertEqual(original.deadline_ns, wait.deadline_ns)
        self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, old.id, new.not_before_ns, 1, 0, 1))
        self.ack(new)
        self.assertEqual((2, 1), (self.status().inputs, self.status().moves))
        moved = native.translated(changed, new.direction)
        self.now = max(self.now+2, new.target_ns+80_000_002)
        self.assertEqual(1, self.observe(moved))
        self.assertEqual((2, 2), (self.status().inputs, self.status().moves))

    def test_started_ack_or_unknown_input_never_refreshes_or_resends(self):
        for stage in ('started', 'ack', 'unknown'):
            with self.subTest(stage=stage):
                self.fresh_engine(); _, changed, old = self.pending_refresh()
                self.now = old.not_before_ns
                self.assertEqual(1, self.lib.ng2_controller_begin(self.engine, old.id, self.now, 1, 0, 1))
                if stage != 'started':
                    self.now += 1
                    self.assertEqual(1, self.lib.ng2_controller_complete(self.engine, old.id, self.now,
                        1 if stage == 'ack' else -1))
                    if stage == 'ack': self.prefix = old.id
                count = len(self.events())
                self.now += 2; self.observe(changed)
                self.assertEqual(count, len(self.events()))
                self.assertNotEqual(4, self.tick()[1].kind)
                self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, old.id, self.now, 1, 0, 1))

    def test_only_one_refinement_per_physical_ticket_and_repetitions_keep_its_source(self):
        before, changed, old = self.pending_refresh()
        self.now += 2; self.observe(before)
        self.assertEqual((old.id, 0), (self.events()[-1].command.id, self.events()[-1].outcome))
        self.now += 2; self.observe(changed)
        ready, new = self.tick()
        self.assertEqual((1, 4), (ready, new.kind))
        source, epoch = new.source_capture_id, self.preparation_epoch(new)
        third = deepcopy(changed); self.assertEqual('dirt', third.tiles[(3, 2)])
        third.tiles[(3, 2)] = 'stone'
        self.assertEqual((2, 0, 0), self.direct_motion(before, third, old.direction))
        count = len(self.events())
        for terrain in (changed, third, third):
            self.now += 2; self.observe(terrain)
            self.assertEqual((new.id, 0), (self.events()[-1].command.id, self.events()[-1].outcome))
            self.assertEqual(source, self.events()[-1].command.source_capture_id)
            self.assertEqual(count, len(self.events()))
            self.assertEqual(epoch, self.preparation_epoch(new))
        self.ack(new)
        self.assertEqual((2, 1), (self.status().inputs, self.status().moves))

    def test_refinement_rejects_wrong_prefix_protection_local_material_choice_and_expiry(self):
        for fault in ('prefix', 'protected', 'near_material', 'wrong_choice', 'gold', 'expired'):
            with self.subTest(fault=fault):
                self.fresh_engine(); before, changed, old = self.pending_refresh()
                saved, count = self.credit(), len(self.events())
                options = {}
                if fault == 'prefix': options['prefix'] = self.prefix+1
                elif fault == 'protected': changed.protected.add((8, 2))
                elif fault == 'near_material': changed.tiles[(1, 1)] = 'stone'
                elif fault == 'wrong_choice': changed.tiles[native.DIRS[old.direction]] = 'stone'
                elif fault == 'gold':
                    changed.tiles[(8, 2)] = 'gold'; changed.gold.add((8, 2))
                self.now = old.deadline_ns+1 if fault == 'expired' else self.now+2
                self.observe(changed, **options)
                self.assertEqual(saved, self.credit())
                self.assertEqual(count, len(self.events()))
                self.assertIn(self.status().current_command_id, (0, old.id))
                _, command = self.tick()
                self.assertNotEqual(4, command.kind,
                    'none of these observations may publish a replacement MOVE')
                self.assertEqual(saved, self.credit())


def candidate_pair():
    result = []
    for source in scalar.plural_phase_pair():
        scene = native.Scene(abi_version=1, struct_size=C.sizeof(native.Scene),
            state=2, gold_state=2, gold_peak=158)
        scene.tiles[:] = source.tiles
        scene.signature[:] = source.signature
        result.append(scene)
    return result


class NativeUnlocalizedZero115Tests(Passage115Base):
    def proof(self, pair, direction=3):
        original = tuple(bytes(scene) for scene in pair)
        function = getattr(self.lib, 'ng2_unlocalized_passage_stationary_zero', None)
        if function is None:
            result = 0  # Absent recognition evidence cannot grant any qualification.
        else:
            function.argtypes = [C.POINTER(native.Scene), C.POINTER(native.Scene), C.c_int32]
            result = function(C.byref(pair[0]), C.byref(pair[1]), direction)
        self.assertEqual(original, tuple(bytes(scene) for scene in pair))
        return result

    def test_unlocalized_positive_uses_strict_zero_evidence_without_rewriting_motion(self):
        for direction in (1, 2, 3, 4):
            with self.subTest(direction=direction):
                pair = candidate_pair()
                observed = motion.Motion()
                self.assertEqual(1, self.lib.ng2_motion(C.byref(pair[0]), C.byref(pair[1]),
                    direction, C.byref(observed)))
                self.assertEqual((0, 0, 0), (observed.kind, observed.dx, observed.dy))
                self.assertEqual(1, self.proof(pair, direction),
                    'a positive unlocalized hint does not destroy the same strict fixed-world numeric zero')

    def test_actual_gold_goods_protection_and_lost_material_are_not_qualified(self):
        for fault in ('clear', 'unknown', 'low_hint', 'gold', 'door', 'item',
                      'partial', 'protected', 'origin', 'next', 'old_stone', 'flat'):
            with self.subTest(fault=fault):
                pair = candidate_pair()
                if fault == 'clear': pair[1].gold_state = 1
                elif fault == 'unknown': pair[1].gold_state = 0
                elif fault == 'low_hint': pair[1].gold_peak = 134
                elif fault in ('gold', 'door', 'item'):
                    pair[1].tiles[CELL(7, 2)] = {'gold': 2, 'door': 5, 'item': 6}[fault]
                elif fault == 'partial': pair[1].goods = 1
                elif fault == 'protected': pair[1].protected_cells[CELL(7, 2)] = 1
                elif fault == 'origin': pair[1].tiles[CELL(0, 0)] = 0
                elif fault == 'next': pair[1].tiles[CELL(0, -1)] = 0
                elif fault == 'old_stone': pair[1].tiles[CELL(-5, -2)] = 1
                else:
                    for scene in pair: scene.signature[:] = bytes([40]) * 23296
                self.assertEqual(0, self.proof(pair))

    def test_invalid_sources_directions_and_actual_translation_never_qualify_zero(self):
        for index in (0, 1):
            for field, value in (('state', 0), ('state', 1), ('state', 3),
                                 ('abi_version', 2), ('struct_size', C.sizeof(native.Scene)-1)):
                with self.subTest(index=index, field=field, value=value):
                    pair = candidate_pair(); setattr(pair[index], field, value)
                    self.assertEqual(0, self.proof(pair))
        for direction in (0, 5, -1):
            self.assertEqual(0, self.proof(candidate_pair(), direction))
        source = candidate_pair()[0]
        translated = native.Scene(abi_version=1, struct_size=C.sizeof(native.Scene),
            state=2, gold_state=2, gold_peak=158)
        for y in range(-5, 5):
            for x in range(-11, 11):
                translated.tiles[CELL(x+1, y)] = source.tiles[CELL(x, y)]
        image = native.Image.frombytes('L', (224, 104), bytes(source.signature))
        shifted = native.Image.new('L', image.size); shifted.paste(image, (9, 0))
        translated.signature[:] = shifted.tobytes()
        observed = motion.Motion()
        self.lib.ng2_motion(C.byref(source), C.byref(translated), 1, C.byref(observed))
        self.assertEqual((1, -1, 0), (observed.kind, observed.dx, observed.dy))
        self.assertEqual(0, self.proof((source, translated), 1),
            'normal observed displacement is never stationary qualification')


class NativeUnlocalizedWait115Tests(Passage115Base):
    recovery = native.NativeControllerTests.recovery
    motion = NativePassageSource115Tests.direct_motion
    assert_waiting = stationary.NativeStationaryWait076Tests.assert_waiting
    choice = stationary.NativeStationaryWait076Tests.choice
    observed_vantage = stationary.NativeStationaryWait076Tests.observed_vantage
    observed_result = stationary.NativeStationaryWait076Tests.observed_result
    reject_old_callbacks_without_mutation = stationary.NativeStationaryWait076Tests.reject_old_callbacks_without_mutation
    all_public_bytes = stationary.NativeStationaryWait076Tests.all_public_bytes
    recovery_samples = stationary.NativeStationaryWait076Tests.recovery_samples

    def scene(self, state=1, gold=0, terrain=None, beat=False):
        scene = native.NativeControllerTests.scene(self, state,
            2 if terrain is not None else gold, terrain, beat)
        if terrain is not None: scene.gold_peak = 158
        return scene

    def future_ticket(self, terrain):
        # Runtime ticks immediately after committing a frame. Do not add an
        # artificial20ms before checking the first current proof/fit pair.
        for _ in range(100):
            ready, command = self.tick()
            self.assertEqual(0, self.status().reason)
            if ready:
                self.assertEqual(4, command.kind)
                self.assertGreaterEqual(command.not_before_ns-self.now, 50_000_000)
                return command
            self.now += 20_000_000
            self.observe(terrain)
        self.fail('current direct-anchor proof and fit must fund a bounded prepared ticket')

    def candidate_wait(self, trigger_offset=-52_313_208):
        room = passage.passage_room(mouth=(-2, -3))
        room.tiles[(-5, -2)] = room.tiles[(2, 2)] = 'stone'
        with patch.object(passage, 'passage_room', return_value=room):
            terrain, second = self.armed('passage')
        self.ack(second)
        terrain = native.translated(terrain, second.direction)
        self.now = max(self.now, second.target_ns+80_000_002)
        self.assertEqual(1, self.observe(terrain))
        self.assertEqual((2, 2, 1),
            (self.status().inputs, self.status().moves, self.status().lead_confirmed))
        self.verified_ns = self.now
        before, after = deepcopy(terrain), deepcopy(terrain)
        before.signature, after.signature = plural.room_phase_pair(self.frame(terrain))
        self.now += 10_000_000
        self.assertEqual(1, self.observe(before))
        old = passage.NativePassage072Tests.next_move(self, before)
        self.assertEqual((0, 0, 0), self.motion(before, after, old.direction))
        self.saved_credit = self.credit()
        self.parent_deadline = min(old.source_start_ns+3*native.SECOND,
            old.phase_sample_ns+3*native.SECOND, self.verified_ns+12*native.SECOND,
            self.status().walk_started_ns+45*native.SECOND,
            self.status().started_ns+180*native.SECOND)
        self.original_period = self.status().beat_period_ns
        # Recorded86 entered52.313208ms before the unsent ticket's notBefore.
        # This procedural phase model keeps that timing; it is not phone replay.
        self.now = old.not_before_ns+trigger_offset
        self.trigger_commit = self.trigger_end = self.now
        self.wait_deadline = min(self.parent_deadline, self.now+2*self.original_period)
        self.assertEqual(1, self.observe(after))
        self.trigger_id = self.number
        self.assert_waiting(old)
        return before, after, old

    def test_independent_candidate_zero_then_blur_waits_without_input_and_reproves(self):
        before, after, old = self.candidate_wait()
        self.now = self.trigger_commit+90_811_291
        self.assertEqual(1, self.observe(after))
        self.assertEqual(0, self.status().reason)
        blurred = stationary.NativeStationaryWait076Tests.uncertain(self, after)
        self.assertEqual((0, 0, 0), self.motion(before, blurred, old.direction))
        self.now = self.trigger_commit+135_688_958
        self.assertEqual(1, self.observe(blurred))
        self.assertEqual((0, 0, 0),
            (self.status().reason, self.status().input_state, self.status().current_command_id),
            'temporary lost scalar evidence must discard READY without granting input or finishing')
        self.assertEqual(0, self.tick()[0])
        self.assertEqual(self.saved_credit, self.credit())
        self.now = self.trigger_commit+513_735_958
        self.assertEqual(1, self.observe(after))
        new = self.future_ticket(after)
        self.assertGreater(new.id, old.id)
        self.assertGreater(new.target_ns, old.target_ns)
        self.assertLess(self.now, self.wait_deadline)
        self.assertEqual(self.saved_credit, self.credit())
        self.reject_old_callbacks_without_mutation(old)
        self.assertLess(new.not_before_ns, self.wait_deadline,
            'the positive path must have an actual begin window before the original W')
        self.now = max(self.now, new.not_before_ns)
        self.assertLess(self.now, self.wait_deadline)
        self.ack(new)
        self.assertEqual((3, 2), (self.status().inputs, self.status().moves), 'ACK is not displacement')
        moved = native.translated(after, new.direction)
        self.assertEqual((1, *native.DIRS[new.direction]), self.motion(after, moved, new.direction))
        self.now = max(self.now+2, new.target_ns+80_000_002)
        self.observe(moved)
        self.assertEqual((0, 3, 3), (self.status().reason, self.status().inputs, self.status().moves))

    def test_candidate_reproof_does_not_extend_original_two_beat_wait(self):
        for extra in (0, 1):
            with self.subTest(extra=extra):
                self.fresh_engine(); _, after, _ = self.candidate_wait()
                self.now += 90_811_291; self.observe(after)
                blurred = stationary.NativeStationaryWait076Tests.uncertain(self, after)
                self.now += 44_877_667; self.observe(blurred)
                self.assertEqual(0, self.status().reason)
                self.now = self.wait_deadline+extra
                self.observe(after)
                self.assertEqual((8, *self.saved_credit[:2]),
                    (self.status().reason, self.status().inputs, self.status().moves))
                self.assertNotEqual(4, self.tick()[1].kind)

    def test_issued_candidate_ticket_cannot_begin_beyond_original_parent(self):
        _, after, old = self.candidate_wait()
        self.now = self.trigger_commit+90_811_291
        self.observe(after)
        new = self.future_ticket(after)
        self.assertLess(self.now, self.wait_deadline)
        self.assertLess(new.not_before_ns, self.wait_deadline)
        # SSOT TEST076: W bounds gaining READY; an issued ticket retains its
        # original parentP. Keep the actual-begin hard boundary at that P.
        self.now = self.parent_deadline
        self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, new.id, self.now, 1, 0, 1),
            'an issued physical ticket cannot extend its original parent')
        self.assertEqual((8, 2, 2), (self.status().reason, self.status().inputs, self.status().moves))
        self.assertEqual(0, next(e for e in self.events() if e.command.id == new.id).begin_ns)
        self.assertEqual(0, self.preparation_epoch(new))
        self.reject_old_callbacks_without_mutation(old)

    def test_ready_before_W_can_prepare_and_begin_after_W_within_original_parent(self):
        _, after, old = self.candidate_wait()
        self.now = self.wait_deadline-100_000_000
        self.observe(after)
        new = self.future_ticket(after)
        self.assertLess(self.now, self.wait_deadline)
        self.assertGreater(new.not_before_ns, self.wait_deadline)
        self.assertLess(new.deadline_ns, self.parent_deadline)
        self.assertLessEqual(self.motion_wait().deadline_ns, self.parent_deadline)
        self.assertEqual((2, 2), (self.status().inputs, self.status().moves))
        self.now = new.not_before_ns-1_000_000
        self.assertGreater(self.now, self.wait_deadline)
        self.observe(after)  # Current direct proof and phase after W, same fixed anchor/P.
        self.assertEqual(0, self.status().reason)
        self.ack(new)
        self.assertLess(self.events()[-1].begin_ns, self.parent_deadline)
        self.assertEqual((3, 2), (self.status().inputs, self.status().moves))
        moved = native.translated(after, new.direction)
        self.now = max(self.now+2, new.target_ns+80_000_002)
        self.observe(moved)
        self.assertEqual((0, 3, 3), (self.status().reason, self.status().inputs, self.status().moves))
        self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, old.id, self.now, 1, 0, 1))

    def test_ready_ticket_keeps_normal_window_and_original_parent_after_W(self):
        # A definitely-unsent frame can arrive within the old10ms window.
        # This public fixture makes W cut through a future valid window.
        # W is not the issued MOVE deadline in the original TEST076 contract.
        _, after, _ = self.candidate_wait(trigger_offset=5_000_000)
        self.now = self.wait_deadline-100_000_000
        self.observe(after)
        new = self.future_ticket(after)
        self.assertLess(new.not_before_ns, self.wait_deadline)
        self.assertGreater(new.not_before_ns+10_000_000, self.wait_deadline)
        self.assertEqual(new.not_before_ns+10_000_000, new.deadline_ns)
        self.assertGreater(new.deadline_ns, self.wait_deadline)
        self.assertLess(new.deadline_ns, self.parent_deadline)
        self.now = new.deadline_ns
        self.assertEqual(1, self.lib.ng2_controller_begin(self.engine, new.id, self.now, 1, 0, 1))
        self.assertEqual((2, 2, 2), (self.status().inputs, self.status().moves, self.status().input_state))
        self.assertEqual(self.now, self.events()[-1].begin_ns)
        self.now += 50_000_000
        self.assertEqual(1, self.lib.ng2_controller_complete(self.engine, new.id, self.now, 1))
        self.assertEqual((3, 2), (self.status().inputs, self.status().moves))

    def test_ready_or_issued_blur_at_W_expires_without_renewing_observation(self):
        for issued in (False, True):
            for extra in (0, 1):
                with self.subTest(issued=issued, extra=extra):
                    self.fresh_engine(); before, after, old = self.candidate_wait()
                    self.now = self.trigger_commit+90_811_291
                    self.observe(after)
                    new = self.future_ticket(after) if issued else None
                    blurred = stationary.NativeStationaryWait076Tests.uncertain(self, after)
                    self.assertEqual((0, 0, 0), self.motion(before, blurred, old.direction))
                    self.now = self.wait_deadline+extra
                    self.observe(blurred)
                    self.assertEqual((8, 2, 2),
                        (self.status().reason, self.status().inputs, self.status().moves))
                    self.assertNotEqual(4, self.tick()[1].kind)
                    for command in (old, new):
                        if command is not None:
                            event = next(e for e in self.events() if e.command.id == command.id)
                            self.assertEqual((3, 0), (event.outcome, event.begin_ns))
                            self.assertEqual(0, self.preparation_epoch(command))

    def test_issued_but_unbegun_candidate_blur_retires_only_its_permission(self):
        before, after, old = self.candidate_wait()
        new = self.future_ticket(after)
        frozen = (new.target_ns, new.not_before_ns, new.deadline_ns, self.wait_deadline, self.parent_deadline)
        blurred = stationary.NativeStationaryWait076Tests.uncertain(self, after)
        self.assertEqual((0, 0, 0), self.motion(before, blurred, old.direction))
        self.now += 2; self.assertEqual(1, self.observe(blurred))
        self.assertEqual((0, 0, 0),
            (self.status().reason, self.status().input_state, self.status().current_command_id))
        retired = self.events()[-1]
        self.assertEqual((new.id, 3, 0, 0),
            (retired.command.id, retired.outcome, retired.begin_ns, retired.motion))
        self.assertEqual(frozen[:3], (retired.command.target_ns,
            retired.command.not_before_ns, retired.command.deadline_ns))
        self.assertEqual(self.saved_credit, self.credit())
        self.assertEqual(0, self.preparation_epoch(new))
        self.assertEqual(0, self.tick()[0])
        self.reject_old_callbacks_without_mutation(old)
        self.reject_old_callbacks_without_mutation(new)
        self.now = frozen[3]
        self.observe(after)
        self.assertEqual((8, 2, 2), (self.status().reason, self.status().inputs, self.status().moves))


for _name in ('setUp', 'tick', 'status', 'events', 'ack', 'motion_wait',
              'preparation_epoch', 'fresh_engine', 'fit', 'publish_procedural_candidate',
              'next_move', 'credit', 'armed', 'next_operation', 'frame', 'observe'):
    setattr(NativeUnlocalizedWait115Tests, _name, getattr(NativePassageSource115Tests, _name))


if __name__ == '__main__':
    unittest.main()
