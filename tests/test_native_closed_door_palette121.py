"""TEST121 closed-door quiet permission through one blocking corner.

Public C normal fit/ACK/MOVED earns ownership. Maps, grayscale fields, HUD
clocks and successor frames are procedural semantic cases. The original
3a4a125/126 raw guard cut is separate; unexported six-step private state and
missing phone successors are not reconstructed here.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import random
import unittest

from tests import test_native_controller as native
from tests import test_native_route_observation120 as route


CORE = Path(os.environ.get('NECRO121_CLOSED_CORE', native.CORE))


class NativeClosedDoorPalette121Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = route.CORE
        try:
            route.CORE = CORE
            route.NativeRouteObservation120Tests.setUpClass.__func__(cls)
        finally:
            route.CORE = previous

    tearDownClass = classmethod(native.NativeControllerTests.tearDownClass.__func__)
    for _method in ('setUp', 'fresh_engine', 'frame', 'scene', 'observe', 'tick',
        'status', 'events', 'ack', 'fit', 'next_move', 'motion_wait', 'preparation_epoch',
        'publish_procedural_candidate', 'scene_changes', 'scene_details', 'credit',
        'direct_motion', 'shop_choice', 'recovery', 'recovery_samples', 'all_public_bytes',
        'reject_old_callbacks_without_mutation'):
        locals()[_method] = getattr(route.NativeRouteObservation120Tests, _method)

    @staticmethod
    def rotate(point, turns):
        x, y = point
        for _ in range(turns):
            x, y = -y, x
        return x, y

    def closed_ticket(self, turns=0, side=1, source_corner='dirt', far_blocker=False):
        # The exact original remote (8,2) is covered in the unrotated case.
        # Other rotations use a bounded far cell that stays in all four ROIs.
        far = (8, 2) if turns == 0 else (4, 3)
        tiles = {(0, 0): 'floor', (1, 0): 'floor', (-1, 0): 'door',
            (-1, -1): 'gold', (-1, 1): 'gold', (1, -1): source_corner,
            (1, 1): source_corner, (1, 2): 'dirt', far: 'floor', (3, 4): 'dirt'}
        if far_blocker:
            tiles[(-3, 4)] = 'dirt'
        rotated = {self.rotate(point, turns): kind for point, kind in tiles.items()}
        direction = next(d for d, unit in native.DIRS.items() if unit == self.rotate((-1, 0), turns))
        dx, dy = native.DIRS[direction]
        initial = native.textured({(x+dx, y+dy): kind for (x, y), kind in rotated.items()})
        self.fit(initial)
        first = self.next_move(initial)
        self.assertEqual(direction, first.direction)
        self.ack(first)
        before = native.translated(initial, direction)
        self.assertEqual(rotated, before.tiles)
        self.now = max(self.now+2, first.target_ns+80_000_002)
        self.observe(before)
        self.assertEqual((0, 1, 1), (self.status().reason, self.status().inputs, self.status().moves))
        old = self.next_move(before)
        self.assertEqual((direction, 5, dx, dy, 5), self.shop_choice(before))
        self.assertEqual(direction, old.direction)
        after = deepcopy(before)
        after.tiles[self.rotate((1, side), turns)] = 'stone' if source_corner=='dirt' else 'dirt'
        after.tiles[self.rotate((1, 2), turns)] = 'stone'
        after.tiles[self.rotate(far, turns)] = 'dirt'
        after.tiles[self.rotate((3, 4), turns)] = 'floor'
        self.assertEqual(self.shop_choice(before), self.shop_choice(after))
        self.assertEqual((2, 0, 0), self.direct_motion(before, after, direction))
        return before, after, old

    def retain(self, before, after, old):
        event = bytes(self.events()[-1])
        credit = self.credit()
        epoch = self.preparation_epoch(old)
        wait = bytes(self.motion_wait())
        self.assertNotEqual(0, epoch)
        self.now += 2
        self.observe(after)
        self.assertEqual((0, 1, old.id), (self.status().reason,
            self.status().input_state, self.status().current_command_id),
            'one behind-corner blocking refinement must keep the original closed-door ticket')
        # A published pending ID is not published a second time by tick.
        self.assertEqual(0, self.tick()[0])
        current = self.events()[-1].command
        self.assertEqual(bytes(old), bytes(current))
        self.assertEqual(event, bytes(self.events()[-1]))
        self.assertEqual(wait, bytes(self.motion_wait()))
        self.assertEqual(epoch, self.preparation_epoch(current))
        self.assertEqual(credit, self.credit())
        return current

    def test_unstarted_closed_door_keeps_same_id_source_bounds_and_zero_move_credit(self):
        for turns in range(4):
            for side in (-1, 1):
                with self.subTest(turns=turns, side=side):
                    self.fresh_engine()
                    before, after, old = self.closed_ticket(turns, side)
                    self.retain(before, after, old)
                    self.ack(old)
                    self.assertEqual((2, 1, 0), (self.status().inputs,
                        self.status().moves, self.status().door_changes), 'ACK is not opening or movement')
                    opened = deepcopy(after)
                    opened.tiles[native.DIRS[old.direction]] = 'floor'
                    self.assertEqual((3, 0, 0), self.direct_motion(before, opened, old.direction))
                    self.now = max(self.now+2, old.target_ns+80_000_002)
                    self.observe(opened)
                    self.assertEqual((0, 2, 1, 1), (self.status().reason,
                        self.status().inputs, self.status().moves, self.status().door_changes))
                    event = next(e for e in self.events() if e.command.id==old.id)
                    self.assertEqual((2, 3, 0, 0), (event.outcome, event.motion, event.dx, event.dy))

    def test_near_admission_rejects_extra_corners_traversal_goods_and_protection(self):
        for fault in ('both_corners', 'wrong_corner', 'floor', 'unknown', 'reverse',
                      'lost_door', 'lost_gold', 'item', 'protected', 'goods'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                before, after, old = self.closed_ticket(source_corner='stone' if fault=='reverse' else 'dirt')
                credit = self.credit()
                if fault == 'both_corners': after.tiles[(1, -1)] = 'stone'
                elif fault == 'wrong_corner':
                    after.tiles[(1, 1)] = 'dirt'; after.tiles[(0, 1)] = 'stone'
                elif fault == 'floor': after.tiles[(1, 1)] = 'floor'
                elif fault == 'unknown': del after.tiles[(1, 1)]
                elif fault == 'reverse':
                    self.assertEqual('stone', before.tiles[(1, 1)])
                    self.assertEqual('dirt', after.tiles[(1, 1)])
                elif fault == 'lost_door': after.tiles[(-1, 0)] = 'dirt'
                elif fault == 'lost_gold':
                    after.tiles[(-1, -1)] = 'dirt'; after.gold.remove((-1, -1))
                elif fault == 'item': after.tiles[(1, 1)] = 'item'
                elif fault == 'protected': after.protected.add((1, 1))
                else: after.goods = 'partial'
                self.now += 2
                self.observe(after)
                self.assertEqual(credit, self.credit())
                self.assertFalse(self.status().input_state==1 and self.status().current_command_id==old.id
                    and self.status().reason==0, 'the new near rule cannot retain unsafe material')

    def test_direct_zero_full_choice_and_current_prefix_are_required(self):
        for fault in ('unknown_motion', 'tween', 'unit', 'changed_choice', 'prefix', 'unstable'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                before, after, old = self.closed_ticket()
                credit = self.credit()
                kwargs = {}
                if fault == 'unknown_motion': after.signature = bytes([80])*23296
                elif fault in ('tween', 'unit'):
                    after.signature = native.translated(before, old.direction,
                        amount=1 if fault=='tween' else 9).signature
                elif fault == 'changed_choice':
                    after.tiles[(-1, 0)] = 'floor'
                    self.assertNotEqual(self.shop_choice(before), self.shop_choice(after))
                elif fault == 'prefix': kwargs['prefix'] = self.prefix+9
                else: kwargs['stable'] = 0
                accepted = self.status().last_capture_id
                self.now += 2
                self.observe(after, **kwargs)
                self.assertEqual(credit, self.credit())
                if fault in ('prefix', 'unstable'):
                    self.assertEqual(accepted, self.status().last_capture_id)
                else:
                    self.assertFalse(self.status().input_state==1 and self.status().reason==0
                        and self.status().current_command_id==old.id)

    def test_original_D_actual_commit_and_external_owner_guards_remain(self):
        for fault in ('before', 'equal', 'after', 'commit_after', 'foreground', 'locked', 'owner'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                before, after, old = self.closed_ticket()
                if fault in ('before', 'equal', 'after', 'commit_after'):
                    self.now = old.deadline_ns+({'before': -1, 'equal': 0,
                        'after': 1, 'commit_after': 1}[fault])
                    kwargs = {'start': old.deadline_ns-3, 'end': old.deadline_ns-1} if fault=='commit_after' else {}
                    self.observe(after, **kwargs)
                    if fault in ('before', 'equal'):
                        self.assertEqual((0, 1, old.id), (self.status().reason,
                            self.status().input_state, self.status().current_command_id))
                        self.assertEqual(bytes(old), bytes(self.events()[-1].command))
                        self.assertEqual(0, self.tick()[0])
                    else:
                        self.assertEqual(0, self.lib.ng2_controller_begin(self.engine,
                            old.id, self.now, 1, 0, 1))
                else:
                    self.retain(before, after, old)
                    self.now = old.not_before_ns
                    self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, old.id,
                        self.now, int(fault!='foreground'), int(fault=='locked'), int(fault!='owner')))
                self.assertEqual(1, self.status().moves)

    def test_started_ACK_unknown_and_original_visual_parent_do_not_gain_authority(self):
        for stage in ('begun', 'ACK', 'unknown'):
            with self.subTest(stage=stage):
                self.fresh_engine()
                before, after, old = self.closed_ticket()
                self.now = old.not_before_ns
                self.assertEqual(1, self.lib.ng2_controller_begin(self.engine,
                    old.id, self.now, 1, 0, 1))
                if stage != 'begun':
                    self.now += 1
                    self.assertEqual(1, self.lib.ng2_controller_complete(self.engine,
                        old.id, self.now, 1 if stage=='ACK' else -1))
                    if stage == 'ACK': self.prefix = old.id
                self.now += 2
                self.observe(after)
                self.assertEqual(0, self.lib.ng2_controller_begin(self.engine,
                    old.id, self.now, 1, 0, 1))
                self.assertEqual(1, self.status().moves)
                if stage == 'unknown': self.assertEqual(4, self.status().input_state)
        for late in (False, True):
            with self.subTest(parent_late=late):
                self.fresh_engine()
                before, after, old = self.closed_ticket()
                parent = self.motion_wait().deadline_ns
                self.retain(before, after, old)
                self.ack(old)
                self.assertEqual(parent, self.motion_wait().deadline_ns)
                opened = deepcopy(after); opened.tiles[native.DIRS[old.direction]] = 'floor'
                self.now = parent+(1 if late else 0)
                self.observe(opened)
                self.assertEqual(1, self.status().moves)
                self.assertEqual(0 if late else 1, self.status().door_changes)

    def test_old_far_quiet_and_unknown_gate_refit_keep_existing_qualification(self):
        before, after, old = self.closed_ticket()
        after.tiles[(1, 1)] = 'dirt'
        self.retain(before, after, old)
        self.fresh_engine()
        before, after, old = self.closed_ticket(far_blocker=True)
        after = deepcopy(before); after.tiles[(-3, 4)] = 'stone'
        rng = random.Random(121081)
        after.signature = bytes(rng.randrange(20, 100) for _ in after.signature)
        self.assertEqual((0, 0, 0), self.direct_motion(before, after, old.direction))
        self.assertEqual((2, 0, 0), self.direct_motion(after, after, old.direction))
        self.now += 2
        self.observe(after)
        self.assertEqual((0, 0), (self.status().reason, self.status().input_state),
            'the old UNKNOWN gate must still retire into its separate refit')
        self.assertEqual(1, self.recovery().post_move_reacquisitions)
        self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, old.id,
            old.not_before_ns, 1, 0, 1))


if __name__ == '__main__':
    unittest.main()
