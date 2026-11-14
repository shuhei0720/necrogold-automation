"""TEST100 cycle-only opened-entry wall relabel, public C boundaries.

TEST099's232->233 supplied a remote bracketed DOOR->GOLD difference after a
real opened-gate ACK. Textures, clocks, prior responses and future input here
are procedural; this does not reproduce unrecorded iPhone arrival.
"""
import ctypes as C
from copy import deepcopy
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests import test_native_opened_entry093 as opened
from tests import test_native_observation072 as observation


class NativeOpenedFade100Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cycle.NativeCycle094Tests.setUpClass()
        cls.lib = cycle.NativeCycle094Tests.lib
        cls.lib.ng2_controller_create_cycle.argtypes = [C.c_uint64]
        cls.lib.ng2_controller_create_cycle.restype = C.c_void_p
        cls.lib.ng2_controller_observe_at.argtypes = [
            *cls.lib.ng2_controller_observe.argtypes, C.c_uint64]
        cls.lib.ng2_choose.argtypes = [C.POINTER(native.Scene), C.c_int32, C.c_int32,
            C.POINTER(C.c_uint16), C.c_size_t, C.POINTER(observation.Entrance),
            C.POINTER(observation.Decision)]
        cls.lib.ng2_motion.argtypes = [C.POINTER(native.Scene), C.POINTER(native.Scene),
            C.c_int32, C.POINTER(observation.Motion)]

    @classmethod
    def tearDownClass(cls):
        cycle.NativeCycle094Tests.tearDownClass()

    def harness(self, cycle_profile=True):
        # Borrow mechanics explicitly, without inheriting or discovering the
        # old test methods. Select the real constructor before any observation.
        h = opened.NativeOpenedEntry093Tests(methodName='runTest')
        h.lib = self.lib
        h.now = native.SECOND + 100_000_000
        h.number = h.prefix = 0
        create = self.lib.ng2_controller_create_cycle if cycle_profile else self.lib.ng2_controller_create
        h.engine = create(native.SECOND)
        self.assertTrue(h.engine)
        self.addCleanup(self.lib.ng2_controller_destroy, h.engine)
        return h

    def armed(self, direction=1, cycle_profile=True, actual_opening=True,
              bracketed=True, protected_remote=False, source_item=False, reserve=True):
        h = self.harness(cycle_profile)
        rotate = {1: lambda x, y: (x, y), 2: lambda x, y: (-x, -y),
                  3: lambda x, y: (-y, x), 4: lambda x, y: (y, -x)}[direction]
        final = {(0, 0): 'floor', (-1, 0): 'door' if actual_opening else 'floor',
                 (-1, -1): 'gold', (-1, 1): 'gold', (-2, 0): 'dirt',
                 (-3, 0): 'floor', (-3, 1): 'door', (-4, 1): 'gold',
                 (-2, 1): 'gold' if bracketed else 'dirt',
                 (-4, -2): 'stone', (5, 1): 'stone', (8, 2): 'stone', (5, 3): 'gold'}
        if source_item:
            final[(7, 3)] = 'item'
        dx, dy = native.DIRS[direction]
        tiles = {(rotate(x, y)[0] + dx, rotate(x, y)[1] + dy): kind
                 for (x, y), kind in final.items()}
        tiles[(0, 0)] = 'floor'
        terrain = native.textured(tiles)
        remote = rotate(-3, 1)
        if protected_remote:
            terrain.protected.add((remote[0] + dx, remote[1] + dy))
        if source_item:
            item = rotate(7, 3)
            terrain.protected.add((item[0] + dx, item[1] + dy))
        h.fit(terrain)
        first = h.next_move(terrain)
        self.assertEqual(direction, first.direction)
        h.ack(first)
        terrain = native.translated(terrain, direction)
        h.observed_result(first, terrain)
        if actual_opening:
            opening = h.next_move(terrain)
            self.assertEqual(direction, opening.direction)
            h.ack(opening)
            terrain = deepcopy(terrain)
            terrain.tiles[native.DIRS[direction]] = 'floor'
            h.observed_result(opening, terrain)
            self.assertEqual((1, 1, 3), (h.status().moves, h.status().door_changes,
                                       h.events()[-1].motion))
        else:
            self.assertEqual((1, 0), (h.status().moves, h.status().door_changes))
        command = h.next_move(terrain) if reserve else None
        if command:
            self.assertEqual((direction, 5, dx, dy, 1), h.choice(terrain))
            self.assertEqual(0, h.events()[-1].begin_ns)
        return h, terrain, command, remote

    def latest(self, terrain, remote):
        changed = deepcopy(terrain)
        changed.tiles[remote] = 'gold'
        return changed

    def observe_latest(self, h, changed, old, **kwargs):
        h.now = max(h.now + 2, old.not_before_ns - 44_000_000)
        return h.observe_actual(h.scene(2, 2, changed, beat=True), **kwargs)

    def assert_no_fresh(self, h, old, counts):
        self.assertEqual(counts, (h.status().inputs, h.status().moves, h.status().door_changes))
        self.assertNotEqual(12, h.scene_details()[-1].validation if h.scene_details() else 0)
        self.assertEqual(0, self.lib.ng2_controller_begin(h.engine, old.id,
            max(h.now, old.not_before_ns), 1, 0, 1))

    def test_cycle_remote_bracketed_door_to_gold_keeps_fresh_frozen_entry(self):
        for direction in (1, 2, 3, 4):
            with self.subTest(direction=direction):
                h, terrain, old, remote = self.armed(direction)
                changed = self.latest(terrain, remote)
                self.assertEqual(h.choice(terrain), h.choice(changed))
                self.assertEqual((2, 0, 0), h.motion(terrain, changed, direction))
                counts = (h.status().inputs, h.status().moves, h.status().door_changes)
                epoch = h.preparation_epoch(old)
                self.assertEqual(1, self.observe_latest(h, changed, old))
                self.assertEqual((0, 0), (h.status().reason, h.status().terminal),
                    'cycle opened entry must retain permission through remote bracketed DOOR->GOLD')
                self.assertEqual(counts, (h.status().inputs, h.status().moves, h.status().door_changes))
                retired = next(e for e in h.events() if e.command.id == old.id)
                self.assertEqual((3, 17, 0, bytes(old)),
                    (retired.outcome, retired.reason, retired.begin_ns, bytes(retired.command)))
                new = h.next_move(changed)
                self.assertGreater(new.id, old.id)
                self.assertEqual((old.target_ns, old.not_before_ns, old.deadline_ns, old.ordinal),
                    (new.target_ns, new.not_before_ns, new.deadline_ns, new.ordinal))
                self.assertGreater(new.source_capture_id, old.source_capture_id)
                self.assertEqual(epoch, h.preparation_epoch(new))
                self.assertEqual(12, h.scene_details()[-1].validation)
                self.assertEqual(0, self.lib.ng2_controller_begin(h.engine, old.id, h.now, 1, 0, 1))

    def test_legacy_profile_does_not_gain_remote_door_relabel_permission(self):
        h, terrain, old, remote = self.armed(cycle_profile=False)
        counts = (h.status().inputs, h.status().moves, h.status().door_changes)
        self.observe_latest(h, self.latest(terrain, remote), old)
        self.assert_no_fresh(h, old, counts)

    def test_remote_relabel_requires_real_same_direction_opening(self):
        h, terrain, old, remote = self.armed(actual_opening=False)
        counts = (h.status().inputs, h.status().moves, h.status().door_changes)
        self.observe_latest(h, self.latest(terrain, remote), old)
        self.assert_no_fresh(h, old, counts)

    def test_other_direction_opening_does_not_authorize_this_entry(self):
        h, terrain, _, remote = self.armed(reserve=False)
        # The LEFT opening is real. A separately observed RIGHT floor gate
        # gets a fresh normal ticket, without inheriting that LEFT ACK.
        terrain = deepcopy(terrain)
        terrain.tiles[(-1, 0)] = 'stone'
        terrain.tiles[(-1, -1)] = terrain.tiles[(-1, 1)] = 'stone'
        terrain.tiles.update({(1, 0): 'floor', (1, -1): 'gold', (1, 1): 'gold'})
        h.now += 2
        self.assertEqual(1, h.observe_actual(h.scene(2, 2, terrain, beat=True)))
        old = h.next_move(terrain)
        self.assertEqual((2, 5, 1, 0, 1), h.choice(terrain))
        self.assertEqual(2, old.direction)
        counts = (h.status().inputs, h.status().moves, h.status().door_changes)
        self.observe_latest(h, self.latest(terrain, remote), old)
        self.assert_no_fresh(h, old, counts)

    def test_remote_relabel_requires_observed_gold_bracket_and_no_protection(self):
        for fault in ('missing_bracket', 'old_protected', 'new_protected'):
            with self.subTest(fault=fault):
                h, terrain, old, remote = self.armed(bracketed=fault != 'missing_bracket',
                    protected_remote=fault == 'old_protected')
                changed = self.latest(terrain, remote)
                if fault == 'new_protected':
                    changed.protected.add(remote)
                counts = (h.status().inputs, h.status().moves, h.status().door_changes)
                self.observe_latest(h, changed, old)
                self.assert_no_fresh(h, old, counts)

    def test_nearby_material_or_old_gold_item_loss_are_not_remote_permission(self):
        for fault in ('near_origin', 'next_floor', 'old_gold', 'old_item', 'new_item', 'motion'):
            with self.subTest(fault=fault):
                h, terrain, old, remote = self.armed(source_item=fault == 'old_item')
                changed = self.latest(terrain, remote)
                if fault == 'near_origin': changed.tiles[(1, 1)] = 'dirt'
                elif fault == 'next_floor': changed.tiles[(-1, 0)] = 'gold'
                elif fault == 'old_gold': changed.tiles[(5, 3)] = 'floor'
                elif fault == 'old_item': changed.tiles[(7, 3)] = 'floor'
                elif fault == 'new_item':
                    changed.tiles[(7, 3)] = 'item'; changed.protected.add((7, 3))
                elif fault == 'motion': changed.signature = native.translated(terrain, 1).signature
                counts = (h.status().inputs, h.status().moves, h.status().door_changes)
                self.observe_latest(h, changed, old)
                self.assert_no_fresh(h, old, counts)

    def test_prefix_deadline_and_cancel_do_not_create_new_entry_authority(self):
        for fault in ('prefix', 'deadline', 'cancel'):
            with self.subTest(fault=fault):
                h, terrain, old, remote = self.armed()
                changed = self.latest(terrain, remote)
                counts = (h.status().inputs, h.status().moves, h.status().door_changes)
                if fault == 'prefix':
                    fields = ('current_command_id', 'input_state', 'last_completed_id', 'x', 'y',
                              'inputs', 'moves', 'reason')
                    before = tuple(getattr(h.status(), k) for k in fields), tuple(bytes(e) for e in h.events())
                    self.assertEqual(0, self.observe_latest(h, changed, old, prefix=h.prefix + 1))
                    self.assertEqual(before, (tuple(getattr(h.status(), k) for k in fields),
                        tuple(bytes(e) for e in h.events())))
                    continue
                if fault == 'deadline':
                    h.now = old.deadline_ns + 1
                else:
                    self.lib.ng2_controller_cancel(h.engine, h.now, 2)
                self.observe_latest(h, changed, old)
                self.assert_no_fresh(h, old, counts)


if __name__ == '__main__':
    unittest.main()
