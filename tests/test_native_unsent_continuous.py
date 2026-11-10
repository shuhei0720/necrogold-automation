"""TEST063: a known-unsent continuous ticket may obtain a new bounded beat.

Procedural signatures and public C entrypoints establish control semantics.
They do not supply the unrecorded continuation of the TEST062 device run.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from tests import test_native_controller as fixture
from tests import test_native_recovery as fixture_recovery

CORE = fixture_recovery.CORE
SECOND = fixture_recovery.SECOND


class NativeUnsentContinuousTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = fixture_recovery.CORE
        cls.baseline_directory = None
        try:
            fixture_recovery.CORE = CORE
            baseline = os.environ.get('NECRO_TEST063_BASELINE_CONTROLLER')
            if baseline:
                cls.baseline_directory = tempfile.TemporaryDirectory(prefix='test063-baseline-')
                directory = Path(cls.baseline_directory.name)
                for path in CORE.glob('NG2*'):
                    if path.suffix in ('.c', '.h'):
                        shutil.copyfile(path, directory / path.name)
                shutil.copyfile(baseline, directory / 'NG2Controller.c')
                fixture_recovery.CORE = directory
            fixture_recovery.NativeRecoveryTests.setUpClass.__func__(cls)
        finally:
            fixture_recovery.CORE = previous

    @classmethod
    def tearDownClass(cls):
        fixture_recovery.NativeRecoveryTests.tearDownClass.__func__(cls)
        if cls.baseline_directory:
            cls.baseline_directory.cleanup()

    # Share only mechanics; do not inherit either historical test collection.
    setUp = fixture_recovery.NativeRecoveryTests.setUp
    scene = fixture_recovery.NativeRecoveryTests.scene
    observe = fixture_recovery.NativeRecoveryTests.observe
    observe_actual = fixture_recovery.NativeRecoveryTests.observe_actual
    tick = fixture_recovery.NativeRecoveryTests.tick
    status = fixture_recovery.NativeRecoveryTests.status
    events = fixture_recovery.NativeRecoveryTests.events
    motion_wait = fixture_recovery.NativeRecoveryTests.motion_wait
    recovery = fixture_recovery.NativeRecoveryTests.recovery
    ack = fixture_recovery.NativeRecoveryTests.ack
    fit = fixture_recovery.NativeRecoveryTests.fit
    next_move = fixture_recovery.NativeRecoveryTests.next_move
    fresh_engine = fixture_recovery.NativeRecoveryTests.fresh_engine
    publish_procedural_candidate = fixture.NativeControllerTests.publish_procedural_candidate
    continuous_walk = fixture.NativeControllerTests.continuous_walk
    scene_details = fixture.NativeControllerTests.scene_details

    def observed_result(self, command, terrain, offset=80_000_002):
        self.now = max(self.now + 2, command.target_ns + offset)
        end = self.now
        status = self.status()
        previous = (status.moves, status.door_changes, status.terrain_changes)
        commit = end + getattr(self, 'proof_commit_offset_ns', 0)
        self.observe_actual(self.scene(2, 2, terrain, beat=True), commit=commit)
        self.now = commit
        status = self.status()
        if (status.moves, status.door_changes, status.terrain_changes) != previous:
            self.verified_capture_end = end
            self.verified_commit = commit

    def armed(self, moves=2, next_kind='floor'):
        self.proof_commit_offset_ns = getattr(self, 'proof_commit_offset_ns', 0)
        gate_y = -3 if next_kind == 'door' else -4
        terrain = fixture.textured({(0, 0): 'floor', (0, -1): 'floor', (0, -2): 'floor',
            (0, -3): next_kind, (0, gate_y): 'door', (-1, gate_y): 'gold',
            (1, gate_y): 'gold', (-4, -2): 'stone', (5, 1): 'stone'})
        terrain, command = self.continuous_walk(moves=moves, direction=3, terrain=terrain)
        self.assertEqual((moves, moves, 1, 1), (self.status().inputs, self.status().moves,
                         self.status().lead_confirmed, self.status().input_state))
        return terrain, command

    def frozen(self):
        return (bytes(self.status()), tuple(bytes(e) for e in self.events()), bytes(self.recovery()))

    def late_complete(self, command, at=None):
        self.now = command.deadline_ns + 8_039_775 if at is None else at
        return self.lib.ng2_controller_complete(self.engine, command.id, self.now, 0)

    def assert_retired(self, command, counts=(2, 2)):
        s = self.status()
        self.assertEqual((0, 0, 4, 0, 0), (s.reason, s.terminal, s.phase,
                         s.input_state, s.current_command_id),
                         'known-unsent continuous deadline must reacquire, not finish CAPTURE/LATE')
        self.assertEqual(counts, (s.inputs, s.moves))
        row = next(e for e in self.events() if e.command.id == command.id)
        self.assertEqual((3, 9, 0), (row.outcome, row.reason, row.begin_ns))
        self.assertEqual(bytes(command), bytes(row.command))
        self.assertEqual((2, 1), (self.recovery().mode, self.recovery().post_move_reacquisitions))

    def next_recovery_ticket(self, terrain):
        for _ in range(100):
            self.now += 20_000_000
            self.assertEqual(1, self.observe_actual(self.scene(2, 2, terrain, beat=True)),
                             'new live frames must remain admissible after stale callback rejection')
            ready, command = self.tick()
            self.assertEqual(0, self.status().reason)
            if ready:
                self.assertEqual(4, command.kind)
                self.assertGreaterEqual(command.not_before_ns - self.now, 50_000_000)
                return command
        self.fail('live bounded recovery did not publish a future ticket')

    def test_complete_zero_late_retires_known_unsent_ticket_and_restarts_from_verified_pose(self):
        _, command = self.armed()
        pose = (self.status().x, self.status().y, self.status().last_completed_id)
        self.assertEqual(1, self.late_complete(command))
        self.assert_retired(command)
        self.assertEqual(pose, (self.status().x, self.status().y, self.status().last_completed_id))
        r = self.recovery(); latest = r.records[min(1, r.record_count - 1)]
        self.assertEqual((5, 2, self.now), (latest.reason, latest.clock, latest.at_ns))
        self.assertEqual(self.verified_commit + 12 * SECOND, latest.sync_deadline_ns)

    def test_direct_begin_and_tick_late_share_definite_unsent_retirement(self):
        for entry in ('begin', 'tick', 'backdated_begin'):
            with self.subTest(entry=entry):
                self.fresh_engine(); terrain, command = self.armed(); self.now = command.deadline_ns + 1
                if entry == 'backdated_begin':
                    self.now = command.deadline_ns - 1
                    self.observe_actual(self.scene(2, 2, terrain, beat=True), commit=command.deadline_ns + 1)
                    self.now = command.not_before_ns
                if entry in ('begin', 'backdated_begin'):
                    self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, command.id, self.now, 1, 0, 1))
                else:
                    ready, ticket = self.tick()
                    self.assertEqual((0, 0), (ready, ticket.kind))
                self.assert_retired(command)
                if entry == 'backdated_begin':
                    r = self.recovery(); latest = r.records[min(1, r.record_count - 1)]
                    self.assertEqual(command.deadline_ns + 1, latest.at_ns)

    def test_same_and_fresh_reissues_retire_without_mutating_old_fields(self):
        for policy in ('same', 'fresh'):
            with self.subTest(policy=policy):
                self.fresh_engine(); terrain, command = self.armed(moves=1)
                changed = deepcopy(terrain)
                changed.tiles[(-10, 4)] = 'stone'
                if policy == 'fresh': changed.tiles[(0, -1)] = 'dirt'
                self.now += 2; self.observe_actual(self.scene(2, 2, changed, beat=True))
                ready, replacement = self.tick()
                self.assertEqual((1, 4), (ready, replacement.kind))
                self.assertEqual(2 if policy == 'same' else 12, self.scene_details()[-1].validation)
                self.assertEqual((command.target_ns, command.not_before_ns, command.deadline_ns, command.ordinal),
                                 (replacement.target_ns, replacement.not_before_ns, replacement.deadline_ns, replacement.ordinal))
                self.assertEqual(1, self.late_complete(replacement))
                self.assert_retired(replacement, counts=(1, 1))

    def test_expired_old_callbacks_cannot_advance_recovery_state_or_clock(self):
        terrain, old = self.armed(); self.late_complete(old)
        before = self.frozen(); future = self.now + 30 * SECOND
        self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, old.id, future, 1, 0, 1))
        for outcome in (-1, 0, 1):
            self.assertEqual(0, self.lib.ng2_controller_complete(self.engine, old.id, future, outcome))
        self.assertEqual(before, self.frozen())
        new = self.next_recovery_ticket(terrain); before = self.frozen()
        self.assertEqual(0, self.lib.ng2_controller_complete(self.engine, old.id, future, 0))
        self.assertEqual(before, self.frozen()); self.assertNotEqual(old.id, new.id)

    def test_new_slot_is_future_and_prepared_without_extra_input(self):
        terrain, old = self.armed(); self.late_complete(old)
        self.assert_retired(old)
        new = self.next_recovery_ticket(terrain)
        self.assertGreater(new.target_ns, old.target_ns)
        self.assertNotEqual(new.id, old.id)
        self.assertEqual((2, 2), (self.status().inputs, self.status().moves))
        self.ack(new)
        self.assertEqual((3, 2), (self.status().inputs, self.status().moves))

    def test_in_time_complete_zero_does_not_recover_and_deadline_equality_can_begin(self):
        for boundary in ('complete', 'begin'):
            with self.subTest(boundary=boundary):
                self.fresh_engine(); _, command = self.armed(); self.now = command.deadline_ns
                if boundary == 'complete':
                    self.assertEqual(1, self.lib.ng2_controller_complete(self.engine, command.id, self.now, 0))
                    self.assertEqual(6, self.status().reason)
                else:
                    self.assertEqual(1, self.lib.ng2_controller_begin(self.engine, command.id, self.now, 1, 0, 1))
                    self.assertEqual(2, self.status().input_state)
                self.assertEqual(0, self.recovery().post_move_reacquisitions)

    def test_started_ack_unknown_cancel_and_goods_never_use_unsent_recovery(self):
        for variant in ('started', 'ack', 'unknown', 'blocked', 'signature_drift', 'cancel', 'goods'):
            with self.subTest(variant=variant):
                self.fresh_engine(); terrain, command = self.armed()
                if variant == 'signature_drift':
                    changed = deepcopy(terrain); changed.signature = bytes([40]) * 23296
                    before = self.scene(2, 2, terrain, beat=True)
                    self.now += 2; after = self.scene(2, 2, changed, beat=True)
                    self.assertEqual(bytes(before.tiles), bytes(after.tiles))
                    self.assertEqual(bytes(before.protected_cells), bytes(after.protected_cells))
                    class Decision(C.Structure):
                        _fields_ = [(key, C.c_int32) for key in ('direction', 'reason', 'target_x', 'target_y', 'obstacle')]
                    class Entrance(C.Structure):
                        _fields_ = [(key, C.c_int32) for key in ('valid', 'x', 'y', 'direction')]
                    class Motion(C.Structure):
                        _fields_ = [(key, C.c_int32) for key in ('kind', 'dx', 'dy')]
                    choose = self.lib.ng2_choose
                    choose.argtypes = [C.POINTER(fixture.Scene), C.c_int32, C.c_int32,
                                       C.POINTER(C.c_uint16), C.c_size_t, C.POINTER(Entrance), C.POINTER(Decision)]
                    visits = (C.c_uint16 * 1089)(); entrance = Entrance(); choices = []
                    for frame in (before, after):
                        choice = Decision()
                        self.assertEqual(1, choose(C.byref(frame), self.status().x, self.status().y,
                                         visits, len(visits), C.byref(entrance), C.byref(choice)))
                        choices.append(bytes(choice))
                    self.assertEqual(choices[0], choices[1], 'signature drift leaves all five route fields unchanged')
                    motion = self.lib.ng2_motion
                    motion.argtypes = [C.POINTER(fixture.Scene), C.POINTER(fixture.Scene), C.c_int32, C.POINTER(Motion)]
                    result = Motion()
                    self.assertEqual(1, motion(C.byref(before), C.byref(after), command.direction, C.byref(result)))
                    self.assertEqual(0, result.kind, 'same-grid signature drift is actual UNKNOWN, not strict BLOCKED')
                    self.assertEqual(1, self.observe_actual(after))
                    self.assertEqual((1, command.id, 0),
                                     (self.status().input_state, self.status().current_command_id, self.status().reason))
                elif variant == 'blocked':
                    self.ack(command); self.observed_result(command, terrain)
                    self.assertEqual(10, self.status().reason)
                elif variant in ('started', 'ack', 'unknown'):
                    self.now = command.not_before_ns
                    self.assertEqual(1, self.lib.ng2_controller_begin(self.engine, command.id, self.now, 1, 0, 1))
                    if variant != 'started':
                        self.lib.ng2_controller_complete(self.engine, command.id, self.now + 1, 1 if variant == 'ack' else -1)
                elif variant == 'cancel': self.lib.ng2_controller_cancel(self.engine, self.now, 2)
                else:
                    goods = deepcopy(terrain); goods.goods = 'visible'; self.now += 2
                    self.observe_actual(self.scene(2, 2, goods, beat=True))
                self.late_complete(command)
                self.assertEqual(0, self.recovery().post_move_reacquisitions)
                self.assertEqual(2 + (variant in ('ack', 'unknown', 'blocked')), self.status().inputs)
                if variant == 'goods': self.assertEqual(1, self.status().goods)
                if variant == 'signature_drift':
                    self.assertEqual((6, 2, 2), (self.status().reason, self.status().inputs, self.status().moves))

    def test_live_authority_failures_prioritize_cancellation_over_recovery(self):
        for front, locked, owner, reason in ((0, 0, 1, 3), (1, 1, 1, 4), (1, 0, 0, 5)):
            with self.subTest(reason=reason):
                self.fresh_engine(); _, command = self.armed(); self.now = command.deadline_ns + 1
                self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, command.id, self.now, front, locked, owner))
                self.assertEqual((reason, 0), (self.status().reason, self.recovery().post_move_reacquisitions))

    def test_proof_twelve_second_equality_and_late_stop_without_new_episode(self):
        for extra in (0, 1):
            with self.subTest(extra=extra):
                self.fresh_engine(); _, command = self.armed()
                self.late_complete(command, self.verified_commit + 12 * SECOND + extra)
                self.assertEqual((8, 0, 2, 2), (self.status().reason,
                                 self.recovery().post_move_reacquisitions, self.status().inputs, self.status().moves))

    def test_repeated_unsent_recovery_keeps_original_episode_and_deadline(self):
        terrain, old = self.armed(); self.late_complete(old)
        initial = self.recovery(); deadline = initial.records[0].sync_deadline_ns
        for _ in range(2):
            new = self.next_recovery_ticket(terrain); self.late_complete(new)
            r = self.recovery(); latest = r.records[min(1, r.record_count - 1)]
            self.assertEqual((initial.episode_id, 1, deadline),
                             (r.episode_id, r.post_move_reacquisitions, latest.sync_deadline_ns))
            self.assertEqual((2, 2, 0), (self.status().inputs, self.status().moves, self.status().reason))
        self.now = deadline
        self.tick()
        self.assertEqual((8, 1), (self.status().reason, self.recovery().post_move_reacquisitions))

    def test_only_new_verified_motion_can_start_new_recovery_budget(self):
        for proof in ('floor', 'door', 'dirt'):
            with self.subTest(proof=proof):
                self.fresh_engine(); terrain, old = self.armed(next_kind=proof); self.late_complete(old)
                original = self.recovery(); old_deadline = original.records[0].sync_deadline_ns
                new = self.next_recovery_ticket(terrain); self.ack(new)
                after = fixture_recovery.translated(terrain, new.direction) if proof == 'floor' else deepcopy(terrain)
                if proof != 'floor': after.tiles[(0, -1)] = 'floor'
                self.observed_result(new, after)
                self.assertEqual((3 if proof == 'floor' else 2, int(proof == 'door'), int(proof == 'dirt')),
                                 (self.status().moves, self.status().door_changes, self.status().terrain_changes))
                following = self.next_move(after); self.late_complete(following)
                r = self.recovery(); latest = r.records[min(1, r.record_count - 1)]
                self.assertEqual((3, 3 if proof == 'floor' else 2, 2, original.episode_id + 1),
                                 (self.status().inputs, self.status().moves, r.post_move_reacquisitions, r.episode_id))
                self.assertEqual(self.verified_commit + 12 * SECOND, latest.sync_deadline_ns)
                self.assertGreater(latest.sync_deadline_ns, old_deadline)

    def test_proof_budget_uses_actual_commit_and_global_budgets_do_not_reopen(self):
        self.proof_commit_offset_ns = 50_000_000
        _, command = self.armed(); self.late_complete(command)
        self.assertEqual(self.verified_capture_end + 50_000_000 + 12 * SECOND,
                         self.recovery().records[0].sync_deadline_ns)
        for budget, reason in (('walk_started_ns', 14), ('started_ns', 15)):
            with self.subTest(budget=budget):
                self.fresh_engine(); self.proof_commit_offset_ns = 0; _, command = self.armed()
                origin = getattr(self.status(), budget)
                self.late_complete(command, origin + (45 if budget == 'walk_started_ns' else 180) * SECOND)
                self.assertEqual((reason, 0), (self.status().reason, self.recovery().post_move_reacquisitions))


if __name__ == '__main__':
    unittest.main()
