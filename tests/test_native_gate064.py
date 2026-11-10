"""TEST064: irrelevant distant drift must not cancel an unstarted shop entry.

Public C sequences use procedural textures, an ACK plus verified translation,
then a verified opening. They prove reservation guards, not device reachability.
The distant changes mirror TEST063 source120→121 and source139→140.
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

CORE = mechanics.CORE


class NativeGate064Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = mechanics.CORE
        cls.baseline_directory = None
        try:
            mechanics.CORE = CORE
            baseline = os.environ.get('NECRO_TEST064_BASELINE_CONTROLLER')
            if baseline:
                cls.baseline_directory = tempfile.TemporaryDirectory(prefix='test064-gate-baseline-')
                directory = Path(cls.baseline_directory.name)
                for path in CORE.glob('NG2*'):
                    if path.suffix in ('.c', '.h'):
                        shutil.copyfile(path, directory / path.name)
                shutil.copyfile(baseline, directory / 'NG2Controller.c')
                mechanics.CORE = directory
            mechanics.NativeRecoveryTests.setUpClass.__func__(cls)
        finally:
            mechanics.CORE = previous

    @classmethod
    def tearDownClass(cls):
        mechanics.NativeRecoveryTests.tearDownClass.__func__(cls)
        if cls.baseline_directory:
            cls.baseline_directory.cleanup()

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
    continuous_walk = fixture.NativeControllerTests.continuous_walk
    scene_details = fixture.NativeControllerTests.scene_details

    def armed_gate(self, direction=3, goods='partial'):
        terrain = fixture.textured({(0, 0): 'floor', (0, -1): 'floor',
            (0, -2): 'door', (-1, -2): 'gold', (1, -2): 'gold',
            (0, -3): 'floor', (-1, -3): 'floor', (1, -3): 'floor',
            (4, 3): 'dirt', (5, 1): 'stone'})
        rotations = {1: lambda x, y: (y, -x), 2: lambda x, y: (-y, x),
                     3: lambda x, y: (x, y), 4: lambda x, y: (-x, -y)}
        terrain.tiles = {rotations[direction](x, y): value for (x, y), value in terrain.tiles.items()}
        terrain.gold = {p for p, value in terrain.tiles.items() if value == 'gold'}
        terrain, opening = self.continuous_walk(moves=1, direction=direction, terrain=terrain)
        self.ack(opening)
        opened = deepcopy(terrain)
        dx, dy = fixture.DIRS[direction]
        opened.tiles[(dx, dy)] = 'floor'
        opened.goods = goods
        self.remote_cell = (4, 4) if direction == 3 else (9, 1)
        opened.tiles[self.remote_cell] = 'dirt' if direction == 3 else 'stone'
        opened.protected.add((3, -3))
        self.observed_result(opening, opened)
        self.assertEqual((2, 1, 1, 1, 0), (self.status().inputs, self.status().moves,
            self.status().door_changes, self.status().lead_confirmed, self.status().reason))
        command = self.next_move(opened)
        self.assertEqual((4, direction, 1), (command.kind, command.direction, self.status().input_state))
        return opened, command

    def remote_change(self, terrain):
        changed = deepcopy(terrain)
        changed.tiles[self.remote_cell] = 'dirt' if changed.tiles.get(self.remote_cell) == 'stone' else 'stone'
        return changed

    def assert_current_ticket(self, command, count):
        s = self.status()
        self.assertEqual((0, 0, 1, command.id, 2, 1, 1), (s.reason, s.terminal,
            s.input_state, s.current_command_id, s.inputs, s.moves, s.door_changes),
            'distant irrelevant drift must preserve the known-unsent gate entry')
        self.assertEqual(count, len(self.events()))
        self.assertEqual((0, 0, 0), (self.events()[-1].outcome,
            self.events()[-1].begin_ns, self.events()[-1].reason))
        self.assertEqual(bytes(command), bytes(self.events()[-1].command))

    def test_distant_dirt_stone_drift_keeps_same_gate_ticket_and_can_begin(self):
        for direction in (1, 2, 3, 4):
            for goods in ('unknown', 'partial'):
                with self.subTest(direction=direction, goods=goods):
                    self.fresh_engine(); terrain, command = self.armed_gate(direction, goods)
                    count = len(self.events()); wait = bytes(self.motion_wait()); recovery = bytes(self.recovery())
                    for _ in range(3):
                        terrain = self.remote_change(terrain)
                        self.now += 2
                        self.assertEqual(1, self.observe_actual(self.scene(2, 2, terrain, beat=True)))
                        self.assert_current_ticket(command, count)
                        self.assertEqual(wait, bytes(self.motion_wait()))
                        self.assertEqual(recovery, bytes(self.recovery()))
                    self.now = command.not_before_ns
                    self.assertEqual(1, self.lib.ng2_controller_begin(self.engine, command.id, self.now, 1, 0, 1))
                    self.assertEqual((2, 2, 1), (self.status().input_state, self.status().inputs, self.status().moves))

    def test_gate_local_gold_protected_and_blocker_changes_are_not_coalesced(self):
        for fault in ('origin_near', 'target', 'bracket', 'far_gold', 'far_protected', 'item', 'goods_change'):
            with self.subTest(fault=fault):
                self.fresh_engine(); terrain, command = self.armed_gate()
                changed = self.remote_change(terrain)
                if fault == 'origin_near': changed.tiles[(1, 1)] = 'stone'
                elif fault == 'target': changed.tiles[(0, -1)] = 'dirt'
                elif fault == 'bracket': changed.tiles[(-1, -1)] = 'stone'
                elif fault == 'far_gold': changed.tiles[(8, 3)] = 'gold'
                elif fault == 'far_protected': changed.protected.add((8, 3))
                elif fault == 'item': changed.tiles[(8, 3)] = 'item'
                else: changed.goods = 'unknown'
                self.now += 2; self.observe_actual(self.scene(2, 2, changed, beat=True))
                self.assertEqual(17, self.status().reason)
                self.assertEqual((3, 0), (self.events()[-1].outcome, self.events()[-1].begin_ns))
                self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, command.id, command.not_before_ns, 1, 0, 1))

    def test_gate_signature_drift_requires_actual_blocked_motion_proof(self):
        terrain, command = self.armed_gate()
        changed = self.remote_change(terrain); changed.signature = bytes([40]) * 23296
        class Motion(C.Structure):
            _fields_ = [(key, C.c_int32) for key in ('kind', 'dx', 'dy')]
        motion = self.lib.ng2_motion
        motion.argtypes = [C.POINTER(fixture.Scene), C.POINTER(fixture.Scene), C.c_int32, C.POINTER(Motion)]
        before, after = self.scene(2, 2, terrain, beat=True), self.scene(2, 2, changed, beat=True)
        result = Motion()
        self.assertEqual(1, motion(C.byref(before), C.byref(after), command.direction, C.byref(result)))
        self.assertEqual(0, result.kind)
        self.now += 2; self.observe_actual(after)
        self.assertEqual(17, self.status().reason)
        self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, command.id, command.not_before_ns, 1, 0, 1))

    def test_gate_expired_commit_never_reuses_an_in_time_capture_end(self):
        terrain, command = self.armed_gate()
        changed = self.remote_change(terrain)
        self.now = command.deadline_ns - 1
        self.observe_actual(self.scene(2, 2, changed, beat=True), commit=command.deadline_ns + 1)
        self.assertEqual(17, self.status().reason)
        self.assertEqual((2, 1, 1), (self.status().inputs, self.status().moves, self.status().door_changes))
        self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, command.id, command.not_before_ns, 1, 0, 1))

    def test_gate_goods_latch_and_cancel_preempt_distant_drift(self):
        for mode in ('goods', 'cancel', 'foreground', 'locked', 'owner'):
            with self.subTest(mode=mode):
                self.fresh_engine(); terrain, command = self.armed_gate()
                changed = self.remote_change(terrain)
                if mode == 'goods': changed.goods = 'visible'
                elif mode == 'cancel': self.lib.ng2_controller_cancel(self.engine, self.now, 2)
                self.now += 2; self.observe_actual(self.scene(2, 2, changed, beat=True))
                if mode in ('foreground', 'locked', 'owner'):
                    self.assert_current_ticket(command, len(self.events()))
                    self.now = command.not_before_ns
                    self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, command.id, self.now,
                        0 if mode == 'foreground' else 1, 1 if mode == 'locked' else 0,
                        0 if mode == 'owner' else 1))
                self.assertEqual({'goods': 1, 'cancel': 2, 'foreground': 3, 'locked': 4, 'owner': 5}[mode],
                                 self.status().reason)
                self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, command.id, command.not_before_ns, 1, 0, 1))
                self.assertEqual((2, 1, 1), (self.status().inputs, self.status().moves, self.status().door_changes))

    def test_gate_discarded_prefix_and_inflight_frames_supply_no_new_authority(self):
        for mode in ('unstable', 'prefix', 'begun', 'acked', 'unknown'):
            with self.subTest(mode=mode):
                self.fresh_engine(); terrain, command = self.armed_gate()
                changed = self.remote_change(terrain)
                last = self.status().last_capture_id
                if mode in ('begun', 'acked', 'unknown'):
                    self.now = command.not_before_ns
                    self.assertEqual(1, self.lib.ng2_controller_begin(self.engine, command.id, self.now, 1, 0, 1))
                    if mode != 'begun':
                        self.now += 1
                        self.assertEqual(1, self.lib.ng2_controller_complete(self.engine, command.id, self.now, -1 if mode == 'unknown' else 1))
                self.now += 2
                self.observe_actual(self.scene(2, 2, changed, beat=True),
                    stable=0 if mode == 'unstable' else 1,
                    prefix=self.prefix + 1 if mode == 'prefix' else self.prefix)
                self.assertEqual(last, self.status().last_capture_id)
                if mode in ('begun', 'acked', 'unknown'):
                    self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, command.id, command.not_before_ns, 1, 0, 1))
                self.assertEqual(2 if mode in ('unstable', 'prefix', 'begun') else 3,
                                 self.status().inputs)
