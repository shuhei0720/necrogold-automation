"""TEST060 independent, discrete host world through the production C APIs.

The fixed terrain and expectations are docs/tests/test060-world-cases.md.
This is synthetic timing/goal coverage, not a device recording or actual-game
acceptance test. The world does not simulate dense motion or one-pixel camera
shake. Capture/processing/preparation/ACK delays are simulated, not measured.
"""
import ctypes as C
from dataclasses import dataclass
import heapq
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from PIL import Image
from necroprobe import gold_scan
from test_native_controller import Command, Event, MotionReference, Scene, Status


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "patches/loopctrl/ngg2"
MS = 1_000_000
SECOND = 1_000 * MS
PERIOD = 520 * MS
LEAD = 150 * MS
TOLERANCE = 10 * MS
EPOCH = 2 * SECOND  # World clock origin, never derived from a C ticket.
PIXELS = 896 * 414 * 4
MODULE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
VECTORS = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}
CASES = (("N-W", 3, 7), ("N-I", 3, 3), ("E-W", 2, 7), ("E-I", 2, 3),
         ("S-W", 4, 7), ("S-I", 4, 3), ("W-W", 1, 7), ("W-I", 1, 3))


def capture_phases(latency):
    cadence = latency + 5 * MS
    return (0, 1, cadence // 2, cadence - 1,
            (cadence - (200 * MS % cadence)) % cadence + 1)


def compile_world(directory, controller=None):
    """Compile the app's actual per-file profile, plus the host-only renderer.

    An explicit controller path lets Git-external evidence run these same
    assertions against saved pre-change C bytes without changing the repo.
    """
    directory = Path(directory)
    objects = []
    sources = (controller or CORE / "NG2Controller.c", CORE / "NG2Beat.c",
               CORE / "NG2Navigation.c", CORE / "NG2Perception.c",
               ROOT / "patches/loopctrl/ngg2_runtime_scene_fixtures.c")
    provenance = (*sources, CORE / "NG2Core.h", CORE / "NG2Controller.h",
                  CORE / "NG2Templates.h", ROOT / "patches/loopctrl/ngg2_runtime_scene_fixtures.h")
    source_hashes = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in provenance}
    commands = []
    for index, source in enumerate(sources):
        flags = ["-O0"] if index < 2 else ["-O2", "-fno-fast-math", "-ffp-contract=off"]
        obj = directory / (source.stem + ".o")
        command = ["cc", "-std=c99", *flags, "-Wall", "-Wextra", "-Werror", "-pedantic",
                   "-fPIC", "-I", str(CORE), "-c", str(source), "-o", str(obj)]
        subprocess.run(command, check=True, capture_output=True)
        commands.append(command)
        objects.append(obj)
    library = directory / "goal-world.so"
    command = ["cc", "-shared", *map(str, objects), "-lm", "-o", str(library)]
    subprocess.run(command, check=True, capture_output=True)
    commands.append(command)
    lib = C.CDLL(str(library))
    assert source_hashes == {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in provenance}, \
        "world sources changed while the library was compiling"
    lib.world_source_sha256 = source_hashes
    lib.world_source_sha256[str(Path(__file__))] = MODULE_SHA256
    lib.world_object_sha256 = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in objects}
    lib.world_library_sha256 = hashlib.sha256(library.read_bytes()).hexdigest()
    lib.ng2_controller_create.argtypes = [C.c_uint64]
    lib.ng2_controller_create.restype = C.c_void_p
    lib.ng2_controller_destroy.argtypes = [C.c_void_p]
    lib.ng2_controller_observe.argtypes = [C.c_void_p, C.POINTER(Scene),
                                         *([C.c_uint64] * 4), C.c_int32]
    lib.ng2_controller_tick.argtypes = [C.c_void_p, C.c_uint64, *([C.c_int32] * 3),
                                      C.POINTER(Command)]
    lib.ng2_controller_begin.argtypes = [C.c_void_p, C.c_uint64, C.c_uint64,
                                       *([C.c_int32] * 3)]
    lib.ng2_controller_complete.argtypes = [C.c_void_p, C.c_uint64, C.c_uint64, C.c_int32]
    lib.ng2_controller_status.argtypes = [C.c_void_p, C.POINTER(Status)]
    lib.ng2_controller_events.argtypes = [C.c_void_p, C.POINTER(Event), C.c_size_t]
    lib.ng2_controller_events.restype = C.c_size_t
    lib.ng2_controller_motion_references.argtypes = [C.c_void_p, C.POINTER(MotionReference), C.c_size_t]
    lib.ng2_controller_motion_references.restype = C.c_size_t
    lib.ng2_fixture_shop_rgba.argtypes = [C.POINTER(C.c_uint8), C.c_size_t, C.c_int32,
                                        C.c_int32, C.c_double, C.POINTER(C.c_uint8),
                                        C.c_size_t, *([C.c_int32] * 4)]
    lib.ng2_analyze_rgba.argtypes = [C.POINTER(C.c_uint8), C.c_size_t, C.c_size_t,
                                   C.POINTER(Scene)]
    return lib, commands, sources


def rotate(x, y, direction):
    return {1: (y, -x), 2: (-y, x), 3: (x, y), 4: (-x, -y)}[direction]


def world_index(point):
    x, y = point
    assert -16 <= x <= 16 and -16 <= y <= 16
    return (y + 16) * 33 + x + 16


def pause_rgba():
    image = Image.new("RGBA", (896, 414), (0, 0, 0, 255))
    for name in ("continue", "restart"):
        box, _, _, mask = gold_scan._TEMPLATES[name]
        image.paste(Image.new("RGBA", mask.size, (180, 180, 180, 255)), box[:2], mask)
    return (C.c_uint8 * PIXELS).from_buffer_copy(image.tobytes())


class GoalWorld:
    """Terrain, position, visibility and beat acceptance own their own state.

    Input acceptance takes only an input kind/direction and actual time. No C
    Decision, target, source, reported motion or Status enters this oracle.
    """
    def __init__(self, direction, material):
        self.direction = direction
        self.gate = rotate(0, -5, direction)
        self.tiles = (C.c_uint8 * 1089)(*([3] * 1089))
        dx, dy = VECTORS[direction]
        center = (self.gate[0] + 2 * dx, self.gate[1] + 2 * dy)
        for y in range(center[1] - 2, center[1] + 3):
            for x in range(center[0] - 2, center[0] + 3):
                if (x - self.gate[0]) * dx + (y - self.gate[1]) * dy >= 1:
                    self.tiles[world_index((x, y))] = 1
        for k in range(5):
            self.tiles[world_index(rotate(0, -k, direction))] = 1
        for x in (-2, -1, 1, 2):
            self.tiles[world_index(rotate(x, -5, direction))] = 2
        for point in ((-2, -4), (2, -4), (-2, -3), (2, -3)):
            self.tiles[world_index(rotate(*point, direction))] = 2
        self.tiles[world_index(self.gate)] = material
        self.player = (0, 0)
        self.paused = True
        self.resumes = self.pauses = self.moves = self.doors = 0
        self.purchases = 0
        self.last_beat = None
        self.operations = []

    @property
    def goods_visible(self):
        dx, dy = VECTORS[self.direction]
        inside = (self.player[0] - self.gate[0]) * dx + (self.player[1] - self.gate[1]) * dy >= 0
        return self.tiles[world_index(self.gate)] == 1 and inside

    def input(self, kind, direction, now):
        if kind == 1:
            assert self.paused
            self.paused = False
            self.resumes += 1
        elif kind == 2:
            assert not self.paused
            self.paused = True
            self.pauses += 1
        else:
            assert kind == 4, "restart/purchase is outside this fixed goal world"
            before = self.player
            elapsed = now - EPOCH
            beat = (elapsed + LEAD + PERIOD // 2) // PERIOD
            error = abs(elapsed + LEAD - beat * PERIOD)
            result = "paused" if self.paused else "off_beat"
            accepted = not self.paused and elapsed >= 0 and error <= TOLERANCE
            if accepted:
                if beat == self.last_beat:
                    accepted = False
                    result = "duplicate_beat"
                else:
                    self.last_beat = beat
                    dx, dy = VECTORS[direction]
                    point = (before[0] + dx, before[1] + dy)
                    material = self.tiles[world_index(point)]
                    if point == self.gate and material != 1:
                        self.tiles[world_index(point)] = 1
                        self.doors += 1
                        result = "door_opened"
                    elif material == 1:
                        self.player = point
                        self.moves += 1
                        result = "moved"
                    else:
                        result = "blocked"
            self.operations.append(dict(at=now, direction=direction, beat=beat, error=error,
                                        signed_error=elapsed + LEAD - beat * PERIOD,
                                        accepted=accepted, result=result, before=before,
                                        after=self.player, goods=self.goods_visible))

    def rgba(self, lib, now, pause):
        if self.paused:
            return pause
        remaining = (PERIOD - 1 - ((now - EPOCH) % PERIOD)) / PERIOD
        raw = (C.c_uint8 * PIXELS)()
        assert lib.ng2_fixture_shop_rgba(raw, PIXELS, *self.player, remaining,
                                        self.tiles, 1089, *self.gate, self.direction, 0) == 1
        return raw


@dataclass
class Capture:
    id: int
    start: int
    end: int
    decode_end: int
    analysis_start: int
    analysis_end: int
    start_prefix: int
    start_inflight: bool
    prefix: int = 0
    stable: bool = False
    raw: object = None
    scene: object = None
    committed: int = 0
    accepted: int = 0


class GoalRun:
    """Event queue for one capture worker and one serialized C control queue.

    A frame samples world pixels at acquisition midpoint, retains the actual
    acquisition interval, then finishes two milliseconds of decode and two of
    analysis. L is the total acquisition-to-analysis latency. Capture starts
    lie on epoch+phase+k*(L+5ms), independently of commands. During preparation
    and synth the control queue stops; capture/analysis continue, replacing a
    single latest frame exactly as Runtime does. Future completions are never
    passed into observe(). The simulated decode stage does not test a codec.
    """
    def __init__(self, lib, direction, material, latency, phase, slow=None):
        self.lib = lib
        self.world = GoalWorld(direction, material)
        self.latency, self.phase, self.cadence = latency, phase, latency + 5 * MS
        self.slow = slow
        self.now = EPOCH
        self.engine = lib.ng2_controller_create(self.now)
        assert self.engine
        self.pause = pause_rgba()
        self.queue = []
        self.serial = 0
        self.capture_id = 0
        self.prefix = 0
        self.inflight = False
        self.blocked = False
        self.latest = None
        self.pending = {}
        self.captures = []
        self.publications = []
        self.begin_attempts = []
        self.control_blocks = []
        self.replaced = 0
        self.slow_started = False
        self.capture_cutoff = None
        self.slow_boundary = None
        self.late = None
        self.schedule(EPOCH + phase, "capture_start")
        self.schedule(EPOCH, "timer")

    def schedule(self, at, kind, payload=None):
        assert at >= self.now, (kind, at, self.now)
        self.serial += 1
        heapq.heappush(self.queue, (at, self.serial, kind, payload))

    def status(self):
        status = Status()
        self.lib.ng2_controller_status(self.engine, C.byref(status))
        return status

    def events(self):
        rows = (Event * 64)()
        count = self.lib.ng2_controller_events(self.engine, rows, 64)
        return list(rows)[:count]

    def references(self):
        rows = (MotionReference * 16)()
        count = self.lib.ng2_controller_motion_references(self.engine, rows, 16)
        return list(rows)[:count]

    def cycle(self):
        if self.blocked:
            return
        if self.latest is not None:
            frame, self.latest = self.latest, None
            assert frame.analysis_end <= self.now and frame.end <= frame.analysis_end
            frame.committed = self.now
            frame.accepted = self.lib.ng2_controller_observe(
                self.engine, C.byref(frame.scene), frame.id,
                frame.start, frame.end, frame.prefix, frame.stable)
        before = self.status()
        command = Command()
        ready = self.lib.ng2_controller_tick(self.engine, self.now, 1, 0, 1, C.byref(command))
        assert ready >= 0
        if self.late is None and self.status().reason == 9:
            self.late = dict(at=self.now, original_deadline=before.next_target_ns - before.lead_ns + TOLERANCE)
        if ready:
            command = Command.from_buffer_copy(bytes(command))
            self.publications.append(dict(at=self.now, command=command, moves=before.moves,
                                          lead_confirmed=before.lead_confirmed,
                                          source=before.last_capture_id, prefix=before.last_completed_id))
            self.pending[command.id] = command
            self.blocked = True
            preparation = 60 * MS if self.slow == "prepare" and command.ordinal == 4 else 20 * MS
            self.control_blocks.append(dict(start=self.now, end=self.now + preparation,
                                            kind="prepare", command_id=command.id))
            self.schedule(self.now + preparation, "prepared", command)

    def dispatch(self, kind, payload):
        if kind == "timer":
            self.cycle()
            self.schedule(self.now + MS, "timer")
        elif kind == "capture_start":
            if self.capture_cutoff is not None and self.now >= self.capture_cutoff:
                return
            self.start_capture(self.latency)
            self.schedule(self.now + self.cadence, "capture_start")
        elif kind == "slow_capture_start":
            self.start_capture(160 * MS)
            self.schedule(self.now + 165 * MS, "slow_capture_start")
        elif kind == "capture_pixels":
            payload.raw = self.world.rgba(self.lib, self.now, self.pause)
        elif kind == "capture_end":
            payload.prefix = self.prefix
            payload.stable = (not payload.start_inflight and not self.inflight
                              and payload.start_prefix == self.prefix)
        elif kind == "decode_end":
            assert payload.raw is not None and payload.end < self.now
        elif kind == "analysis_end":
            frame = payload
            assert frame.decode_end == frame.analysis_start < self.now
            frame.scene = Scene()
            assert self.lib.ng2_analyze_rgba(frame.raw, PIXELS, 3584, C.byref(frame.scene)) == 0
            frame.raw = None
            if self.latest is not None:
                self.replaced += 1
            self.latest = frame
            self.cycle()
        elif kind == "prepared":
            self.blocked = False
            command = payload
            if self.now >= command.not_before_ns:
                self.dispatch("begin", command)
            else:
                self.schedule(command.not_before_ns, "begin", command)
                self.cycle()
        elif kind == "begin":
            command = payload
            assert not self.blocked
            permitted = self.lib.ng2_controller_begin(self.engine, command.id, self.now, 1, 0, 1)
            self.begin_attempts.append(dict(at=self.now, command=command, permitted=permitted))
            if not permitted and self.late is None and self.status().reason == 9:
                self.late = dict(at=self.now, original_deadline=command.deadline_ns)
            if permitted:
                self.world.input(command.kind, command.direction, self.now)
                self.inflight = self.blocked = True
                self.control_blocks.append(dict(start=self.now, end=self.now + 280 * MS,
                                                kind="synth", command_id=command.id))
                self.schedule(self.now + 280 * MS, "ack", command)
                if (self.slow == "capture" and command.kind == 4
                        and len(self.world.operations) == 3 and not self.slow_started):
                    # Inject only after the third world MOVE. The old frame
                    # confirms that MOVE after its ACK, before ticket four.
                    # A 10ms margin keeps this world assertion independent of
                    # HUD pixel quantization; exact 1ns is tested by C contracts.
                    beat = self.world.operations[-1]["beat"]
                    self.slow_boundary = EPOCH + (beat + 1) * PERIOD - LEAD
                    self.capture_cutoff = self.now + 280 * MS - self.latency
                    self.schedule(self.slow_boundary - 210 * MS, "slow_capture_start")
                    self.slow_started = True
            else:
                self.cycle()
        elif kind == "ack":
            assert self.inflight and self.blocked
            assert self.lib.ng2_controller_complete(self.engine, payload.id, self.now, 1) == 1
            self.prefix = payload.id
            self.inflight = self.blocked = False
            self.cycle()
        else:
            raise AssertionError(kind)

    def start_capture(self, latency):
        self.capture_id += 1
        acquisition = latency - 4 * MS
        frame = Capture(self.capture_id, self.now, self.now + acquisition,
                        self.now + acquisition + 2 * MS, self.now + acquisition + 2 * MS,
                        self.now + latency, self.prefix, self.inflight)
        self.captures.append(frame)
        self.schedule(self.now + acquisition // 2, "capture_pixels", frame)
        self.schedule(frame.end, "capture_end", frame)
        self.schedule(frame.decode_end, "decode_end", frame)
        self.schedule(frame.analysis_end, "analysis_end", frame)

    def run(self):
        try:
            while self.queue and self.now <= EPOCH + 16 * SECOND:
                self.now, _, kind, payload = heapq.heappop(self.queue)
                self.dispatch(kind, payload)
                if self.status().terminal:
                    break
            return self
        finally:
            # Keep copied public results after freeing the actual C controller.
            self.final = Status.from_buffer_copy(bytes(self.status()))
            self.native_events = self.events()
            self.native_references = self.references()
            self.lib.ng2_controller_destroy(self.engine)
            self.engine = None

    def assert_pipeline(self, test):
        test.assertGreater(self.replaced, 0, "capture latest must replace frames while synth blocks control")
        test.assertTrue(any(not f.stable for f in self.captures), "inflight/cross-prefix captures must exist")
        for index, frame in enumerate(self.captures):
            test.assertEqual(EPOCH + self.phase + index * self.cadence, frame.start)
            test.assertLess(frame.start, frame.end)
            test.assertLess(frame.end, frame.decode_end)
            test.assertEqual(frame.decode_end, frame.analysis_start)
            test.assertEqual(frame.start + self.latency, frame.analysis_end)
            if frame.committed:
                test.assertGreaterEqual(frame.committed, frame.analysis_end)
                test.assertFalse(any(block["start"] < frame.committed < block["end"]
                                     for block in self.control_blocks), "C observe must wait for control queue")
        for event in self.native_events:
            if event.outcome == 2:
                test.assertEqual(280 * MS, event.end_ns - event.begin_ns)

    def assert_admission(self, test):
        frames = {frame.id: frame for frame in self.captures}
        logical = set()
        continuous = 0
        for row in self.publications:
            command = row["command"]
            if command.kind != 4 or command.ordinal in logical:
                continue
            logical.add(command.ordinal)
            if not row["lead_confirmed"] or not row["moves"]:
                continue
            continuous += 1
            frame = frames[command.source_capture_id]
            test.assertEqual(command.source_start_ns, frame.start)
            test.assertEqual(row["source"], frame.id)
            test.assertTrue(frame.stable)
            test.assertEqual(row["prefix"], frame.prefix)
            test.assertEqual(frame.start_prefix, frame.prefix)
            test.assertLessEqual(frame.analysis_end, frame.committed)
            test.assertLessEqual(frame.committed, row["at"])
            test.assertGreaterEqual(row["at"], command.not_before_ns - 100 * MS,
                                    "continuous first publication is too early")
            test.assertGreaterEqual(frame.start, command.not_before_ns - 200 * MS,
                                    "continuous first authority uses an old source")
        test.assertEqual(5, continuous)

    def assert_goal(self, test):
        world, status = self.world, self.final
        test.assertEqual((6, 5, 1, 0, 1, 1),
                         (len(world.operations), world.moves, world.doors,
                          world.purchases, world.resumes, world.pauses))
        test.assertEqual(world.gate, world.player)
        test.assertTrue(world.goods_visible)
        test.assertTrue(world.paused)
        test.assertEqual(["moved"] * 4 + ["door_opened", "moved"],
                         [op["result"] for op in world.operations])
        test.assertEqual([world.direction] * 6, [op["direction"] for op in world.operations])
        test.assertTrue(all(op["accepted"] and op["error"] <= TOLERANCE for op in world.operations))
        beats = [op["beat"] for op in world.operations]
        test.assertEqual(list(range(beats[0], beats[0] + 6)), beats, "every world beat must be consecutive")
        test.assertEqual([False] * 5 + [True], [op["goods"] for op in world.operations])
        test.assertEqual((1, 1, 1, 6, 1, 0),
                         (status.terminal, status.goods, status.paused, status.inputs,
                          status.door_changes, status.terrain_changes))
        test.assertEqual(1, status.reason)
        test.assertIn(status.moves, (4, 5))
        test.assertEqual(6, len([e for e in self.native_events if e.command.kind == 4]))
        test.assertEqual(1, len([e for e in self.native_events if e.command.kind == 2]))
        test.assertEqual(6, len(self.native_references))
        moves = [e for e in self.native_events if e.command.kind == 4]
        test.assertEqual([1, 1, 1, 1, 3], [e.motion for e in moves[:5]])
        if status.moves == 4:
            final_event, reference = moves[-1], self.native_references[-1]
            test.assertEqual(world.operations[-1]["before"], (status.x, status.y))
            test.assertEqual(final_event.command.id, reference.command_id)
            test.assertEqual(2, final_event.outcome)
            test.assertGreater(final_event.observed_capture_id, 0)
            test.assertEqual(0, final_event.motion)
            goods_frame = {frame.id: frame for frame in self.captures}[final_event.observed_capture_id]
            test.assertEqual(2, goods_frame.scene.goods)
            test.assertEqual(final_event.command.source_capture_id, reference.authority_capture_id)
            test.assertEqual((0, 0, 0, 0, 0),
                             (reference.observed_capture_id, reference.primary_motion,
                              reference.fallback_attempted, reference.fallback_motion,
                              reference.selected_motion))
            test.assertEqual(reference.authority_capture_id, reference.selected_capture_id)
        else:
            test.assertEqual(world.gate, (status.x, status.y))
            test.assertEqual(1, moves[-1].motion)
        self.assert_holding_pause(test)

    def assert_holding_pause(self, test):
        pauses = [event for event in self.native_events if event.command.kind == 2]
        test.assertEqual(1, len(pauses))
        pause = pauses[0]
        test.assertEqual(2, pause.outcome)
        test.assertGreater(pause.observed_capture_id, 0, "holding PAUSE needs a new actual capture after ACK")
        frame = {frame.id: frame for frame in self.captures}[pause.observed_capture_id]
        test.assertEqual(1, frame.scene.state)
        test.assertTrue(frame.stable)
        test.assertEqual((pause.command.id, pause.command.id), (frame.start_prefix, frame.prefix))
        test.assertGreaterEqual(frame.start, pause.end_ns)
        test.assertGreaterEqual(frame.committed, frame.analysis_end)
        test.assertEqual(frame.id, self.final.last_capture_id)

    def assert_slow_stop(self, test):
        world, status = self.world, self.final
        test.assertEqual((3, 3, 0, 0, 1, 1),
                         (len(world.operations), world.moves, world.doors,
                          world.purchases, world.resumes, world.pauses))
        dx, dy = VECTORS[world.direction]
        test.assertEqual((3 * dx, 3 * dy), world.player)
        test.assertFalse(world.goods_visible)
        test.assertTrue(world.paused)
        test.assertEqual(["moved"] * 3, [op["result"] for op in world.operations])
        beats = [op["beat"] for op in world.operations]
        test.assertEqual(list(range(beats[0], beats[0] + 3)), beats)
        test.assertEqual((1, 9, 0, 1, 3, 3, 0, 0),
                         (status.terminal, status.reason, status.goods, status.paused,
                          status.inputs, status.moves, status.door_changes, status.terrain_changes))
        test.assertEqual(world.player, (status.x, status.y))
        test.assertIsNotNone(self.late)
        test.assertGreater(self.late["at"], self.late["original_deadline"])
        moves = [e for e in self.native_events if e.command.kind == 4]
        test.assertEqual(3, sum(e.outcome == 2 for e in moves))
        test.assertEqual([1, 1, 1], [e.motion for e in moves if e.outcome == 2])
        test.assertEqual(1, len([e for e in self.native_events if e.command.kind == 2]))
        fourth = [r for r in self.publications if r["command"].kind == 4 and r["command"].ordinal == 4]
        if self.slow == "capture":
            test.assertTrue(self.slow_started)
            test.assertEqual([], fourth, "an old authority must not reserve the fourth MOVE")
            slow = [f for f in self.captures if f.analysis_end - f.start == 160 * MS]
            test.assertGreaterEqual(len(slow), 2)
            test.assertEqual(self.slow_boundary - 210 * MS, slow[0].start)
            test.assertEqual(self.slow_boundary - 50 * MS, slow[0].analysis_end)
            test.assertEqual(self.slow_boundary - 45 * MS, slow[1].start)
            test.assertEqual(self.slow_boundary + 115 * MS, slow[1].analysis_end)
            # The first slow frame is real, stable, after ACK3, and confirms
            # movement three before being rejected as fourth-MOVE authority.
            test.assertTrue(slow[0].stable)
            test.assertEqual(slow[0].id, moves[2].observed_capture_id)
            test.assertLessEqual(self.late["at"] - self.late["original_deadline"], MS,
                                 "unreserved fourth MOVE must stop at its original deadline")
            test.assertLess(slow[0].start, self.late["original_deadline"] - TOLERANCE - 200 * MS)
        else:
            test.assertEqual(1, len(fourth))
            command = fourth[0]["command"]
            attempt = [r for r in self.begin_attempts if r["command"].id == command.id]
            test.assertEqual(1, len(attempt))
            test.assertEqual(0, attempt[0]["permitted"])
            test.assertEqual(60 * MS, attempt[0]["at"] - fourth[0]["at"])
            test.assertLess(fourth[0]["at"], command.not_before_ns)
            test.assertGreater(attempt[0]["at"], command.deadline_ns)
            test.assertEqual((attempt[0]["at"], command.deadline_ns),
                             (self.late["at"], self.late["original_deadline"]))
            test.assertEqual((3, 9), (moves[-1].outcome, moves[-1].reason))
        self.assert_holding_pause(test)

    def evidence(self):
        def fields(value):
            if isinstance(value, C.Structure):
                return {name: fields(getattr(value, name)) for name, _ in value._fields_}
            return value
        attempts = [row for row in self.begin_attempts if row["permitted"] and row["command"].kind == 4]
        phase_errors = [row["command"].target_ns - (EPOCH + op["beat"] * PERIOD)
                        for row, op in zip(attempts, self.world.operations)]
        return dict(direction=self.world.direction, latency_ns=self.latency, phase_ns=self.phase,
                    slow=self.slow, world_epoch_ns=EPOCH, world_period_ns=PERIOD,
                    world_lead_ns=LEAD, world_tolerance_ns=TOLERANCE,
                    c_target_minus_world_nominal_ns=phase_errors,
                    slow_world_fourth_not_before_ns=self.slow_boundary,
                    late=self.late,
                    player=self.world.player, gate=self.world.gate, paused=self.world.paused,
                    resumes=self.world.resumes, pauses=self.world.pauses, moves=self.world.moves,
                    doors=self.world.doors, purchases=self.world.purchases,
                    goods_visible=self.world.goods_visible, operations=self.world.operations,
                    native_status=fields(self.final), native_events=[fields(e) for e in self.native_events],
                    motion_references=[fields(r) for r in self.native_references],
                    publications=[fields_dict(row, fields) for row in self.publications],
                    begin_attempts=[fields_dict(row, fields) for row in self.begin_attempts],
                    control_blocks=self.control_blocks,
                    replaced_frames=self.replaced,
                    captures=[dict(id=f.id, start=f.start, end=f.end, decode_end=f.decode_end,
                                   analysis_start=f.analysis_start, analysis_end=f.analysis_end,
                                   commit=f.committed, start_prefix=f.start_prefix, prefix=f.prefix,
                                   start_inflight=f.start_inflight, stable=f.stable, accepted=f.accepted,
                                   scene_state=f.scene.state if f.scene else None,
                                   scene_goods=f.scene.goods if f.scene else None,
                                   beat_remaining=f.scene.beat_remaining if f.scene else None)
                              for f in self.captures])


def fields_dict(row, converter):
    return {key: converter(value) for key, value in row.items()}


class NativeGoalWorldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix="ngg2-goal-world-")
        cls.lib, cls.compile_commands, cls.sources = compile_world(cls.directory.name)
        cls.evidence_cases = []

    @classmethod
    def tearDownClass(cls):
        destination = Path(os.environ.get("NECRO_TEST060_WORLD_EVIDENCE",
                                          str(Path(tempfile.gettempdir()) / "test060-world")))
        destination.mkdir(parents=True, exist_ok=True)
        evidence = dict(scope="Synthetic production-C discrete timing/goal world; not real-game/iPhone acceptance, "
                              "dense motion, camera shake, codec or Runtime/AX integration.",
                        expectation="docs/tests/test060-world-cases.md", cases=cls.evidence_cases,
                        expected_goal_executions=160, expected_stop_executions=2,
                        goal_executions=sum(row["slow"] is None for row in cls.evidence_cases),
                        stop_executions=sum(row["slow"] is not None for row in cls.evidence_cases),
                        successful_executions=sum(row.get("passed", False) for row in cls.evidence_cases),
                        compile_commands=cls.compile_commands,
                        source_sha256={str(Path(path).relative_to(ROOT)): value
                                       for path, value in cls.lib.world_source_sha256.items()},
                        object_sha256=cls.lib.world_object_sha256,
                        library_sha256=cls.lib.world_library_sha256)
        (destination / "goal-world.json").write_text(json.dumps(evidence, indent=2) + "\n")
        cls.directory.cleanup()

    def test_160_fixed_goal_executions_reach_goods_on_six_consecutive_world_beats(self):
        count = 0
        for name, direction, material in CASES:
            for latency in (60 * MS, 70 * MS, 80 * MS, 85 * MS):
                for phase in capture_phases(latency):
                    with self.subTest(case=name, latency=latency, phase=phase):
                        run = GoalRun(self.lib, direction, material, latency, phase).run()
                        record = dict(name=name, passed=False, **run.evidence())
                        self.evidence_cases.append(record)
                        count += 1
                        run.assert_goal(self)
                        run.assert_pipeline(self)
                        run.assert_admission(self)
                        record["passed"] = True
        self.assertEqual(160, count)

    def test_slow_capture_before_fourth_move_stops_at_original_deadline_and_holds_pause(self):
        run = GoalRun(self.lib, 3, 7, 85 * MS, 0, slow="capture").run()
        record = dict(name="SLOW-CAPTURE", passed=False, **run.evidence())
        self.evidence_cases.append(record)
        run.assert_slow_stop(self)
        record["passed"] = True

    def test_slow_prepare_before_fourth_move_never_sends_after_original_deadline(self):
        run = GoalRun(self.lib, 3, 7, 85 * MS, 0, slow="prepare").run()
        record = dict(name="SLOW-PREPARE", passed=False, **run.evidence())
        self.evidence_cases.append(record)
        run.assert_slow_stop(self)
        record["passed"] = True


if __name__ == "__main__":
    unittest.main()
