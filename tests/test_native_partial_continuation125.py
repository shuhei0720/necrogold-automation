"""TEST125 material and conservative top-alias continuation, public C callbacks.

TEST124 d301/122->124 and 8831/135->137 supply the changed material/role
conditions. Textures, prior callback scenes, normal typed worker control
packets and future responses below are procedural models, not phone frames.
No private Controller flags or missing historic DATA counters are injected.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import tempfile
import unittest

from tests import test_native_controller as native
from tests import test_native_partial_refresh104 as refresh
from tests import test_native_partial_remote109 as remote
from tests import test_native_cycle094 as cycle
from tests import test_native_offer_controller105 as offers_controller
from tests import test_native_offer_coverage104 as offers
from tests import test_native_ring_bank094 as bank
from tests import test_native_partial_entry097 as entry
from tests import test_native_current_view114 as runtime
from tests import test_native_irregular110 as irregular


class NativePartialContinuation125Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = native.CORE
        try:
            frozen = os.environ.get('NECRO_TEST125_PARTIAL_CORE')
            if frozen:
                native.CORE = Path(frozen)
            refresh.NativePartialRefresh104Tests.setUpClass.__func__(cls)
            cls.lib.ng2_controller_enable_irregular.argtypes = [C.c_void_p]
            cls.lib.ng2_controller_enable_restart_yield.argtypes = [C.c_void_p]
            cls.lib.ng2_controller_observe_irregular_at.argtypes = [C.c_void_p,
                C.POINTER(native.Scene), C.POINTER(irregular.Observation),
                *([C.c_uint64]*4), C.c_int32, C.c_uint64]
        finally:
            native.CORE = previous

    tearDownClass = classmethod(refresh.NativePartialRefresh104Tests.tearDownClass.__func__)
    setUp = refresh.NativePartialRefresh104Tests.setUp
    fresh = refresh.NativePartialRefresh104Tests.fresh
    choice = refresh.NativePartialRefresh104Tests.choice
    motion = refresh.NativePartialRefresh104Tests.motion
    counts = refresh.NativePartialRefresh104Tests.counts
    cross = staticmethod(refresh.NativePartialRefresh104Tests.cross)

    def runtime_fresh(self):
        self.driver = runtime.current_view_fixture(self.lib)
        self.addCleanup(self.driver.doCleanups)
        self.h = self.driver.harness()
        self.q = cycle.NativeCycle094Tests('runTest')
        self.q.lib, self.q.h = self.lib, self.h
        self.p = entry.NativePartialEntry097Tests('runTest')
        self.p.lib, self.p.h, self.p.q = self.lib, self.h, self.q
        self.entrance = None

    def normal_packet(self, rgba, scene):
        if not hasattr(self, 'ring'):
            temporary = tempfile.TemporaryDirectory(prefix='partial-continuation125-ring-')
            self.addCleanup(temporary.cleanup)
            self.ring = bank.NativeRingBank094Tests.build_library(
                native.CORE/'NG2Ring.c', Path(temporary.name)/'ring.so')
        code, value = offers.normal_assess(self.ring, rgba, scene, mode=2)
        self.assertEqual((0, 0), (code, value.status))
        return value

    def preserve_normal_packet(self, target, normal):
        started, finished = target.started_ns, target.finished_ns
        original = cycle.Result.from_buffer_copy(bytes(normal))
        C.memmove(C.byref(target), C.byref(normal), C.sizeof(target))
        target.started_ns, target.finished_ns = started, finished
        copied = cycle.Result.from_buffer_copy(bytes(target))
        original.started_ns = original.finished_ns = 0
        copied.started_ns = copied.finished_ns = 0
        self.assertEqual(bytes(original), bytes(copied),
                         'only the explicitly modeled worker clock may differ from the normal producer')

    def source(self, *, empty, extra=None, mutate=None, admitted=True, normal=False):
        # Perception's two conservative rows describe possible goods. They
        # are not ten registered shop items and must remain the old anchor.
        left = -3 if empty else -1
        items = {(x, y) for x in range(left, left+5) for y in (-5, -4)}
        mask = set().union(*(self.cross(point) for point in items))
        mask = {point for point in mask if -11 <= point[0] <= 11 and -5 <= point[1] <= 4}
        cells = {point: 'item' for point in items}
        cells.update({(-1 if not empty else 1, -3): 'gold',
                      (-1 if not empty else 1, -2): 'gold',
                      (5, 4): 'dirt' if empty else 'unknown',
                      (7, 4): 'unknown' if empty else 'stone'})
        cells.update(extra or {})
        cells = {point: kind for point, kind in cells.items() if kind != 'unknown'}
        def assessment(value):
            if normal:
                pixels = offers.shop_pixels(left=411, sy=-24 if empty else 12,
                                           faces=(None, (-15, -14, 30, 29)))
                packet = self.normal_packet(pixels, self.h._last_fixture_scene)
                self.assertEqual((0, 1, 0, 0 if empty else 3, 0 if empty else 1),
                    (packet.outcome, packet.coverage, packet.row_count,
                     packet.partial_count, packet.partial_safe_no_positive))
                self.preserve_normal_packet(value, packet)
            if mutate:
                mutate(value)
        terrain, opening = self.p.pending(direction=3, extra=cells,
            protected=mask, safe_slots=not empty, mutate_assessment=assessment)
        terrain.gold = {point for point, kind in terrain.tiles.items() if kind == 'gold'}
        self.assertEqual((3, 5, 0, -1, 1), self.choice(terrain))
        state = self.q.cycle()
        if admitted:
            self.assertEqual((3, 0, 0, 0, 1, 0),
                (state.state, state.pending, state.status, state.outcome,
                 state.coverage, state.completed_shops))
        self.assertEqual((2, 1, 1),
            (self.h.status().inputs, self.h.status().moves, self.h.status().door_changes))
        return terrain, opening

    @staticmethod
    def floor_revelation(source):
        current = deepcopy(source)
        current.tiles.pop((5, 4), None)
        current.tiles[(7, 4)] = 'floor'
        return current

    @staticmethod
    def supported_contraction(source):
        current = deepcopy(source)
        for x, kind in zip(range(-1, 4), ('gold', 'unknown', 'dirt', 'floor', 'unknown')):
            if kind == 'unknown':
                current.tiles.pop((x, -5), None)
            else:
                current.tiles[(x, -5)] = kind
        current.protected.difference_update({(-2, -5), (4, -5)})
        current.tiles[(7, 4)] = 'dirt'
        current.gold = {point for point, kind in current.tiles.items() if kind == 'gold'}
        return current

    def unchanged_authority(self, source, current):
        before, counts = self.q.cycle(), self.counts()
        frozen = dict(source.tiles), set(source.gold), set(source.protected), source.signature
        self.assertEqual(self.choice(source), self.choice(current))
        self.assertEqual((2, 0, 0), self.motion(source, current, 3))
        self.assertEqual(1, self.p.observe(current))
        latest = self.q.cycle()
        self.assertEqual((0, 0, 0, 0),
            (latest.state, latest.pending, self.h.status().reason, self.h.status().terminal),
            'independent strict zero with preserved old potential must continue after opening')
        self.assertEqual((before.job_id, before.capture_id, before.prefix,
                          before.deadline_ns, before.continuation_deadline_ns),
            (latest.job_id, latest.capture_id, latest.prefix,
             latest.deadline_ns, latest.continuation_deadline_ns),
            'static material/role comparison cannot renew a job, source or clock')
        self.assertEqual(counts, self.counts(), 'a stationary proof is not a walking unit')
        self.assertEqual(frozen, (source.tiles, source.gold, source.protected, source.signature))
        return before

    def test_empty_up_framing_remote_unknown_floor_keeps_original_authority(self):
        source, _ = self.source(empty=True)
        self.unchanged_authority(source, self.floor_revelation(source))

    def test_supported_top_gold_contraction_keeps_larger_original_potential(self):
        source, _ = self.source(empty=False)
        current = self.supported_contraction(source)
        old_items = {p for p, kind in source.tiles.items() if kind == 'item'}
        new_items = {p for p, kind in current.tiles.items() if kind == 'item'}
        self.assertLess(new_items, old_items)
        self.assertLess(current.protected, source.protected)
        self.assertLessEqual(source.gold, current.gold)
        self.assertTrue(current.gold-source.gold <= old_items)
        self.unchanged_authority(source, current)

    def test_supported_contraction_uses_observed_rail_not_the_recorded_column(self):
        source, _ = self.source(empty=False,
            extra={(2, y): 'gold' for y in (-3, -2, -1)})
        current = self.supported_contraction(source)
        current.tiles.pop((-1, -5), None)
        current.tiles[(2, -5)] = 'gold'
        current.gold = {point for point, kind in current.tiles.items() if kind == 'gold'}
        self.assertEqual({(2, -5)}, current.gold-source.gold)
        self.unchanged_authority(source, current)

    def test_both_relations_share_observe_search_reserved_and_begin(self):
        for empty in (True, False):
            for stage in ('observe', 'search', 'reserved'):
                with self.subTest(empty=empty, stage=stage):
                    self.fresh()
                    source, opening = self.source(empty=empty)
                    current = (self.floor_revelation(source) if empty
                               else self.supported_contraction(source))
                    if stage != 'observe':
                        self.assertEqual(1, self.p.observe(source))
                    command = self.h.next_move(source) if stage == 'reserved' else None
                    old = self.unchanged_authority(source, current)
                    if command is None:
                        command = self.h.next_move(current)
                    ticket = bytes(command)
                    self.assertEqual((4, 3), (command.kind, command.direction))
                    self.assertGreater(command.id, opening.id)
                    self.assertLessEqual(command.deadline_ns, old.continuation_deadline_ns)
                    # New post-reservation images recheck the original source.
                    while self.h.now < command.not_before_ns:
                        self.h.now += min(20_000_000, command.not_before_ns-self.h.now)
                        self.assertEqual(1, self.h.observe(self.h.scene(2, 2, current, beat=True)))
                    event = next(e for e in self.h.events() if e.command.id == command.id)
                    self.assertEqual((ticket, 0, 0), (bytes(event.command), event.begin_ns, event.outcome))
                    before = self.counts()
                    self.h.ack(command)
                    self.assertEqual((before[0]+1, before[1]), self.counts()[:2], 'ACK is not a unit')
                    self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine,
                        command.id, self.h.now, 1, 0, 1), 'a begun ticket cannot be resent')
                    moved = native.translated(current, 3)
                    self.h.observed_result(command, moved)
                    event = next(e for e in self.h.events() if e.command.id == command.id)
                    self.assertEqual((1, 0, -1), (event.motion, event.dx, event.dy))
                    self.assertEqual((before[0]+1, before[1]+1), self.counts()[:2])
                    self.assertEqual(1, self.q.cycle().pending, 'one real unit needs a new normal assessment')

    def test_remote_revealed_floor_is_shared_with_clean_horizontal_partial(self):
        for direction in (1, 2):
            for point in ((8, 1), (-9, 4)):
                with self.subTest(direction=direction, point=point):
                    self.fresh()
                    source, _ = remote.NativePartialRemote109Tests.pending(self, direction=direction)
                    current = deepcopy(source); current.tiles[point] = 'floor'
                    self.assertEqual(self.choice(source), self.choice(current))
                    self.assertEqual((2, 0, 0), self.motion(source, current, direction))
                    old, before = self.q.cycle(), self.counts()
                    self.assertEqual(1, self.p.observe(current))
                    self.assertEqual((0, old.job_id, old.capture_id, old.continuation_deadline_ns),
                        (self.q.cycle().state, self.q.cycle().job_id, self.q.cycle().capture_id,
                         self.q.cycle().continuation_deadline_ns))
                    self.assertEqual(before, self.counts())

    def assert_no_old_move(self, source, current, **options):
        old, before = self.q.cycle(), self.counts()
        self.p.observe(current, **options)
        self.assertFalse(self.q.cycle().state == 0 and self.q.cycle().job_id == old.job_id,
                         'this change cannot retain the old continuation')
        self.assertEqual(before, self.counts())
        ready, command = self.h.tick()
        self.assertFalse(ready and command.kind in (3, 4))

    def test_contraction_keeps_support_lower_goods_masks_and_material_boundaries(self):
        for fault in ('source_rail', 'current_rail', 'old_gold', 'lower_item', 'new_item',
                      'mask_loss', 'mask_growth', 'margin_material', 'unsupported_gold',
                      'ordinary_gold', 'origin', 'destination', 'motion', 'unknown_motion'):
            with self.subTest(fault=fault):
                self.fresh()
                source, _ = self.source(empty=False,
                    extra={(-1, -2): 'floor'} if fault == 'source_rail' else None)
                current = self.supported_contraction(source)
                if fault == 'current_rail': current.tiles[(-1, -2)] = 'floor'
                elif fault == 'old_gold': current.tiles[(1, -1)] = 'floor'
                elif fault == 'lower_item': current.tiles[(0, -4)] = 'floor'
                elif fault == 'new_item':
                    current.tiles[(8, 3)] = 'item'; current.protected.update(self.cross((8, 3)))
                elif fault == 'mask_loss': current.protected.discard((0, -3))
                elif fault == 'mask_growth': current.protected.add((10, 3))
                elif fault == 'margin_material': current.tiles[(-2, -5)] = 'floor'
                elif fault == 'unsupported_gold': current.tiles[(2, -5)] = 'gold'
                elif fault == 'ordinary_gold': current.tiles[(8, 4)] = 'gold'
                elif fault == 'origin': current.tiles[(0, 0)] = 'dirt'
                elif fault == 'destination': current.tiles[(0, -1)] = 'dirt'
                elif fault == 'motion': current.signature = native.translated(source, 3).signature
                elif fault == 'unknown_motion': current.signature = bytes([80])*23296
                self.assert_no_old_move(source, current)

    def test_remote_permission_does_not_add_unknown_dirt_stone_or_local_floor(self):
        for empty in (True, False):
            for point, material, protected in (((7, 4), 'dirt', False), ((7, 4), 'stone', False),
                    ((1, 0), 'floor', False), ((0, -2), 'floor', True),
                    ((7, 4), 'floor', True)):
                with self.subTest(empty=empty, point=point, material=material, protected=protected):
                    self.fresh()
                    # This test's changed cell begins UNKNOWN; the source
                    # deliberately does not inherit 8831's remote STONE.
                    source, _ = self.source(empty=empty, extra={(7, 4): 'unknown'})
                    current = deepcopy(source); current.tiles[point] = material
                    if protected: current.protected.add(point)
                    if point == (1, 0):
                        # Revealing an origin-neighbor unknown is not an
                        # ordinary far material permission.
                        self.assertNotIn(point, source.tiles)
                    self.assert_no_old_move(source, current)

    def test_release_prefix_candidate_word_deadline_and_owner_still_bound_both(self):
        for empty in (True, False):
            for fault in ('release', 'prefix', 'candidate', 'target', 'word',
                          'deadline', 'cancel', 'foreground', 'locked', 'owner'):
                with self.subTest(empty=empty, fault=fault):
                    self.fresh()
                    def mutate(value):
                        if fault in ('candidate', 'target'):
                            value.outcome = 2 if fault == 'target' else 1
                        elif fault == 'word':
                            value.partial_count = value.partial_safe_no_positive = 1
                            value.partial[0].icon_score = value.partial[0].icon_upper_bound = .1
                            value.partial[0].icon_score_exact = 1
                            value.partial[0].word_present = 1
                            value.partial[0].word_iou, value.partial[0].word_coverage = .83, .95
                    source, _ = self.source(empty=empty, mutate=mutate,
                        admitted=fault not in ('candidate', 'target', 'word'))
                    current = (self.floor_revelation(source) if empty
                               else self.supported_contraction(source))
                    if fault == 'release':
                        self.assert_no_old_move(source, current, start=self.q.cycle().release_after_ns-1)
                    elif fault == 'prefix':
                        self.assert_no_old_move(source, current, prefix=self.h.prefix+1)
                    elif fault in ('candidate', 'target', 'word'):
                        self.assert_no_old_move(source, current)
                    elif fault in ('deadline', 'cancel'):
                        if fault == 'deadline': self.h.now = self.q.cycle().continuation_deadline_ns+1
                        else: self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 2)
                        self.assert_no_old_move(source, current)
                    else:
                        self.unchanged_authority(source, current)
                        command = self.h.next_move(current); self.h.now = command.not_before_ns
                        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, command.id,
                            self.h.now, int(fault != 'foreground'), int(fault == 'locked'), int(fault != 'owner')))

    def test_normal_unknown_independent_up_unit_and_new_normal_negative_reach_restart(self):
        for empty in (True, False):
            with self.subTest(empty=empty):
                self.fresh()
                source, _ = self.source(empty=empty, normal=True)
                current = (self.floor_revelation(source) if empty
                           else self.supported_contraction(source))
                old = self.unchanged_authority(source, current)
                command = self.h.next_move(current)
                self.assertEqual((4, 3), (command.kind, command.direction))
                self.assertLessEqual(command.deadline_ns, old.continuation_deadline_ns)
                # Declared later Perception model: a real UP resolves the
                # larger conservative projection to three observed products.
                # Preserve every translated actual GOLD, including the rail
                # and the supported contraction, rather than erase obstacles
                # to force a pixel certificate.
                full = native.translated(current, 3)
                actual_gold = {p for p, kind in full.tiles.items() if kind == 'gold'}
                left = -2 if empty else 0
                items = {(x, -3) for x in range(left, left+3)}
                for point, kind in list(full.tiles.items()):
                    if kind == 'item' and point not in items:
                        full.tiles[point] = 'floor'
                for x, y in items:
                    full.tiles[(x, y)] = 'item'
                    full.tiles[(x, y+1)] = 'floor'
                for x in (left-1, left+3):
                    full.tiles[(x, -3)] = 'floor'
                full.protected = set().union(*(self.cross(point) for point in items))
                full.goods = 'visible'
                self.assertLessEqual(actual_gold, {p for p, kind in full.tiles.items() if kind == 'gold'})
                self.assertEqual((1, 0, -1), self.motion(current, full, 3))
                before = self.counts()
                self.h.ack(command)
                self.assertEqual((before[0]+1, before[1]), self.counts()[:2])
                self.h.observed_result(command, full)
                self.assertEqual((before[0]+1, before[1]+1), self.counts()[:2])
                job = self.q.cycle()
                self.assertEqual((old.job_id+1, 1, command.id, 0),
                    (job.job_id, job.pending, job.prefix, job.partial))
                # Keep both actual faces below the pause HUD at these
                # declared columns; an occluded sign remains UNKNOWN.
                packet = self.normal_packet(offers.shop_pixels(left=447+36*left, sy=60),
                                            self.h._last_fixture_scene)
                self.assertEqual((3, 2, 22),
                    (packet.outcome, packet.coverage, packet.certificate.policy_version))
                def normal_negative(value):
                    self.preserve_normal_packet(value, packet)
                self.q.assess(3, 2, normal_negative)
                offers_controller.NativeOfferController105Tests.restart_after_durable_intent(self, job)

    def test_runtime_profile_preserves_reserved_ticket_and_earned_zero_at_begin(self):
        for empty in (True, False):
            with self.subTest(empty=empty):
                self.runtime_fresh()
                source, _ = self.source(empty=empty, normal=True)
                current = (self.floor_revelation(source) if empty
                           else self.supported_contraction(source))
                original = self.unchanged_authority(source, current)
                command = self.h.next_move(current)
                ticket = bytes(command)
                before = self.counts()
                while self.h.now < command.not_before_ns:
                    self.h.now += min(20_000_000, command.not_before_ns-self.h.now)
                    self.assertEqual(1, self.h.observe(self.h.scene(2, 2, current, beat=True)))
                self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine, command.id,
                    self.h.now, 1, 0, 1))
                self.assertEqual(before, self.counts())
                event = next(e for e in self.h.events() if e.command.id == command.id)
                self.assertEqual(ticket, bytes(event.command))
                self.assertEqual((original.job_id, original.capture_id, original.continuation_deadline_ns),
                    (self.q.cycle().job_id, self.q.cycle().capture_id, self.q.cycle().continuation_deadline_ns))
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, command.id,
                    self.h.now, 1, 0, 1))
                self.h.now += 1
                self.assertEqual(1, self.lib.ng2_controller_complete(self.h.engine,
                    command.id, self.h.now, -1))
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, command.id,
                    self.h.now, 1, 0, 1), 'UNKNOWN synth does not renew a static proof or resend')


if __name__ == '__main__':
    unittest.main()
