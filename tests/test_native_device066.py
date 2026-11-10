"""TEST066: retain an unchanged, unstarted shop-door opening reservation.

TEST065 frames141/142 differ only at two distant STONE/DIRT cells. Public
C sequences below use procedural images/clocks, not the missing continuation
of that device run, and distinguish opening a door from stepping through it.
"""
import ctypes as C
from copy import deepcopy
import unittest

from tests import test_native_controller as fixture
from tests import test_native_recovery as mechanics

CORE = mechanics.CORE


class NativeDevice066Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = mechanics.CORE
        try:
            mechanics.CORE = CORE
            mechanics.NativeRecoveryTests.setUpClass.__func__(cls)
        finally:
            mechanics.CORE = previous

    @classmethod
    def tearDownClass(cls):
        mechanics.NativeRecoveryTests.tearDownClass.__func__(cls)

    setUp = mechanics.NativeRecoveryTests.setUp
    scene = mechanics.NativeRecoveryTests.scene
    observe = mechanics.NativeRecoveryTests.observe
    observe_actual = mechanics.NativeRecoveryTests.observe_actual
    tick = mechanics.NativeRecoveryTests.tick
    status = mechanics.NativeRecoveryTests.status
    events = mechanics.NativeRecoveryTests.events
    motion_wait = mechanics.NativeRecoveryTests.motion_wait
    recovery = mechanics.NativeRecoveryTests.recovery
    ack = mechanics.NativeRecoveryTests.ack
    fit = mechanics.NativeRecoveryTests.fit
    next_move = mechanics.NativeRecoveryTests.next_move
    fresh_engine = mechanics.NativeRecoveryTests.fresh_engine
    observed_result = mechanics.NativeRecoveryTests.observed_result
    publish_procedural_candidate = fixture.NativeControllerTests.publish_procedural_candidate
    scene_details = fixture.NativeControllerTests.scene_details

    def armed_door(self, direction=1, goods='unknown'):
        tiles = {(0, 0): 'floor', (0, -1): 'floor', (0, -2): 'door',
                 (-1, -2): 'gold', (1, -2): 'gold', (0, -3): 'floor',
                 (-1, -3): 'floor', (1, -3): 'floor'}
        rotations = {1: lambda x, y: (y, -x), 2: lambda x, y: (-y, x),
                     3: lambda x, y: (x, y), 4: lambda x, y: (-x, -y)}
        terrain = fixture.textured({rotations[direction](x, y): value
                                    for (x, y), value in tiles.items()})
        self.fit(terrain)
        first = self.next_move()
        self.assertEqual(direction, first.direction)
        self.ack(first)
        terrain = fixture.translated(terrain, direction)
        terrain.goods = goods
        terrain.protected.add((8, -4))
        terrain.tiles[(3, 2)] = terrain.tiles[(3, 4)] = 'stone'
        self.observed_result(first, terrain)
        command = self.next_move(terrain)
        self.assertEqual((1, 1, 0, 1, 0), (self.status().inputs,
            self.status().moves, self.status().door_changes,
            self.status().lead_confirmed, self.status().reason))
        self.assertEqual((4, direction), (command.kind, command.direction))
        self.assertEqual('door', terrain.tiles[fixture.DIRS[direction]])
        return terrain, command

    def distant_change(self, terrain):
        changed = deepcopy(terrain)
        for point in ((3, 2), (3, 4)):
            changed.tiles[point] = 'dirt' if changed.tiles[point] == 'stone' else 'stone'
        return changed

    def assert_unchanged_ticket(self, command, frozen):
        self.assertEqual((0, 0, 1, command.id, 1, 1, 0),
            (self.status().reason, self.status().terminal,
             self.status().input_state, self.status().current_command_id,
             self.status().inputs, self.status().moves, self.status().door_changes),
            'distant palette drift must preserve the known-unsent door opening')
        self.assertEqual(frozen, (tuple(bytes(row) for row in self.events()),
            bytes(self.motion_wait()), bytes(self.recovery())))
        self.assertEqual(bytes(command), bytes(self.events()[-1].command))

    def frozen(self):
        return (tuple(bytes(row) for row in self.events()),
                bytes(self.motion_wait()), bytes(self.recovery()))

    def test_unchanged_door_survives_distant_palette_drift_and_opens_before_entry(self):
        for direction in (1, 2, 3, 4):
            for goods in ('unknown', 'partial'):
                with self.subTest(direction=direction, goods=goods):
                    self.fresh_engine(); terrain, command = self.armed_door(direction, goods)
                    frozen = self.frozen()
                    for _ in range(3):
                        terrain = self.distant_change(terrain); self.now += 2
                        self.assertEqual(1, self.observe_actual(self.scene(2, 2, terrain, beat=True)))
                        self.assert_unchanged_ticket(command, frozen)
                    self.ack(command)
                    opened = deepcopy(terrain); opened.tiles[fixture.DIRS[direction]] = 'floor'
                    self.observed_result(command, opened)
                    self.assertEqual((2, 1, 1, 3), (self.status().inputs,
                        self.status().moves, self.status().door_changes, self.events()[-1].motion))
                    entry = self.next_move(opened)
                    self.assertNotEqual(command.id, entry.id)
                    self.ack(entry); self.observed_result(entry, fixture.translated(opened, direction))
                    self.assertEqual((3, 2, 1, 0), (self.status().inputs,
                        self.status().moves, self.status().door_changes, self.status().reason))

    def test_changed_local_door_bracket_goods_or_protection_never_reuses_the_ticket(self):
        for fault in ('door', 'dirt', 'near', 'bracket', 'far_gold', 'protected', 'item', 'goods'):
            with self.subTest(fault=fault):
                self.fresh_engine(); terrain, command = self.armed_door(goods='partial')
                changed = self.distant_change(terrain)
                if fault == 'door': changed.tiles[(-1, 0)] = 'floor'
                elif fault == 'dirt': changed.tiles[(-1, 0)] = 'dirt'
                elif fault == 'near': changed.tiles[(0, 1)] = 'stone'
                elif fault == 'bracket': changed.tiles[(-1, -1)] = 'stone'
                elif fault == 'far_gold': changed.tiles[(8, 3)] = 'gold'
                elif fault == 'protected': changed.protected.add((7, 3))
                elif fault == 'item': changed.tiles[(8, 3)] = 'item'
                else: changed.goods = 'unknown'
                self.now += 2; self.observe_actual(self.scene(2, 2, changed, beat=True))
                self.assertNotEqual(command.id, self.status().current_command_id)
                self.assertEqual(0, self.lib.ng2_controller_begin(
                    self.engine, command.id, command.not_before_ns, 1, 0, 1))
                self.assertEqual((1, 1, 0), (self.status().inputs,
                    self.status().moves, self.status().door_changes))

    def test_door_requires_strict_blocked_signature_proof(self):
        terrain, command = self.armed_door()
        changed = self.distant_change(terrain); changed.signature = bytes([40]) * 23296
        self.now += 2; self.observe_actual(self.scene(2, 2, changed, beat=True))
        self.assertEqual(17, self.status().reason)
        self.assertEqual(0, self.events()[-1].begin_ns)
        self.assertEqual(0, self.lib.ng2_controller_begin(
            self.engine, command.id, command.not_before_ns, 1, 0, 1))

    def test_door_quiet_uses_actual_commit_and_frozen_deadline(self):
        for offset in (0, 1):
            with self.subTest(offset=offset):
                self.fresh_engine(); terrain, command = self.armed_door()
                changed = self.distant_change(terrain); frozen = self.frozen()
                self.now = command.deadline_ns - 1
                self.observe_actual(self.scene(2, 2, changed, beat=True),
                                    commit=command.deadline_ns + offset)
                if offset == 0:
                    self.assert_unchanged_ticket(command, frozen)
                    self.assertEqual(1, self.lib.ng2_controller_begin(
                        self.engine, command.id, command.deadline_ns, 1, 0, 1))
                else:
                    self.assertEqual(17, self.status().reason)
                    self.assertEqual(0, self.lib.ng2_controller_begin(
                        self.engine, command.id, command.deadline_ns + 1, 1, 0, 1))
                    self.assertEqual(command.deadline_ns, self.events()[-1].command.deadline_ns)

    def test_door_goods_cancel_and_control_authority_preempt_distant_drift(self):
        for mode in ('goods', 'cancel', 'foreground', 'locked', 'owner'):
            with self.subTest(mode=mode):
                self.fresh_engine(); terrain, command = self.armed_door()
                changed = self.distant_change(terrain)
                if mode == 'goods': changed.goods = 'visible'
                elif mode == 'cancel': self.lib.ng2_controller_cancel(self.engine, self.now, 2)
                self.now += 2; self.observe_actual(self.scene(2, 2, changed, beat=True))
                if mode in ('foreground', 'locked', 'owner'):
                    self.assert_unchanged_ticket(command, self.frozen())
                    self.assertEqual(0, self.lib.ng2_controller_begin(
                        self.engine, command.id, command.not_before_ns,
                        0 if mode == 'foreground' else 1,
                        1 if mode == 'locked' else 0, 0 if mode == 'owner' else 1))
                self.assertEqual({'goods': 1, 'cancel': 2, 'foreground': 3,
                                  'locked': 4, 'owner': 5}[mode], self.status().reason)
                self.assertEqual(0, self.lib.ng2_controller_begin(
                    self.engine, command.id, command.not_before_ns, 1, 0, 1))

    def test_unstable_prefix_and_started_or_unknown_door_cannot_gain_quiet_authority(self):
        for mode in ('unstable', 'prefix', 'begun', 'acked', 'unknown'):
            with self.subTest(mode=mode):
                self.fresh_engine(); terrain, command = self.armed_door()
                changed = self.distant_change(terrain); last = self.status().last_capture_id
                if mode in ('begun', 'acked', 'unknown'):
                    self.now = command.not_before_ns
                    self.assertEqual(1, self.lib.ng2_controller_begin(
                        self.engine, command.id, self.now, 1, 0, 1))
                    if mode != 'begun':
                        self.now += 1
                        self.assertEqual(1, self.lib.ng2_controller_complete(
                            self.engine, command.id, self.now, -1 if mode == 'unknown' else 1))
                self.now += 2
                self.observe_actual(self.scene(2, 2, changed, beat=True),
                    stable=0 if mode == 'unstable' else 1,
                    prefix=self.prefix+1 if mode == 'prefix' else self.prefix)
                self.assertEqual(last, self.status().last_capture_id)
                if mode in ('begun', 'acked', 'unknown'):
                    self.assertEqual(0, self.lib.ng2_controller_begin(
                        self.engine, command.id, command.not_before_ns, 1, 0, 1))


if __name__ == '__main__':
    unittest.main()
