"""TEST064 initial-ticket regressions from TEST063's third device run.

Recorded83/84 are FLOOR with the same full LEFT decision and strict BLOCKED;
only remote(-4,+1) changes DIRT to UNKNOWN at notBefore-90.060ms commit.
These procedural scenes test that boundary, not missing future game images.
"""
import ctypes as C
from copy import deepcopy
import unittest

from tests import test_native_controller as fixture
from tests import test_native_recovery as recovery_fixture

CORE = fixture.CORE
MS = 1_000_000


class _Entrance(C.Structure):
    _fields_ = [(name, C.c_int32) for name in ('valid', 'x', 'y', 'direction')]


class _Decision(C.Structure):
    _fields_ = [(name, C.c_int32) for name in
                ('direction', 'reason', 'target_x', 'target_y', 'obstacle')]


class NativeDevice064Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = recovery_fixture.CORE
        try:
            recovery_fixture.CORE = CORE
            recovery_fixture.NativeRecoveryTests.setUpClass.__func__(cls)
        finally:
            recovery_fixture.CORE = previous
        cls.lib.ng2_choose.argtypes = [
            C.POINTER(fixture.Scene), C.c_int32, C.c_int32,
            C.POINTER(C.c_uint16), C.c_size_t, C.POINTER(_Entrance),
            C.POINTER(_Decision)]

    @classmethod
    def tearDownClass(cls):
        recovery_fixture.NativeRecoveryTests.tearDownClass.__func__(cls)

    # Share public-entrypoint mechanics, without inheriting historical suites.
    setUp = fixture.NativeControllerTests.setUp
    scene = fixture.NativeControllerTests.scene
    observe = fixture.NativeControllerTests.observe
    tick = fixture.NativeControllerTests.tick
    status = fixture.NativeControllerTests.status
    events = fixture.NativeControllerTests.events
    motion_wait = fixture.NativeControllerTests.motion_wait
    ack = fixture.NativeControllerTests.ack
    fit = fixture.NativeControllerTests.fit
    next_move = fixture.NativeControllerTests.next_move
    fresh_engine = fixture.NativeControllerTests.fresh_engine
    observed_result = fixture.NativeControllerTests.observed_result
    scene_changes = fixture.NativeControllerTests.scene_changes
    scene_details = fixture.NativeControllerTests.scene_details
    recovery = recovery_fixture.NativeRecoveryTests.recovery
    observe_actual = recovery_fixture.NativeRecoveryTests.observe_actual

    def initial(self):
        terrain = fixture.textured({
            **{(x, 0): 'floor' for x in range(-7, 1)},
            (-7, 0): 'stone', (-8, 0): 'door',
            (-8, -1): 'gold', (-8, 1): 'gold',
            (-4, 1): 'dirt', (10, -1): 'dirt', (9, 0): 'floor'})
        self.fit(terrain)
        command = self.next_move()
        self.assertEqual(1, command.direction)
        return terrain, command

    def observe_at(self, terrain, commit, *, capture_end=None,
                   stable=1, prefix=None, state=2):
        self.now = commit
        frame = self.scene(state, 2, terrain, beat=True)
        end = commit if capture_end is None else capture_end
        frame.beat_remaining = ((5 * fixture.SECOND - (end - 1)) %
                                fixture.PERIOD) / fixture.PERIOD
        return self.observe_actual(frame, commit=commit, start=end-2, end=end,
                                   stable=stable, prefix=prefix)

    def choice(self, terrain):
        scene = self.scene(2, 2, terrain, beat=True)
        visits = (C.c_uint16 * 1089)()
        visits[16 * 33 + 16] = 1
        decision = _Decision()
        self.assertEqual(1, self.lib.ng2_choose(C.byref(scene), 0, 0,
            visits, len(visits), C.byref(_Entrance()), C.byref(decision)))
        return tuple(getattr(decision, name) for name, _ in decision._fields_)

    def assert_frozen(self, command, events, wait):
        status = self.status()
        self.assertEqual((0, 1, command.id, 0, 0),
                         (status.reason, status.input_state,
                          status.current_command_id, status.inputs, status.moves),
                         'irrelevant remote flicker must preserve the live initial ticket')
        self.assertEqual(events, b''.join(bytes(row) for row in self.events()))
        self.assertEqual(wait, bytes(self.motion_wait()))
        self.assertEqual((0, 0), (self.tick()[0], self.status().inputs))

    def test_initial_remote_flicker_preserves_ticket_across_publication_window(self):
        for offset in (-100*MS, -90*MS, -50*MS-1, -50*MS, -4*MS, 5*MS, 10*MS):
            with self.subTest(offset=offset):
                self.fresh_engine()
                terrain, command = self.initial()
                changed = deepcopy(terrain)
                del changed.tiles[(-4, 1)]
                self.assertEqual(self.choice(terrain), self.choice(changed))
                events = b''.join(bytes(row) for row in self.events())
                wait = bytes(self.motion_wait())
                self.observe_at(changed, command.not_before_ns + offset)
                self.assert_frozen(command, events, wait)
                self.assertEqual([], self.scene_changes())
                self.assertEqual(0, self.recovery().initial_reacquisitions)
                if offset == -90*MS:
                    self.ack(command)
                    self.observed_result(command, fixture.translated(changed, 1))
                    self.assertEqual((1, 1, 1), (self.status().inputs,
                                     self.status().moves, self.status().lead_confirmed))

    def test_initial_remote_flicker_after_replan_budget_and_refit_keeps_budget(self):
        terrain, command = self.initial()
        for count, cell in enumerate(((-10, 4), (-9, 4)), 1):
            terrain = deepcopy(terrain)
            terrain.tiles[cell] = 'stone'
            self.now += 2
            self.observe_actual(self.scene(2, 2, terrain, beat=True))
            command = self.next_move()
            self.assertEqual((count, 1), (self.scene_changes()[-1].replan_count,
                                         self.scene_changes()[-1].replan_allowed))
        self.now = command.deadline_ns + 1
        self.assertEqual(1, self.lib.ng2_controller_complete(self.engine, command.id, self.now, 0))
        for _ in range(27):
            self.now += 100 * MS
            self.observe_actual(self.scene(2, 2, terrain, beat=True))
        command = self.next_move()
        old_recovery = bytes(self.recovery())
        old_changes = b''.join(bytes(row) for row in self.scene_changes())
        old_events = b''.join(bytes(row) for row in self.events())
        old_wait = bytes(self.motion_wait())
        changed = deepcopy(terrain)
        del changed.tiles[(-4, 1)]
        self.observe_at(changed, command.not_before_ns - 90*MS)
        self.assert_frozen(command, old_events, old_wait)
        self.assertEqual(old_recovery, bytes(self.recovery()))
        self.assertEqual(old_changes, b''.join(bytes(row) for row in self.scene_changes()))
        # Coalescing gives no extra replan: the next non-eligible change still
        # fails the original two-replan cap, even after a new model was fitted.
        blocked = deepcopy(changed)
        blocked.tiles[(-8, 4)] = 'stone'
        self.observe_at(blocked, command.not_before_ns - 80*MS)
        self.assertEqual((2, 0), (self.scene_changes()[-1].replan_count,
                                 self.scene_changes()[-1].replan_allowed))
        self.assertEqual((17, 0, 0), (self.status().reason,
                                     self.status().inputs, self.status().moves))

    def test_initial_remote_coalescing_uses_actual_commit_and_original_deadline(self):
        terrain, command = self.initial()
        changed = deepcopy(terrain)
        del changed.tiles[(-4, 1)]
        events = b''.join(bytes(row) for row in self.events())
        wait = bytes(self.motion_wait())
        self.observe_at(changed, command.not_before_ns - 90*MS,
                        capture_end=command.not_before_ns - 130*MS)
        self.assert_frozen(command, events, wait)
        # A capture ending before D cannot restore an already expired ticket.
        later = deepcopy(terrain)
        self.observe_at(later, command.deadline_ns + 1,
                        capture_end=command.deadline_ns - 1)
        self.tick()
        self.assertNotEqual(command.id, self.status().current_command_id)
        self.assertEqual(0, self.lib.ng2_controller_begin(self.engine,
                         command.id, command.deadline_ns + 1, 1, 0, 1))
        self.assertEqual((0, 0), (self.status().inputs, self.status().moves))
        self.assertEqual(command.deadline_ns, self.events()[0].command.deadline_ns)

    def test_initial_early_window_rejects_changed_authority(self):
        for case in ('near', 'protected', 'gold', 'stone', 'door', 'item',
                     'full_choice', 'unknown_motion', 'state', 'partial',
                     'unstable', 'wrong_prefix'):
            with self.subTest(case=case):
                self.fresh_engine()
                terrain, command = self.initial()
                changed = deepcopy(terrain)
                del changed.tiles[(-4, 1)]
                state, stable, prefix = 2, 1, self.prefix
                if case == 'near':
                    changed.tiles[(-1, 1)] = 'floor'
                elif case == 'protected':
                    changed.protected.add((-10, 4))
                elif case == 'gold':
                    del changed.tiles[(-8, -1)]
                elif case in ('stone', 'door', 'item'):
                    changed.tiles[(-4, 1)] = case
                elif case == 'full_choice':
                    del changed.tiles[(-4, 0)]
                    self.assertNotEqual(self.choice(terrain), self.choice(changed))
                elif case == 'unknown_motion':
                    changed.signature = bytes([40]) * 23296
                elif case == 'state':
                    state = 0
                elif case == 'partial':
                    changed.goods = 'partial'
                elif case == 'unstable':
                    stable = 0
                else:
                    prefix += 1
                self.observe_at(changed, command.not_before_ns - 90*MS,
                                state=state, stable=stable, prefix=prefix)
                if case in ('unstable', 'wrong_prefix'):
                    self.assertEqual(command.id, self.status().current_command_id)
                    self.assertEqual(1, self.status().discarded_frames)
                else:
                    self.tick()
                    self.assertNotEqual(command.id, self.status().current_command_id,
                        'changed authority must not be coalesced into the issued ticket')
                    self.assertEqual(0, self.lib.ng2_controller_begin(self.engine,
                        command.id, command.not_before_ns, 1, 0, 1))
                self.assertEqual((0, 0), (self.status().inputs, self.status().moves))

    def test_initial_early_window_control_guards_and_goods_priority(self):
        for case in ('foreground', 'locked', 'owner', 'cancel', 'goods'):
            with self.subTest(case=case):
                self.fresh_engine()
                terrain, command = self.initial()
                changed = deepcopy(terrain)
                del changed.tiles[(-4, 1)]
                if case == 'goods':
                    changed.goods = 'visible'
                self.observe_at(changed, command.not_before_ns - 90*MS)
                if case == 'cancel':
                    self.lib.ng2_controller_cancel(self.engine, self.now, 2)
                front, locked, owner = int(case != 'foreground'), int(case == 'locked'), int(case != 'owner')
                self.now = command.not_before_ns
                self.assertEqual(0, self.lib.ng2_controller_begin(self.engine,
                                 command.id, self.now, front, locked, owner))
                self.assertEqual((0, 0), (self.status().inputs, self.status().moves))
                if case == 'goods':
                    self.assertEqual((1, 1), (self.status().reason, self.status().goods))


if __name__ == '__main__':
    unittest.main()
