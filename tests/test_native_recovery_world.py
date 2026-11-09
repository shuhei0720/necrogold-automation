"""TEST061 focused synthetic whole-shop paths with a slow camera/service model.

Actual production C runs against independent terrain/beat/position state.
The 35px camera render is a controlled synthetic intermediate frame, not the
missing continuation of TEST060. No real-game/device acceptance is asserted.
"""
import ctypes as C
import heapq
import json
import os
from pathlib import Path
import tempfile
import unittest

import test_native_goal_world as base
from test_native_controller import Command, Scene, Status

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'patches/loopctrl/ngg2'
MS = 1_000_000
SECOND = 1_000 * MS
ACK = 295 * MS
ACQUISITION = 24 * MS
DECODE = 60 * MS
ANALYSIS = 16 * MS
LATENCY = ACQUISITION + DECODE + ANALYSIS


class SettlingWorld(base.GoalWorld):
    def __init__(self, direction, material, *, slow_camera=True, turn=False):
        super().__init__(direction, material)
        self.slow_camera = slow_camera
        self.partial_frames = 0
        self.start = (1, 0) if turn else (0, 0)
        if turn:
            assert direction == 3
            self.tiles[base.world_index(self.start)] = 1
            self.player = self.start

    def rgba(self, lib, now, pause):
        raw = super().rgba(lib, now, pause)
        if (self.paused or not self.slow_camera or self.goods_visible
                or not self.operations or self.operations[-1]['result'] != 'moved'
                or now - self.operations[-1]['at'] >= base.PERIOD):
            return raw
        # World receipt immediately updates its tile position. Its camera is
        # one raw pixel behind the full36px render until the next world beat.
        # The production motion mask lies wholly inside this terrain region;
        # HUD/footer/template masks are never shifted or regenerated from C.
        dx, dy = base.VECTORS[self.operations[-1]['direction']]
        original = bytes(raw)
        shifted = bytearray(original)
        for y in range(72, 332):
            at = (y * 896 + 160) * 4
            source = ((y - dy) * 896 + 160 - dx) * 4
            shifted[at:at + 576 * 4] = original[source:source + 576 * 4]
        self.partial_frames += 1
        return (C.c_uint8 * base.PIXELS).from_buffer_copy(shifted)


class RecoveryRun(base.GoalRun):
    def __init__(self, lib, direction, material, *, slow_camera=True, turn=False, phase=0):
        super().__init__(lib, direction, material, LATENCY, phase)
        self.world = SettlingWorld(direction, material, slow_camera=slow_camera, turn=turn)
        self.slow_camera = slow_camera
        self.motion_observations = []
        if hasattr(lib, 'ng2_controller_observe_at'):
            lib.ng2_controller_observe_at.argtypes = [C.c_void_p, C.POINTER(Scene),
                *([C.c_uint64] * 4), C.c_int32, C.c_uint64]

    def cycle(self):
        if self.blocked:
            return
        if self.latest is not None:
            frame, self.latest = self.latest, None
            assert frame.analysis_end <= self.now
            frame.committed = self.now
            if hasattr(self.lib, 'ng2_controller_observe_at'):
                frame.accepted = self.lib.ng2_controller_observe_at(self.engine,
                    C.byref(frame.scene), frame.id, frame.start, frame.end,
                    frame.prefix, frame.stable, self.now)
            else:
                frame.accepted = self.lib.ng2_controller_observe(self.engine,
                    C.byref(frame.scene), frame.id, frame.start, frame.end,
                    frame.prefix, frame.stable)
            for event in self.events():
                if event.command.kind == 4 and event.observed_capture_id == frame.id:
                    self.motion_observations.append(dict(capture_id=frame.id,
                        at=self.now, command_id=event.command.id, motion=event.motion,
                        start=frame.start, end=frame.end, prefix=frame.prefix))
        before = self.status()
        command = Command()
        ready = self.lib.ng2_controller_tick(self.engine, self.now, 1, 0, 1, C.byref(command))
        assert ready >= 0
        if ready:
            command = Command.from_buffer_copy(bytes(command))
            self.publications.append(dict(at=self.now, command=command, moves=before.moves,
                lead_confirmed=before.lead_confirmed, source=before.last_capture_id,
                prefix=before.last_completed_id))
            self.pending[command.id] = command
            self.blocked = True
            self.control_blocks.append(dict(start=self.now, end=self.now + 20 * MS,
                                           kind='prepare', command_id=command.id))
            self.schedule(self.now + 20 * MS, 'prepared', command)

    def dispatch(self, kind, payload):
        if kind != 'begin':
            return super().dispatch(kind, payload)
        command = payload
        assert not self.blocked
        permitted = self.lib.ng2_controller_begin(self.engine, command.id, self.now, 1, 0, 1)
        self.begin_attempts.append(dict(at=self.now, command=command, permitted=permitted))
        if permitted:
            self.world.input(command.kind, command.direction, self.now)
            self.inflight = self.blocked = True
            self.control_blocks.append(dict(start=self.now, end=self.now + ACK,
                                           kind='synth', command_id=command.id))
            self.schedule(self.now + ACK, 'ack', command)
        else:
            self.cycle()

    def start_capture(self, latency):
        assert latency == LATENCY
        self.capture_id += 1
        frame = base.Capture(self.capture_id, self.now, self.now + ACQUISITION,
            self.now + ACQUISITION + DECODE, self.now + ACQUISITION + DECODE,
            self.now + LATENCY, self.prefix, self.inflight)
        self.captures.append(frame)
        self.schedule(self.now + ACQUISITION // 2, 'capture_pixels', frame)
        self.schedule(frame.end, 'capture_end', frame)
        self.schedule(frame.decode_end, 'decode_end', frame)
        self.schedule(frame.analysis_end, 'analysis_end', frame)

    def run(self):
        try:
            while self.queue and self.now <= base.EPOCH + 40 * SECOND:
                self.now, _, kind, payload = heapq.heappop(self.queue)
                self.dispatch(kind, payload)
                if self.status().terminal:
                    break
            return self
        finally:
            self.final = Status.from_buffer_copy(bytes(self.status()))
            self.native_events = self.events()
            self.native_references = self.references()
            self.lib.ng2_controller_destroy(self.engine)
            self.engine = None

    def assert_goal(self, test):
        world, status = self.world, self.final
        test.assertTrue(world.goods_visible and status.goods == 1,
                        'test061_whole_shop_reaches_goods_after_camera_confirmation')
        test.assertTrue(world.paused and status.paused == 1)
        test.assertEqual(1, status.reason)
        test.assertEqual((1, 1, 1, 0),
                         (world.resumes, world.pauses, world.doors, world.purchases))
        test.assertEqual(world.gate, world.player)
        expected_moves = 6 if world.start != (0, 0) else 5
        test.assertEqual(expected_moves, world.moves)
        test.assertEqual(expected_moves + 1, len(world.operations))
        test.assertEqual(expected_moves + 1, status.inputs)
        test.assertEqual(1, status.door_changes)
        test.assertEqual(0, status.terrain_changes)
        # GOODS priority may leave the final actual movement uncredited.
        test.assertIn(status.moves, (expected_moves - 1, expected_moves))
        acknowledged = [e for e in self.native_events
                        if e.command.kind == 4 and e.outcome == 2]
        test.assertEqual(expected_moves + 1, len(acknowledged))
        test.assertEqual([1] * (expected_moves - 1) + [3],
                         [e.motion for e in acknowledged[:-1]])
        test.assertEqual(status.moves, sum(e.motion == 1 for e in acknowledged))
        if status.moves == expected_moves - 1:
            test.assertIn(acknowledged[-1].motion, (0, 7))
            test.assertEqual((0, 0), (acknowledged[-1].dx, acknowledged[-1].dy))
        else:
            test.assertEqual(1, acknowledged[-1].motion)
        if world.start != (0, 0):
            test.assertEqual([1] + [3] * 6, [op['direction'] for op in world.operations])
        test.assertTrue(all(op['accepted'] and op['error'] <= base.TOLERANCE
                            for op in world.operations))
        test.assertEqual([False] * expected_moves + [True],
                         [op['goods'] for op in world.operations])
        test.assertEqual(['moved'] * (expected_moves - 1) + ['door_opened', 'moved'],
                         [op['result'] for op in world.operations])
        beats = [op['beat'] for op in world.operations]
        test.assertTrue(all(b > a for a, b in zip(beats, beats[1:])))
        if self.slow_camera:
            test.assertGreater(world.partial_frames, 0)
            test.assertTrue(any(row['motion'] in (0, 7) for row in self.motion_observations),
                            'intermediate camera frames must actually be assessed as unconfirmed')
            test.assertTrue(any(b > a + 1 for a, b in zip(beats, beats[1:])),
                            'recovery scenario must not be mislabeled consecutive beats')
        for attempt in self.begin_attempts:
            if attempt['permitted']:
                command = attempt['command']
                test.assertLessEqual(command.not_before_ns, attempt['at'])
                test.assertLessEqual(attempt['at'], command.deadline_ns)
        for frame in self.captures:
            test.assertEqual(ACQUISITION, frame.end - frame.start)
            test.assertEqual(DECODE, frame.decode_end - frame.end)
            test.assertEqual(ANALYSIS, frame.analysis_end - frame.analysis_start)
            if frame.committed:
                test.assertGreaterEqual(frame.committed, frame.analysis_end)
        self.assert_holding_pause(test)


class NativeRecoveryWorldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix='test061-world-')
        base.CORE = CORE
        override = os.environ.get('NECRO_TEST061_BASELINE_CONTROLLER')
        cls.lib, cls.compile_commands, _ = base.compile_world(cls.directory.name,
            controller=Path(override) if override else None)
        cls.cases = []

    @classmethod
    def tearDownClass(cls):
        output = os.environ.get('NECRO_TEST061_WORLD_EVIDENCE')
        if output:
            p = Path(output)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(dict(scope='Synthetic camera/service and independent shop world; not actual game.',
                compiler_commands=cls.compile_commands, source_sha256=cls.lib.world_source_sha256,
                cases=cls.cases), indent=2) + '\n')
        cls.directory.cleanup()

    def run_case(self, name, direction, material, *, turn=False, slow_camera=True):
        run = RecoveryRun(self.lib, direction, material, slow_camera=slow_camera, turn=turn).run()
        record = run.evidence()
        record.update(name=name, slow_camera=slow_camera, turn=turn,
                      camera_partial_frames=run.world.partial_frames,
                      motion_observations=run.motion_observations, passed=False)
        self.cases.append(record)
        run.assert_goal(self)
        record['passed'] = True

    def test_slow_camera_all_directions_wood_and_iron_reach_full_goods(self):
        for name, direction, material in base.CASES:
            with self.subTest(case=name):
                self.run_case(name, direction, material)

    def test_turn_left_then_up_open_enter_and_hold_goods(self):
        self.run_case('LEFT-UP-WOOD', 3, 7, turn=True)

    def test_same_service_without_camera_tween_reaches_full_goods(self):
        self.run_case('SERVICE-ONLY', 3, 7, slow_camera=False)


if __name__ == '__main__':
    unittest.main()
