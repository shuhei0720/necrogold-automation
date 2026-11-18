"""TEST115 shop continuation through public Controller calls.

Clocks and later game responses are procedural. R2 uses the unchanged public
upper112 pixel world through normal Perception/Ring. R3 uses declared finite
procedural Scenes and normal Ring pixels; recorded PNG calibration is separate.
Neither fixture represents unrecorded future iPhone frames.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import subprocess
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests import test_native_upper_entry112 as upper
from tests import test_native_current_view114 as current
from tests import test_native_irregular110 as irregular
from tests import test_native_offer_coverage104 as offer
from tests.test_native_ring094 import Options, Result, Clock, Cancelled


class NativeShop115Tests(unittest.TestCase):
    PERIOD = 520_666_909
    SYNTH = 275_953_666
    RESPONSE = 66_098_334

    @classmethod
    def setUpClass(cls):
        previous = os.environ.get('NECRO112_UPPER_CORE')
        selected = os.environ.get('NECRO115_SHOP_CORE')
        try:
            if selected:
                os.environ['NECRO112_UPPER_CORE'] = selected
            upper.NativeUpperEntry112Tests.setUpClass()
        finally:
            if previous is None:
                os.environ.pop('NECRO112_UPPER_CORE', None)
            else:
                os.environ['NECRO112_UPPER_CORE'] = previous
        cls.lib = upper.NativeUpperEntry112Tests.lib
        cls.ring = upper.NativeUpperEntry112Tests.ring
        cls.pixels = upper.NativeUpperEntry112Tests.pixels
        core = Path(selected or native.CORE)
        source = Path(__file__).resolve().parents[1] / 'patches/loopctrl'
        library = Path(upper.NativeUpperEntry112Tests.pixel_tmp.name) / 'partial115.so'
        subprocess.run(['cc', '-std=c99', '-O2', '-fno-fast-math', '-ffp-contract=off',
            '-Wall', '-Wextra', '-Werror', '-shared', '-fPIC', '-I'+str(core),
            '-I'+str(source), '-I'+str(upper.NativeUpperEntry112Tests.pixel_tmp.name),
            str(source/'ngg2_runtime_scene_fixtures.c'),
            str(source/'ngg2_runtime115_fixture.c'), '-lm', '-o', str(library)], check=True)
        cls.partial_pixels = C.CDLL(str(library))
        cls.partial_pixels.ng2_fixture_partial115_rgba.argtypes = [C.c_void_p, C.c_size_t, C.c_int, C.c_double]
        cls.lib.ng2_controller_enable_irregular.argtypes = [C.c_void_p]
        cls.lib.ng2_controller_enable_restart_yield.argtypes = [C.c_void_p]
        cls.lib.ng2_controller_observe_irregular_at.argtypes = [C.c_void_p,
            C.POINTER(native.Scene), C.POINTER(irregular.Observation)] + [C.c_uint64] * 4 + [C.c_int32, C.c_uint64]
        cls.lib.ng2_controller_observe_irregular_at.restype = None

    @classmethod
    def tearDownClass(cls):
        upper.NativeUpperEntry112Tests.tearDownClass()

    def fresh_upper(self):
        self.fixture = upper.NativeUpperEntry112Tests(methodName='runTest')
        self.fixture.lib = self.lib
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.h = self.fixture.p.harness()
        self.q = self.fixture.q
        self.q.h = self.h

    def upper_frame(self, stage, direction=1, *, advance=20_000_000):
        self.h.now += advance
        start, end = self.h.now - 58_483_959, self.h.now - 35_162_542
        midpoint = (start + end) // 2
        q = ((5*native.SECOND - midpoint) % self.PERIOD) / self.PERIOD
        pixels = (C.c_ubyte * (896*414*4))()
        self.assertEqual(1, self.pixels.ng2_fixture_upper112_rgba(
            pixels, len(pixels), stage, int(direction == 2), q))
        scene = native.Scene()
        self.assertEqual(0, self.lib.ng2_analyze_rgba(pixels, len(pixels), 896*4, C.byref(scene)))
        self.assertEqual(1, self.h.observe_actual(scene, start=start, end=end))
        return pixels, scene

    def normal_commit(self, pixels, scene, *, callback_delay=5_000_000, mutate=None):
        state = self.q.cycle()
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(
            self.h.engine, state.job_id, state.capture_id, state.prefix, self.h.now))
        clock = Clock(lambda _context: self.h.now)
        cancelled = Cancelled(lambda _context: 0)
        options = Options(abi=1, size=C.sizeof(Options), mode=2, deadline_ns=state.deadline_ns,
            now_ns=clock, cancelled=cancelled, scene=C.addressof(scene), fast=1)
        result = Result()
        self.assertEqual(0, self.ring.ng2_ring_assess_rgba(
            pixels, len(pixels), 896*4, C.byref(options), C.byref(result)))
        if mutate:
            mutate(result)  # Explicit negative test at the public result boundary.
        self.h.now += callback_delay
        self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine,
            state.job_id, state.capture_id, state.prefix, self.h.now, C.byref(result)))
        return result

    def upper_ticket(self, stage, direction=1):
        for _ in range(230):
            self.upper_frame(stage, direction)
            ready, command = self.h.tick()
            if ready:
                self.assertEqual(4, command.kind,
                    'whole normal shop route must continue before a holding PAUSE')
                return command
            self.assertFalse(self.h.status().terminal, 'shop route terminated before all three goods')
        self.fail('no bounded upper observation ticket')

    def phone_ack(self, command, stage, direction):
        # Captures continue between publication and begin. Stopping them here
        # would artificially age the phase model and shorten the parent.
        while self.h.now < command.not_before_ns:
            self.upper_frame(stage, direction,
                advance=min(20_000_000, command.not_before_ns-self.h.now))
        self.assertEqual(1, self.lib.ng2_controller_begin(
            self.h.engine, command.id, self.h.now, 1, 0, 1))
        self.h.now += self.SYNTH
        self.assertEqual(1, self.lib.ng2_controller_complete(
            self.h.engine, command.id, self.h.now, 1))
        self.h.prefix = command.id
        self.h.now += self.RESPONSE

    def test_phone_delay_normal_hhdd_reaches_complete_negative_and_restart(self):
        for direction in (1, 2):
            with self.subTest(direction=direction):
                self.fresh_upper()
                for stage in (0, 1):
                    command = self.upper_ticket(stage, direction)
                    self.assertEqual(direction, command.direction)
                    self.phone_ack(command, stage, direction)
                    pixels, scene = self.upper_frame(stage+1, direction, advance=0)
                    self.assertEqual(1 if stage == 0 else 3, self.h.events()[-1].motion)
                root = self.q.cycle()
                self.assertEqual((1, 7), (scene.goods, sum(cell == 6 for cell in scene.tiles)))
                result = self.normal_commit(pixels, scene)
                self.assertEqual((0, 1), (result.outcome, result.coverage))
                # Procedural callback/proof scheduling delay, independent of
                # the 5ms normal worker: the next preparation phase is gone.
                self.h.now += 200_000_000
                issued = []
                for stage, wanted in zip(range(2, 6), (direction, direction, 4, 4)):
                    command = self.upper_ticket(stage, direction)
                    self.assertEqual(wanted, command.direction)
                    self.assertLessEqual(command.target_ns + 80_000_000,
                        root.continuation_deadline_ns, 'forecast retains earliest visual room')
                    before = self.h.status()
                    self.phone_ack(command, stage, direction)
                    self.assertEqual(before.moves, self.h.status().moves, 'ACK is not MOVED')
                    pixels, scene = self.upper_frame(stage+1, direction, advance=0)
                    event = self.h.events()[-1]
                    self.assertEqual((1, *native.DIRS[wanted]), (event.motion, event.dx, event.dy))
                    self.assertLessEqual(self.h.now, root.continuation_deadline_ns,
                        '275ms synth and recorded relative visual delay must fit original parent')
                    result = self.normal_commit(pixels, scene)
                    self.assertEqual(3 if stage == 5 else 0, result.outcome)
                    self.assertLessEqual(self.q.cycle().continuation_deadline_ns,
                        root.continuation_deadline_ns)
                    issued.append(command)
                self.assertEqual((3, 2), (result.outcome, result.coverage))
                self.assertEqual(4, len(issued))
                self.assertEqual((6, 5, 1), (self.h.status().inputs,
                    self.h.status().moves, self.h.status().door_changes))
                self.q.pause_observed()
                self.assertEqual(1, self.q.durable())
                ready, restart = self.h.tick()
                self.assertEqual((1, 3), (ready, restart.kind))
                self.assertEqual(1, self.q.intent(restart))

    def partial_source(self, stage):
        q = ((5*native.SECOND-(self.h.now-1)) % native.PERIOD) / native.PERIOD
        pixels = (C.c_ubyte * (896*414*4))()
        self.assertEqual(1, self.partial_pixels.ng2_fixture_partial115_rgba(pixels, len(pixels), stage, q))
        scene = native.Scene()
        self.assertEqual(0, self.lib.ng2_analyze_rgba(pixels, len(pixels), 896*4, C.byref(scene)))
        return pixels, scene

    def partial_frame(self, stage, *, advance=20_000_000, prefix=None):
        self.h.now += advance
        pixels, scene = self.partial_source(stage)
        self.assertEqual(1, self.h.observe_actual(scene,
            prefix=self.h.prefix if prefix is None else prefix))
        return pixels, scene

    def partial_pending(self, *, yield_enabled=True):
        self.fixture = current.current_view_fixture(self.lib)
        self.fixture.yield_enabled = yield_enabled
        self.addCleanup(self.fixture.doCleanups)
        self.h = self.fixture.harness()
        self.q = cycle.NativeCycle094Tests(methodName='runTest')
        self.q.lib, self.q.h = self.lib, self.h
        for stage in (0, 1):
            for _ in range(220):
                self.partial_frame(stage)
                ready, command = self.h.tick()
                if ready:
                    self.assertEqual((4, 3), (command.kind, command.direction))
                    break
            else:
                self.fail('normal partial pixel world did not reach its UP door')
            self.h.ack(command)
            self.h.now = max(self.h.now, command.target_ns+100_000_000)
            pixels, scene = self.partial_frame(stage+1, advance=0)
            self.assertEqual(1 if stage == 0 else 3, self.h.events()[-1].motion)
        self.old = native.Scene.from_buffer_copy(bytes(scene))
        self.root = self.q.cycle()
        result = self.normal_commit(pixels, scene)
        self.assertEqual((0, 1, 0, 0, 0), (result.outcome, result.coverage,
            result.row_count, result.partial_count, result.partial_safe_no_positive))
        self.assertEqual((3, 0), (self.q.cycle().state, self.q.cycle().completed_shops))
        self.before_counts = self.h.status().inputs, self.h.status().moves

    def queue_partial(self):
        self.partial_pending()
        self.latest_pixels, self.latest = self.partial_frame(3)
        state = self.q.cycle()
        self.assertEqual((self.root.job_id+1, self.h.number, self.root.prefix, 1),
            (state.job_id, state.capture_id, state.prefix, state.pending),
            'top projection change must retire old framing and queue one independent current PARTIAL job')
        self.assertEqual(self.before_counts, (self.h.status().inputs, self.h.status().moves))
        self.assertLessEqual(state.continuation_deadline_ns, self.root.continuation_deadline_ns)
        self.assertEqual(self.root.hold_started_ns, state.hold_started_ns)
        return state

    def test_partial_projection_change_queues_independent_current_data(self):
        self.queue_partial()

    def partial_ticket(self):
        self.queue_partial()
        result = self.normal_commit(self.latest_pixels, self.latest)
        self.assertEqual((0, 1, 0, 1), (result.outcome, result.coverage,
            result.row_count, result.partial_safe_no_positive))
        self.assertGreater(result.partial_count, 0, 'normal producer exposes real safe partial probes')
        self.assertEqual(0, self.h.tick()[0], 'new normal DATA gives no direction credit')
        self.partial_frame(3)
        self.assertEqual(0, self.h.tick()[0], 'one direct zero is insufficient')
        self.first_proof = self.h.number
        self.partial_frame(3)
        self.second_proof = self.h.number
        for _ in range(100):
            ready, command = self.h.tick()
            if ready:
                self.assertEqual((4, 3), (command.kind, command.direction))
                self.assertGreaterEqual(command.source_capture_id, self.second_proof)
                self.assertLessEqual(command.target_ns+50_000_000, self.root.continuation_deadline_ns)
                return command
            self.partial_frame(3)
        self.fail('independent PARTIAL epoch did not produce its single qualified UP')

    def test_partial_normal_probes_two_zeros_one_up_then_unknown_never_mints_second_up(self):
        command = self.partial_ticket()
        self.h.ack(command)
        self.h.now = max(self.h.now, command.target_ns+100_000_000)
        pixels, scene = self.partial_frame(4, advance=0)
        event = self.h.events()[-1]
        self.assertEqual((1, 0, -1), (event.motion, event.dx, event.dy))
        result = self.normal_commit(pixels, scene)
        self.assertEqual((0, 1), (result.outcome, result.coverage))
        self.assertEqual((self.before_counts[0]+1, self.before_counts[1]+1),
            (self.h.status().inputs, self.h.status().moves))
        self.assertEqual(0, self.h.status().restarts)
        for _ in range(5):
            ready, next_command = self.h.tick()
            self.assertFalse(ready and next_command.kind in (3, 4),
                'the transferred one-view allowance cannot become entry2 or upper4')
            if self.h.status().input_state:
                break
            self.partial_frame(4)

    def test_partial_one_up_then_normal_complete_goods_durable_and_restart(self):
        command = self.partial_ticket()
        self.h.ack(command)
        self.h.now = max(self.h.now, command.target_ns+100_000_000)
        pixels, scene = self.partial_frame(5, advance=0)
        self.assertEqual(2, scene.goods, 'the new source independently shows complete merchandise')
        event = self.h.events()[-1]
        self.assertEqual((1, 0, -1), (event.motion, event.dx, event.dy))
        result = self.normal_commit(pixels, scene)
        self.assertEqual((3, 2), (result.outcome, result.coverage),
            'only the actual normal complete producer may supply target absence')
        self.assertEqual((self.before_counts[0]+1, self.before_counts[1]+1),
            (self.h.status().inputs, self.h.status().moves))
        self.q.pause_observed()
        self.assertEqual(1, self.q.durable())
        ready, restart = self.h.tick()
        self.assertEqual((1, 3), (ready, restart.kind))
        self.assertEqual(1, self.q.intent(restart))
        self.h.ack(restart)
        self.assertEqual(0, self.h.status().restarts, 'ACK is not a proven next floor')
        self.h.now += 210_000_000
        self.partial_frame(0)
        self.assertEqual(1, self.h.status().restarts)

    def no_move_or_restart(self):
        ready, command = self.h.tick()
        self.assertFalse(ready and command.kind in (3, 4))

    @staticmethod
    def tile_index(x, y):
        return (y+5)*23+x+11

    def exact_mask(self, scene):
        items = {(i % 23-11, i // 23-5) for i, value in enumerate(scene.tiles) if value == 6}
        protected = upper.NativeUpperEntry112Tests.cross(items)
        for i in range(230):
            scene.protected_cells[i] = int((i % 23-11, i // 23-5) in protected)

    def test_partial_requalification_rejects_real_goods_wall_route_and_unexplained_changes(self):
        for fault in ('lower_item', 'old_gold', 'unknown_up', 'protected_up',
                      'extra_item', 'remote_tile', 'unsupported_top_gold'):
            with self.subTest(fault=fault):
                self.partial_pending()
                self.h.now += 20_000_000
                _pixels, scene = self.partial_source(3)
                if fault == 'lower_item':
                    scene.tiles[self.tile_index(-1, -4)] = 1
                    self.exact_mask(scene)
                elif fault == 'old_gold': scene.tiles[self.tile_index(1, -2)] = 1
                elif fault == 'unknown_up': scene.tiles[self.tile_index(0, -1)] = 0
                elif fault == 'protected_up': scene.protected_cells[self.tile_index(0, -1)] = 1
                elif fault == 'extra_item':
                    scene.tiles[self.tile_index(5, 3)] = 6
                    self.exact_mask(scene)
                elif fault == 'remote_tile': scene.tiles[self.tile_index(-6, 2)] = 2
                elif fault == 'unsupported_top_gold': scene.tiles[self.tile_index(0, -5)] = 2
                self.h.observe_actual(scene)
                self.assertEqual(self.root.job_id, self.q.cycle().job_id,
                    'an unexplained source change cannot mint an independent epoch')
                self.assertEqual(self.before_counts, (self.h.status().inputs, self.h.status().moves))
                self.no_move_or_restart()

    def test_partial_requires_yield_profile_matching_prefix_and_original_parent(self):
        for fault in ('no_yield', 'prefix', 'parent', 'source_age'):
            with self.subTest(fault=fault):
                self.partial_pending(yield_enabled=fault != 'no_yield')
                self.h.now = self.root.continuation_deadline_ns+1 if fault == 'parent' else self.h.now+20_000_000
                _pixels, scene = self.partial_source(3)
                kwargs = {'prefix': self.h.prefix+1} if fault == 'prefix' else {}
                if fault == 'source_age':
                    self.h.now += 160_000_000
                    kwargs.update(start=self.h.now-150_000_001, end=self.h.now-140_000_001)
                self.h.observe_actual(scene, **kwargs)
                self.assertEqual(self.root.job_id, self.q.cycle().job_id)
                self.no_move_or_restart()

    def test_partial_two_zeros_without_a_new_phase_sample_cannot_use_old_fit(self):
        self.queue_partial()
        self.normal_commit(self.latest_pixels, self.latest)
        for _ in range(8):
            self.h.now += 20_000_000
            _pixels, scene = self.partial_source(3)
            scene.beat_valid = 0  # Explicit trust-boundary missing-observation counterexample.
            self.h.observe_actual(scene)
            self.no_move_or_restart()
        self.assertEqual(self.before_counts, (self.h.status().inputs, self.h.status().moves))

    def test_partial_pairwise_zero_cannot_replace_the_fixed_new_anchor_or_retry_it(self):
        self.queue_partial()
        self.normal_commit(self.latest_pixels, self.latest)
        changed = native.Scene.from_buffer_copy(bytes(self.latest))
        changed.signature[:] = bytes((37*i+71) % 251 for i in range(len(changed.signature)))
        direct = self.lib.ng2_motion.argtypes[3]._type_()
        self.assertEqual(1, self.lib.ng2_motion(C.byref(self.latest), C.byref(changed), 3, C.byref(direct)))
        self.assertEqual((0, 0, 0), (direct.kind, direct.dx, direct.dy))
        first = native.Scene.from_buffer_copy(bytes(changed))
        self.assertEqual(1, self.lib.ng2_motion(C.byref(first), C.byref(changed), 3, C.byref(direct)))
        self.assertEqual((2, 0, 0), (direct.kind, direct.dx, direct.dy))
        current_job = self.q.cycle().job_id
        for scene in (first, changed, self.latest):
            self.h.now += 20_000_000
            self.h.observe_actual(scene)
            self.no_move_or_restart()
        self.assertEqual(current_job, self.q.cycle().job_id, 'invalid current epoch cannot migrate or retry')

    def test_partial_normal_candidate_has_priority_over_any_observation(self):
        self.queue_partial()
        # Positive trust-boundary case: the normal classifier supplies its
        # actual candidate, instead of a hand-written Result outcome.
        raw = offer.shop_pixels(left=415, sy=47, target=True, target_name=False)
        pixels = C.create_string_buffer(raw, len(raw))
        result = self.normal_commit(pixels, self.latest)
        self.assertIn(result.outcome, (1, 2), 'real normal target pixels must supply the positive oracle')
        self.assertEqual(1, self.q.cycle().candidate_latched)
        self.no_move_or_restart()

    def test_partial_forged_complete_negative_cannot_become_a_restart(self):
        self.queue_partial()
        state = self.q.cycle()
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(
            self.h.engine, state.job_id, state.capture_id, state.prefix, self.h.now))
        value = Result(abi=1, size=C.sizeof(Result), outcome=3, coverage=2,
            selected_row=-1, selected_partial=-1, started_ns=self.h.now, finished_ns=self.h.now)
        self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine,
            state.job_id, state.capture_id, state.prefix, self.h.now, C.byref(value)))
        self.assertEqual(0, self.q.cycle().outcome)
        self.no_move_or_restart()

    def test_partial_probe_result_boundaries_never_authorize_the_new_view(self):
        for fault in ('wrong_cell', 'wrong_row', 'half_cell', 'upper_bound',
                      'nonfinite', 'strong_name', 'outside_preservation', 'safe0', 'safe2'):
            with self.subTest(fault=fault):
                self.queue_partial()
                def corrupt(value):
                    self.assertGreater(value.partial_count, 0)
                    slot = value.partial[0]
                    if fault == 'wrong_cell': slot.cx = 448+2*36
                    elif fault == 'wrong_row': slot.sy += 36
                    elif fault == 'half_cell': slot.cx = 448+18
                    elif fault == 'upper_bound': slot.icon_upper_bound = .80
                    elif fault == 'nonfinite': slot.icon_score = float('nan')
                    elif fault == 'strong_name':
                        slot.word_present = 1
                        slot.word_iou = slot.word_coverage = .95
                    elif fault == 'outside_preservation': slot.sy = 250
                    elif fault == 'safe0': value.partial_safe_no_positive = 0
                    elif fault == 'safe2': value.partial_safe_no_positive = 2
                self.normal_commit(self.latest_pixels, self.latest, mutate=corrupt)
                self.assertNotEqual(0, self.q.cycle().status,
                    'malformed probes must be rejected, not wait like an admissible current view')
                self.no_move_or_restart()
                self.assertEqual(self.before_counts, (self.h.status().inputs, self.h.status().moves))

