"""TEST077: distant newly lit GOLD must not cancel a verified shop entry.

The TEST076 second run stopped before its already-open FLOOR gate when one
distant DIRT cell became GOLD. These public-C procedural worlds exercise the
bounded continuation and its guards; later images are not device recordings.
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
from tests import test_native_shop071 as shop
from tests import test_native_observation072 as observation

CORE = mechanics.CORE


class NativeOpenEntry077Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = mechanics.CORE
        cls.baseline_directory = None
        try:
            mechanics.CORE = CORE
            baseline = os.environ.get('NECRO_TEST077_BASELINE_CONTROLLER')
            if baseline:
                cls.baseline_directory = tempfile.TemporaryDirectory(prefix='test077-entry-')
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
    recovery = mechanics.NativeRecoveryTests.recovery
    ack = mechanics.NativeRecoveryTests.ack
    next_move = mechanics.NativeRecoveryTests.next_move
    fresh_engine = mechanics.NativeRecoveryTests.fresh_engine
    observed_result = mechanics.NativeRecoveryTests.observed_result
    publish_procedural_candidate = fixture.NativeControllerTests.publish_procedural_candidate
    preparation_epoch = fixture.NativeControllerTests.preparation_epoch
    choice = observation.NativeObservation072Tests.choice
    motion = observation.NativeObservation072Tests.motion
    credit = observation.NativeObservation072Tests.credit
    opened_entry = shop.NativeShop071Tests.opened_entry

    def fit(self, terrain=None):
        # Seed observable remote materials before any ticket is created. Their
        # later translation is the ordinary procedural world transformation.
        terrain.tiles.update({(-8, 0): 'dirt', (-9, 0): 'floor',
                              (-10, 0): 'stone', (-10, -2): 'gold'})
        if getattr(self, 'protect_remote', False):
            terrain.protected.add((-8, 0))
            terrain.tiles.update({(-8, 2): 'item', (-9, 2): 'floor'})
            terrain.protected.update({(-8, 2), (-9, 2)})
        return mechanics.NativeRecoveryTests.fit(self, terrain)

    def armed(self, stage='entry', direction=3, **options):
        self.protect_remote = options.pop('protect_remote', False)
        terrain, command = self.opened_entry(direction=direction, **options)
        self.entrance = observation.Entrance()
        if stage == 'interior':
            before = self.scene(2, 2, terrain)
            state = self.status()
            self.ack(command)
            terrain = fixture.translated(terrain, direction)
            after = self.scene(2, 2, terrain)
            self.assertEqual(1, self.lib.ng2_entered_gate(C.byref(before), C.byref(after),
                direction, state.x, state.y, 1, C.byref(self.entrance)))
            self.observed_result(command, terrain)
            command = self.next_move(terrain)
            self.assertEqual((direction, 8, 1),
                (self.choice(terrain, self.entrance)[0],
                 self.choice(terrain, self.entrance)[1],
                 self.choice(terrain, self.entrance)[4]))
        return terrain, command

    def remote(self, terrain, kind='dirt'):
        return next(point for point, material in terrain.tiles.items()
                    if material == kind and abs(point[0]) >= 6)

    def reveal(self, terrain, point=None):
        changed = deepcopy(terrain)
        changed.tiles[point if point is not None else self.remote(terrain)] = 'gold'
        return changed

    def preserve(self, terrain, changed, command):
        self.assertEqual(self.choice(terrain, self.entrance),
                         self.choice(changed, self.entrance))
        self.assertEqual((2, 0, 0), self.motion(terrain, changed, command.direction))
        saved = (self.credit(), bytes(command), self.preparation_epoch(command),
                 tuple(bytes(row) for row in self.events()), bytes(self.motion_wait()),
                 bytes(self.recovery()), tuple(bytes(row) for row in self.scene_details()))
        self.now += 2
        self.observe_actual(self.scene(2, 2, changed, beat=True))
        self.assertEqual((0, 0, 1, command.id), (self.status().reason, self.status().terminal,
            self.status().input_state, self.status().current_command_id),
            'distant added GOLD must keep this verified PARTIAL-shop ticket')
        self.assertEqual(saved, (self.credit(), bytes(self.events()[-1].command),
            self.preparation_epoch(command), tuple(bytes(row) for row in self.events()),
            bytes(self.motion_wait()), bytes(self.recovery()),
            tuple(bytes(row) for row in self.scene_details())))

    def finish_step(self, terrain, command):
        before = self.status()
        self.ack(command)
        self.assertEqual(command.not_before_ns, self.events()[-1].begin_ns)
        moved = fixture.translated(terrain, command.direction)
        self.observed_result(command, moved)
        dx, dy = fixture.DIRS[command.direction]
        self.assertEqual((0, before.inputs + 1, before.moves + 1,
                          before.x + dx, before.y + dy, before.door_changes, 0),
            (self.status().reason, self.status().inputs, self.status().moves,
             self.status().x, self.status().y, self.status().door_changes, self.status().goods))
        self.assertEqual((2, 1, dx, dy), (self.events()[-1].outcome,
            self.events()[-1].motion, self.events()[-1].dx, self.events()[-1].dy))
        return moved

    def test_opened_entry_reveal_preserves_ticket_then_enters_on_original_beat(self):
        for direction in (1, 2, 3, 4):
            for material in ('unknown', 'dirt'):
                with self.subTest(direction=direction, material=material):
                    self.fresh_engine()
                    terrain, command = self.armed(direction=direction,
                        protect_remote=material == 'unknown')
                    point = (8, -3) if material == 'unknown' else self.remote(terrain)
                    changed = self.reveal(terrain, point)
                    self.preserve(terrain, changed, command)
                    before = self.scene(2, 2, changed)
                    state = self.status()
                    moved = self.finish_step(changed, command)
                    after = self.scene(2, 2, moved)
                    entrance = observation.Entrance()
                    self.assertEqual(1, self.lib.ng2_entered_gate(C.byref(before), C.byref(after),
                        direction, state.x, state.y, 1, C.byref(entrance)))
                    self.assertEqual((1, self.status().x, self.status().y, direction),
                        (entrance.valid, entrance.x, entrance.y, entrance.direction))
                    following = self.next_move(moved)
                    self.assertEqual((following.direction, 8, 1),
                        (self.choice(moved, entrance)[0], self.choice(moved, entrance)[1],
                         self.choice(moved, entrance)[4]))

    def test_interior_partial_reveals_continue_after_verified_entry_and_next_step(self):
        for material in ('unknown', 'dirt'):
            with self.subTest(material=material):
                self.fresh_engine()
                terrain, command = self.armed('interior', protect_remote=material == 'unknown')
                point = (8, -3) if material == 'unknown' else self.remote(terrain)
                changed = self.reveal(terrain, point)
                self.preserve(terrain, changed, command)
                moved = self.finish_step(changed, command)
                following = self.next_move(moved)
                self.assertEqual((following.direction, 8, 1),
                    (self.choice(moved, self.entrance)[0], self.choice(moved, self.entrance)[1],
                     self.choice(moved, self.entrance)[4]))
                later = self.reveal(moved, (7, -3))
                self.preserve(moved, later, following)
                self.finish_step(later, following)

    def test_geometry_old_gold_and_protected_material_changes_cannot_use_reveal(self):
        for stage in ('entry', 'interior'):
            for fault in ('old_gold', 'origin_near', 'next_near', 'next', 'stone', 'floor',
                          'protected_old', 'protected_new', 'protected_material',
                          'previous_floor', 'bracket', 'route'):
                with self.subTest(stage=stage, fault=fault):
                    self.fresh_engine()
                    terrain, command = self.armed(stage,
                        protect_remote=fault in ('protected_old', 'protected_material'))
                    changed = self.reveal(terrain)
                    if fault == 'old_gold':
                        changed.tiles[self.remote(terrain, 'gold')] = 'dirt'
                    elif fault == 'origin_near': changed.tiles[(1, 1)] = 'gold'
                    elif fault == 'next_near': changed.tiles[(1, -2)] = 'gold'
                    elif fault == 'next': changed.tiles[(0, -1)] = 'gold'
                    elif fault in ('stone', 'floor'):
                        changed = self.reveal(terrain, self.remote(terrain, fault))
                    elif fault == 'protected_new': changed.protected.add(self.remote(terrain))
                    elif fault == 'protected_material':
                        changed = self.reveal(terrain, (8, -3))
                        changed.tiles[self.remote(terrain)] = 'floor'
                    elif fault == 'previous_floor':
                        previous = deepcopy(terrain)
                        previous.tiles[self.remote(terrain)] = 'floor'
                        self.now += 2; self.observe_actual(self.scene(2, 2, previous, beat=True))
                        self.assertEqual((0, 1, command.id),
                            (self.status().reason, self.status().input_state, self.status().current_command_id))
                    elif fault == 'bracket': changed.tiles[(-1, -1 if stage == 'entry' else 0)] = 'floor'
                    elif fault == 'route': changed.tiles[(0, -1)] = 'dirt'
                    counts = self.credit()
                    self.now += 2; self.observe_actual(self.scene(2, 2, changed, beat=True))
                    self.assertNotEqual((0, 1, command.id),
                        (self.status().reason, self.status().input_state, self.status().current_command_id))
                    self.assertEqual(0, self.lib.ng2_controller_begin(
                        self.engine, command.id, command.not_before_ns, 1, 0, 1))
                    self.assertEqual(counts, self.credit())

    def test_no_open_ack_or_partial_entrance_permission_is_created_by_new_gold(self):
        for fault in ('closed_door', 'not_opened', 'wrong_direction', 'unknown_goods', 'approach'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                if fault == 'closed_door':
                    terrain = fixture.textured({(0, 0): 'floor', (0, -1): 'floor',
                        (0, -2): 'door', (-1, -2): 'gold', (1, -2): 'gold', (0, -3): 'floor'})
                    self.protect_remote = False; self.fit(terrain)
                    first = self.next_move(terrain); self.ack(first)
                    terrain = fixture.translated(terrain, first.direction)
                    self.observed_result(first, terrain)
                    command = self.next_move(terrain)
                    self.entrance = observation.Entrance()
                    self.assertEqual((3, 5, 0, -1, 5), self.choice(terrain))
                elif fault == 'approach':
                    terrain, command = observation.NativeObservation072Tests.observed_vantage(self)
                    self.entrance = observation.Entrance()
                else:
                    terrain, command = self.armed(opened_ack=fault != 'not_opened',
                        wrong_opening_direction=fault == 'wrong_direction')
                changed = self.reveal(terrain, (8, -3))
                if fault == 'unknown_goods': changed.goods = 'unknown'
                counts = self.credit()
                self.now += 2; self.observe_actual(self.scene(2, 2, changed, beat=True))
                self.assertNotEqual((0, 1, command.id),
                    (self.status().reason, self.status().input_state, self.status().current_command_id))
                self.assertEqual(0, self.lib.ng2_controller_begin(
                    self.engine, command.id, command.not_before_ns, 1, 0, 1))
                self.assertEqual(counts, self.credit())

    def test_accepted_new_gold_cannot_disappear_or_shift_within_same_ticket(self):
        for stage in ('entry', 'interior'):
            for fault in ('removed', 'dirt', 'shifted'):
                with self.subTest(stage=stage, fault=fault):
                    self.fresh_engine(); terrain, command = self.armed(stage)
                    point = self.remote(terrain)
                    accepted = self.reveal(terrain, point)
                    self.preserve(terrain, accepted, command)
                    changed = deepcopy(accepted)
                    if fault == 'removed': del changed.tiles[point]
                    else: changed.tiles[point] = 'dirt'
                    if fault == 'shifted': changed.tiles[(8, -3)] = 'gold'
                    counts = self.credit()
                    self.now += 2; self.observe_actual(self.scene(2, 2, changed, beat=True))
                    self.assertEqual(17, self.status().reason)
                    self.assertEqual(0, self.lib.ng2_controller_begin(
                        self.engine, command.id, command.not_before_ns, 1, 0, 1))
                    self.assertEqual(counts, self.credit())

    def test_original_deadline_prefix_goods_and_control_priority_remain(self):
        for fault in ('deadline_equal', 'deadline_late', 'prefix', 'unstable',
                      'goods', 'cancel', 'owner', 'locked', 'foreground', 'unknown_motion'):
            with self.subTest(fault=fault):
                self.fresh_engine(); terrain, command = self.armed()
                changed = self.reveal(terrain)
                options = {}
                if fault.startswith('deadline'):
                    self.now = command.deadline_ns - 1
                    options['commit'] = command.deadline_ns + int(fault == 'deadline_late')
                else: self.now += 2
                if fault == 'prefix': options['prefix'] = self.prefix + 1
                elif fault == 'unstable': options['stable'] = 0
                elif fault == 'unknown_motion': changed.signature = bytes([40]) * 23296
                elif fault == 'goods': changed.goods = 'visible'
                self.observe_actual(self.scene(2, 2, changed, beat=True), **options)
                if fault in ('cancel', 'owner', 'locked', 'foreground'):
                    self.assertEqual(0, self.status().reason)
                    if fault == 'cancel': self.lib.ng2_controller_cancel(self.engine, self.now, 2)
                    else:
                        flags = {'front': 1, 'locked': 0, 'owner': 1}
                        flags[{'owner': 'owner', 'locked': 'locked', 'foreground': 'front'}[fault]] = int(fault == 'locked')
                        self.tick(**flags)
                expected = {'deadline_late': 17, 'goods': 1, 'cancel': 2, 'owner': 5,
                            'locked': 4, 'foreground': 3, 'unknown_motion': 17}.get(fault, 0)
                self.assertEqual(expected, self.status().reason)
                if fault == 'deadline_equal':
                    self.assertEqual(1, self.lib.ng2_controller_begin(
                        self.engine, command.id, command.deadline_ns, 1, 0, 1))
                elif expected:
                    self.assertEqual(0, self.lib.ng2_controller_begin(
                        self.engine, command.id, command.not_before_ns, 1, 0, 1))
                self.assertEqual((2, 1, 1),
                    (self.status().inputs, self.status().moves, self.status().door_changes))


if __name__ == '__main__':
    unittest.main()
