"""TEST103 plural fixed-world zero evidence inside a public unsent wait.

All maps, signatures and later captures are procedural. A known completed MOVE
and an actually unbegun next ticket establish Controller ownership. Numeric
evidence qualifies zero only; it does not rewrite Motion or create input credit.
"""
import ctypes as C
from copy import deepcopy
import math
import random
from unittest.mock import patch
import unittest

from tests import test_native_controller as fixture
from tests import test_native_clear_stationary095 as clear095
from tests import test_native_passage072 as passage

def room_phase_pair(scene):
    """Render the same fixed material with two lighting phases, never motion.

    The all-FLOOR scalar fixture's islands could fall on this room's UNKNOWN
    exterior. Only island placement changes: every chosen center has the exact
    21 observed, UI-free derivative dependencies used by world_kernel_known.
    Seeds, grain, 17 islands per original band, intensity ranges, lighting and
    independent noise remain fixed. No matcher result selects their positions.
    """
    width, height = 224, 104

    def world_mask(x, y):
        return (40 <= x < 179 and 20 <= y < 85
                and not (103 <= x < 122 and 43 <= y < 61)
                and not (101 <= x < 123 and y >= 80))

    def known_kernel(x, y):
        for oy in range(-2, 3):
            for ox in range(-2, 3):
                if abs(ox) == 2 and abs(oy) == 2:
                    continue
                xx, yy = x + ox, y + oy
                if not world_mask(xx, yy):
                    return False
                # Numerators are positive throughout world_mask, so // is
                # exactly C's integer division before the tile-origin offset.
                ax, ay = (4 * xx - 34) // 36 - 11, (4 * yy - 9) // 36 - 5
                if not (-11 <= ax <= 11 and -5 <= ay <= 4):
                    return False
                cell = (ay + 5) * 23 + ax + 11
                if scene.tiles[cell] not in (1, 2, 3, 4) or scene.protected_cells[cell]:
                    return False
        return True

    rng = random.Random(85085)
    world = [rng.randrange(14, 35) for _ in range(width * height)]
    for lower, upper in ((23, 34), (68, 80)):
        domain = [(x, y) for y in range(lower, upper) for x in range(44, 174)
                  if known_kernel(x, y)]
        rng.shuffle(domain)
        islands = []
        for x, y in domain:
            if all(max(abs(x - px), abs(y - py)) >= 5 for px, py in islands):
                islands.append((x, y))
                if len(islands) == 17:
                    break
        if len(islands) != 17:
            raise AssertionError('the procedural observed band must fit 17 separated fixed islands')
        for x, y in islands:
            world[y * width + x] = rng.randrange(160, 200)
    before = bytes(max(7, min(255, round(value +
        36 * (1 + math.sin(2 * math.pi * (i % width) / 48)))))
        for i, value in enumerate(world))
    noise = random.Random(85086)
    after = bytes(max(7, min(255, round(value +
        36 * (1 + math.sin(2 * math.pi * ((i % width) - 1) / 48))) + noise.randrange(-17, 18)))
        for i, value in enumerate(world))
    return before, after


class NativePluralWait103Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        clear095.NativeClearStationary095Tests.setUpClass.__func__(cls)
        cls.lib.ng2_clear_plural_stationary_zero.argtypes = [C.POINTER(fixture.Scene),
            C.POINTER(fixture.Scene), C.c_int32]
        cls.lib.ng2_clear_plural_stationary_zero.restype = C.c_int32

    tearDownClass = classmethod(clear095.NativeClearStationary095Tests.tearDownClass.__func__)

    def plural_wait(self):
        # Two old stones lie off the route and outside the fixed HUD. A lower
        # left corner at (-2,2) would enter the heart mask after LEFT+UP, so the
        # second old landmark is the already observed remote (-5,-2) instead.
        # The public planner/MOVED callbacks choose the local LEFT/UP route.
        room = passage.passage_room(mouth=(-2, -3))
        room.tiles[(-5, -2)] = room.tiles[(2, 2)] = 'stone'
        with patch.object(passage, 'passage_room', return_value=room):
            terrain, second = self.armed('passage')
        self.assertIn(second.direction, (1, 3))
        self.ack(second)
        terrain = fixture.translated(terrain, second.direction)
        self.now = max(self.now, second.target_ns + 80_000_002)
        self.assertEqual(1, self.observe(terrain))
        self.assertEqual((2, 2, 1),
            (self.status().inputs, self.status().moves, self.status().lead_confirmed))
        self.verified_ns = self.now
        before, after = deepcopy(terrain), deepcopy(terrain)
        before.signature, after.signature = room_phase_pair(self.frame(terrain))
        self.now += 10_000_000
        self.assertEqual(1, self.observe(before))
        old = passage.NativePassage072Tests.next_move(self, before)
        self.assertIn(old.direction, (1, 3))
        self.assertEqual((0, 0, 0), self.motion(before, after, old.direction),
                         'normal global motion must independently remain UNKNOWN')
        self.assertEqual((2, 0, 0), self.motion(after, after, old.direction))
        a, b = self.frame(before), self.frame(after)
        self.assertEqual(bytes(a.tiles), bytes(b.tiles))
        self.assertEqual(bytes(a.protected_cells), bytes(b.protected_cells))
        self.assertGreaterEqual(list(a.tiles).count(3), 2)
        self.assertEqual(0, self.lib.ng2_clear_singleton_stationary_zero(
            C.byref(a), C.byref(b), old.direction), 'the old singleton proof stays inapplicable')
        self.assertEqual(1, self.lib.ng2_clear_plural_stationary_zero(
            C.byref(a), C.byref(b), old.direction),
            'the separate numeric proof must qualify the public fixture before adoption: '
            f'world={(self.status().x, self.status().y)}, '
            f'stones={sorted(p for p, kind in before.tiles.items() if kind == "stone")}')
        self.parent_deadline = min(old.source_start_ns + 3 * fixture.SECOND,
            old.phase_sample_ns + 3 * fixture.SECOND, self.verified_ns + 12 * fixture.SECOND,
            self.status().walk_started_ns + 45 * fixture.SECOND,
            self.status().started_ns + 180 * fixture.SECOND)
        self.original_period = self.status().beat_period_ns
        self.saved_credit = self.credit()
        self.saved_position = (self.status().x, self.status().y)
        self.now = old.deadline_ns - 30_000_000
        self.trigger_commit = self.trigger_end = self.now
        self.wait_deadline = min(self.parent_deadline, self.now + 2 * self.original_period)
        self.assertEqual(1, self.observe(after))
        self.trigger_id = self.number
        self.assert_waiting(old)
        return before, after, old

    def test_plural_zero_retires_old_id_then_rearms_only_an_independent_future_ticket(self):
        for cycle in (False, True):
            with self.subTest(cycle=cycle):
                self.fresh_engine()
                if cycle:
                    self.engine = self.lib.ng2_controller_create_cycle(fixture.SECOND)
                    self.addCleanup(self.lib.ng2_controller_destroy, self.engine)
                _, after, old = self.plural_wait()
                anchor_id, completed = old.source_capture_id, self.status().last_completed_id
                self.now += 20_000_000
                self.assertEqual(1, self.observe(after))
                new = self.future_ticket(after)
                self.assertGreater(new.id, old.id)
                self.assertGreater(new.target_ns, old.target_ns)
                self.assertEqual(old.direction, new.direction)
                self.assertGreater(new.source_capture_id, self.trigger_id)
                self.assertEqual((2, 2, completed),
                    (self.status().inputs, self.status().moves, self.status().last_completed_id),
                    'the rearmed ticket has no synth or displacement credit')
                self.assertEqual(self.saved_position, (self.status().x, self.status().y))
                self.assertLessEqual(new.deadline_ns + self.status().lead_ns + 50_000_000,
                                     self.parent_deadline)
                self.assertLessEqual(self.recovery().schedule_deadline_ns, self.parent_deadline)
                old_event = next(e for e in self.events() if e.command.id == old.id)
                self.assertEqual((anchor_id, 0, 3),
                    (old_event.command.source_capture_id, old_event.begin_ns, old_event.outcome))
                self.assertEqual(bytes(old), bytes(old_event.command))
                self.reject_old_callbacks_without_mutation(old)
                self.ack(new)
                self.assertEqual((3, 2), (self.status().inputs, self.status().moves),
                    'only the new future ticket can acquire synth ACK; ACK still is not movement')

    def test_plural_proof_needs_independent_stable_current_prefix_capture(self):
        for fault in ('prefix', 'unstable', 'id', 'overlap'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                _, after, old = self.plural_wait()
                self.now += 20_000_000
                options = ({'prefix': self.prefix - 1} if fault == 'prefix' else
                           {'stable': 0} if fault == 'unstable' else
                           {'number': self.trigger_id} if fault == 'id' else
                           {'start': self.trigger_end - 1})
                result = self.observe(after, **options)
                if fault != 'overlap':
                    self.assertEqual(0, result)
                ready, command = self.tick()
                self.assertFalse(ready and command.kind == 4)
                self.assertEqual((2, 2, *self.saved_position),
                    (self.status().inputs, self.status().moves, self.status().x, self.status().y))
                self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, old.id,
                    old.not_before_ns, 1, 0, 1))
                self.assertEqual(0, self.preparation_epoch(old))

    def test_changed_old_stone_material_protection_or_near_floor_cannot_reuse_plural_zero(self):
        for fault in ('old_stone_loss', 'origin', 'target', 'protected', 'item', 'gold'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                before, after, old = self.plural_wait()
                changed = deepcopy(after)
                if fault == 'old_stone_loss':
                    stone = next(p for p, kind in before.tiles.items() if kind == 'stone')
                    changed.tiles[stone] = 'floor'
                elif fault == 'origin':
                    changed.tiles[(0, 0)] = 'dirt'
                elif fault == 'target':
                    changed.tiles[fixture.DIRS[old.direction]] = 'dirt'
                elif fault == 'protected':
                    changed.protected.add((1, 0))
                elif fault == 'item':
                    changed.tiles[(-8, 2)] = 'item'
                else:
                    changed.tiles[(-8, 2)] = 'gold'
                    changed.gold.add((-8, 2))
                a, b = self.frame(before), self.frame(changed)
                self.assertEqual(0, self.lib.ng2_clear_plural_stationary_zero(
                    C.byref(a), C.byref(b), old.direction))
                self.now += 20_000_000
                self.observe(changed)
                ready, command = self.tick()
                self.assertFalse(ready and command.kind == 4)
                self.assertEqual((2, 2, *self.saved_position),
                    (self.status().inputs, self.status().moves, self.status().x, self.status().y))
                self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, old.id,
                    old.not_before_ns, 1, 0, 1))

    def test_original_wait_and_parent_equalities_never_renew_from_plural_proof(self):
        for issued in (False, True):
            for extra in (0, 1):
                with self.subTest(issued=issued, extra=extra):
                    self.fresh_engine()
                    _, after, old = self.plural_wait()
                    if issued:
                        new = self.future_ticket(after)
                        self.assertLessEqual(new.deadline_ns + self.status().lead_ns + 50_000_000,
                                             self.parent_deadline)
                    self.now = (self.parent_deadline if issued else self.wait_deadline) + extra
                    self.observe(after)
                    self.assertEqual((8, 2, 2),
                        (self.status().reason, self.status().inputs, self.status().moves))
                    ready, command = self.tick()
                    self.assertFalse(ready and command.kind == 4)
                    self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, old.id,
                        old.not_before_ns, 1, 0, 1))

    def test_cancel_or_unknown_synth_cannot_reuse_the_plural_wait(self):
        for fault in ('cancel_wait', 'cancel_issued', 'unknown_sent'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                _, after, old = self.plural_wait()
                new = self.future_ticket(after) if fault != 'cancel_wait' else None
                if fault == 'unknown_sent':
                    self.now = max(self.now, new.not_before_ns)
                    self.assertEqual(1, self.lib.ng2_controller_begin(self.engine, new.id,
                        self.now, 1, 0, 1))
                    self.now += 1
                    self.assertEqual(1, self.lib.ng2_controller_complete(self.engine, new.id, self.now, -1))
                    self.assertEqual(4, self.status().input_state)
                else:
                    self.lib.ng2_controller_cancel(self.engine, self.now, 2)
                self.now += 10_000_000
                self.observe(after)
                self.assertEqual((3 if fault == 'unknown_sent' else 2, 2),
                                 (self.status().inputs, self.status().moves))
                self.assertEqual(self.saved_position, (self.status().x, self.status().y))
                self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, old.id,
                    old.not_before_ns, 1, 0, 1))
                if new:
                    self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, new.id,
                        new.not_before_ns, 1, 0, 1))
                ready, command = self.tick()
                self.assertFalse(ready and command.kind == 4)

    def test_known_zero_keeps_old_route_but_nonzero_or_failed_motion_never_falls_back(self):
        before, _, old = self.plural_wait()
        self.assertEqual((2, 0, 0), self.motion(before, before, old.direction))
        a = self.frame(before)
        self.assertEqual(0, self.lib.ng2_clear_plural_stationary_zero(
            C.byref(a), C.byref(a), old.direction), 'strict BLOCKED uses the existing route directly')
        new = self.future_ticket(before)
        self.assertGreater(new.id, old.id)
        self.assertEqual((2, 2), (self.status().inputs, self.status().moves))
        # Explicit one-call result selection checks the guard independently;
        # every unarmed call still uses the actual unchanged C motion matcher.
        self.selected_motion()
        for stage in ('observe', 'begin'):
            for result, kind, dx, dy in ((1, 1, 0, -1), (1, 3, 0, 0),
                                        (1, 4, 1, 0), (0, 0, 0, 0)):
                with self.subTest(stage=stage, result=result, kind=kind):
                    self.lib.test_motion_reset()
                    self.fresh_engine()
                    _, after, old = self.plural_wait()
                    new = self.future_ticket(after) if stage == 'begin' else None
                    self.lib.test_motion_once(1, result, kind, dx, dy)
                    if stage == 'observe':
                        self.now += 20_000_000
                        self.observe(after)
                    else:
                        self.now = max(self.now, new.not_before_ns)
                        self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, new.id,
                            self.now, 1, 0, 1))
                    self.assertEqual((2, 2), (self.status().inputs, self.status().moves))
                    self.assertEqual(0, self.preparation_epoch(old))
                    ready, command = self.tick()
                    self.assertFalse(ready and command.kind == 4)


# Explicit public harness delegation avoids inheriting/discovering old tests or
# invoking the singleton fixture, whose scalar proof expectation is different.
for _name in ('setUp', 'scene', 'frame', 'observe', 'observe_actual', 'tick', 'status',
              'events', 'ack', 'fit', 'next_move', 'publish_procedural_candidate',
              'fresh_engine', 'recovery', 'recovery_samples', 'all_public_bytes',
              'reject_old_callbacks_without_mutation', 'motion_wait', 'credit',
              'choice', 'observed_vantage', 'observed_result', 'preparation_epoch',
              'armed', 'motion', 'assert_waiting', 'future_ticket', 'selected_motion'):
    setattr(NativePluralWait103Tests, _name,
            getattr(clear095.NativeClearStationary095Tests, _name))

NativePluralWait103Tests.next_operation = passage.NativePassage072Tests.next_operation

if __name__ == '__main__':
    unittest.main()
