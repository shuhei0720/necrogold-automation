"""TEST076: a proven-unsent passage ticket may obtain a bounded future beat.

The maps, follow-up images and clocks are procedural public-C fixtures. They
exercise the late callback observed in TEST075 without inventing its missing
phone frames or claiming device arrival. No old ticket or unknown synth retries.
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

CORE = mechanics.CORE
SECOND = fixture.SECOND


class NativePassageUnsent076Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = mechanics.CORE
        cls.baseline_directory = None
        try:
            mechanics.CORE = CORE
            baseline = os.environ.get('NECRO_TEST076_BASELINE_CONTROLLER')
            if baseline:
                cls.baseline_directory = tempfile.TemporaryDirectory(prefix='test076-controller-')
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

    setUp = fixture.NativeControllerTests.setUp
    status = fixture.NativeControllerTests.status
    events = fixture.NativeControllerTests.events
    tick = fixture.NativeControllerTests.tick
    ack = fixture.NativeControllerTests.ack
    fresh_engine = fixture.NativeControllerTests.fresh_engine
    motion_wait = fixture.NativeControllerTests.motion_wait
    recovery = mechanics.NativeRecoveryTests.recovery
    recovery_samples = mechanics.NativeRecoveryTests.recovery_samples
    all_public_bytes = mechanics.NativeRecoveryTests.all_public_bytes
    reject_old_callbacks_without_mutation = mechanics.NativeRecoveryTests.reject_old_callbacks_without_mutation
    scene = passage.NativePassage072Tests.scene
    observe = passage.NativePassage072Tests.observe
    fit_clear = passage.NativePassage072Tests.fit_clear
    next_operation = passage.NativePassage072Tests.next_operation
    next_move = passage.NativePassage072Tests.next_move
    moved = passage.NativePassage072Tests.moved

    def armed(self, mouth=(0, -3), moves=1):
        terrain = self.fit_clear(passage.passage_room(mouth))
        for _ in range(moves):
            command = self.next_move(terrain)
            terrain = self.moved(terrain, command)
        self.verified_commit = self.now
        command = self.next_move(terrain)
        self.assertEqual((moves, moves, 1, 1),
            (self.status().inputs, self.status().moves,
             self.status().lead_confirmed, self.status().input_state))
        return terrain, command

    def late(self, command, entry='complete', at=None, scene=None):
        self.now = command.deadline_ns + 1 if at is None else at
        if entry == 'complete':
            return self.lib.ng2_controller_complete(self.engine, command.id, self.now, 0)
        if entry == 'begin':
            return self.lib.ng2_controller_begin(self.engine, command.id, self.now, 1, 0, 1)
        if entry == 'observe':
            return self.observe(scene)
        ready, candidate = self.tick()
        self.assertEqual(0, candidate.kind)
        return ready

    def assert_retired(self, command, counts):
        state = self.status()
        self.assertEqual((0, 0, 4, 0, 0),
            (state.reason, state.terminal, state.phase,
             state.input_state, state.current_command_id),
            'a proven-unsent passage callback must reacquire, not stop CAPTURE/LATE')
        self.assertEqual(counts, (state.inputs, state.moves))
        row = next(e for e in self.events() if e.command.id == command.id)
        self.assertEqual((3, 9, 0, 0, 0, 0),
            (row.outcome, row.reason, row.begin_ns, row.motion, row.dx, row.dy))
        self.assertEqual(bytes(command), bytes(row.command),
                         'retirement cannot change the issued ticket fields')
        recovery = self.recovery()
        latest = recovery.records[min(1, recovery.record_count - 1)]
        self.assertEqual((2, 1, 5, 2),
            (recovery.mode, recovery.post_move_reacquisitions,
             latest.reason, latest.clock))
        self.assertEqual(self.verified_commit + 12 * SECOND, latest.sync_deadline_ns)

    def next_recovery(self, terrain):
        for _ in range(100):
            self.now += 20_000_000
            self.assertEqual(1, self.observe(terrain))
            ready, command = self.tick()
            self.assertEqual(0, self.status().reason)
            if ready:
                self.assertEqual(4, command.kind)
                self.assertGreaterEqual(command.not_before_ns - self.now, 50_000_000,
                    'new physical beat needs the original main preparation interval')
                return command
        self.fail('bounded recovery needs a future ticket or a stated stop')

    def test_late_live_passage_complete_begin_and_tick_preserve_verified_pose(self):
        for mouth, moves, direction in (((0, -3), 1, 3), ((-3, 0), 1, 1),
                                         ((2, -3), 1, 2), ((-3, 2), 2, 4)):
            for entry in ('complete', 'begin', 'tick', 'observe'):
                with self.subTest(mouth=mouth, entry=entry):
                    self.fresh_engine()
                    terrain, command = self.armed(mouth, moves)
                    self.assertEqual(direction, command.direction)
                    pose = (self.status().x, self.status().y,
                            self.status().last_completed_id, self.status().first_move_ns)
                    self.assertEqual(1 if entry in ('complete', 'observe') else 0,
                                     self.late(command, entry, scene=terrain))
                    self.assert_retired(command, (moves, moves))
                    self.assertEqual(pose,
                        (self.status().x, self.status().y,
                         self.status().last_completed_id, self.status().first_move_ns))

    def test_future_passage_ticket_and_stale_callbacks_never_reuse_old_authority(self):
        terrain, old = self.armed()
        self.late(old)
        self.assert_retired(old, (1, 1))
        self.reject_old_callbacks_without_mutation(old)
        new = self.next_recovery(terrain)
        self.assertGreater(new.id, old.id)
        self.assertGreater(new.target_ns, old.target_ns)
        self.assertEqual((old.direction, old.x, old.y), (new.direction, new.x, new.y))
        self.assertEqual((1, 1), (self.status().inputs, self.status().moves))
        self.reject_old_callbacks_without_mutation(old)
        self.ack(new)
        self.assertEqual((2, 1), (self.status().inputs, self.status().moves),
                         'a new ACK remains distinct from an observed move')

    def test_repeated_passage_misses_keep_one_original_episode_and_deadline(self):
        terrain, old = self.armed()
        self.late(old)
        self.assert_retired(old, (1, 1))
        first = self.recovery()
        deadline = first.records[0].sync_deadline_ns
        for _ in range(2):
            new = self.next_recovery(terrain)
            self.late(new)
            current = self.recovery()
            latest = current.records[min(1, current.record_count - 1)]
            self.assertEqual((first.episode_id, 1, deadline),
                (current.episode_id, current.post_move_reacquisitions,
                 latest.sync_deadline_ns))
            self.assertEqual((1, 1, 0),
                (self.status().inputs, self.status().moves, self.status().reason))
        self.now = deadline
        self.tick()
        self.assertEqual((8, 1),
            (self.status().reason, self.recovery().post_move_reacquisitions))

    def test_deadline_equality_in_time_failure_and_unproven_first_step_do_not_recover(self):
        for entry in ('begin', 'complete'):
            with self.subTest(entry=entry):
                self.fresh_engine()
                _, command = self.armed()
                self.now = command.deadline_ns
                if entry == 'begin':
                    self.assertEqual(1, self.lib.ng2_controller_begin(
                        self.engine, command.id, self.now, 1, 0, 1))
                    self.assertEqual(2, self.status().input_state)
                else:
                    self.assertEqual(1, self.lib.ng2_controller_complete(
                        self.engine, command.id, self.now, 0))
                    self.assertEqual(6, self.status().reason)
                self.assertEqual(0, self.recovery().post_move_reacquisitions)
        self.fresh_engine()
        terrain = self.fit_clear(passage.passage_room())
        first = self.next_move(terrain)
        self.late(first)
        self.assertEqual((0, 0, 0, 0),
            (self.status().inputs, self.status().moves,
             self.status().lead_confirmed, self.recovery().post_move_reacquisitions))

    def test_started_unknown_authority_and_changed_evidence_cannot_gain_passage_recovery(self):
        variants = ('started', 'ack', 'unknown', 'cancel', 'signature', 'remote_tile',
                    'protection', 'goods', 'partial_goods', 'new_gold', 'gold_unknown',
                    'stale', 'foreground', 'locked', 'owner')
        for variant in variants:
            with self.subTest(variant=variant):
                self.fresh_engine()
                terrain, command = self.armed()
                if variant in ('started', 'ack', 'unknown'):
                    self.now = command.not_before_ns
                    self.assertEqual(1, self.lib.ng2_controller_begin(
                        self.engine, command.id, self.now, 1, 0, 1))
                    if variant != 'started':
                        self.now += 1
                        self.lib.ng2_controller_complete(self.engine, command.id,
                            self.now, 1 if variant == 'ack' else -1)
                elif variant == 'cancel':
                    self.lib.ng2_controller_cancel(self.engine, self.now, 2)
                elif variant in ('foreground', 'locked', 'owner'):
                    self.now = command.deadline_ns + 1
                    flags = (0, 0, 1) if variant == 'foreground' else (
                             (1, 1, 1) if variant == 'locked' else (1, 0, 0))
                    self.lib.ng2_controller_begin(self.engine, command.id, self.now, *flags)
                elif variant not in ('stale',):
                    changed = deepcopy(terrain)
                    if variant == 'signature': changed.signature = bytes([40]) * 23296
                    elif variant == 'remote_tile': changed.tiles[(-10, 4)] = 'stone'
                    elif variant == 'protection': changed.protected.add((-10, 4))
                    elif variant == 'goods': changed.goods = 'visible'
                    elif variant == 'partial_goods': changed.goods = 'partial'
                    elif variant == 'new_gold':
                        changed.tiles[(-1, -2)] = 'gold'; changed.gold.add((-1, -2))
                    self.now += 2
                    frame = self.scene(changed, gold=0 if variant == 'gold_unknown' else None)
                    self.observe(frame)
                before = (self.status().inputs, self.status().moves)
                # A new gold observation can already revoke exploration and
                # start its own bounded shop handoff. This old callback must
                # not add another recovery or reopen its retired ticket.
                recoveries = self.recovery().post_move_reacquisitions
                at = command.deadline_ns + (3 * SECOND if variant == 'stale' else 1)
                self.late(command, at=at)
                self.assertEqual(recoveries, self.recovery().post_move_reacquisitions)
                self.assertEqual(before, (self.status().inputs, self.status().moves))
        for fault in ('remote_tile', 'protection', 'partial_goods', 'signature'):
            with self.subTest(late_observe=fault):
                self.fresh_engine()
                terrain, command = self.armed()
                latest = deepcopy(terrain)
                if fault == 'remote_tile': latest.tiles[(-10, 4)] = 'stone'
                elif fault == 'protection': latest.protected.add((-10, 4))
                elif fault == 'partial_goods': latest.goods = 'partial'
                else: latest.signature = bytes([40]) * 23296
                # The previous accepted scene is still safe. The new expired
                # observation must be checked directly before retiring its ID.
                self.assertEqual(1, self.late(command, 'observe', scene=latest))
                self.assertEqual((0, 1, 1),
                    (self.recovery().post_move_reacquisitions,
                     self.status().inputs, self.status().moves))
                self.assertEqual(13 if fault in ('protection', 'partial_goods') else 17,
                                 self.status().reason)

    def test_passage_recovery_never_extends_proof_walk_or_session_budgets(self):
        for budget, reason in (('proof', 8), ('walk', 14), ('session', 15)):
            with self.subTest(budget=budget):
                self.fresh_engine()
                _, command = self.armed()
                at = self.verified_commit + 12 * SECOND if budget == 'proof' else (
                    self.status().walk_started_ns + 45 * SECOND if budget == 'walk' else
                    self.status().started_ns + 180 * SECOND)
                self.late(command, at=at)
                self.assertEqual((reason, 0, 1, 1),
                    (self.status().reason, self.recovery().post_move_reacquisitions,
                     self.status().inputs, self.status().moves))


if __name__ == '__main__':
    unittest.main()
