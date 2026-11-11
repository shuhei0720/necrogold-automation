"""TEST080: a reached local passage mouth may be independently proved closed.

The received TEST079 final world mouth became observed DIRT while the player
stood at its inboard neighbour. These maps, images and clocks are procedural
public-C units. They do not reconstruct the omitted response capture 160 or
prove the iPhone's later restart/shop result.
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
from tests import test_native_passage072 as passage
from tests import test_native_observation072 as observation

CORE = mechanics.CORE
PERIOD = fixture.PERIOD
SECOND = fixture.SECOND


class NativeClosedMouth080Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = mechanics.CORE
        cls.baseline_directory = None
        try:
            mechanics.CORE = CORE
            baseline = os.environ.get('NECRO_TEST080_BASELINE_CONTROLLER')
            if baseline:
                cls.baseline_directory = tempfile.TemporaryDirectory(prefix='test080-mouth-baseline-')
                directory = Path(cls.baseline_directory.name)
                for path in CORE.glob('NG2*'):
                    if path.suffix in ('.c', '.h'):
                        shutil.copyfile(path, directory / path.name)
                shutil.copyfile(baseline, directory / 'NG2Controller.c')
                mechanics.CORE = directory
            mechanics.NativeRecoveryTests.setUpClass.__func__(cls)
        finally:
            mechanics.CORE = previous
        cls.lib.ng2_motion.argtypes = [C.POINTER(fixture.Scene), C.POINTER(fixture.Scene),
            C.c_int32, C.POINTER(observation.Motion)]

    @classmethod
    def tearDownClass(cls):
        mechanics.NativeRecoveryTests.tearDownClass.__func__(cls)
        if cls.baseline_directory:
            cls.baseline_directory.cleanup()

    setUp = fixture.NativeControllerTests.setUp
    status = fixture.NativeControllerTests.status
    events = fixture.NativeControllerTests.events
    tick = fixture.NativeControllerTests.tick
    ack = fixture.NativeControllerTests.ack
    motion_wait = fixture.NativeControllerTests.motion_wait
    fresh_engine = fixture.NativeControllerTests.fresh_engine
    scene = passage.NativePassage072Tests.scene
    observe = passage.NativePassage072Tests.observe
    fit_clear = passage.NativePassage072Tests.fit_clear
    next_operation = passage.NativePassage072Tests.next_operation
    next_move = passage.NativePassage072Tests.next_move
    moved = passage.NativePassage072Tests.moved
    observe_actual = mechanics.NativeRecoveryTests.observe_actual
    recovery = mechanics.NativeRecoveryTests.recovery
    recovery_samples = mechanics.NativeRecoveryTests.recovery_samples
    all_public_bytes = mechanics.NativeRecoveryTests.all_public_bytes
    reject_old_callbacks_without_mutation = mechanics.NativeRecoveryTests.reject_old_callbacks_without_mutation

    def closed_wait(self, side='upper', wall='dirt', second=None, steps=2, close_on_arrival=True):
        mouth = (0, -3) if side == 'upper' else (-3, 0)
        direction = 3 if side == 'upper' else 1
        dx, dy = fixture.DIRS[direction]
        terrain = self.fit_clear(passage.passage_room(mouth, second=second))
        commands = []
        for index in range(steps):
            command = self.next_move(terrain)
            self.assertEqual(direction, command.direction)
            commands.append(command)
            reveal = {(mouth[0]-(index+1)*dx, mouth[1]-(index+1)*dy): wall} if index == steps-1 and close_on_arrival else None
            terrain = self.moved(terrain, command, reveal)
        self.assertEqual((steps*dx, steps*dy), (self.status().x, self.status().y))
        self.assertEqual((steps, steps, 0, 0),
            (self.status().moves, self.status().inputs, self.status().restarts, self.status().reason))
        self.wall_local = (mouth[0]-steps*dx, mouth[1]-steps*dy)
        self.direction = direction
        return terrain, commands, self.now

    def strict_motion(self, before, after):
        out = observation.Motion()
        self.assertEqual(1, self.lib.ng2_motion(C.byref(before), C.byref(after),
            self.direction, C.byref(out)))
        return out.kind, out.dx, out.dy

    def prove(self, terrain, delay=100_000_000):
        self.now += delay
        self.assertEqual((2, 0, 0), self.strict_motion(self.scene(terrain), self.scene(terrain)))
        self.assertEqual(1, self.observe(terrain))

    def assert_existing_restart(self, terrain):
        before = self.status()
        pause = self.next_operation(terrain)
        self.assertEqual((0, 2, 0), (self.status().reason, pause.kind, self.status().restarts),
            'an independently observed closed local mouth must return to the existing restart cycle')
        self.assertEqual((before.inputs, before.moves, before.last_ordinal),
            (self.status().inputs, self.status().moves, self.status().last_ordinal))
        self.ack(pause)
        self.now += 2
        self.observe(self.scene(terrain, state=1))
        self.now += 200_000_000
        restart = self.next_operation(terrain)
        self.assertEqual((3, 0, 0), (restart.kind, self.status().reason, self.status().restarts))
        self.assertGreater(restart.id, pause.id)
        self.assertEqual((before.inputs, before.moves, before.walk_started_ns, before.started_ns),
            (self.status().inputs, self.status().moves, self.status().walk_started_ns, self.status().started_ns))
        self.assertEqual(0, len([e for e in self.events() if e.command.kind == 4 and not e.begin_ns]))
        return pause, restart

    def test_independent_closed_upper_and_left_mouth_use_existing_restart_without_step_credit(self):
        for side in ('upper', 'left'):
            for wall in ('dirt', 'stone'):
                with self.subTest(side=side, wall=wall):
                    self.fresh_engine()
                    terrain, commands, _ = self.closed_wait(side, wall)
                    self.assertEqual(0, self.tick()[0], 'the same MOVED capture is not an independent inspection')
                    self.prove(terrain)
                    _, restart = self.assert_existing_restart(terrain)
                    self.assertEqual((2, 2, 0, 0), (self.status().inputs, self.status().moves,
                        self.status().door_changes, self.status().terrain_changes))
                    for command in commands:
                        self.reject_old_callbacks_without_mutation(command)
                    if side == 'upper' and wall == 'dirt':
                        previous = self.status()
                        self.ack(restart)
                        self.now += 100_000_000
                        fresh = passage.passage_room()
                        self.observe(self.scene(fresh, fingerprint=bytes([160])*48))
                        self.assertEqual((1, 0, 0, 0), (self.status().restarts,
                            self.status().x, self.status().y, self.status().lead_confirmed))
                        self.assertEqual((previous.inputs, previous.moves, previous.walk_started_ns,
                            previous.started_ns, previous.last_ordinal), (self.status().inputs,
                            self.status().moves, self.status().walk_started_ns,
                            self.status().started_ns, self.status().last_ordinal))
                        self.fit_clear(fresh)
                        following = self.next_move(fresh)
                        self.assertEqual((3, previous.last_ordinal+1),
                            (following.direction, following.ordinal),
                            'the same world mouth is eligible again in the new level')
                        self.assertGreater(following.id, restart.id)

        # The last confirmed MOVE may precede the blocked-route observation.
        # Its unchanged pose still establishes arrival; that later anchor must
        # itself get a second independent stationary observation.
        self.fresh_engine()
        terrain, commands, _ = self.closed_wait(close_on_arrival=False)
        last_move_capture = self.events()[-1].observed_capture_id
        changed = deepcopy(terrain); changed.tiles[self.wall_local] = 'dirt'
        self.now += 100_000_000
        self.observe(changed)
        self.assertGreater(self.status().last_capture_id, last_move_capture)
        self.assertEqual((0, 0), (self.tick()[0], self.status().restarts))
        self.prove(changed)
        self.assert_existing_restart(changed)

    def test_only_closed_candidate_retires_and_other_fixed_candidate_is_still_inspected(self):
        terrain, _, _ = self.closed_wait(second=(-3, 0))
        self.prove(terrain)
        self.assertEqual((0, 0, 2, 2), (self.status().reason, self.status().restarts,
            self.status().moves, self.status().inputs))
        first = self.next_move(terrain)
        self.assertEqual(1, first.direction)
        terrain = self.moved(terrain, first)
        for _ in range(8):
            if (self.status().x, self.status().y) == (-4, 0):
                break
            command = self.next_move(terrain)
            terrain = self.moved(terrain, command)
        self.assertEqual((-4, 0), (self.status().x, self.status().y))
        self.assertEqual(0, self.tick()[0])
        self.now += 100_000_000
        self.observe(terrain)
        self.assert_existing_restart(terrain)

        # Another UNKNOWN outer goal remains unresolved after its full wait.
        # Closing the second candidate cannot turn that first result into a
        # completed inspection or authorize a restart.
        self.fresh_engine()
        terrain = passage.passage_room(second=(-3, 0), outside=False)
        terrain.tiles[(-4, 0)] = 'floor'
        self.fit_clear(terrain)
        for _ in range(3):
            command = self.next_move(terrain)
            self.assertEqual(3, command.direction)
            terrain = self.moved(terrain, command)
        self.assertEqual((0, -3), (self.status().x, self.status().y))
        self.now += 2*PERIOD
        self.tick()
        self.assertEqual(0, self.status().restarts)
        for _ in range(8):
            command = self.next_move(terrain)
            dx, dy = fixture.DIRS[command.direction]
            destination = (self.status().x+dx, self.status().y+dy)
            reveal = {(-3-destination[0], -destination[1]): 'dirt'} if destination == (-2, 0) else None
            terrain = self.moved(terrain, command, reveal)
            if destination == (-2, 0): break
        self.assertEqual((-2, 0), (self.status().x, self.status().y))
        self.prove(terrain)
        self.assertEqual((12, 0), (self.status().reason, self.status().restarts))
        self.assertNotEqual(3, self.tick()[1].kind)

    def test_unknown_changed_or_unsupported_mouth_never_becomes_a_closed_inspection(self):
        for fault in ('unknown', 'different_wall', 'unsupported'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                terrain, _, waiting = self.closed_wait()
                changed = deepcopy(terrain)
                if fault == 'unknown': changed.tiles.pop(self.wall_local)
                elif fault == 'different_wall': changed.tiles[self.wall_local] = 'stone'
                else:
                    x, y = self.wall_local
                    changed.tiles.pop((x-1, y), None)
                self.now += 100_000_000
                self.observe(changed)
                self.assertNotEqual(3, self.tick()[1].kind)
                self.assertEqual(0, self.status().restarts)
                self.now = waiting+2*PERIOD
                self.tick()
                self.assertEqual((12, 2, 2, 0), (self.status().reason,
                    self.status().moves, self.status().inputs, self.status().restarts))
        self.fresh_engine()
        terrain, _, _ = self.closed_wait(steps=1)
        self.prove(terrain)
        self.assertEqual((0, 0), (self.status().reason, self.status().restarts))
        following = self.next_move(terrain)
        self.assertEqual(3, following.direction, 'a remote closed mouth does not retire the approach before reaching its inboard cell')

    def test_independence_stable_prefix_and_strict_zero_are_required_before_any_restart(self):
        for fault in ('same_id', 'unstable', 'prefix', 'unknown', 'nonzero'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                terrain, _, waiting = self.closed_wait()
                latest = self.scene(terrain)
                self.now += 100_000_000
                if fault == 'same_id':
                    self.assertEqual(0, self.lib.ng2_controller_observe_at(self.engine,
                        C.byref(latest), self.number, self.now-2, self.now, self.prefix, 1, self.now))
                elif fault in ('unstable', 'prefix'):
                    self.observe_actual(latest, stable=0 if fault == 'unstable' else 1,
                        prefix=self.prefix+1 if fault == 'prefix' else self.prefix)
                else:
                    if fault == 'unknown': latest.signature[:] = bytes(len(latest.signature))
                    else:
                        shifted = fixture.translated(terrain, self.direction)
                        latest.signature[:] = self.scene(shifted).signature
                    self.assertNotEqual((2, 0, 0), self.strict_motion(self.scene(terrain), latest))
                    self.observe_actual(latest)
                self.assertNotEqual(3, self.tick()[1].kind)
                self.assertEqual((2, 2, 0), (self.status().moves, self.status().inputs, self.status().restarts))
                self.now = waiting+2*PERIOD
                self.tick()
                self.assertEqual(12, self.status().reason)

    def test_original_two_beat_and_walk_session_deadlines_are_not_extended(self):
        for boundary in ('just_before', 'equal', 'after', 'wait_horizon', 'walk', 'session'):
            with self.subTest(boundary=boundary):
                self.fresh_engine()
                terrain, _, waiting = self.closed_wait()
                if boundary == 'just_before':
                    self.now = waiting+2*PERIOD-1
                    self.observe(terrain)
                    self.assert_existing_restart(terrain)
                elif boundary in ('equal', 'after'):
                    self.now = waiting+2*PERIOD+(boundary == 'after')
                    self.observe(terrain)
                    self.assertEqual((12, 0, 2), (self.status().reason,
                        self.status().restarts, self.status().inputs))
                elif boundary == 'wait_horizon':
                    # This fixture has no recovery before entering the wait;
                    # its inherited sync horizon is the first floor epoch+12s.
                    self.assertEqual(1, self.recovery().post_move_reacquisitions)
                    self.now = self.status().walk_started_ns+12*SECOND
                    self.observe(terrain)
                    self.assertEqual((8, 0, 2), (self.status().reason,
                        self.status().restarts, self.status().inputs))
                else:
                    self.now = self.status().walk_started_ns+45*SECOND if boundary == 'walk' else self.status().started_ns+180*SECOND
                    self.tick()
                    self.assertEqual((14 if boundary == 'walk' else 15, 0, 2), (self.status().reason,
                        self.status().restarts, self.status().inputs))

    def test_gold_goods_protection_cancel_owner_and_unknown_input_preempt_closed_skip(self):
        for fault in ('gold', 'visible', 'partial', 'item', 'protected', 'cancel', 'owner', 'foreground'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                terrain, _, _ = self.closed_wait()
                changed = deepcopy(terrain)
                if fault == 'gold':
                    changed.tiles.update({(-1, -2): 'gold', (1, -2): 'gold', (0, -2): 'door'})
                    changed.gold = {p for p, v in changed.tiles.items() if v == 'gold'}
                elif fault in ('visible', 'partial'): changed.goods = fault
                elif fault == 'item': changed.tiles[(4, 2)] = 'item'
                elif fault == 'protected': changed.protected.add((4, 2))
                self.now += 100_000_000
                if fault == 'cancel': self.lib.ng2_controller_cancel(self.engine, self.now, 0)
                elif fault in ('owner', 'foreground'):
                    self.tick(owner=0 if fault == 'owner' else 1, front=0 if fault == 'foreground' else 1)
                else: self.observe(changed)
                self.assertNotEqual(3, self.tick()[1].kind)
                self.assertEqual((2, 2, 0), (self.status().moves, self.status().inputs, self.status().restarts))
        self.fresh_engine()
        terrain = self.fit_clear(passage.passage_room())
        old = self.next_move(terrain)
        self.now += 2
        closed = deepcopy(terrain); closed.tiles[(0, -3)] = 'dirt'
        self.observe(closed)
        self.assertEqual((0, 0, 0), (self.status().moves, self.status().inputs, self.status().restarts))
        self.assertEqual((3, 0, 0), (self.events()[-1].outcome,
            self.events()[-1].begin_ns, self.events()[-1].motion))
        self.assertNotIn(self.tick()[1].kind, (3, 4),
            'an unstarted zero-move candidate cannot use reached-mouth inspection')
        self.reject_old_callbacks_without_mutation(old)
        self.fresh_engine()
        terrain = self.fit_clear(passage.passage_room())
        old = self.next_move(terrain)
        self.now = old.not_before_ns
        self.assertEqual(1, self.lib.ng2_controller_begin(self.engine, old.id, self.now, 1, 0, 1))
        self.now += 2
        self.assertEqual(1, self.lib.ng2_controller_complete(self.engine, old.id, self.now, -1))
        before = self.all_public_bytes()
        self.now += 100_000_000
        changed = deepcopy(terrain); changed.tiles[(0, -3)] = 'dirt'
        self.observe(changed)
        self.assertEqual(before, self.all_public_bytes())
        self.assertEqual((4, 0), (self.status().input_state, self.status().restarts))
        self.assertNotIn(self.tick()[1].kind, (3, 4))


if __name__ == '__main__':
    unittest.main()
