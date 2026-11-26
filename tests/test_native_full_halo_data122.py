"""One observed FULL halo exposure gets a new immutable DATA epoch.

All C ownership is earned through public lifecycle calls. The temporary C
suffix only reads the earned framing/source/counters; it never sets state.
Scene/HUD clocks and Ring pixels are declared procedural inputs, not a replay
of missing private iPhone state or future game responses.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests import test_native_current_view114 as current
from tests import test_native_irregular110 as irregular
from tests import test_native_offer_coverage104 as offer
from tests import test_native_single_sign_shop103 as single
from tests import test_native_ring_bank094 as bank
from tests.test_native_observation072 import Motion


READ_ONLY_SUFFIX = r'''
/* Public lifecycle earned every field. This test suffix only copies it. */
int ng2_halo122_earned(const NG2Controller *p,uint64_t *out,size_t count){
 if(!p||!out||count<14)return 0;
 out[0]=(uint64_t)p->cycle_full_framing;out[1]=(uint64_t)p->cycle_full_spent;
 out[2]=(uint64_t)p->cycle_full_source_valid;out[3]=p->cycle_full_source_id;
 out[4]=p->cycle_full_source_start;out[5]=p->cycle_full_source_prefix;
 out[6]=p->cycle_full_parent;out[7]=(uint64_t)p->cycle_current_used;
 out[8]=(uint64_t)p->cycle_current_active;out[9]=(uint64_t)p->cycle_current_partial;
 out[10]=(uint64_t)p->cycle_retry_used;out[11]=(uint64_t)p->cycle_entered.active;
 out[12]=(uint64_t)cycle_data_prepared_pause(p);
 out[13]=(uint64_t)cycle_current_data_pair(&p->cycle_anchor,&p->scene);
 return 14;
}
'''


class NativeFullHaloData122Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='full-halo122-')
        cls.addClassCleanup(cls.temp.cleanup)
        folder = Path(cls.temp.name)
        cls.core = Path(os.environ.get('NECRO122_FULL_HALO_CORE', str(native.CORE)))
        staged = folder/'core'
        staged.mkdir()
        for source in cls.core.iterdir():
            if source.suffix in ('.h', '.c'):
                shutil.copyfile(source, staged/source.name)
        controller = cls.core/'NG2Controller.c'
        (staged/'NG2Controller.c').write_bytes(controller.read_bytes()+READ_ONLY_SUFFIX.encode())
        prior = native.CORE
        try:
            native.CORE = staged
            cycle.NativeCycle094Tests.setUpClass()
        finally:
            native.CORE = prior
        cls.lib = lib = cycle.NativeCycle094Tests.lib
        lib.ng2_controller_observe_at.argtypes = [*lib.ng2_controller_observe.argtypes, C.c_uint64]
        lib.ng2_motion.argtypes = [C.POINTER(native.Scene), C.POINTER(native.Scene),
                                 C.c_int32, C.POINTER(Motion)]
        cls.ring = bank.NativeRingBank094Tests.build_library(cls.core/'NG2Ring.c', folder/'ring.so')
        lib.ng2_controller_create_cycle.argtypes = [C.c_uint64]
        lib.ng2_controller_create_cycle.restype = C.c_void_p
        lib.ng2_controller_enable_irregular.argtypes = [C.c_void_p]
        lib.ng2_controller_enable_restart_yield.argtypes = [C.c_void_p]
        lib.ng2_controller_observe_irregular_at.argtypes = [C.c_void_p,
            C.POINTER(native.Scene), C.POINTER(irregular.Observation)] + [C.c_uint64]*4 + [C.c_int32, C.c_uint64]
        lib.ng2_halo122_earned.argtypes = [C.c_void_p, C.POINTER(C.c_uint64), C.c_size_t]

    @classmethod
    def tearDownClass(cls):
        cycle.NativeCycle094Tests.tearDownClass()

    def setUp(self):
        self.p = current.current_view_fixture(self.lib)
        self.addCleanup(self.p.doCleanups)

    def earned(self):
        out = (C.c_uint64*14)()
        self.assertEqual(14, self.lib.ng2_halo122_earned(self.h.engine, out, 14))
        return tuple(out)

    def counts(self):
        s = self.h.status()
        return tuple(getattr(s, k) for k in ('inputs', 'moves', 'door_changes',
            'terrain_changes', 'restarts', 'x', 'y'))

    def normal(self, source, *, unknown=False, target=False):
        pixels = single.shop_pixels(left=268, sy=159, missing_wall=unknown,
                                    target=target, target_name=False)
        status, value = offer.normal_assess(self.ring, pixels,
            self.h.scene(2, 2, source, beat=True))
        self.assertEqual((0, 0), (status, value.status))
        return value

    def start_worker(self):
        state = self.q.cycle()
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            state.job_id, state.capture_id, state.prefix, self.h.now))
        return state

    def commit(self, result, delay=10_000_000):
        state = self.q.cycle()
        if not state.worker_started_ns:
            self.start_worker()
        result.started_ns = self.h.now
        self.h.now += delay
        result.finished_ns = self.h.now
        self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine,
            state.job_id, state.capture_id, state.prefix, self.h.now, C.byref(result)))

    def admitted(self, *, enabled=True, old_halo='unknown', old_target=False):
        self.p.yield_enabled = enabled
        self.h = self.p.harness()
        self.q = cycle.NativeCycle094Tests(methodName='runTest')
        self.q.h, self.q.lib = self.h, self.lib
        cells = {(0, 0): 'floor', (1, 0): 'floor', (-1, 0): 'door',
            (-1, -1): 'gold', (-1, 1): 'gold', (-8, -3): 'stone',
            (5, 2): 'stone', (8, 3): 'stone'}
        for y in range(-2, 3):
            cells[(-7, y)] = 'gold'
        for x in range(-6, -1):
            cells[(x, 0)] = 'floor'
        for x in range(-5, -2):
            cells[(x, 0)], cells[(x, 1)] = 'dirt', 'floor'
        initial = {(x-1, y): kind for (x, y), kind in cells.items()}
        initial[(0, 0)] = 'floor'
        terrain = native.textured(initial)
        self.h.fit(terrain)
        first = self.h.next_move(terrain)
        self.assertEqual(1, first.direction)
        self.h.ack(first)
        terrain = native.translated(terrain, 1)
        self.h.observed_result(first, terrain)
        self.assertEqual(1, self.h.events()[-1].motion)
        opening = self.h.next_move(terrain)
        self.assertEqual(1, opening.direction)
        self.h.ack(opening)
        source = deepcopy(terrain)
        source.tiles[(-1, 0)] = 'floor'
        source.goods = 'visible'
        for x in range(-5, -2):
            source.tiles[(x, 0)] = 'item'
        source.protected = {(x+dx, y+dy) for (x, y), kind in source.tiles.items()
            if kind == 'item' for dx, dy in ((0, 0), *native.DIRS.values())}
        if old_halo == 'unknown':
            source.tiles.pop((-3, -1), None)
        else:
            source.tiles[(-3, -1)] = old_halo
        source.tiles[(6, 4)] = 'floor'
        self.h.now = max(self.h.now+2, opening.target_ns+100_000_000)
        self.assertEqual(1, self.h.observe_actual(self.h.scene(2, 2, source, beat=True)))
        self.assertEqual((2, 1, 1, 3), (self.h.status().inputs, self.h.status().moves,
            self.h.status().door_changes, self.h.events()[-1].motion),
            'the FULL source is the actual opening response, not an invented entered unit')
        self.source, self.opening, self.root = source, opening, self.q.cycle()
        self.saved_counts = self.counts()
        value = self.normal(source, unknown=True, target=old_target)
        if old_target:
            self.assertIn(value.outcome, (1, 2))
        else:
            self.assertEqual((0, 1, 1, 2, 0), (value.outcome, value.coverage,
                value.row_count, value.partial_count, value.partial_safe_no_positive))
        self.commit(value)
        if not old_target:
            state = self.q.cycle()
            self.assertEqual((3, 0, 0), (state.state, state.pending, state.completed_shops))
            self.assertEqual((1, 1, 1, state.capture_id, state.capture_start_ns,
                state.prefix, state.continuation_deadline_ns), self.earned()[:7],
                'the normal UNKNOWN must publicly earn exact unissued framing1/source/parent before halo current')
            self.assertEqual((0, 0, 0, 0, 0), self.earned()[7:12],
                'no current DATA, spent shared DATA, or entered token was injected')
            self.assertEqual(self.saved_counts, self.counts())
            self.assertEqual(0, self.h.status().input_state)
        return source

    def latest(self):
        value = deepcopy(self.source)
        value.tiles[(-3, -1)] = 'dirt'
        value.tiles[(6, 4)] = 'dirt'
        return value

    def observe(self, source, *, advance=10_000_000, age=2, prefix=None, stable=1):
        self.h.now += advance
        return self.h.observe_actual(self.h.scene(2, 2, source, beat=True),
            start=self.h.now-age, end=self.h.now,
            prefix=self.h.prefix if prefix is None else prefix, stable=stable)

    def queued(self):
        self.admitted()
        latest = self.latest()
        self.assertEqual((2, 0, 0), self.h.motion(self.source, latest, 1))
        self.assertEqual(1, self.observe(latest))
        job = self.q.cycle()
        self.assertEqual((self.root.job_id+1, self.h.number, 1, 0),
            (job.job_id, job.capture_id, job.pending, job.worker_started_ns),
            'a new immutable DATA source must replace the rejected halo comparison before any framing MOVE tick')
        self.assertEqual((0, 1, 0), self.earned()[:3],
            'the consumed FULL observation allowance stays spent after DATA-only downgrade')
        self.assertEqual((1, 1, 2, 1, 0), self.earned()[7:12],
            'one current mode2 job consumes one shared DATA and never gains an entered token')
        self.assertEqual((self.root.prefix, self.root.hold_started_ns,
            self.root.continuation_deadline_ns), (job.prefix, job.hold_started_ns,
            job.continuation_deadline_ns))
        self.assertEqual(self.saved_counts, self.counts())
        self.assertEqual(0, self.h.status().input_state)
        self.assertEqual(0, self.h.tick()[0], 'DATA has no MOVE/RS/UI input authority')
        return latest, job

    def no_new_data_or_progress(self):
        self.assertEqual(self.root.job_id, self.q.cycle().job_id)
        self.assertEqual(self.saved_counts, self.counts())
        self.assertEqual(0, self.h.status().restarts)

    def test_exact_halo_exposure_queues_mode2_then_normal_negative_durable_restart(self):
        latest, job = self.queued()
        value = self.normal(latest)
        self.assertEqual((3, 2, 7), (value.outcome, value.coverage,
            value.certificate.policy_version), 'the new source has a real complete normal policy7 result')
        self.commit(value)
        self.assertEqual((3, 0, 4, job.capture_id), (self.q.cycle().outcome,
            self.q.cycle().status, self.q.cycle().state, self.q.cycle().capture_id))
        self.assertEqual(self.saved_counts, self.counts())
        self.assertEqual(0, self.q.durable())
        self.q.pause_observed()
        self.assertEqual(0, self.h.tick()[0])
        self.assertEqual(1, self.q.durable())
        ready, restart = self.h.tick()
        self.assertEqual((1, 3), (ready, restart.kind))
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine,
            restart.id, self.h.now, 1, 0, 1))
        self.assertEqual(1, self.q.intent(restart))
        self.q.next_floor(restart)
        state = self.q.cycle()
        self.assertEqual(1, self.lib.ng2_controller_cycle_outcome_commit(self.h.engine,
            state.job_id, state.next_floor_capture_id, self.h.prefix, self.h.now))
        self.assertEqual(self.root.level_id+1, self.q.cycle().level_id)
        self.assertEqual(self.saved_counts[:4], self.counts()[:4])

    def test_new_unknown_is_held_and_cannot_remint_current_data_or_observation_move(self):
        latest, job = self.queued()
        value = self.normal(latest, unknown=True)
        self.assertEqual(0, value.outcome)
        self.commit(value)
        self.assertEqual((0, 0, 7), (self.q.cycle().outcome,
            self.q.cycle().status, self.q.cycle().state))
        second = deepcopy(latest)
        second.tiles[(-4, -1)] = 'dirt'
        self.observe(second)
        self.assertEqual((job.job_id, 1), (self.q.cycle().job_id, self.earned()[10]))
        ready, command = self.h.tick()
        self.assertFalse(ready and command.kind in (3, 4))
        self.assertEqual(self.saved_counts, self.counts())

    def test_new_normal_target_wins_without_move_or_restart(self):
        latest, job = self.queued()
        value = self.normal(latest, target=True)
        self.assertIn(value.outcome, (1, 2))
        self.commit(value)
        self.assertEqual((1, 7, job.capture_id), (self.q.cycle().candidate_latched,
            self.q.cycle().state, self.q.cycle().capture_id))
        self.assertEqual(self.saved_counts, self.counts())
        ready, command = self.h.tick()
        self.assertFalse(ready and command.kind in (3, 4))

    def test_two_halo_changes_reverse_and_other_materials_do_not_gain_data(self):
        for fault in ('two', 'floor', 'stone', 'reverse'):
            with self.subTest(fault=fault):
                self.setUp()
                self.admitted(old_halo='dirt' if fault == 'reverse' else 'unknown')
                latest = self.latest()
                if fault == 'two': latest.tiles[(-4, -1)] = 'dirt'
                elif fault == 'reverse': latest.tiles.pop((-3, -1), None)
                else: latest.tiles[(-3, -1)] = fault
                self.observe(latest)
                self.no_new_data_or_progress()

    def test_item_mask_gold_door_and_walking_cross_cannot_borrow_halo_admission(self):
        for fault in ('item', 'mask', 'gold', 'door', 'origin', 'next', 'cross'):
            with self.subTest(fault=fault):
                self.setUp(); self.admitted(); latest = self.latest()
                if fault == 'item': latest.tiles[(-3, 0)] = 'floor'
                elif fault == 'mask': latest.protected.remove((-4, -1))
                elif fault == 'gold': latest.tiles[(-7, -1)] = 'floor'
                elif fault == 'door': latest.tiles[(6, 4)] = 'door'
                elif fault == 'origin': latest.tiles[(0, 0)] = 'dirt'
                elif fault == 'next': latest.tiles[(-1, 0)] = 'dirt'
                else: latest.tiles[(1, 0)] = 'dirt'
                self.observe(latest)
                self.no_new_data_or_progress()

    def test_unknown_motion_feature_off_candidate_and_invalid_metadata_do_not_gain_data(self):
        for fault in ('motion', 'feature_off', 'candidate', 'prefix', 'unstable', 'stale'):
            with self.subTest(fault=fault):
                self.setUp(); self.admitted(enabled=fault!='feature_off', old_target=fault=='candidate')
                latest = self.latest()
                if fault == 'motion': latest.signature = bytes([80])*len(latest.signature)
                self.observe(latest, prefix=self.h.prefix+1 if fault=='prefix' else None,
                    stable=0 if fault=='unstable' else 1,
                    age=150_000_001 if fault=='stale' else 2)
                self.no_new_data_or_progress()

    def test_original_parent_and_actual_commit_are_not_extended(self):
        for where in ('equal', 'after', 'commit_only_after'):
            with self.subTest(boundary=where):
                self.setUp(); self.admitted(); latest = self.latest()
                parent = self.root.continuation_deadline_ns
                self.h.now = parent+(where!='equal')
                if where == 'commit_only_after':
                    scene = self.h.scene(2, 2, latest, beat=True)
                    self.h.observe_actual(scene, start=parent-20_000_000,
                        end=parent-1, commit=parent+1)
                else:
                    self.h.observe_actual(self.h.scene(2, 2, latest, beat=True))
                self.no_new_data_or_progress()
                self.assertLessEqual(self.q.cycle().continuation_deadline_ns, parent)

    def test_legacy_published_framing_move_started_or_ack_never_becomes_new_data(self):
        for state in ('reserved', 'started', 'ack'):
            with self.subTest(input=state):
                self.setUp(); self.admitted(enabled=False)
                # Legacy framing can publish a MOVE. In the yield profile a
                # data-qualified next frame already selects existing mode2;
                # do not inject an unreachable published-framing state.
                command = None
                for _ in range(120):
                    self.observe(self.source, advance=20_000_000)
                    ready, candidate = self.h.tick()
                    if ready:
                        self.assertEqual(4, candidate.kind)
                        command = candidate
                        break
                    self.assertFalse(self.h.status().terminal)
                self.assertIsNotNone(command, 'normal independent static frames must earn the published framing MOVE')
                self.assertEqual((4, 1), (command.kind, self.h.status().input_state))
                if state != 'reserved':
                    self.h.now = max(self.h.now, command.not_before_ns)
                    self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine,
                        command.id, self.h.now, 1, 0, 1))
                if state == 'ack':
                    self.h.now += 50_000_000
                    self.assertEqual(1, self.lib.ng2_controller_complete(self.h.engine,
                        command.id, self.h.now, 1)); self.h.prefix = command.id
                self.saved_counts = self.counts()
                self.observe(self.latest())
                self.no_new_data_or_progress()
                self.assertEqual(bytes(command), bytes(next(e for e in self.h.events()
                    if e.command.id == command.id).command))
