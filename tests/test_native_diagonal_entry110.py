"""TEST109/fe54: a positively bracketed closed diagonal is not the entry floor.

Original244->245 keeps the actual LEFT destination and stationary world while
one diagonal DOOR resolves to solid GOLD. These textures, clocks and future
responses are procedural public-C contracts, not missing phone frames.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import unittest

from tests import test_native_controller as native
from tests import test_native_opened_fade100 as opened


class NativeDiagonalEntry110Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = native.CORE
        try:
            frozen = os.environ.get('NECRO_TEST110_DIAGONAL_CORE')
            if frozen:
                native.CORE = Path(frozen)
            opened.NativeOpenedFade100Tests.setUpClass.__func__(cls)
        finally:
            native.CORE = previous

    tearDownClass = classmethod(opened.NativeOpenedFade100Tests.tearDownClass.__func__)

    def setUp(self):
        self.p = opened.NativeOpenedFade100Tests(methodName='runTest')
        self.p.lib = self.lib
        self.addCleanup(self.p.doCleanups)

    @staticmethod
    def rotate(direction, point):
        x, y = point
        return {1: (x, y), 2: (-x, -y), 3: (-y, x), 4: (y, -x)}[direction]

    def armed(self, direction=1, side=1, cycle_profile=True, actual_opening=True,
              missing_bracket=False, protected=False):
        h, terrain, _, original_remote = self.p.armed(direction=direction,
            cycle_profile=cycle_profile, actual_opening=actual_opening, reserve=False)
        terrain = deepcopy(terrain)
        terrain.tiles[original_remote] = 'gold'
        alias = self.rotate(direction, (-2, side))
        terrain.tiles[alias] = 'door'
        for point in ((-3, side), (-1, side)):
            terrain.tiles[self.rotate(direction, point)] = 'gold'
        if missing_bracket:
            terrain.tiles[self.rotate(direction, (-3, side))] = 'dirt'
        if protected:
            terrain.protected.add(alias)
        terrain.tiles[self.rotate(direction, (-6, 0))] = 'dirt'
        h.now += 2
        self.assertEqual(1, h.observe_actual(h.scene(2, 2, terrain, beat=True)))
        command = h.next_move(terrain)
        self.assertEqual((direction, 5, *native.DIRS[direction], 1), h.choice(terrain))
        return h, terrain, command, alias

    def latest(self, source, direction, alias):
        changed = deepcopy(source)
        changed.tiles[alias] = 'gold'
        changed.tiles[self.rotate(direction, (-6, 0))] = 'floor'
        return changed

    def observe(self, h, terrain, command, **kwargs):
        h.now = max(h.now + 2, command.not_before_ns - 44_000_000)
        current = deepcopy(terrain)
        current.tiles = {point: kind for point, kind in current.tiles.items() if kind != 'unknown'}
        return h.observe_actual(h.scene(2, 2, current, beat=True), **kwargs)

    def assert_not_fresh(self, h, command, before):
        self.assertEqual(before, (h.status().inputs, h.status().moves,
                                 h.status().door_changes))
        self.assertNotEqual(12, h.scene_details()[-1].validation if h.scene_details() else 0)
        self.assertEqual(0, self.lib.ng2_controller_begin(h.engine, command.id,
            max(h.now, command.not_before_ns), 1, 0, 1))

    def test_bracketed_diagonal_closure_retires_old_ticket_and_enters_on_same_frozen_beat(self):
        for direction in (1, 2, 3, 4):
            for side in (-1, 1):
                with self.subTest(direction=direction, side=side):
                    h, terrain, old, alias = self.armed(direction, side)
                    latest = self.latest(terrain, direction, alias)
                    self.assertEqual(h.choice(terrain), h.choice(latest))
                    self.assertEqual((2, 0, 0), h.motion(terrain, latest, direction))
                    before = (h.status().inputs, h.status().moves, h.status().door_changes)
                    self.assertEqual(1, self.observe(h, latest, old))
                    self.assertEqual((0, 0), (h.status().reason, h.status().terminal),
                        'closing a positively bracketed diagonal must not block the still-observed entry floor')
                    new = h.next_move(latest)
                    self.assertGreater(new.id, old.id)
                    self.assertEqual((old.target_ns, old.not_before_ns, old.deadline_ns, old.ordinal),
                        (new.target_ns, new.not_before_ns, new.deadline_ns, new.ordinal))
                    self.assertGreater(new.source_capture_id, old.source_capture_id)
                    self.assertEqual(12, h.scene_details()[-1].validation)
                    self.assertEqual(before, (h.status().inputs, h.status().moves, h.status().door_changes))
                    self.assertEqual(0, self.lib.ng2_controller_begin(h.engine, old.id,
                        h.now, 1, 0, 1))
                    h.ack(new)
                    self.assertEqual(before[1], h.status().moves, 'ACK alone is not displacement')
                    h.observed_result(new, native.translated(latest, direction))
                    self.assertEqual(before[1] + 1, h.status().moves)

    def test_legacy_profile_and_missing_actual_opening_do_not_gain_diagonal_permission(self):
        for cycle_profile, opened_gate in ((False, True), (True, False)):
            with self.subTest(cycle_profile=cycle_profile, opened=opened_gate):
                h, terrain, command, alias = self.armed(cycle_profile=cycle_profile,
                    actual_opening=opened_gate)
                before = (h.status().inputs, h.status().moves, h.status().door_changes)
                self.observe(h, self.latest(terrain, 1, alias), command)
                self.assert_not_fresh(h, command, before)

    def test_source_and_latest_brackets_and_every_protected_role_remain_required(self):
        for fault in ('old_bracket', 'new_bracket', 'old_protected', 'new_protected'):
            with self.subTest(fault=fault):
                h, terrain, command, alias = self.armed(missing_bracket=fault == 'old_bracket',
                    protected=fault == 'old_protected')
                latest = self.latest(terrain, 1, alias)
                if fault == 'new_bracket': latest.tiles[(-3, 1)] = 'dirt'
                if fault == 'new_protected': latest.protected.add(alias)
                before = (h.status().inputs, h.status().moves, h.status().door_changes)
                self.observe(h, latest, command)
                self.assert_not_fresh(h, command, before)

    def test_actual_origin_destination_and_other_near_material_are_not_the_diagonal(self):
        for point, kind in (((0, 0), 'dirt'), ((-1, 0), 'unknown'),
                            ((0, 1), 'dirt'), ((-2, 0), 'stone'), ((1, 1), 'floor')):
            with self.subTest(point=point, kind=kind):
                h, terrain, command, alias = self.armed()
                latest = self.latest(terrain, 1, alias)
                latest.tiles[point] = kind
                before = (h.status().inputs, h.status().moves, h.status().door_changes)
                self.observe(h, latest, command)
                self.assert_not_fresh(h, command, before)

    def test_only_positive_solid_gold_resolution_is_the_new_diagonal_relation(self):
        for material in ('unknown', 'floor', 'dirt', 'stone', 'item'):
            with self.subTest(material=material):
                h, terrain, command, alias = self.armed()
                latest = self.latest(terrain, 1, alias)
                latest.tiles[alias] = material
                if material == 'item': latest.protected.add(alias)
                before = (h.status().inputs, h.status().moves, h.status().door_changes)
                self.observe(h, latest, command)
                self.assert_not_fresh(h, command, before)

    def test_nonzero_motion_prefix_deadline_and_cancel_cannot_reissue_entry(self):
        for fault in ('motion', 'prefix', 'deadline', 'cancel'):
            with self.subTest(fault=fault):
                h, terrain, command, alias = self.armed()
                latest = self.latest(terrain, 1, alias)
                before = (h.status().inputs, h.status().moves, h.status().door_changes)
                if fault == 'motion': latest.signature = native.translated(terrain, 1).signature
                elif fault == 'deadline': h.now = command.deadline_ns + 1
                elif fault == 'cancel': self.lib.ng2_controller_cancel(h.engine, h.now, 1)
                if fault == 'prefix':
                    fields = ('current_command_id', 'input_state', 'last_completed_id', 'x', 'y',
                              'inputs', 'moves', 'reason')
                    saved = tuple(getattr(h.status(), k) for k in fields), tuple(bytes(e) for e in h.events())
                    self.assertEqual(0, self.observe(h, latest, command, prefix=h.prefix + 1))
                    self.assertEqual(saved, (tuple(getattr(h.status(), k) for k in fields),
                        tuple(bytes(e) for e in h.events())), 'foreign data cannot alter the original valid permission')
                    continue
                self.observe(h, latest, command, **({'prefix': h.prefix + 1} if fault == 'prefix' else {}))
                self.assert_not_fresh(h, command, before)

    def test_unknown_sent_input_remains_frozen_without_another_move(self):
        h, terrain, command, alias = self.armed()
        h.now = command.not_before_ns
        self.assertEqual(1, self.lib.ng2_controller_begin(h.engine, command.id, h.now, 1, 0, 1))
        self.lib.ng2_controller_complete(h.engine, command.id, h.now + 1, -1)
        self.assertEqual(4, h.status().input_state)
        h.now += 2
        h.observe_actual(h.scene(2, 2, self.latest(terrain, 1, alias), beat=True))
        self.assertEqual(4, h.status().input_state)
        self.assertNotEqual(4, h.tick()[1].kind)
        self.assertEqual(0, self.lib.ng2_controller_begin(h.engine, command.id, h.now, 1, 0, 1))


if __name__ == '__main__':
    unittest.main()
