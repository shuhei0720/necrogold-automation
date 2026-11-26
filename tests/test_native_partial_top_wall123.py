"""A clipped top projection and one observed GOLD rail hole get DATA only.

Public lifecycle earns every owner, ACK, result and budget. Scenes and later
responses are procedural component inputs, not missing 636e phone frames.
The C suffix reads earned state; it never writes private flags or counters.
"""
import ctypes as C
from copy import deepcopy
import os
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from tests import test_native_controller as native
from tests import test_native_partial_refresh104 as refresh
from tests import test_native_irregular110 as irregular
from tests.test_native_ring094 import Result


READ_ONLY_SUFFIX = r'''
int ng2_topwall123_earned(const NG2Controller *p,uint64_t *out,size_t count){
 if(!p||!out||count<12)return 0;
 out[0]=(uint64_t)p->cycle_retry_used;out[1]=(uint64_t)p->cycle_partial_rebind_used;
 out[2]=p->cycle.hold_started_ns;out[3]=p->cycle_sync_deadline;
 out[4]=(uint64_t)p->cycle_partial_credit;out[5]=(uint64_t)p->cycle_framing_credit;
 out[6]=(uint64_t)p->cycle_current_active;out[7]=(uint64_t)p->cycle_current_used;
 out[8]=(uint64_t)p->sample_count;out[9]=p->model.period_ns;
 out[10]=p->recovery_slot_target;out[11]=p->preparation_epoch;
 return 12;
}
size_t ng2_topwall123_samples(const NG2Controller*p,void*out,size_t size){
 if(!p)return 0;
 if(out&&size==sizeof(p->samples))memcpy(out,p->samples,size);
 return sizeof(p->samples);
}
'''


class NativePartialTopWall123Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Procedural dictionaries may name the ABI's explicit UNKNOWN=0.
        # Restore the shared parser table when this component class finishes.
        cls.prior_unknown = native.KINDS.get('unknown')
        native.KINDS['unknown'] = 0
        cls.temp = tempfile.TemporaryDirectory(prefix='partial-top-wall123-')
        cls.addClassCleanup(cls.temp.cleanup)
        source = Path(os.environ.get('NECRO123_TOP_WALL_CORE', str(native.CORE)))
        staged = Path(cls.temp.name)/'core'
        staged.mkdir()
        for file in source.iterdir():
            if file.suffix in ('.c', '.h'):
                shutil.copyfile(file, staged/file.name)
        controller = staged/'NG2Controller.c'
        controller.write_bytes(controller.read_bytes()+READ_ONLY_SUFFIX.encode())
        previous = native.CORE
        try:
            native.CORE = staged
            refresh.NativePartialRefresh104Tests.setUpClass()
        finally:
            native.CORE = previous
        cls.lib = refresh.NativePartialRefresh104Tests.lib
        cls.lib.ng2_controller_enable_irregular.argtypes = [C.c_void_p]
        cls.lib.ng2_controller_enable_restart_yield.argtypes = [C.c_void_p]
        cls.lib.ng2_controller_observe_irregular_at.argtypes = [C.c_void_p,
            C.POINTER(native.Scene), C.POINTER(irregular.Observation),
            *([C.c_uint64]*4), C.c_int32, C.c_uint64]
        cls.lib.ng2_controller_observe_at.argtypes = [*cls.lib.ng2_controller_observe.argtypes, C.c_uint64]
        cls.lib.ng2_topwall123_earned.argtypes = [C.c_void_p, C.POINTER(C.c_uint64), C.c_size_t]
        cls.lib.ng2_topwall123_samples.argtypes = [C.c_void_p, C.c_void_p, C.c_size_t]
        cls.lib.ng2_topwall123_samples.restype = C.c_size_t

    @classmethod
    def tearDownClass(cls):
        refresh.NativePartialRefresh104Tests.tearDownClass()
        if cls.prior_unknown is None:
            native.KINDS.pop('unknown', None)
        else:
            native.KINDS['unknown'] = cls.prior_unknown

    def setUp(self):
        self.fresh()

    def fresh(self, enabled=True):
        self.p = refresh.NativePartialRefresh104Tests(methodName='runTest')
        self.p.setUp()
        self.addCleanup(self.p.doCleanups)
        self.h, self.q = self.p.h, self.p.q
        self.assertEqual(1, self.lib.ng2_controller_enable_irregular(self.h.engine))
        if enabled:
            self.assertEqual(1, self.lib.ng2_controller_enable_restart_yield(self.h.engine))
        self.companion = irregular.NativeIrregular110Tests(methodName='runTest')
        self.companion.lib, self.companion.h, self.companion.has_irregular = self.lib, self.h, True
        self.h.observe = lambda scene, **kwargs: self.companion.observe(scene, irregular.none(), **kwargs)
        self.assertEqual(1, self.h.observe(self.h.scene(state=1)))
        ready, resume = self.h.tick()
        self.assertEqual((1, 1), (ready, resume.kind))
        self.h.ack(resume)
        self.h.now += 210_000_000

    def earned(self):
        out = (C.c_uint64*12)()
        self.assertEqual(12, self.lib.ng2_topwall123_earned(self.h.engine, out, 12))
        return tuple(out)

    def source(self, side=1, old='unknown', **options):
        xs = range(-3, 2) if side == 1 else range(-1, 4)
        items = {(x, -4) for x in xs}
        protected = set().union(*(self.p.cross(point) for point in items))
        cells = {point: 'item' for point in items}
        for x, kind in zip(xs, ('unknown', 'floor', 'dirt', 'unknown', 'gold')):
            cells[(x, -5)] = kind
        cells.update({(side, -3): 'gold', (side, -2): old, (0, -2): 'floor'})
        source, opened = self.p.p.pending(direction=3, side=side, initial=old,
            extra=cells, protected=protected, **options)
        self.assertEqual((3, 5, 0, -1, 1), self.p.choice(source))
        self.assertEqual((3, 0, 0), (self.q.cycle().state,
            self.h.status().input_state, self.h.status().current_command_id))
        self.assertEqual((3, 0, 0), (self.h.events()[-1].motion,
            self.h.events()[-1].dx, self.h.events()[-1].dy))
        return source, opened

    def grown(self, source, side=1):
        latest = deepcopy(source)
        for (x, y), kind in source.tiles.items():
            if y == -4 and kind == 'item':
                latest.tiles[(x, -5)] = 'item'
                latest.protected.update((xx, yy) for xx, yy in self.p.cross((x, -5)) if -5 <= yy <= 4)
        latest.tiles[(side, -2)] = 'gold'
        latest.gold = {point for point, kind in latest.tiles.items() if kind == 'gold'}
        return latest

    def frame(self, terrain, *, start=None, end=None, commit=None, prefix=None,
              stable=1, number=None, beat=True):
        # Original current121 has age31.380875ms at actual commit. Its start
        # is after the old result release; pre-release120 is a negative case.
        start = self.h.now+10_000_000 if start is None else start
        end = start+9_373_833 if end is None else end
        commit = start+31_380_875 if commit is None else commit
        self.h.now = (start+end)//2+1
        scene = self.h.scene(2, 2, terrain, beat=beat)
        self.h.now = commit
        return self.companion.observe(scene, irregular.none(), number=number,
            start=start, end=end, prefix=self.h.prefix if prefix is None else prefix,
            stable=stable, commit=commit)

    def admitted(self, side=1):
        source, opened = self.source(side)
        latest = self.grown(source, side)
        old, counts, earned = self.q.cycle(), self.p.counts(), self.earned()
        self.assertEqual((2, 0, 0), self.p.motion(source, latest, 3))
        self.assertEqual(self.p.choice(source), self.p.choice(latest))
        self.assertEqual(1, self.frame(latest))
        fresh = self.q.cycle()
        self.assertEqual((old.job_id+1, 1, 1, 1, 0),
            (fresh.job_id, fresh.pending, fresh.state, fresh.partial, fresh.full_seen),
            'supported top projection plus observed rail closure must bind a new normal PARTIAL job')
        self.assertEqual((self.h.number, old.prefix), (fresh.capture_id, fresh.prefix))
        self.assertEqual((0, 0), (fresh.worker_started_ns, fresh.assessment_ns))
        self.assertEqual((earned[0]+1, 1, earned[2], earned[3], 0, 0, 0, earned[7]), self.earned()[:8])
        self.assertEqual(old.hold_started_ns, fresh.hold_started_ns)
        self.assertLessEqual(fresh.continuation_deadline_ns, old.continuation_deadline_ns)
        self.assertEqual(min(fresh.capture_start_ns+150_000_000,
            fresh.continuation_deadline_ns), fresh.deadline_ns)
        self.assertEqual(counts, self.p.counts())
        self.p.no_move()
        return source, latest, old, fresh, opened

    def samples(self):
        size = self.lib.ng2_topwall123_samples(self.h.engine, None, 0)
        out = C.create_string_buffer(size)
        self.assertEqual(size, self.lib.ng2_topwall123_samples(self.h.engine, out, size))
        return out.raw

    def test_immutable_hud_history_is_retained_but_old_model_slot_and_epoch_are_revoked(self):
        source, _ = self.source()
        old, before, samples = self.q.cycle(), self.earned(), self.samples()
        self.assertGreater(before[8], 0)
        self.assertGreater(before[9], 0)
        self.frame(self.grown(source))
        self.assertEqual(old.job_id+1, self.q.cycle().job_id)
        self.assertEqual(before[8], self.earned()[8], 'same-owner HUD history must survive only as samples for a new fit')
        self.assertEqual(samples, self.samples())
        self.assertEqual((0, 0, 0), self.earned()[9:12])
        self.p.no_move()

    def test_both_rails_bind_new_source_with_frozen_parent_and_no_move_credit(self):
        for side in (1, -1):
            with self.subTest(side=side):
                self.fresh()
                _source, latest, _old, fresh, opened = self.admitted(side)
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine,
                    opened.id, self.h.now, 1, 0, 1), 'known opening ACK never revives')
                before = bytes(self.q.cycle())
                self.frame(latest)
                self.assertEqual(before, bytes(self.q.cycle()), 'pending new job keeps its immutable source')
                self.assertEqual(fresh.capture_id, self.q.cycle().capture_id)

    def test_new_safe_unknown_needs_independent_current_and_fit_before_up_actual_unit(self):
        _source, latest, old, fresh, _opened = self.admitted()
        counts = self.p.counts()
        self.q.assess(0, 1, self.p.safe)
        self.assertEqual((fresh.job_id, 3, 0), (self.q.cycle().job_id,
            self.q.cycle().state, self.q.cycle().candidate_latched))
        self.p.no_move()
        self.assertEqual(1, self.frame(latest))
        # Only the independent current may add a sample to the retained
        # past HUD history and earn a new model. The old model stayed zero.
        self.assertGreater(self.h.status().beat_period_ns, 0)
        command = self.h.next_move(latest)
        self.assertEqual((4, 3), (command.kind, command.direction))
        self.assertGreater(command.source_capture_id, fresh.capture_id)
        self.assertLessEqual(command.deadline_ns, old.continuation_deadline_ns)
        self.assertEqual(counts, self.p.counts())
        self.p.actual_move(latest, command)
        self.assertEqual((counts[0]+1, counts[1]+1, counts[2], counts[3]-1), self.p.counts())
        self.assertEqual(0, self.h.status().restarts, 'procedural UP is not future phone goods or RS proof')

    def test_original_phase_budget_with_new_worker100_and_current31ms_reaches_up_unit(self):
        rows = []
        previous = native.PERIOD
        native.PERIOD = 520_308_009
        try:
            for worker_ns in (1, 100_000_000):
                with self.subTest(new_worker_budget_ns=worker_ns):
                    self.fresh()
                    source, opened = self.source()
                    old, counts = self.q.cycle(), self.p.counts()
                    # A translation maps the original UP10 target to this
                    # earned target. Its phase/period/lead remain exact. Our
                    # public context's P is 59.880231ms tighter than original
                    # P, so no extra time is granted to this component.
                    original_target = 52_274_388_808_686
                    original_current = 52_274_659_423_083
                    original_parent = 52_277_198_688_916
                    translation = opened.target_ns-original_target
                    current = original_current+translation
                    mapped_parent = original_parent+translation
                    self.assertLessEqual(old.continuation_deadline_ns, mapped_parent)
                    latest = self.grown(source)
                    self.frame(latest, start=current-31_380_875,
                        end=current-22_007_042, commit=current)
                    fresh = self.q.cycle()
                    self.assertEqual(old.job_id+1, fresh.job_id)
                    self.assertEqual(0, self.h.status().beat_period_ns)
                    self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
                        fresh.job_id, fresh.capture_id, fresh.prefix, self.h.now))
                    result = Result(abi=1, size=C.sizeof(Result), outcome=0, coverage=1,
                        selected_row=-1, selected_partial=-1, started_ns=self.h.now,
                        finished_ns=self.h.now+worker_ns)
                    self.p.safe(result)
                    self.h.now += worker_ns
                    self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine,
                        fresh.job_id, fresh.capture_id, fresh.prefix, self.h.now, C.byref(result)))
                    self.assertEqual(0, self.h.status().beat_period_ns)
                    self.p.no_move()
                    self.frame(latest, start=self.h.now+1)
                    self.assertGreater(self.h.status().beat_period_ns, 0,
                        'independent current must refit from retained immutable HUD history')
                    command = self.h.next_move(latest)
                    self.assertEqual((4, 3, 150_000_000),
                        (command.kind, command.direction, self.h.status().lead_ns))
                    self.assertEqual(0, (command.target_ns-opened.target_ns) % native.PERIOD)
                    # Original UP10 begin offset and ACK/capture/analysis
                    # costs are declared component costs, not future phone
                    # guarantees or a replay of its missing post121 images.
                    self.h.now = command.not_before_ns+2_494_647
                    self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine,
                        command.id, self.h.now, 1, 0, 1))
                    begin = self.h.now
                    self.h.now += 276_892_125
                    self.assertEqual(1, self.lib.ng2_controller_complete(self.h.engine,
                        command.id, self.h.now, 1))
                    self.h.prefix = command.id
                    self.assertEqual(counts[1], self.h.status().moves, 'ACK is not unit credit')
                    start = self.h.now+7_563_417
                    end = start+20_756_958
                    commit = end+36_682_417
                    self.frame(native.translated(latest, 3), start=start, end=end, commit=commit)
                    event = next(e for e in self.h.events() if e.command.id == command.id)
                    self.assertEqual((1, 0, -1), (event.motion, event.dx, event.dy))
                    self.assertEqual((counts[0]+1, counts[1]+1, counts[2], counts[3]-1), self.p.counts())
                    self.assertLessEqual(commit, old.continuation_deadline_ns)
                    self.assertLessEqual(commit, mapped_parent)
                    self.assertEqual(0, self.h.status().restarts)
                    rows.append(dict(worker_ns=worker_ns, period_ns=native.PERIOD,
                        translation_ns=translation, current_commit=current,
                        actual_earned_P=old.continuation_deadline_ns, original_mapped_P=mapped_parent,
                        command_target=command.target_ns, command_NB=command.not_before_ns,
                        begin=begin, unit_commit=commit,
                        remaining_earned_P=old.continuation_deadline_ns-commit,
                        remaining_original_P=mapped_parent-commit))
        finally:
            native.PERIOD = previous
        output = os.environ.get('NECRO123_TOP_WALL_TIMING_OUTPUT')
        if output:
            Path(output).write_text(json.dumps({'scope': 'public earned component with original phase/period/lead and declared later HUD/ACK costs; not future phone replay',
                'cases': rows}, indent=2)+'\n')

    def test_retained_hud_history_cannot_replace_current_freshness_prefix_or_owner(self):
        for fault in ('no_hud', 'pre_release', 'future', 'prefix', 'parent', 'cancel', 'owner'):
            with self.subTest(fault=fault):
                self.fresh()
                _source, latest, _old, fresh, _opened = self.admitted()
                self.q.assess(0, 1, self.p.safe)
                self.assertEqual(0, self.h.status().beat_period_ns)
                options = {}
                if fault == 'no_hud': options['beat'] = False
                elif fault == 'pre_release': options['start'] = self.q.cycle().release_after_ns-1
                elif fault == 'future': options.update(start=self.h.now+20_000_000, commit=self.h.now+10_000_000)
                elif fault == 'prefix': options['prefix'] = self.h.prefix+1
                elif fault == 'parent': self.h.now = fresh.continuation_deadline_ns+1
                elif fault == 'cancel': self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 2)
                elif fault == 'owner': self.h.tick(owner=0)
                self.frame(latest, **options)
                self.p.no_move()
                self.assertEqual(0, self.h.status().restarts)
                self.assertEqual((2, 1), self.p.counts()[:2])

    def test_new_candidate_or_unproved_current_keeps_data_and_never_resends(self):
        for outcome in (0, 1, 2):
            with self.subTest(outcome=outcome):
                self.fresh()
                _source, latest, _old, fresh, _opened = self.admitted()
                counts = self.p.counts()
                self.q.assess(outcome, 1, self.p.safe if outcome == 0 else None)
                if outcome:
                    self.assertEqual((7, 1), (self.q.cycle().state, self.q.cycle().candidate_latched))
                else:
                    changed = deepcopy(latest)
                    changed.signature = bytes([80])*23296
                    self.frame(changed)
                    self.assertEqual((fresh.job_id, 3), (self.q.cycle().job_id, self.q.cycle().state))
                self.p.no_move()
                self.assertEqual(counts, self.p.counts())

    def test_original_geometry_support_and_five_cell_crosses_remain_required(self):
        faults = ('lower_item', 'mask_extra', 'mask_loss', 'outside_item', 'lost_gold',
                  'origin', 'next', 'cross', 'two_holes', 'unsupported_rail',
                  'outside_gold', 'no_projection', 'motion', 'unknown_motion',
                  'old_floor', 'old_dirt', 'old_stone', 'old_door')
        for fault in faults:
            with self.subTest(fault=fault):
                self.fresh()
                source, _ = self.source(old=fault[4:] if fault.startswith('old_') else 'unknown')
                old, counts = self.q.cycle(), self.p.counts()
                latest = self.grown(source)
                if fault == 'lower_item': latest.tiles[(-2, -4)] = 'floor'
                elif fault == 'mask_extra': latest.protected.add((9, 3))
                elif fault == 'mask_loss': latest.protected.discard((-3, -4))
                elif fault == 'outside_item': latest.tiles[(8, 3)] = 'item'
                elif fault == 'lost_gold': latest.tiles[(-1, -1)] = 'floor'
                elif fault == 'origin': latest.tiles[(0, 0)] = 'dirt'
                elif fault == 'next': latest.tiles[(0, -1)] = 'dirt'
                elif fault == 'cross': latest.tiles[(0, -2)] = 'dirt'
                elif fault == 'two_holes': latest.tiles[(-1, -2)] = 'gold'
                elif fault == 'unsupported_rail': latest.tiles[(1, -3)] = 'unknown'
                elif fault == 'outside_gold': latest.tiles[(8, 2)] = 'gold'
                elif fault == 'no_projection':
                    latest = deepcopy(source); latest.tiles[(1, -2)] = 'gold'
                elif fault == 'motion': latest.signature = native.translated(source, 3).signature
                elif fault == 'unknown_motion': latest.signature = bytes([80])*23296
                latest.gold = {point for point, kind in latest.tiles.items() if kind == 'gold'}
                self.frame(latest)
                self.assertEqual(old.job_id, self.q.cycle().job_id)
                self.p.no_move()
                self.assertEqual(counts, self.p.counts())

    def test_current_metadata_release_source_age_and_owner_are_not_borrowed(self):
        for fault in ('prefix', 'unstable', 'id', 'pre_release', 'source_age', 'end_after_commit',
                      'cancel', 'foreground', 'locked', 'owner', 'disabled'):
            with self.subTest(fault=fault):
                self.fresh(enabled=fault != 'disabled')
                source, _ = self.source()
                old, counts = self.q.cycle(), self.p.counts()
                latest = self.grown(source)
                options = {}
                if fault == 'prefix': options['prefix'] = self.h.prefix+1
                elif fault == 'unstable': options['stable'] = 0
                elif fault == 'id': options['number'] = old.capture_id
                elif fault == 'pre_release': options['start'] = old.release_after_ns-1
                elif fault == 'source_age': options.update(start=self.h.now+1, commit=self.h.now+150_000_002)
                elif fault == 'end_after_commit': options.update(start=self.h.now+1, end=self.h.now+40_000_000)
                elif fault == 'cancel': self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 2)
                elif fault in ('foreground', 'locked', 'owner'):
                    self.h.tick(front=int(fault != 'foreground'), locked=int(fault == 'locked'), owner=int(fault != 'owner'))
                self.frame(latest, **options)
                self.assertEqual(old.job_id, self.q.cycle().job_id)
                self.p.no_move()
                self.assertEqual(counts, self.p.counts())

    def test_actual_commit_parent_before_equal_after_is_independent_of_capture_analysis(self):
        for delta in (-1, 0, 1):
            with self.subTest(actual_commit_minus_original_P=delta):
                self.fresh()
                source, _ = self.source()
                old = self.q.cycle()
                commit = old.continuation_deadline_ns+delta
                start = commit-31_380_875
                self.frame(self.grown(source), start=start, end=start+9_373_833, commit=commit)
                self.assertEqual(old.job_id+int(delta <= 0), self.q.cycle().job_id)
                if delta <= 0:
                    self.assertEqual((1, 1), (self.q.cycle().pending, self.q.cycle().state))
                    self.assertLessEqual(self.q.cycle().deadline_ns, old.continuation_deadline_ns)
                else:
                    self.p.no_move()

    def test_second_projection_job_cannot_rearm_one_use_or_refund_shared_data(self):
        _source, latest, old, fresh, _opened = self.admitted()
        self.q.assess(0, 1, self.p.safe)
        once = self.earned()
        changed = deepcopy(latest)
        changed.tiles[(-1, -5)] = 'unknown'
        self.frame(changed)
        self.assertEqual(fresh.job_id, self.q.cycle().job_id)
        self.assertEqual((once[0], once[1]), self.earned()[:2])
        self.assertEqual((1, 1), self.earned()[:2])
        self.assertLessEqual(self.q.cycle().continuation_deadline_ns, old.continuation_deadline_ns)
        self.p.no_move()

    def test_existing_credit_and_reserved_move_are_never_rescued_by_new_data(self):
        for stage in ('credit', 'reserved', 'begun', 'ack', 'unknown'):
            with self.subTest(stage=stage):
                self.fresh()
                source, _ = self.source()
                self.p.p.observe(source)
                command = None
                if stage != 'credit':
                    command = self.h.next_move(source)
                    if stage in ('begun', 'ack', 'unknown'):
                        self.h.now = max(self.h.now, command.not_before_ns)
                        self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine,
                            command.id, self.h.now, 1, 0, 1))
                        if stage in ('ack', 'unknown'):
                            self.h.now += 1
                            self.lib.ng2_controller_complete(self.h.engine, command.id, self.h.now,
                                1 if stage == 'ack' else -1)
                            self.h.prefix = command.id
                old, counts = self.q.cycle(), self.p.counts()
                self.frame(self.grown(source))
                if stage == 'ack':
                    # Existing goods-first latch may create its ordinary job
                    # for a known ACK; it must not spend this new DATA path.
                    self.assertEqual((0, 0), self.earned()[:2])
                    event = next(e for e in self.h.events() if e.command.id == command.id)
                    self.assertEqual((2, 0, 0, 0), (event.outcome, event.motion, event.dx, event.dy))
                else:
                    self.assertEqual(old.job_id, self.q.cycle().job_id)
                self.assertEqual(counts, self.p.counts())
                self.assertEqual(0, self.h.status().restarts)


if __name__ == '__main__':
    unittest.main()
