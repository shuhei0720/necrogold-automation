"""TEST079: keep an unsent dig immediately before the same closed gold gate.

The reported 272/273 pair motivates remote DIRT/FLOOR flicker while the actual
DIRT target stays unchanged. Maps, signatures, clocks and later acknowledgments
below are procedural public-C units, not reconstructed phone responses.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import random
import shutil
import tempfile
import unittest

from tests import test_native_controller as fixture
from tests import test_native_recovery as mechanics
from tests import test_native_observation072 as observation

CORE = mechanics.CORE


class NativeDirtTicket079Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = mechanics.CORE
        cls.baseline_directory = None
        try:
            mechanics.CORE = CORE
            baseline = os.environ.get('NECRO_TEST079_BASELINE_CONTROLLER')
            if baseline:
                cls.baseline_directory = tempfile.TemporaryDirectory(prefix='test079-dirt-baseline-')
                directory = Path(cls.baseline_directory.name)
                for path in CORE.glob('NG2*'):
                    if path.suffix in ('.c', '.h'):
                        shutil.copyfile(path, directory / path.name)
                shutil.copyfile(baseline, directory / 'NG2Controller.c')
                mechanics.CORE = directory
            mechanics.NativeRecoveryTests.setUpClass.__func__(cls)
        finally:
            mechanics.CORE = previous
        cls.lib.ng2_choose.argtypes = [C.POINTER(fixture.Scene), C.c_int32, C.c_int32,
            C.POINTER(C.c_uint16), C.c_size_t, C.POINTER(observation.Entrance),
            C.POINTER(observation.Decision)]
        cls.lib.ng2_motion.argtypes = [C.POINTER(fixture.Scene), C.POINTER(fixture.Scene),
            C.c_int32, C.POINTER(observation.Motion)]
        cls.lib.ng2_entered_gate.argtypes = [C.POINTER(fixture.Scene), C.POINTER(fixture.Scene),
            C.c_int32, C.c_int32, C.c_int32, C.c_int32, C.POINTER(observation.Entrance)]

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
    scene_details = mechanics.NativeRecoveryTests.scene_details
    motion_wait = mechanics.NativeRecoveryTests.motion_wait
    motion_references = fixture.NativeControllerTests.motion_references
    recovery = mechanics.NativeRecoveryTests.recovery
    ack = mechanics.NativeRecoveryTests.ack
    fit = mechanics.NativeRecoveryTests.fit
    next_move = mechanics.NativeRecoveryTests.next_move
    fresh_engine = mechanics.NativeRecoveryTests.fresh_engine
    observed_result = mechanics.NativeRecoveryTests.observed_result
    publish_procedural_candidate = fixture.NativeControllerTests.publish_procedural_candidate
    preparation_epoch = fixture.NativeControllerTests.preparation_epoch
    choice = observation.NativeObservation072Tests.choice
    motion = observation.NativeObservation072Tests.motion
    credit = observation.NativeObservation072Tests.credit

    def armed(self, direction=3, initial='dirt', verified=True, gate_kind='door',
              target_kind='dirt', distant_gate=False, protected_remote=False, goods='unknown'):
        self.rotate = {1: lambda x,y:(y,-x), 2: lambda x,y:(-y,x),
                       3: lambda x,y:(x,y), 4: lambda x,y:(-x,-y)}[direction]
        first = 1 if verified else 0
        gate = first + (3 if distant_gate else 2)
        tiles = {(0, 0): 'floor', (0, -first - 1): target_kind,
                 (0, -gate): gate_kind, (-1, -gate): 'gold', (1, -gate): 'gold',
                 (0, -gate - 1): 'floor'}
        if verified: tiles[(0, -1)] = 'floor'
        if distant_gate: tiles[(0, -first - 2)] = 'floor'
        if initial != 'unknown': tiles[(-1, 2 - first)] = initial
        terrain = fixture.textured({self.rotate(x, y): kind for (x, y), kind in tiles.items()})
        if protected_remote:
            terrain.tiles[(8, 2)] = 'floor'; terrain.protected.add((8, 2))
            terrain.tiles[(9, 2)] = 'item'
        self.fit(terrain)
        if verified:
            move = self.next_move(terrain); self.assertEqual(direction, move.direction)
            self.ack(move); terrain = fixture.translated(terrain, direction)
            terrain.goods = goods
            self.observed_result(move, terrain)
        command = self.next_move(terrain)
        dx, dy = fixture.DIRS[direction]
        distance = 2 if distant_gate else 1
        self.assertEqual((direction, 6 if target_kind == 'dirt' else 7,
                          distance * dx, distance * dy, fixture.KINDS[target_kind]),
                         self.choice(terrain))
        self.assertEqual((int(verified), int(verified), int(verified), 1),
            (self.status().inputs, self.status().moves, self.status().lead_confirmed,
             self.status().input_state))
        self.remote = self.rotate(-1, 2)
        return terrain, command

    def drift(self, terrain, latest='floor'):
        changed = deepcopy(terrain)
        if latest == 'unknown': changed.tiles.pop(self.remote, None)
        else: changed.tiles[self.remote] = latest
        return changed

    def preserve(self, terrain, changed, command):
        self.assertEqual(self.choice(terrain), self.choice(changed))
        self.assertEqual((2, 0, 0), self.motion(terrain, changed, command.direction))
        saved = (self.credit(), bytes(command), self.preparation_epoch(command),
                 tuple(bytes(e) for e in self.events()), bytes(self.motion_wait()),
                 bytes(self.recovery()), tuple(bytes(d) for d in self.scene_details()))
        self.assertNotEqual(0, saved[2], 'the logical dig already has a preparation epoch')
        self.now += 2; self.observe_actual(self.scene(2, 2, changed, beat=True))
        self.assertEqual((0, 0, 1, command.id), (self.status().reason, self.status().terminal,
            self.status().input_state, self.status().current_command_id),
            'unchanged observed dig before the same closed gold gate must keep its original beat')
        self.assertEqual(saved, (self.credit(), bytes(self.events()[-1].command),
            self.preparation_epoch(command), tuple(bytes(e) for e in self.events()),
            bytes(self.motion_wait()), bytes(self.recovery()),
            tuple(bytes(d) for d in self.scene_details())))

    def test_verified_four_direction_dig_keeps_ticket_then_counts_only_terrain_opening(self):
        for direction in (1, 2, 3, 4):
            for initial, latest in (('dirt', 'floor'), ('floor', 'dirt'), ('unknown', 'stone')):
                with self.subTest(direction=direction, initial=initial, latest=latest):
                    self.fresh_engine()
                    terrain, command = self.armed(direction, initial=initial, protected_remote=True)
                    changed = self.drift(terrain, latest)
                    self.preserve(terrain, changed, command)
                    old = self.status(); before = self.scene(2, 2, changed)
                    self.ack(command)
                    self.assertEqual(command.not_before_ns, self.events()[-1].begin_ns)
                    opened = deepcopy(changed); opened.tiles[fixture.DIRS[direction]] = 'floor'
                    self.observed_result(command, opened)
                    self.assertEqual((0, old.inputs + 1, old.moves, 0, 1, old.x, old.y, old.lead_ns),
                        (self.status().reason, self.status().inputs, self.status().moves,
                         self.status().door_changes, self.status().terrain_changes,
                         self.status().x, self.status().y, self.status().lead_ns))
                    self.assertEqual((2, 4, 0, 0), (self.events()[-1].outcome,
                        self.events()[-1].motion, self.events()[-1].dx, self.events()[-1].dy))
                    reference = self.motion_references()[-1]
                    self.assertEqual((0, 0, 0), (reference.reference_capture_id,
                        reference.reference_eligible, reference.fallback_attempted))
                    after = self.scene(2, 2, opened); entrance = observation.Entrance()
                    self.assertEqual(0, self.lib.ng2_entered_gate(C.byref(before), C.byref(after),
                        direction, old.x, old.y, 4, C.byref(entrance)))
                    following = self.next_move(opened)
                    dx, dy = fixture.DIRS[direction]
                    self.assertEqual((direction, 7, dx, dy, 1), self.choice(opened))
                    self.ack(following)
                    walked = fixture.translated(opened, direction)
                    self.observed_result(following, walked)
                    self.assertEqual((0, old.moves + 1, 0, 1),
                        (self.status().reason, self.status().moves,
                         self.status().door_changes, self.status().terrain_changes))
                    self.assertEqual((direction, 5, dx, dy, 5), self.choice(walked))

    def test_closed_gate_unit_target_unknown_goods_and_verified_lead_are_required(self):
        for fault in ('opened_gate', 'wrong_bracket', 'distant_target', 'floor_target',
                      'unverified', 'old_partial', 'new_partial', 'new_visible'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                terrain, command = self.armed(gate_kind='floor' if fault == 'opened_gate' else 'door',
                    distant_gate=fault == 'distant_target', target_kind='floor' if fault == 'floor_target' else 'dirt',
                    verified=fault != 'unverified', goods='partial' if fault == 'old_partial' else 'unknown')
                changed = self.drift(terrain)
                if fault == 'wrong_bracket':
                    changed.tiles[(1, -2)] = 'floor'; changed.tiles[(2, -2)] = 'gold'
                elif fault == 'new_partial': changed.goods = 'partial'
                elif fault == 'new_visible': changed.goods = 'visible'
                credit = self.credit()
                self.now += 2; self.observe_actual(self.scene(2, 2, changed, beat=True))
                self.assertNotEqual((0, 1, command.id), (self.status().reason,
                    self.status().input_state, self.status().current_command_id))
                self.assertEqual(0, self.lib.ng2_controller_begin(
                    self.engine, command.id, command.not_before_ns, 1, 0, 1))
                self.assertEqual(credit, self.credit())
                if fault == 'new_visible': self.assertEqual((1, 1), (self.status().reason, self.status().goods))

    def test_local_gold_protected_material_item_and_nonpalette_changes_are_rejected(self):
        for fault in ('origin', 'next', 'near_origin', 'near_next', 'gate_door', 'gold',
                      'protected_set', 'protected_material', 'new_item', 'changed_item', 'remote_door'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                terrain, command = self.armed(protected_remote=True)
                changed = self.drift(terrain)
                if fault == 'origin': changed.tiles[(0, 0)] = 'dirt'
                elif fault == 'next': changed.tiles[(0, -1)] = 'stone'
                elif fault == 'near_origin': changed.tiles[(1, 0)] = 'dirt'
                elif fault == 'near_next': changed.tiles[(-1, -1)] = 'dirt'
                elif fault == 'gate_door': changed.tiles[(0, -2)] = 'floor'
                elif fault == 'gold': changed.tiles[(8, -3)] = 'gold'
                elif fault == 'protected_set': changed.protected.add(self.remote)
                elif fault == 'protected_material':
                    point = next(p for p in terrain.protected)
                    changed.tiles[point] = 'dirt'
                elif fault == 'new_item': changed.tiles[(8, -3)] = 'item'
                elif fault == 'changed_item':
                    point = next(p for p, kind in terrain.tiles.items() if kind == 'item')
                    changed.tiles[point] = 'floor'
                elif fault == 'remote_door': changed.tiles[self.remote] = 'door'
                counts = self.credit()
                self.now += 2; self.observe_actual(self.scene(2, 2, changed, beat=True))
                self.assertNotEqual((0, 1, command.id), (self.status().reason,
                    self.status().input_state, self.status().current_command_id))
                self.assertEqual(0, self.lib.ng2_controller_begin(
                    self.engine, command.id, command.not_before_ns, 1, 0, 1))
                self.assertEqual(counts, self.credit())

    def test_unknown_tween_or_nonzero_motion_cannot_preserve_dig_authority(self):
        for fault in ('unknown', 'moved', 'tween'):
            with self.subTest(fault=fault):
                self.fresh_engine(); terrain, command = self.armed()
                changed = self.drift(terrain)
                if fault == 'unknown':
                    rng = random.Random(79079)
                    changed.signature = bytes(rng.randrange(20, 100) for _ in range(23296))
                else:
                    changed.signature = fixture.translated(terrain, 3, 9 if fault == 'moved' else 8).signature
                self.assertNotEqual((2, 0, 0), self.motion(terrain, changed, command.direction))
                counts = self.credit()
                self.now += 2; self.observe_actual(self.scene(2, 2, changed, beat=True))
                self.assertEqual(0, self.lib.ng2_controller_begin(
                    self.engine, command.id, command.not_before_ns, 1, 0, 1))
                self.assertEqual(counts, self.credit())

    def test_original_actual_deadline_and_stable_current_prefix_are_kept(self):
        for fault in ('deadline_equal', 'deadline_plus', 'unstable', 'prefix'):
            with self.subTest(fault=fault):
                self.fresh_engine(); terrain, command = self.armed()
                changed = self.drift(terrain); saved = bytes(command); options = {}
                self.now = command.deadline_ns - 1 if fault.startswith('deadline') else self.now + 2
                if fault.startswith('deadline'):
                    options['commit'] = command.deadline_ns + int(fault == 'deadline_plus')
                elif fault == 'unstable': options['stable'] = 0
                else: options['prefix'] = self.prefix + 1
                self.observe_actual(self.scene(2, 2, changed, beat=True), **options)
                self.assertEqual(saved, bytes(self.events()[-1].command))
                if fault == 'deadline_plus':
                    self.assertEqual(0, self.lib.ng2_controller_begin(
                        self.engine, command.id, command.deadline_ns + 1, 1, 0, 1))
                else:
                    self.assertEqual((0, 1, command.id), (self.status().reason,
                        self.status().input_state, self.status().current_command_id))
                    if fault == 'deadline_equal':
                        self.assertEqual(1, self.lib.ng2_controller_begin(
                            self.engine, command.id, command.deadline_ns, 1, 0, 1))

    def test_goods_cancel_owner_and_started_or_unknown_input_never_gain_another_send(self):
        for fault in ('goods', 'cancel', 'owner', 'locked', 'foreground', 'started', 'unknown', 'ack_blocked'):
            with self.subTest(fault=fault):
                self.fresh_engine(); terrain, command = self.armed()
                changed = self.drift(terrain)
                self.preserve(terrain, changed, command)
                if fault in ('started', 'unknown'):
                    self.now = command.not_before_ns
                    self.assertEqual(1, self.lib.ng2_controller_begin(self.engine, command.id, self.now, 1, 0, 1))
                    self.now += 2; self.observe_actual(self.scene(2, 2, changed, beat=True))
                    self.assertEqual((2, 1), (self.status().input_state, self.status().inputs))
                    self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, command.id, self.now, 1, 0, 1))
                    if fault == 'unknown':
                        self.now += 1
                        self.assertEqual(1, self.lib.ng2_controller_complete(self.engine, command.id, self.now, -1))
                        for _ in range(3):
                            self.now += 100_000_000
                            self.observe_actual(self.scene(2, 2, changed, beat=True))
                            self.assertNotEqual(4, self.tick()[1].kind)
                        self.assertEqual((4, 11, 2, 1, 0), (self.status().input_state,
                            self.status().reason, self.status().inputs, self.status().moves,
                            self.status().terrain_changes))
                elif fault == 'ack_blocked':
                    self.ack(command); self.observed_result(command, changed)
                    self.assertEqual((10, 2, 1, 0, 0), (self.status().reason,
                        self.status().inputs, self.status().moves,
                        self.status().door_changes, self.status().terrain_changes))
                    self.assertNotEqual(4, self.tick()[1].kind)
                else:
                    if fault == 'goods':
                        changed.goods = 'visible'; self.now += 2
                        self.observe_actual(self.scene(2, 2, changed, beat=True))
                    elif fault == 'cancel': self.lib.ng2_controller_cancel(self.engine, self.now, 2)
                    else:
                        flags = {'front': 1, 'locked': 0, 'owner': 1}
                        flags[{'owner': 'owner', 'locked': 'locked', 'foreground': 'front'}[fault]] = int(fault == 'locked')
                        self.tick(**flags)
                    self.assertEqual({'goods': 1, 'cancel': 2, 'owner': 5, 'locked': 4, 'foreground': 3}[fault],
                                     self.status().reason)
                    self.assertEqual(0, self.lib.ng2_controller_begin(
                        self.engine, command.id, command.not_before_ns, 1, 0, 1))
                    self.assertEqual((1, 1, 0, 0), (self.status().inputs, self.status().moves,
                        self.status().door_changes, self.status().terrain_changes))


if __name__ == '__main__':
    unittest.main()
