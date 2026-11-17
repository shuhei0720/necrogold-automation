"""TEST113 bounded FULL data refresh and one upward observation, public C.

Scenes, pixels, clocks and later MOVE responses are procedural. Received
TEST112 frames 220/223 and the two HUD-obscured storefronts are calibrated
separately; these tests do not invent later phone images or input delivery.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import random
import tempfile
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests import test_native_classification111 as classification
from tests import test_native_full_framing101 as full
from tests import test_native_opened_fade100 as opened
from tests import test_native_entry_episode102 as entry
from tests import test_native_offer_coverage104 as offer
from tests import test_native_ring_bank094 as bank
from tests.test_native_ring094 import Result
from tests.test_native_motion075 import Motion

ROOT = Path(__file__).resolve().parents[1]


class Goods113Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = native.CORE
        try:
            native.CORE = Path(os.environ.get('NECRO113_GOODS_CORE', str(previous)))
            full.NativeFullFraming101Tests.setUpClass()
        finally:
            native.CORE = previous
        cls.lib = full.NativeFullFraming101Tests.lib
        cls.lib.ng2_motion.argtypes = [C.POINTER(native.Scene), C.POINTER(native.Scene),
                                      C.c_int32, C.POINTER(Motion)]
        cls.tmp = tempfile.TemporaryDirectory(prefix='goods113-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.ring = bank.NativeRingBank094Tests.build_library(
            ROOT/'patches/loopctrl/ngg2/NG2Ring.c', Path(cls.tmp.name)/'ring.so')

    @classmethod
    def tearDownClass(cls):
        full.NativeFullFraming101Tests.tearDownClass()

    def producer(self, terrain, *, left=304, sy=87, unknown=False, target=False):
        pixels = offer.shop_pixels(left=left, sy=sy, missing_wall=unknown,
                                   target=target, target_name=False)
        status, value = offer.normal_assess(self.ring, pixels,
            self.h.scene(2, 2, terrain, beat=True))
        self.assertEqual(0, status, 'normal procedural Ring producer must succeed')
        return value

    def commit(self, value, elapsed=10_000_000):
        state = self.q.cycle()
        if not state.worker_started_ns:
            self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(
                self.h.engine, state.job_id, state.capture_id, state.prefix, self.h.now))
        value.started_ns = self.h.now
        self.h.now += elapsed
        value.finished_ns = self.h.now
        self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine,
            state.job_id, state.capture_id, state.prefix, self.h.now, C.byref(value)))
        return state

    def immutable_parent(self, root):
        state = self.q.cycle()
        self.assertEqual(root.hold_started_ns, state.hold_started_ns)
        self.assertLessEqual(state.continuation_deadline_ns, root.continuation_deadline_ns)
        self.assertEqual(root.level_id, state.level_id)

    def no_direction_or_restart(self):
        ready, command = self.h.tick()
        self.assertFalse(ready and command.kind in (3, 4))


class NativeGoodsDataRetry113Tests(Goods113Base):
    def setUp(self):
        self.old = classification.NativeClassificationRetry111Tests(methodName='runTest')
        self.old.lib, self.old.ring = self.lib, self.ring
        self.old.setUp()
        self.addCleanup(self.old.doCleanups)
        self.h, self.q = self.old.h, self.old.q
        self.source = deepcopy(self.old.source)
        self.source.tiles[(1, -1)] = 'stone'

    def frame(self, terrain, start=None, age=35_000_000, **kwargs):
        start = self.h.now + 10_000_000 if start is None else start
        self.h.now = start + age
        self.assertEqual(1, self.h.observe_actual(self.h.scene(2, 2, terrain, beat=True),
            start=start, end=start+12_000_000, **kwargs))
        return self.h.number

    def initial_unknown(self):
        self.frame(self.source)
        self.root = self.q.cycle()
        value = self.producer(self.source, unknown=True)
        self.assertEqual((0, 1, 1), (value.outcome, value.coverage, value.row_count),
                         'an observed but incomplete offer is UNKNOWN, never a negative')
        self.counts = (self.h.status().inputs, self.h.status().moves)
        self.commit(value)
        return self.root

    def waiting(self):
        state = self.q.cycle()
        self.assertEqual((3, 0, 0, 0), (state.state, state.pending, state.completed_shops,
                                      state.candidate_latched),
            'a safe FULL UNKNOWN must await bounded fresh DATA before stopping')
        self.assertEqual((0, 0), (self.h.tick()[0], self.h.status().input_state),
                         'DATA refresh grants no PAUSE, RESTART or MOVE ticket')
        self.immutable_parent(self.root)

    def test_safe_full_unknown_waits_for_new_normal_negative_without_any_input(self):
        root = self.initial_unknown()
        self.waiting()
        latest = deepcopy(self.source)
        latest.tiles[(1, -1)] = 'floor'
        latest.tiles[(7, 3)] = 'dirt'
        before = self.h.scene(2, 2, self.source, beat=True)
        after = self.h.scene(2, 2, latest, beat=True)
        still = Motion()
        self.assertEqual(1, self.lib.ng2_motion(C.byref(before), C.byref(after), 1, C.byref(still)))
        self.assertEqual((2, 0, 0), (still.kind, still.dx, still.dy),
                         'the near material refresh is direct strict zero, not a MOVE')
        fresh = self.frame(latest, root.capture_start_ns+125_000_000)
        job = self.q.cycle()
        self.assertEqual((root.job_id+1, fresh, 1), (job.job_id, job.capture_id, job.pending))
        self.immutable_parent(root)
        self.assertEqual(job.capture_start_ns+150_000_000, job.deadline_ns)
        value = self.producer(latest)
        self.assertEqual((3, 2), (value.outcome, value.coverage))
        self.commit(value, 36_000_000)
        self.assertEqual((3, 4), (self.q.cycle().outcome, self.q.cycle().state))
        self.assertEqual(self.counts, (self.h.status().inputs, self.h.status().moves))
        self.assertEqual(0, self.q.cycle().pause_capture_id, 'a fresh PAUSE image is still required')
        self.assertEqual(0, self.q.durable(), 'unpaused normal pixels cannot become durable PAUSE proof')
        self.q.pause_observed()
        self.assertEqual(0, self.h.tick()[0], 'normal negative must be durably stored')
        self.assertEqual(1, self.q.durable())
        ready, restart = self.h.tick()
        self.assertEqual((1, 3), (ready, restart.kind))

    def test_intermediate_unknown_frame_neither_poison_data_retry_nor_grant_authority(self):
        with self.subTest(fault='unknown_after_result'):
            root = self.initial_unknown()
            self.waiting()
            self.h.now += 20_000_000
            unknown = native.Scene(abi_version=1, struct_size=C.sizeof(native.Scene))
            self.assertEqual(1, self.h.observe_actual(unknown))
            self.assertEqual((root.job_id, 0), (self.q.cycle().job_id, self.q.cycle().pending))
            self.no_direction_or_restart()
            self.frame(self.source)
            self.assertEqual((root.job_id+1, 1), (self.q.cycle().job_id, self.q.cycle().pending))
            self.immutable_parent(root)
        for fault in ('unknown_inflight', 'item_inflight', 'gold_inflight',
                      'protection_inflight', 'unknown_then_item_inflight', 'unknown_then_deadline'):
            with self.subTest(fault=fault):
                self.setUp()
                self.frame(self.source)
                self.root = root = self.q.cycle()
                self.counts = (self.h.status().inputs, self.h.status().moves)
                value = self.producer(self.source, unknown=True)
                self.assertEqual((0, 1), (value.outcome, value.coverage))
                self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(
                    self.h.engine, root.job_id, root.capture_id, root.prefix, self.h.now))
                self.h.now += 20_000_000
                if fault == 'unknown_then_item_inflight':
                    unknown = native.Scene(abi_version=1, struct_size=C.sizeof(native.Scene))
                    self.assertEqual(1, self.h.observe_actual(unknown))
                    self.h.now += 10_000_000
                if fault in ('unknown_inflight', 'unknown_then_deadline'):
                    observed = native.Scene(abi_version=1, struct_size=C.sizeof(native.Scene))
                else:
                    changed = deepcopy(self.source)
                    if fault in ('item_inflight', 'unknown_then_item_inflight'):
                        changed.tiles[(-4, -2)] = 'floor'
                    elif fault == 'gold_inflight': changed.tiles[(-6, -1)] = 'floor'
                    else: changed.protected.add((8, 3))
                    observed = self.h.scene(2, 2, changed, beat=True)
                self.assertEqual(1, self.h.observe_actual(observed))
                self.assertEqual((root.job_id, 1), (self.q.cycle().job_id, self.q.cycle().pending))
                if fault == 'unknown_then_deadline':
                    self.old.timeout(self.q.cycle())
                else:
                    self.commit(value)
                if fault == 'unknown_inflight':
                    self.waiting()
                    self.frame(self.source)
                    self.assertEqual((root.job_id+1, 1),
                                     (self.q.cycle().job_id, self.q.cycle().pending))
                else:
                    self.frame(self.source)
                    self.assertEqual(root.job_id, self.q.cycle().job_id,
                                     'hard invalidation and pure deadline may not discard the marker')
                    self.no_direction_or_restart()
                self.immutable_parent(root)

    def test_unknown_and_deadline_retries_share_the_original_two_replacement_budget(self):
        self.initial_unknown()
        self.waiting()
        self.frame(self.source)
        first = self.q.cycle()
        self.assertEqual(1, first.pending)
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            first.job_id, first.capture_id, first.prefix, self.h.now))
        first = self.q.cycle()
        self.old.timeout(first)
        self.frame(self.source)
        second = self.q.cycle()
        self.assertEqual((first.job_id+1, 1), (second.job_id, second.pending))
        self.commit(self.producer(self.source, unknown=True))
        self.assertEqual((7, 0), (self.q.cycle().state, self.q.cycle().pending))
        self.frame(self.source)
        self.assertEqual(second.job_id, self.q.cycle().job_id, 'a third fresh retry is forbidden')
        self.immutable_parent(self.root)
        self.assertEqual(self.counts, (self.h.status().inputs, self.h.status().moves))

    def test_two_pairwise_zeros_cannot_replace_direct_original_full_proof(self):
        rng = random.Random(113440)
        other = bytes(rng.randrange(20, 100) for _ in self.source.signature)
        middle, later = deepcopy(self.source), deepcopy(self.source)
        middle.signature = bytes(round(a*.7+b*.3) for a, b in zip(self.source.signature, other))
        later.signature = bytes(round(a*.5+b*.5) for a, b in zip(self.source.signature, other))
        scenes = [self.h.scene(2, 2, value, beat=True) for value in (self.source, middle, later)]
        for first, second, expected in ((0, 1, 2), (1, 2, 2), (0, 2, 0)):
            result = Motion()
            self.assertEqual(1, self.lib.ng2_motion(C.byref(scenes[first]), C.byref(scenes[second]),
                                                  1, C.byref(result)))
            self.assertEqual((expected, 0, 0), (result.kind, result.dx, result.dy),
                             'the procedural example must expose zero non-transitivity')
        self.initial_unknown()
        self.waiting()
        self.frame(middle)
        fresh = self.q.cycle()
        self.commit(self.producer(middle, unknown=True))
        self.frame(later)
        self.assertEqual((fresh.job_id, 0), (self.q.cycle().job_id, self.q.cycle().pending),
                         'the latest pairwise zero cannot replace direct original FULL proof')
        self.no_direction_or_restart()
        self.immutable_parent(self.root)

    def test_candidates_targets_and_malformed_results_never_wait_for_absence_retry(self):
        for fault in ('candidate', 'target', 'nan', 'bad_status'):
            with self.subTest(fault=fault):
                self.setUp()
                self.frame(self.source)
                value = self.producer(self.source, unknown=True)
                if fault in ('candidate', 'target'):
                    value.outcome = 1 if fault == 'candidate' else 2
                elif fault == 'nan':
                    value.rows[0].slots[0].icon_upper_bound = float('nan')
                else:
                    value.status = 99
                self.commit(value)
                job = self.q.cycle().job_id
                self.no_direction_or_restart()
                self.frame(self.source)
                self.assertEqual(job, self.q.cycle().job_id)
                if fault in ('candidate', 'target'):
                    self.assertEqual(1, self.q.cycle().candidate_latched)

    def test_changed_item_gold_protection_motion_prefix_cancel_and_parent_cannot_rebind(self):
        for fault in ('item', 'gold', 'protection', 'motion', 'prefix', 'cancel', 'parent'):
            with self.subTest(fault=fault):
                self.setUp()
                root = self.initial_unknown()
                self.waiting()
                latest = deepcopy(self.source)
                if fault == 'item': latest.tiles[(-4, -2)] = 'floor'
                elif fault == 'gold': latest.tiles[(-6, -1)] = 'floor'
                elif fault == 'protection': latest.protected.add((8, 3))
                elif fault == 'motion': latest.signature = bytes([80])*23296
                elif fault == 'cancel': self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 2)
                elif fault == 'parent': self.h.now = root.continuation_deadline_ns+1
                start = self.h.now+10_000_000
                self.h.now = start+35_000_000
                kwargs = {'prefix': root.prefix+1} if fault == 'prefix' else {}
                self.h.observe_actual(self.h.scene(2, 2, latest, beat=True),
                    start=start, end=start+12_000_000, **kwargs)
                self.assertEqual(root.job_id, self.q.cycle().job_id)
                self.no_direction_or_restart()

    def test_only_a_definitely_unbegun_pause_can_yield_to_the_fresh_data_wait(self):
        self.frame(self.source)
        self.root = self.q.cycle()
        ready, pause = self.h.tick()
        self.assertEqual((1, 2), (ready, pause.kind))
        self.assertEqual((1, 0), (self.h.status().input_state, self.h.events()[-1].begin_ns))
        self.commit(self.producer(self.source, unknown=True))
        self.waiting()
        retired = next(e for e in self.h.events() if e.command.id == pause.id)
        self.assertEqual((3, 0), (retired.outcome, retired.begin_ns))
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, pause.id,
            max(self.h.now, pause.not_before_ns), 1, 0, 1))

    def test_a_begun_pause_is_not_withdrawn_or_replaced_by_data_retry(self):
        self.frame(self.source)
        root = self.q.cycle()
        ready, pause = self.h.tick()
        self.assertEqual((1, 2), (ready, pause.kind))
        self.h.now = max(self.h.now, pause.not_before_ns)
        self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine, pause.id,
                                                       self.h.now, 1, 0, 1))
        self.assertEqual(2, self.h.status().input_state)
        self.commit(self.producer(self.source, unknown=True))
        self.assertEqual((root.job_id, 2), (self.q.cycle().job_id, self.h.status().input_state))
        self.no_direction_or_restart()

    def test_prepared_pause_does_not_hide_inflight_hard_source_invalidation(self):
        for fault in ('item', 'gold', 'protection', 'unknown_then_item', 'only_unknown'):
            with self.subTest(fault=fault):
                self.setUp()
                self.frame(self.source)
                self.root = root = self.q.cycle()
                counts = (self.h.status().inputs, self.h.status().moves)
                value = self.producer(self.source, unknown=True)
                self.assertEqual((0, 1), (value.outcome, value.coverage))
                self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(
                    self.h.engine, root.job_id, root.capture_id, root.prefix, self.h.now))
                ready, pause = self.h.tick()
                self.assertEqual((1, 2), (ready, pause.kind))
                self.assertEqual((1, 0), (self.h.status().input_state, self.h.events()[-1].begin_ns))
                self.h.now += 10_000_000
                if fault in ('unknown_then_item', 'only_unknown'):
                    unknown = native.Scene(abi_version=1, struct_size=C.sizeof(native.Scene))
                    self.assertEqual(1, self.h.observe_actual(unknown))
                    self.h.now += 10_000_000
                if fault != 'only_unknown':
                    changed = deepcopy(self.source)
                    if fault in ('item', 'unknown_then_item'): changed.tiles[(-4, -2)] = 'floor'
                    elif fault == 'gold': changed.tiles[(-6, -1)] = 'floor'
                    else: changed.protected.add((8, 3))
                    self.assertEqual(1, self.h.observe_actual(self.h.scene(2, 2, changed, beat=True)))
                self.assertEqual((root.job_id, 1, 1),
                    (self.q.cycle().job_id, self.q.cycle().pending, self.h.status().input_state))
                self.commit(value)
                if fault == 'only_unknown':
                    self.waiting()
                    self.frame(self.source)
                    self.assertEqual((root.job_id+1, 1),
                                     (self.q.cycle().job_id, self.q.cycle().pending))
                else:
                    self.assertNotEqual(3, self.q.cycle().state,
                                        'prepared PAUSE may not conceal classified hard invalidation')
                    self.frame(self.source)
                    self.assertEqual((root.job_id, 0),
                                     (self.q.cycle().job_id, self.q.cycle().pending))
                    self.no_direction_or_restart()
                self.assertEqual(counts, (self.h.status().inputs, self.h.status().moves))
                self.immutable_parent(root)
        with self.subTest(fault='prepared_replacement_keeps_data_only_near_material_relation'):
            self.setUp()
            self.initial_unknown()
            self.waiting()
            latest = deepcopy(self.source)
            latest.tiles[(1, -1)] = 'floor'
            self.frame(latest)
            replacement = self.q.cycle()
            self.assertEqual((self.root.job_id+1, 1), (replacement.job_id, replacement.pending))
            value = self.producer(latest)
            self.assertEqual((3, 2), (value.outcome, value.coverage))
            self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
                replacement.job_id, replacement.capture_id, replacement.prefix, self.h.now))
            ready, pause = self.h.tick()
            self.assertEqual((1, 2), (ready, pause.kind))
            self.h.now += 10_000_000
            self.assertEqual(1, self.h.observe_actual(self.h.scene(2, 2, latest, beat=True)))
            self.commit(value)
            self.assertEqual((3, 0, 4),
                (self.q.cycle().outcome, self.q.cycle().status, self.q.cycle().state),
                'already admitted DATA material relation stays DATA-only valid during its prepared PAUSE')
            self.assertEqual((1, 0), (self.h.status().input_state, self.h.events()[-1].begin_ns))
            self.immutable_parent(self.root)


class NativeGoodsUpView113Tests(Goods113Base):
    def setUp(self):
        self.p = opened.NativeOpenedFade100Tests(methodName='runTest')
        self.p.lib = self.lib
        self.addCleanup(self.p.doCleanups)

    @staticmethod
    def source():
        items = {(-2, -3), (-1, -3), (0, -3)}
        tiles = {(x, y): 'floor' for x in range(-3, 2) for y in range(-5, 2)}
        for x in (-4, 2):
            for y in range(-5, -1): tiles[(x, y)] = 'gold'
        tiles[(-1, 0)] = tiles[(1, 0)] = 'gold'
        for point in items: tiles[point] = 'item'
        scene = native.textured(tiles)
        scene.goods = 'visible'
        scene.protected = set(items)
        for x, y in items:
            scene.protected.update((x+dx, y+dy) for dx, dy in native.DIRS.values())
        rng = random.Random(113003)
        scene.signature = bytes(rng.randrange(20, 240) for _ in range(23296))
        return scene

    def pending(self, *, known_moved=False, fault=None, pause_prepared=False, positive=False):
        self.h, terrain, old, _ = self.p.armed(direction=3)
        self.q = cycle.NativeCycle094Tests(methodName='runTest')
        self.q.lib, self.q.h = self.lib, self.h
        before = self.h.status()
        self.h.ack(old)
        scene = self.source()
        if fault == 'up_unknown': scene.tiles.pop((0, -1))
        elif fault == 'up_item': scene.tiles[(0, -1)] = 'item'; scene.protected.add((0, -1))
        elif fault == 'up_protected': scene.protected.add((0, -1))
        elif fault == 'extra_item': scene.tiles[(7, 3)] = 'item'; scene.protected.add((7, 3))
        elif fault == 'projection': scene.protected.discard((-2, -2))
        if known_moved:
            # A normal procedural partial response closes the actual old MOVE
            # before FULL is exposed. It is never a desired motion assignment.
            moved = native.translated(terrain, 3)
            self.h.observed_result(old, moved)
            self.assertEqual((1, 0, -1), (self.h.events()[-1].motion,
                self.h.events()[-1].dx, self.h.events()[-1].dy))
            scene.signature = moved.signature
            original_scene = self.h.scene(2, 2, terrain, beat=True)
            current_scene = self.h.scene(2, 2, scene, beat=True)
            direct = Motion()
            self.assertEqual(1, self.lib.ng2_motion(C.byref(original_scene), C.byref(current_scene),
                                                  3, C.byref(direct)))
            self.assertEqual((1, 0, -1), (direct.kind, direct.dx, direct.dy),
                             'the later FULL must remain in the already proved UP world')
        self.h.now = max(self.h.now+2, old.target_ns+100_000_000)
        self.assertEqual(1, self.h.observe_actual(self.h.scene(2, 2, scene, beat=True)))
        retired = next(e for e in self.h.events() if e.command.id == old.id)
        expected = (2, 1, 0, -1) if known_moved else (2, 0, 0, 0)
        self.assertEqual(expected, (retired.outcome, retired.motion, retired.dx, retired.dy),
                         'known ACK/FULL must not acquire an old displacement credit')
        self.assertEqual(before.moves+int(known_moved), self.h.status().moves)
        self.old, self.root, self.before_moves = old, self.q.cycle(), self.h.status().moves
        self.prepared_pause = None
        if pause_prepared:
            ready, pause = self.h.tick()
            self.assertEqual((1, 2), (ready, pause.kind))
            self.assertEqual((1, 0), (self.h.status().input_state, self.h.events()[-1].begin_ns))
            self.prepared_pause = pause
        value = self.producer(scene, left=375, sy=44, target=positive)
        if positive:
            self.assertIn(value.outcome, (1, 2), 'normal target pixels must supply the initial positive veto')
        self.commit(value)
        return scene

    def view_ticket(self, scene):
        self.assertEqual((3, 0), (self.q.cycle().state, self.q.cycle().completed_shops),
            'the observed FULL top margin needs bounded DATA/view observation, not final hold')
        replacements = 0
        for _ in range(3):
            self.h.now += 25_000_000
            self.assertEqual(1, self.h.observe_actual(self.h.scene(2, 2, scene, beat=True)))
            if not self.q.cycle().pending:
                break
            replacements += 1
            self.assertLessEqual(replacements, 2)
            value = self.producer(scene, left=375, sy=44)
            self.assertEqual(0, value.outcome)
            self.commit(value)
        self.assertEqual(0, self.q.cycle().pending)
        self.immutable_parent(self.root)
        command = self.h.next_move(scene)
        self.assertEqual((4, 3), (command.kind, command.direction))
        self.assertGreater(command.id, self.old.id)
        self.assertGreater(command.ordinal, self.old.ordinal)
        self.assertGreater(command.source_capture_id, self.root.capture_id)
        self.assertLessEqual(command.deadline_ns, self.root.continuation_deadline_ns)
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine,
            self.old.id, max(self.h.now, self.old.not_before_ns), 1, 0, 1))
        return command

    def test_known_ack_unknown_motion_gets_one_new_up_ticket_then_real_move_and_normal_negative(self):
        scene = self.pending()
        command = self.view_ticket(scene)
        self.h.ack(command)
        self.assertEqual(self.before_moves, self.h.status().moves, 'new ACK is also zero credit')
        latest = native.translated(scene, 3)
        self.h.observed_result(command, latest)
        event = next(e for e in self.h.events() if e.command.id == command.id)
        self.assertEqual((1, 0, -1), (event.motion, event.dx, event.dy))
        self.assertEqual(self.before_moves+1, self.h.status().moves)
        old = next(e for e in self.h.events() if e.command.id == self.old.id)
        self.assertEqual((0, 0, 0), (old.motion, old.dx, old.dy), 'old unproved ACK stays unproved')
        value = self.producer(latest, left=375, sy=80)
        self.assertEqual((3, 2), (value.outcome, value.coverage))
        self.commit(value)
        self.assertEqual((3, 4), (self.q.cycle().outcome, self.q.cycle().state))
        self.immutable_parent(self.root)

    def test_up_observation_needs_positive_floor_exact_projection_and_single_shop(self):
        for fault in ('up_unknown', 'up_item', 'up_protected', 'extra_item', 'projection'):
            with self.subTest(fault=fault):
                self.setUp()
                scene = self.pending(fault=fault)
                for _ in range(3):
                    self.no_direction_or_restart()
                    self.h.now += 25_000_000
                    self.h.observe_actual(self.h.scene(2, 2, scene, beat=True))
                    if self.q.cycle().pending:
                        self.commit(self.producer(scene, left=375, sy=44))
                self.no_direction_or_restart()
                self.assertEqual(self.before_moves, self.h.status().moves)

    def test_a_prior_real_up_move_keeps_its_single_credit_while_the_new_view_is_independent(self):
        scene = self.pending(known_moved=True)
        command = self.view_ticket(scene)
        prior = next(e for e in self.h.events() if e.command.id == self.old.id)
        self.assertEqual((1, 0, -1), (prior.motion, prior.dx, prior.dy))
        self.h.ack(command)
        self.assertEqual(self.before_moves, self.h.status().moves)
        self.h.observed_result(command, native.translated(scene, 3))
        self.assertEqual(self.before_moves+1, self.h.status().moves)
        self.immutable_parent(self.root)

    def test_prepared_pause_cannot_replace_cached_prior_move_source_or_ordinal(self):
        scene = self.pending(known_moved=True, pause_prepared=True)
        pause = self.prepared_pause
        command = self.view_ticket(scene)
        retired = next(e for e in self.h.events() if e.command.id == pause.id)
        self.assertEqual((3, 0, 0), (retired.outcome, retired.begin_ns, retired.command.ordinal))
        self.assertGreater(command.id, pause.id)
        self.assertGreater(command.ordinal, self.old.ordinal)
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, pause.id,
            max(self.h.now, pause.not_before_ns), 1, 0, 1))
        self.h.ack(command)
        self.assertEqual(self.before_moves, self.h.status().moves)
        self.h.observed_result(command, native.translated(scene, 3))
        self.assertEqual(self.before_moves+1, self.h.status().moves)
        self.immutable_parent(self.root)

    def test_later_up_ticket_needs_unchanged_original_material_and_direct_zero(self):
        for fault in ('near_material', 'item', 'gold', 'protection', 'motion'):
            with self.subTest(fault=fault):
                self.setUp()
                scene = self.pending()
                self.assertEqual(3, self.q.cycle().state)
                later = deepcopy(scene)
                if fault == 'near_material': later.tiles[(1, -1)] = 'dirt'
                elif fault == 'item': later.tiles[(-2, -3)] = 'floor'
                elif fault == 'gold': later.tiles[(-4, -4)] = 'floor'
                elif fault == 'protection': later.protected.add((8, 3))
                elif fault == 'motion': later.signature = bytes([80])*23296
                for _ in range(4):
                    self.h.now += 25_000_000
                    self.h.observe_actual(self.h.scene(2, 2, later, beat=True))
                    self.no_direction_or_restart()
                self.assertEqual(self.before_moves, self.h.status().moves)
                self.immutable_parent(self.root)

    def test_unknown_after_actual_new_up_does_not_restore_the_single_view_allowance(self):
        scene = self.pending()
        command = self.view_ticket(scene)
        self.h.ack(command)
        latest = native.translated(scene, 3)
        self.h.observed_result(command, latest)
        self.assertEqual(self.before_moves+1, self.h.status().moves)
        value = self.producer(latest, left=375, sy=80, unknown=True)
        self.assertEqual((0, 1), (value.outcome, value.coverage))
        self.commit(value)
        for _ in range(4):
            self.h.now += 25_000_000
            self.h.observe_actual(self.h.scene(2, 2, latest, beat=True))
            self.no_direction_or_restart()
        self.assertEqual(self.before_moves+1, self.h.status().moves)
        self.immutable_parent(self.root)

    def test_existing_entry_episode_cannot_gain_an_independent_third_up_allowance(self):
        episode = entry.NativeEntryEpisode102Tests(methodName='runTest')
        episode.lib = self.lib
        episode.fresh()
        self.addCleanup(episode.doCleanups)
        terrain, opening = episode.a.pending(items={(-2, -4), (-1, -4), (0, -4)})
        parent = episode.a.admitted()
        episode.original_inputs, episode.original_moves = episode.h.status().inputs, episode.h.status().moves
        episode.opening, episode.parent = opening, parent
        first = episode.ticket(terrain)
        latest = episode.moved(terrain, first, goods='visible')
        self.h, self.q = episode.h, episode.q
        self.assertEqual((first.id, 1), (self.q.cycle().prefix, self.q.cycle().pending))
        value = self.producer(latest, left=375, sy=44)
        self.assertEqual((0, 1), (value.outcome, value.coverage))
        self.commit(value)
        # The established episode may retain its own second input. FULL view
        # admission must not add a separate third observation allowance.
        second = None
        until = parent.continuation_deadline_ns+native.PERIOD
        while self.h.now <= until:
            self.h.now += 25_000_000
            self.h.observe(self.h.scene(2, 2, latest, beat=True))
            ready, command = self.h.tick()
            if ready and command.kind == 4:
                self.assertIsNone(second, 'existing entry never acquires an extra independent UP')
                self.assertEqual(3, command.direction)
                second = command
                self.h.ack(command)
                latest = native.translated(latest, 3)
                self.h.observed_result(command, latest)
                if self.q.cycle().pending:
                    self.commit(self.producer(latest, left=375, sy=80, unknown=True))
            self.assertLessEqual(self.h.status().inputs, episode.original_inputs+2)
            self.assertLessEqual(self.h.status().moves, episode.original_moves+2)
            episode.bounded()

    def test_unknown_synth_is_never_reinterpreted_as_known_visual_unknown(self):
        self.h, _, old, _ = self.p.armed(direction=3)
        self.h.now = max(self.h.now, old.not_before_ns)
        self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine, old.id,
                                                       self.h.now, 1, 0, 1))
        self.h.now += 1
        self.assertEqual(1, self.lib.ng2_controller_complete(self.h.engine, old.id,
                                                          self.h.now, -1))
        self.assertEqual(4, self.h.status().input_state)
        self.h.now += 100_000_000
        self.h.observe_actual(self.h.scene(2, 2, self.source(), beat=True))
        self.assertEqual(4, self.h.status().input_state)
        ready, command = self.h.tick()
        self.assertFalse(ready and command.kind in (3, 4))

    def test_up_view_normal_positive_candidate_preempts_initial_observation(self):
        self.pending(positive=True)
        self.assertEqual(1, self.q.cycle().candidate_latched)
        self.no_direction_or_restart()


if __name__ == '__main__':
    unittest.main()
