"""TEST109 same-open PARTIAL palette changes through public C callbacks.

TEST108/a782's original234->236 and244->246 keep the opening, protected
merchandise and immediate walking footprint while distant unprotected
UNKNOWN/FLOOR/DIRT labels fluctuate. Procedural texture/clocks exercise the
classification -> independent zero -> future ticket -> ACK contract here.
These later responses are not missing iPhone frames or device acceptance.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import unittest

from tests import test_native_controller as native
from tests import test_native_partial_refresh104 as refresh


class NativePartialRemote109Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = native.CORE
        try:
            frozen = os.environ.get('NECRO_TEST109_CONTROLLER_CORE')
            if frozen:
                native.CORE = Path(frozen)
            refresh.NativePartialRefresh104Tests.setUpClass.__func__(cls)
        finally:
            native.CORE = previous

    tearDownClass = classmethod(refresh.NativePartialRefresh104Tests.tearDownClass.__func__)
    setUp = refresh.NativePartialRefresh104Tests.setUp
    fresh = refresh.NativePartialRefresh104Tests.fresh
    choice = refresh.NativePartialRefresh104Tests.choice
    motion = refresh.NativePartialRefresh104Tests.motion
    counts = refresh.NativePartialRefresh104Tests.counts
    cross = staticmethod(refresh.NativePartialRefresh104Tests.cross)

    def pending(self, *, direction=1, mask=True, opened=True, rail_cut=None, mutate_assessment=None):
        # The row is still clipped; seven ITEM cells are Perception's
        # conservative projection, not seven registered physical products.
        flip = 1 if direction == 1 else -1
        items = {(flip*x, 2) for x in range(-7, 0)}
        cells = {point: 'item' for point in items}
        cells.update({(flip*10, 1): 'floor', (flip*4, 2): 'floor'})
        cells.update({(flip*-7, y): 'gold' for y in range(-2, 2) if y != rail_cut})
        protection = set().union(*(self.cross(point) for point in items)) if mask else items
        source, opening = self.p.pending(direction=direction, opened=opened,
            extra=cells, protected=protection, mutate_assessment=mutate_assessment)
        self.assertEqual((direction, 5, *native.DIRS[direction], 1), self.choice(source))
        return source, opening

    @staticmethod
    def changed(source, *, direction=1, variant=0):
        flip = 1 if direction == 1 else -1
        latest = deepcopy(source)
        if variant == 0:
            latest.tiles[(flip*8, 1)] = 'dirt'
            latest.tiles[(flip*9, 1)] = 'floor'
            latest.tiles.pop((flip*10, 1), None)
        else:
            latest.tiles[(flip*4, 2)] = 'dirt'
            latest.tiles[(flip*-3, -1)] = 'dirt'
        return latest

    def quiet(self, source, latest):
        before = self.q.cycle()
        counts = self.counts()
        self.assertEqual(self.choice(source), self.choice(latest))
        self.assertEqual((2, 0, 0), self.motion(source, latest, self.choice(source)[0]))
        self.assertEqual(1, self.p.observe(latest))
        current = self.q.cycle()
        self.assertEqual((before.job_id, before.capture_id, before.prefix,
                          before.continuation_deadline_ns),
            (current.job_id, current.capture_id, current.prefix, current.continuation_deadline_ns),
            'same opened merchandise source must not restart classification for distant palette labels')
        self.assertEqual((0, 0, 0, 0),
            (current.state, current.pending, current.completed_shops, current.candidate_latched))
        self.assertEqual(counts, self.counts(), 'a stationary comparison is no movement credit')
        return before

    def not_quiet(self, source, latest):
        old = self.q.cycle()
        counts = self.counts()
        self.p.observe(latest)
        current = self.q.cycle()
        self.assertFalse(current.state == 0 and current.job_id == old.job_id,
                         'this observation cannot keep the old partial movement credit')
        self.assertEqual(counts, self.counts())
        ready, command = self.h.tick()
        self.assertFalse(ready and command.kind in (3, 4))

    def test_remote_palette_keeps_classified_anchor_then_future_entry_ack(self):
        for direction in (1, 2):
            with self.subTest(direction=direction):
                self.fresh()
                source, opening = self.pending(direction=direction)
                frozen = deepcopy(source)
                latest = self.changed(source, direction=direction)
                old = self.quiet(source, latest)
                another = self.changed(source, direction=direction, variant=1)
                self.quiet(source, another)
                command = self.h.next_move(another)
                self.assertEqual((4, direction), (command.kind, command.direction))
                self.assertGreater(command.id, opening.id)
                self.assertGreater(command.source_capture_id, old.capture_id)
                self.assertGreater(command.target_ns, self.h.now + 50_000_000)
                self.assertLessEqual(command.deadline_ns, old.continuation_deadline_ns)
                before = self.h.status()
                self.h.ack(command)
                self.assertEqual((before.inputs+1, before.moves),
                    (self.h.status().inputs, self.h.status().moves), 'ACK is not displacement')
                moved = native.translated(another, direction)
                self.h.observed_result(command, moved)
                event = next(e for e in self.h.events() if e.command.id == command.id)
                self.assertEqual((2, 1, *native.DIRS[direction]),
                    (event.outcome, event.motion, event.dx, event.dy))
                self.assertEqual(before.moves+1, self.h.status().moves)
                self.assertEqual((frozen.tiles, frozen.protected, frozen.signature),
                                 (source.tiles, source.protected, source.signature))

    def test_reserved_palette_observation_keeps_original_ticket_and_deadline(self):
        source, _ = self.pending()
        old = self.quiet(source, self.changed(source))
        command = self.h.next_move(self.changed(source))
        before_event = next(e for e in self.h.events() if e.command.id == command.id)
        self.quiet(source, self.changed(source, variant=1))
        self.assertEqual(1, self.h.status().input_state)
        latest = next(e for e in self.h.events() if e.command.id == command.id)
        self.assertEqual(bytes(before_event.command), bytes(latest.command))
        self.assertEqual((0, 0), (latest.begin_ns, latest.outcome))
        self.assertEqual(old.continuation_deadline_ns, self.q.cycle().continuation_deadline_ns)
        self.h.ack(command)

    def test_nearby_material_and_each_protected_role_cannot_use_remote_palette(self):
        faults = ('origin', 'destination', 'near_origin', 'near_destination',
                  'gold', 'item', 'protection', 'new_item', 'new_door', 'new_stone')
        for fault in faults:
            with self.subTest(fault=fault):
                self.fresh()
                source, _ = self.pending()
                latest = self.changed(source)
                point = {'origin': (0, 0), 'destination': (-1, 0),
                    'near_origin': (1, 1), 'near_destination': (-2, -1),
                    'gold': (-1, -1), 'item': (-5, 2)}.get(fault)
                if point:
                    latest.tiles[point] = 'dirt' if source.tiles.get(point) != 'dirt' else 'floor'
                elif fault == 'protection':
                    latest.protected.discard((-5, 2))
                else:
                    latest.tiles[(8, 1)] = fault.removeprefix('new_')
                    if fault == 'new_item':
                        latest.protected.update(self.cross((8, 1)))
                self.not_quiet(source, latest)

    def test_actual_opening_exact_mask_and_binary_safe_result_are_required(self):
        for fault in ('no_opening', 'bad_mask', 'word_positive'):
            with self.subTest(fault=fault):
                self.fresh()
                def unsafe(value):
                    value.partial[0].word_present = 1
                    value.partial[0].word_iou, value.partial[0].word_coverage = .83, .95
                source, _ = self.pending(opened=fault != 'no_opening', mask=fault != 'bad_mask',
                    mutate_assessment=unsafe if fault == 'word_positive' else None)
                self.not_quiet(source, self.changed(source))

    def test_each_independent_outer_wall_cell_and_horizontal_opening_are_required(self):
        for cut in (-2, -1, 0, 1):
            with self.subTest(missing_outer_wall_cell=cut):
                self.fresh()
                source, _ = self.pending(rail_cut=cut)
                self.not_quiet(source, self.changed(source))
        self.fresh()
        source, _ = self.pending(direction=3)
        self.not_quiet(source, self.changed(source))

    def test_target_candidate_or_invalid_frame_never_create_observation_credit(self):
        for fault in ('target', 'candidate', 'state', 'prefix', 'unstable', 'replay'):
            with self.subTest(fault=fault):
                self.fresh()
                def positive(value):
                    value.outcome = 1 if fault == 'target' else 2
                source, _ = self.pending(mutate_assessment=positive
                    if fault in ('target', 'candidate') else None)
                old, counts = self.q.cycle(), self.counts()
                if fault in ('target', 'candidate'):
                    self.assertEqual((1, 1), (old.candidate_latched, old.completed_shops))
                    self.not_quiet(source, self.changed(source))
                    continue
                self.h.now += 10_000_000
                frame = self.h.scene(2, 2, self.changed(source), beat=True)
                if fault == 'state': frame.state = 0
                options = {'prefix': self.h.prefix+1} if fault == 'prefix' else {}
                if fault == 'unstable': options['stable'] = 0
                if fault == 'replay': options['number'] = self.h.number
                self.h.observe(frame, **options)
                self.assertNotEqual(0, self.q.cycle().state)
                self.assertEqual(counts, self.counts())
                ready, command = self.h.tick()
                self.assertFalse(ready and command.kind in (3, 4))

    def test_unknown_intermediate_pair_never_bridges_the_frozen_motion_proof(self):
        source, _ = self.pending()
        old = self.q.cycle()
        latest = self.changed(source)
        latest.signature = bytes([80])*23296
        self.assertNotEqual((2, 0, 0), self.motion(source, latest, 1))
        for _ in range(2):
            self.assertEqual(1, self.p.observe(latest))
            self.assertEqual((old.job_id, old.capture_id, 3),
                (self.q.cycle().job_id, self.q.cycle().capture_id, self.q.cycle().state))
            ready, command = self.h.tick()
            self.assertFalse(ready and command.kind in (3, 4))

    def test_original_deadline_and_cancel_bound_remote_palette_credit(self):
        for fault in ('deadline', 'cancel'):
            with self.subTest(fault=fault):
                self.fresh()
                source, _ = self.pending()
                old = self.quiet(source, self.changed(source))
                counts = self.counts()
                if fault == 'deadline':
                    self.h.now = old.continuation_deadline_ns + 1
                else:
                    self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 18)
                ready, command = self.h.tick()
                self.assertFalse(ready and command.kind in (3, 4))
                self.assertEqual(counts, self.counts())
                self.assertNotEqual(0, self.h.status().reason)


if __name__ == '__main__':
    unittest.main()
