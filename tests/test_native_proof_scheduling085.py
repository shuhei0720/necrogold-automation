"""TEST085: delayed, already verified moves return to bounded scheduling.

Public procedural scenes, textures and explicit capture/commit clocks exercise
Controller authority. They do not replay private TEST084 state or future frames.
"""
import ctypes as C
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import tempfile
import unittest

from tests import test_native_controller as fixture
from tests import test_native_recovery as mechanics

CORE = mechanics.CORE
MILLISECOND = 1_000_000
SECOND = fixture.SECOND
PERIOD = fixture.PERIOD


class Motion(C.Structure):
    _fields_ = [(name, C.c_int32) for name in ('kind', 'dx', 'dy')]


class NativeProofScheduling085Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_directory = tempfile.TemporaryDirectory(prefix='test085-proof-source-')
        directory = Path(cls.source_directory.name)
        origin = Path(os.environ.get('NECRO_TEST085_PROOF_BASELINE_CORE', CORE))
        for path in origin.glob('NG2*'):
            if path.suffix in ('.c', '.h'):
                shutil.copyfile(path, directory / path.name)
        hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(directory.glob('NG2*')) if p.suffix in ('.c', '.h')}
        if len(hashes) != 8:
            raise AssertionError('exactly the eight existing C/H sources are required')
        expected = os.environ.get('NECRO_TEST085_PROOF_EXPECTED_IDENTITY')
        if expected and hashes != json.loads(Path(expected).read_text()):
            raise AssertionError('the immutable TEST084 eight-file identity changed')
        identity = os.environ.get('NECRO_TEST085_PROOF_SOURCE_IDENTITY')
        if identity:
            Path(identity).write_text(json.dumps({
                'source_directory': str(origin), 'source_sha256': hashes,
                'python_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in (Path(__file__), Path(fixture.__file__),
                                            Path(mechanics.__file__))}},
                sort_keys=True, indent=2)+'\n')
        previous = mechanics.CORE
        try:
            mechanics.CORE = directory
            mechanics.NativeRecoveryTests.setUpClass.__func__(cls)
        finally:
            mechanics.CORE = previous
        cls.lib.ng2_motion.argtypes = [C.POINTER(fixture.Scene), C.POINTER(fixture.Scene),
                                      C.c_int32, C.POINTER(Motion)]
        cls.lib.ng2_motion.restype = C.c_int

    @classmethod
    def tearDownClass(cls):
        mechanics.NativeRecoveryTests.tearDownClass.__func__(cls)
        cls.source_directory.cleanup()

    setUp = mechanics.NativeRecoveryTests.setUp
    scene = mechanics.NativeRecoveryTests.scene
    observe = mechanics.NativeRecoveryTests.observe
    observe_actual = mechanics.NativeRecoveryTests.observe_actual
    tick = mechanics.NativeRecoveryTests.tick
    status = mechanics.NativeRecoveryTests.status
    events = mechanics.NativeRecoveryTests.events
    ack = mechanics.NativeRecoveryTests.ack
    fit = mechanics.NativeRecoveryTests.fit
    next_move = mechanics.NativeRecoveryTests.next_move
    publish_procedural_candidate = mechanics.NativeRecoveryTests.publish_procedural_candidate
    fresh_engine = mechanics.NativeRecoveryTests.fresh_engine
    observed_result = mechanics.NativeRecoveryTests.observed_result
    motion_wait = mechanics.NativeRecoveryTests.motion_wait
    recovery = mechanics.NativeRecoveryTests.recovery
    motion_references = fixture.NativeControllerTests.motion_references
    continuous_walk = fixture.NativeControllerTests.continuous_walk

    def credit(self):
        s = self.status()
        return tuple(getattr(s, key) for key in ('inputs', 'moves', 'door_changes',
            'terrain_changes', 'x', 'y', 'last_ordinal', 'first_move_ns', 'lead_ns'))

    def motion(self, before, after, direction):
        out = Motion()
        self.assertEqual(1, self.lib.ng2_motion(C.byref(before), C.byref(after),
                                              direction, C.byref(out)))
        return out.kind, out.dx, out.dy

    def delayed_proof(self, *, parent=None, terrain=None, source_age=210*MILLISECOND,
                      tick_offset=-40*MILLISECOND, picture='moved', prefix=None, stable=1,
                      commit=None, observed=None):
        if parent is None:
            terrain = self.fit()
            parent = self.next_move()
        self.ack(parent)
        wait = bytes(self.motion_wait())
        next_nb = parent.target_ns + PERIOD - self.status().lead_ns
        start = next_nb-source_age
        end = start+20*MILLISECOND
        self.now = next_nb+tick_offset if commit is None else commit
        self.assertGreaterEqual(start, max(parent.target_ns+80*MILLISECOND,
                                          self.events()[-1].end_ns))
        self.assertGreaterEqual(self.now, end)
        after = deepcopy(observed) if observed is not None else fixture.translated(terrain, parent.direction)
        if picture == 'unknown':
            after.signature = bytes([40])*23296
        if picture == 'goods':
            after.goods = 'visible'
        frame = self.scene(2, 2, after)
        accepted = self.observe_actual(frame, start=start, end=end, commit=self.now,
                                       prefix=prefix, stable=stable)
        if prefix is None and stable:
            self.assertEqual(1, accepted)
        self.assertEqual(fixture.MotionWait.from_buffer_copy(wait).deadline_ns,
                         self.motion_wait().deadline_ns)
        return terrain, after, parent, next_nb, wait

    def verified_preconditions(self, parent, next_nb, source_age):
        s = self.status()
        e = self.events()[-1]
        self.assertEqual((1, 1, 0, 0, parent.id, self.number),
                         (s.moves, s.lead_confirmed, s.input_state, s.reason,
                          s.last_completed_id, s.last_capture_id))
        self.assertEqual((parent.id, 2, 1, self.number),
                         (e.command.id, e.outcome, e.motion, e.observed_capture_id))
        self.assertEqual((0, 1, 1), (self.motion_wait().active,
                                    self.motion_wait().attempts, self.motion_wait().last_motion))
        self.assertEqual(next_nb+self.status().lead_ns, s.next_target_ns)
        self.assertEqual(source_age, next_nb-s.last_capture_start_ns)
        self.assertLessEqual(self.now, self.motion_wait().deadline_ns)
        self.assertGreaterEqual(self.now, next_nb-100*MILLISECOND)

    def next_fresh_recovery(self, terrain, original_event):
        count = len([e for e in self.events() if e.command.kind == 4])
        for _ in range(60):
            self.now += 20*MILLISECOND
            self.observe(self.scene(2, 2, terrain, beat=True))
            ready, command = self.tick()
            if ready and command.kind == 4:
                self.assertEqual(original_event, bytes(self.events()[count-1]))
                self.assertEqual(self.number, command.source_capture_id)
                self.assertGreaterEqual(command.source_start_ns, command.not_before_ns-200*MILLISECOND)
                self.assertGreaterEqual(command.not_before_ns, self.now+50*MILLISECOND)
                self.assertLessEqual(command.not_before_ns-self.now, 100*MILLISECOND)
                self.assertEqual(command.not_before_ns+10*MILLISECOND, command.deadline_ns)
                return command
            self.assertEqual(0, self.status().reason)
        self.fail('fresh public HUD/source did not publish the bounded future slot')

    def test_late_verified_move_reacquires_without_reusing_old_ticket(self):
        _, after, parent, nb, _ = self.delayed_proof()
        self.verified_preconditions(parent, nb, 210*MILLISECOND)
        old_event = bytes(self.events()[-1]); old_credit = self.credit()
        old_wait = bytes(self.motion_wait())
        self.assertEqual((0, 0), (self.tick()[0], self.status().reason))
        self.assertEqual(2, self.recovery().mode,
                         'a delayed verified source cannot authorize the next unreserved beat')
        self.assertEqual((1, 1, 1), (self.recovery().episode_id,
            self.recovery().post_move_reacquisitions, self.recovery().record_count))
        self.assertEqual((old_credit, old_event, old_wait),
                         (self.credit(), bytes(self.events()[-1]), bytes(self.motion_wait())))
        self.now = nb+10*MILLISECOND+1
        self.assertEqual(0, self.tick()[0])
        self.assertEqual(1, self.recovery().record_count)
        new = self.next_fresh_recovery(after, old_event)
        self.assertEqual(parent.ordinal+1, new.ordinal)
        self.assertGreater(new.target_ns, parent.target_ns+PERIOD)
        self.assertNotEqual(parent.id, new.id)
        self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, parent.id, self.now, 1, 0, 1))

    def test_publication_and_source_boundaries_keep_old_admission_limits(self):
        for tick_offset, source_age, recovered in (
                (-100*MILLISECOND-1, 210*MILLISECOND, False),
                (-100*MILLISECOND, 210*MILLISECOND, True),
                (-40*MILLISECOND, 200*MILLISECOND-1, False),
                (-40*MILLISECOND, 200*MILLISECOND, False),
                (-40*MILLISECOND, 200*MILLISECOND+1, True),
                (10*MILLISECOND, 210*MILLISECOND, True)):
            with self.subTest(tick_offset=tick_offset, source_age=source_age):
                self.fresh_engine()
                _, _, parent, nb, _ = self.delayed_proof(source_age=source_age, tick_offset=tick_offset)
                self.assertEqual((1, 0), (self.status().moves, self.status().reason))
                self.assertEqual(nb-source_age, self.status().last_capture_start_ns)
                ready, command = self.tick()
                self.assertEqual(2 if recovered else 0, self.recovery().mode)
                if recovered:
                    self.assertEqual((0, 0, 1), (ready, command.kind, len(self.events())))
                elif tick_offset >= -100*MILLISECOND:
                    self.assertEqual((1, 4, 2), (ready, command.kind, len(self.events())))
                else:
                    self.assertEqual(0, ready)
                    self.now = nb+10*MILLISECOND+1
                    self.assertNotEqual(4, self.tick()[1].kind)
                    self.assertEqual(9, self.status().reason)

    def test_only_same_ack_known_move_proof_can_enter_recovery(self):
        for case in ('unknown', 'prefix', 'unstable', 'issued', 'begun', 'unknown_synth'):
            with self.subTest(case=case):
                self.fresh_engine()
                if case in ('issued', 'begun', 'unknown_synth'):
                    self.fit(); parent = self.next_move()
                    self.now = parent.not_before_ns
                    if case != 'issued':
                        self.assertEqual(1, self.lib.ng2_controller_begin(self.engine, parent.id,
                                                                         self.now, 1, 0, 1))
                    if case == 'unknown_synth':
                        self.now += 1
                        self.assertEqual(1, self.lib.ng2_controller_complete(self.engine, parent.id,
                                                                            self.now, -1))
                else:
                    terrain = self.fit(); parent = self.next_move()
                    self.delayed_proof(parent=parent, terrain=terrain,
                        picture='unknown' if case == 'unknown' else 'moved',
                        prefix=0 if case == 'prefix' else None,
                        stable=0 if case == 'unstable' else 1)
                before = self.credit(); count = len(self.events())
                self.assertNotEqual(4, self.tick()[1].kind)
                self.assertEqual(0, self.recovery().post_move_reacquisitions)
                self.assertEqual(before, self.credit())
                self.assertEqual(count, len(self.events()))
                self.assertEqual(0, self.status().moves)

    def test_qualified_reference_move_is_already_verified_for_recovery(self):
        terrain, original = self.continuous_walk(moves=1, direction=3)
        reference = self.scene(2, 2, terrain)
        refreshed = deepcopy(terrain); refreshed.tiles[(-10, 4)] = 'stone'
        visible_after = deepcopy(terrain)
        rng = random.Random(85085)
        noise = bytes(rng.randrange(20, 100) for _ in range(23296))
        one = bytearray(terrain.signature); two = bytearray(terrain.signature)
        for i in range(len(one)):
            if i % 100 < 15: one[i] = noise[i]
            if 15 <= i % 100 < 30: two[i] = noise[i]
        refreshed.signature = bytes(one); visible_after.signature = bytes(two)
        authority = self.scene(2, 2, refreshed)
        observed = fixture.translated(visible_after, 3)
        after_scene = self.scene(2, 2, observed)
        self.assertEqual((2, 0, 0), self.motion(reference, authority, 3))
        self.assertEqual((0, 0, 0), self.motion(authority, after_scene, 3))
        self.assertEqual((1, 0, -1), self.motion(reference, after_scene, 3))
        self.now += 2
        self.observe(authority)
        parent = self.next_move()
        self.assertNotEqual(original.id, parent.id)
        self.assertEqual((original.target_ns, original.not_before_ns, original.deadline_ns),
                         (parent.target_ns, parent.not_before_ns, parent.deadline_ns))
        self.delayed_proof(parent=parent, terrain=refreshed, observed=observed)
        row = self.motion_references()[-1]
        self.assertEqual((parent.source_capture_id, original.source_capture_id, 1, 0, 1, 1,
                          original.source_capture_id, 1),
                         (row.authority_capture_id, row.reference_capture_id, row.reference_eligible,
                          row.primary_motion, row.fallback_attempted, row.fallback_motion,
                          row.selected_capture_id, row.selected_motion))
        self.assertEqual((2, 2), (self.status().inputs, self.status().moves))
        event = bytes(self.events()[-1]); credit = self.credit()
        self.assertEqual(0, self.tick()[0]); self.assertEqual(2, self.recovery().mode)
        self.assertEqual((credit, event), (self.credit(), bytes(self.events()[-1])))

    def test_parent_horizon_goods_and_cancellation_remain_authoritative(self):
        for late in (0, 1):
            with self.subTest(parent_visual_late=late):
                self.fresh_engine(); terrain = self.fit(); parent = self.next_move()
                deadline = self.motion_wait().deadline_ns
                self.delayed_proof(parent=parent, terrain=terrain, commit=deadline+late)
                self.assertEqual(0 if late else 1, self.status().moves)
                self.assertEqual(deadline, self.motion_wait().deadline_ns)
                self.assertNotEqual(4, self.tick()[1].kind)
                self.assertEqual(1, len([e for e in self.events() if e.command.kind == 4]))
        self.fresh_engine(); self.delayed_proof(picture='goods')
        self.assertEqual((1, 1), (self.status().goods, self.status().reason))
        self.assertEqual(2, self.tick()[1].kind)
        self.assertEqual(0, self.recovery().post_move_reacquisitions)
        self.fresh_engine(); self.delayed_proof()
        self.lib.ng2_controller_cancel(self.engine, self.now, 2)
        self.assertNotEqual(4, self.tick()[1].kind)
        self.assertEqual(2, self.status().reason)
        self.assertEqual(0, self.recovery().post_move_reacquisitions)

    def test_existing_sync_episode_and_future_preparation_bound_new_slot(self):
        _, after, parent, _, _ = self.delayed_proof()
        self.assertEqual(0, self.tick()[0]); self.assertEqual(2, self.recovery().mode)
        first = self.recovery(); original_deadline = first.records[0].sync_deadline_ns
        new = self.next_fresh_recovery(after, bytes(self.events()[-1]))
        _, after, _, _, _ = self.delayed_proof(parent=new, terrain=after)
        old_event = bytes(self.events()[-1]); credit = self.credit()
        self.assertEqual(0, self.tick()[0]); second = self.recovery()
        self.assertEqual((2, first.episode_id, first.post_move_reacquisitions,
                          original_deadline, 2),
                         (second.mode, second.episode_id, second.post_move_reacquisitions,
                          second.records[1].sync_deadline_ns, second.record_count))
        self.assertEqual((credit, old_event), (self.credit(), bytes(self.events()[-1])))
        newest = self.next_fresh_recovery(after, old_event)
        self.now = original_deadline
        self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, newest.id, self.now, 1, 0, 1))
        self.assertEqual(8, self.status().reason)
        self.assertEqual(2, self.status().inputs)
