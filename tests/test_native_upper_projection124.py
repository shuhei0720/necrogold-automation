"""V2's actual H1 keeps newly observed potential products protected.

Public fit/unit/opening/admission/H1/worker callbacks earn the ownership.
Scenes and typed safe worker results are declared control components. The
raw two-SHOP Perception attribution is a separate private original-image cut;
these later responses do not reconstruct missing phone frames or history.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from tests import test_native_controller as native
from tests import test_native_upper_snapshot118 as snapshot
from tests.test_native_ring094 import Result

READ_ONLY_SUFFIX = r'''
int ng2_upper_projection124_earned(const NG2Controller*p,uint64_t*out,size_t count){
 if(!p||!out||count<16)return 0;
 out[0]=(uint64_t)p->upper.active;out[1]=(uint64_t)p->upper.valid;
 out[2]=(uint64_t)p->upper.stage;out[3]=(uint64_t)p->upper.variant;
 out[4]=(uint64_t)p->upper.inputs;out[5]=(uint64_t)p->upper.horizontal;
 out[6]=(uint64_t)p->upper.down;out[7]=(uint64_t)p->upper.steps;
 out[8]=p->upper.parent;out[9]=p->upper.hold;out[10]=p->upper.sync;
 out[11]=p->upper.opening;out[12]=p->cycle.job_id;
 out[13]=p->cycle.capture_id;out[14]=p->cycle.prefix;
 out[15]=(uint64_t)p->cycle_retry_used;return 16;
}
int ng2_upper_projection124_token(const NG2Controller*p,uint64_t*out,size_t count){
 if(!p||!out||count<10)return 0;
 memset(out,0,10*sizeof(*out));
#ifdef NG2_TEST_UPPER_PROJECTION124_PRESENT
 out[0]=(uint64_t)p->upper_projection124.used;out[1]=(uint64_t)p->upper_projection124.armed;
 out[2]=(uint64_t)p->upper_projection124.active;out[3]=(uint64_t)p->upper_projection124.invalid;
 out[4]=p->upper_projection124.parent;out[5]=p->upper_projection124.job;
 out[6]=p->upper_projection124.capture;out[7]=p->upper_projection124.prefix;
 out[8]=(uint64_t)p->upper_projection124.inputs;out[9]=(uint64_t)p->upper_projection124.moves;
#endif
 return 10;
}
size_t ng2_upper_projection124_world(const NG2Controller*p,void*out,size_t size){
 if(!p)return 0;
 if(out&&size==sizeof(p->upper.world))memcpy(out,&p->upper.world,size);
 return sizeof(p->upper.world);
}
'''


class NativeUpperProjection124Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='upper-projection124-')
        cls.addClassCleanup(cls.temp.cleanup)
        core = Path(os.environ.get('NECRO124_UPPER_PROJECTION_CORE', str(native.CORE)))
        stage = Path(cls.temp.name)/'core'; stage.mkdir()
        for p in core.iterdir():
            if p.suffix in ('.c', '.h'): shutil.copyfile(p, stage/p.name)
        p = stage/'NG2Controller.c'
        data = p.read_bytes()
        prefix = b'\n#define NG2_TEST_UPPER_PROJECTION124_PRESENT 1\n' if b'upper_projection_arm124' in data else b'\n'
        p.write_bytes(data+prefix+READ_ONLY_SUFFIX.encode())
        previous = os.environ.get('NECRO118_BEGIN_CORE')
        os.environ['NECRO118_BEGIN_CORE'] = str(stage)
        try:
            snapshot.NativeUpperSnapshot118Tests.setUpClass()
        finally:
            if previous is None: os.environ.pop('NECRO118_BEGIN_CORE', None)
            else: os.environ['NECRO118_BEGIN_CORE'] = previous
        cls.lib = snapshot.NativeUpperSnapshot118Tests.lib
        cls.lib.ng2_upper_projection124_earned.argtypes = [C.c_void_p, C.POINTER(C.c_uint64), C.c_size_t]
        cls.lib.ng2_upper_projection124_token.argtypes = [C.c_void_p, C.POINTER(C.c_uint64), C.c_size_t]
        cls.lib.ng2_upper_projection124_world.argtypes = [C.c_void_p, C.c_void_p, C.c_size_t]
        cls.lib.ng2_upper_projection124_world.restype = C.c_size_t

    @classmethod
    def tearDownClass(cls):
        snapshot.NativeUpperSnapshot118Tests.tearDownClass()

    def setUp(self):
        self.p = snapshot.NativeUpperSnapshot118Tests(methodName='runTest')
        self.p.lib = self.lib; self.p.setup_case()
        self.addCleanup(self.p.doCleanups)
        self.t, self.h = self.p.t, self.p.h

    def earned(self):
        out = (C.c_uint64*16)()
        self.assertEqual(16, self.lib.ng2_upper_projection124_earned(self.h.engine, out, 16))
        return tuple(out)

    def token(self):
        out = (C.c_uint64*10)()
        self.assertEqual(10, self.lib.ng2_upper_projection124_token(self.h.engine, out, 10))
        return tuple(out)

    def world(self):
        out = C.create_string_buffer(C.sizeof(native.Scene))
        self.assertEqual(len(out), self.lib.ng2_upper_projection124_world(self.h.engine, out, len(out)))
        return out.raw

    def safe_current(self, source, hint=0):
        state = self.t.q.cycle(); h = self.h
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(h.engine,
            state.job_id, state.capture_id, state.prefix, h.now))
        value = Result(abi=1, size=C.sizeof(Result), status=0, outcome=0, coverage=1,
            reason=1, selected_row=-1, selected_partial=0, partial_count=1,
            partial_safe_no_positive=int(source.goods == 'partial' and not hint), started_ns=h.now+1)
        slot = value.partial[0]
        x, y = max((p for p, kind in source.tiles.items() if kind == 'item'), key=lambda point: abs(point[0]))
        slot.cx, slot.sy = 448+36*x, 207+36*y-48
        slot.outcome = value.outcome = hint
        slot.icon_score = slot.icon_upper_bound = .683055648
        slot.icon_box[:] = (slot.cx-16, slot.sy+24, 32, 28)
        h.now += self.t.WORKER; value.finished_ns = h.now
        h.now += self.t.CALLBACK
        self.assertEqual(1, self.lib.ng2_controller_cycle_assess(h.engine,
            state.job_id, state.capture_id, state.prefix, h.now, C.byref(value)))
        return value

    def actual_H1_new_projection(self, direction=1, extra=True):
        d = native.DIRS[direction][0]
        source, _base = self.t.pending(direction)
        first = self.earned(); original_world = self.world()
        self.assertEqual((1, 1, 1, 2, 0, 0, 0, 5), first[:8],
            'ordinary V2 admission must precede the first horizontal input')
        self.parent = self.t.q.cycle().continuation_deadline_ns
        command = self.t.ticket(source)
        self.assertEqual(direction, command.direction)
        self.t.ack(command, source)
        latest = native.translated(source, direction)
        latest.tiles[(d, 0)] = 'floor'
        # The new normal projection is not reduced to old five or stock3.
        # These two potential origins produce the full exact seven-cell halo.
        if extra:
            latest.tiles[(d, 4)] = latest.tiles[(0, 4)] = 'item'
        items = {p for p, kind in latest.tiles.items() if kind == 'item'}
        latest.protected = self.t.cross(items)
        self.assertEqual({(d*x, 4) for x in range(2, 7)} if not extra
            else {(d*x, 4) for x in range(7)}, items)
        self.h.observe_actual(self.h.scene(2, 2, latest, beat=True))
        event = self.h.events()[-1]
        self.assertEqual((2, 1, d, 0), (event.outcome, event.motion, event.dx, event.dy),
            'only the actual H1 normal unit may carry this new DATA ownership')
        self.assertEqual((3, 2, 1), (self.h.status().inputs, self.h.status().moves, self.h.status().door_changes))
        self.assertEqual((1, 1, 0, 5), self.earned()[4:8])
        self.assertEqual(original_world, self.world(), 'the original five-cell world remains immutable')
        state = self.t.q.cycle()
        self.assertEqual((1, 1, command.id), (state.pending, state.partial, state.prefix))
        self.assertEqual(event.observed_capture_id, state.capture_id)
        self.assertEqual(self.parent, state.continuation_deadline_ns)
        return latest, original_world, command

    def test_actual_V2_H1_seven_potential_cells_wait_for_safe_current_without_losing_parent(self):
        latest, world, command = self.actual_H1_new_projection()
        before = self.earned(); counts = self.h.status().inputs, self.h.status().moves
        result = self.safe_current(latest)
        state = self.t.q.cycle()
        self.assertEqual((0, 1, 1), (result.outcome, result.coverage, result.partial_safe_no_positive))
        self.assertEqual((3, 0, 0), (state.state, state.pending, state.candidate_latched),
            'normal safe H1 current7 needs independent observation, not HELD for the new protected potential cells')
        self.assertEqual(world, self.world())
        self.assertEqual((1, 1, 0, 5), self.earned()[4:8])
        self.assertEqual(before[8:12], self.earned()[8:12])
        self.assertEqual(self.parent, state.continuation_deadline_ns)
        self.assertEqual(counts, (self.h.status().inputs, self.h.status().moves))
        self.assertEqual(0, self.h.status().input_state, 'normal data alone cannot issue a new MOVE')
        self.assertEqual(command.id, self.h.status().last_completed_id)

    def test_mirrored_H1_uses_the_same_bounded_potential_and_safe_worker_path(self):
        latest, world, _command = self.actual_H1_new_projection(2)
        self.assertEqual((1, 1, 0, 0), self.token()[:4])
        self.safe_current(latest)
        self.assertEqual((3, 0), (self.t.q.cycle().state, self.h.status().input_state))
        self.assertEqual((1, 0, 1, 0), self.token()[:4])
        self.assertEqual(world, self.world())

    def test_independent_current_then_each_unit_rechecks_floor_and_resolves_to_FULL(self):
        latest, world, _command = self.actual_H1_new_projection()
        self.safe_current(latest)
        self.assertEqual((1, 0, 1, 0), self.token()[:4])
        self.assertEqual(0, self.h.status().input_state)
        directions = (1, 4, 4, 4)
        for index, direction in enumerate(directions):
            command = self.t.ticket(latest)
            self.assertEqual(direction, command.direction)
            prior_moves = self.h.status().moves
            self.t.ack(command, latest)
            self.assertEqual(prior_moves, self.h.status().moves, 'ACK alone never adds a unit')
            latest = native.translated(latest, direction)
            if index == 2:
                # A separate declared FULL observation resolves the potential
                # union to the actual three origins. Never erase a normal
                # seven-ITEM mask merely to make the last destination safe.
                actual = {(-3, 2), (-2, 2), (-1, 2)}
                for point, kind in list(latest.tiles.items()):
                    if kind == 'item' and point not in actual: latest.tiles[point] = 'dirt'
                latest.goods = 'visible'
            if index < 3: latest.tiles[native.DIRS[directions[index+1]]] = 'floor'
            latest.protected = self.t.cross({p for p, k in latest.tiles.items() if k == 'item'})
            self.h.observe_actual(self.h.scene(2, 2, latest, beat=True))
            event = self.h.events()[-1]
            self.assertEqual((1, *native.DIRS[direction]), (event.motion, event.dx, event.dy))
            self.assertEqual(prior_moves+1, self.h.status().moves)
            self.safe_current(latest)
            self.assertEqual(self.parent, self.t.q.cycle().continuation_deadline_ns)
            self.assertEqual(world, self.world())
        self.assertEqual((5, 2, 3, 5), self.earned()[4:8])
        self.assertEqual((7, 6), (self.h.status().inputs, self.h.status().moves))
        self.assertEqual((1, 0, 1, 0), self.token()[:4])
        self.assertEqual('visible', latest.goods)
        self.assertEqual({(-3, 1), (-2, 1), (-1, 1)},
            {p for p, kind in latest.tiles.items() if kind == 'item'})
        self.assertEqual(self.t.cross({(-3, 1), (-2, 1), (-1, 1)}), latest.protected)
        self.assertLess(self.h.now, self.parent,
            'the declared FULL3 endpoint must be reached inside the frozen original parent')

    def test_unresolved_seven_cell_halo_never_grants_the_last_DOWN(self):
        latest, world, _command = self.actual_H1_new_projection()
        self.safe_current(latest)
        for direction, upcoming in ((1, 4), (4, 4), (4, 4)):
            command = self.t.ticket(latest); self.assertEqual(direction, command.direction)
            self.t.ack(command, latest); latest = native.translated(latest, direction)
            latest.tiles[native.DIRS[upcoming]] = 'floor'
            latest.protected = self.t.cross({p for p, k in latest.tiles.items() if k == 'item'})
            self.h.observe_actual(self.h.scene(2, 2, latest, beat=True)); self.safe_current(latest)
        self.assertIn((0, 1), latest.protected, 'the unresolved potential still protects D3')
        count = self.h.status().inputs, self.h.status().moves
        for _ in range(3):
            self.t.frame(latest); self.assertNotEqual(4, self.h.tick()[1].kind)
        self.assertEqual(count, (self.h.status().inputs, self.h.status().moves))
        self.assertEqual(world, self.world())

    def test_hard_pending_world_failure_is_sticky_and_safe_result_cannot_restore_it(self):
        for fault in ('old_gold', 'new_item', 'extra_protection', 'origin'):
            with self.subTest(fault=fault):
                self.setUp()
                latest, world, _command = self.actual_H1_new_projection()
                changed = deepcopy(latest)
                if fault == 'old_gold': changed.tiles[(-4, -1)] = 'dirt'
                elif fault == 'new_item':
                    changed.tiles[(5, 3)] = 'item'
                    changed.protected = self.t.cross({p for p, k in changed.tiles.items() if k == 'item'})
                elif fault == 'extra_protection': changed.protected.add((5, 3))
                elif fault == 'origin': changed.tiles[(0, 0)] = 'dirt'
                self.t.frame(changed, 2)
                self.assertEqual((1, 1, 0, 1), self.token()[:4])
                self.t.frame(latest, 2)
                self.safe_current(latest)
                self.assertEqual(7, self.t.q.cycle().state)
                self.assertEqual((1, 0, 0, 1), self.token()[:4])
                self.assertNotEqual(4, self.h.tick()[1].kind)
                self.assertEqual(world, self.world())

    def test_changed_next_surface_can_wait_but_never_supplies_a_MOVE(self):
        latest, world, _command = self.actual_H1_new_projection()
        changed = deepcopy(latest); changed.tiles[(-1, 0)] = 'dirt'
        self.t.frame(changed, 2)
        # The old world rule may wait for a restricted next surface. This
        # is distinct from an invalid original wall/item/protection proof.
        self.assertEqual((1, 1, 0, 0), self.token()[:4])
        self.safe_current(latest)
        count = self.h.status().inputs, self.h.status().moves
        for _ in range(3):
            self.t.frame(changed); self.assertNotEqual(4, self.h.tick()[1].kind)
        self.assertEqual(count, (self.h.status().inputs, self.h.status().moves))
        self.assertEqual(self.parent, self.t.q.cycle().continuation_deadline_ns)
        self.assertEqual(world, self.world())

    def test_target_and_candidate_preempt_pending_projection_before_any_future_MOVE(self):
        for hint in (1, 2):
            with self.subTest(hint=hint):
                self.setUp()
                latest, world, _command = self.actual_H1_new_projection()
                self.safe_current(latest, hint)
                state = self.t.q.cycle()
                self.assertEqual((hint, 1, 7), (state.outcome, state.candidate_latched, state.state))
                self.assertEqual((3, 2), (self.h.status().inputs, self.h.status().moves))
                self.assertNotEqual(4, self.h.tick()[1].kind)
                self.assertEqual(world, self.world())

    def test_unchanged_five_cell_world_uses_only_legacy_V2_without_a_token(self):
        latest, world, _command = self.actual_H1_new_projection(extra=False)
        self.assertEqual((0, 0, 0, 0), self.token()[:4])
        self.safe_current(latest)
        self.assertEqual(3, self.t.q.cycle().state)
        self.assertEqual(world, self.world())

    def test_bad_prefix_and_unstable_current_cannot_replace_the_pending_DATA_source(self):
        for fault in ('prefix', 'unstable'):
            with self.subTest(fault=fault):
                self.setUp()
                latest, world, _command = self.actual_H1_new_projection()
                before = self.token(), self.earned(), self.t.q.cycle().capture_id
                self.h.now += 2
                self.assertEqual(0, self.h.observe_actual(self.h.scene(2, 2, latest, beat=True),
                    prefix=self.h.prefix+int(fault == 'prefix'), stable=int(fault != 'unstable')))
                self.assertEqual(before, (self.token(), self.earned(), self.t.q.cycle().capture_id))
                self.safe_current(latest)
                self.assertEqual((1, 0, 1, 0), self.token()[:4])
                self.assertEqual(world, self.world())

    def test_started_and_unknown_H1_cannot_arm_potential_or_resend(self):
        for unknown in (False, True):
            with self.subTest(unknown=unknown):
                self.setUp()
                source, _base = self.t.pending(); command = self.t.ticket(source)
                while self.h.now < command.not_before_ns:
                    self.t.frame(source, min(20_000_000, command.not_before_ns-self.h.now))
                self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine, command.id, self.h.now, 1, 0, 1))
                if unknown:
                    self.h.now += self.t.SYNTH
                    self.assertEqual(1, self.lib.ng2_controller_complete(self.h.engine, command.id, self.h.now, -1))
                latest = native.translated(source, 1)
                latest.tiles[(-1, 4)] = latest.tiles[(0, 4)] = 'item'
                latest.protected = self.t.cross({p for p, k in latest.tiles.items() if k == 'item'})
                count = len(self.h.events()); self.t.frame(latest)
                self.assertEqual((0, 0, 0, 0), self.token()[:4])
                self.assertEqual(1, self.h.status().moves)
                self.assertEqual(count, len(self.h.events()))
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, command.id, self.h.now, 1, 0, 1))
                self.assertNotEqual(4, self.h.tick()[1].kind)

    def test_parent_checks_actual_current_commit_and_never_extends_the_cap(self):
        for late in (0, 1):
            with self.subTest(late=late):
                self.setUp()
                latest, world, _command = self.actual_H1_new_projection(); self.safe_current(latest)
                counts = self.h.status().inputs, self.h.status().moves
                start, end = self.parent-10_000_000, self.parent
                self.h.now = self.parent+late
                scene = self.h.scene(2, 2, latest, beat=True)
                scene.beat_remaining = ((5*native.SECOND-(start+end)//2)%native.PERIOD)/native.PERIOD
                self.assertEqual(1, self.h.observe_actual(scene, start=start, end=end, commit=self.h.now))
                state = self.t.q.cycle()
                self.assertEqual(self.parent, state.continuation_deadline_ns)
                self.assertEqual(2 if late else 0, state.status,
                    'capture_end at P cannot hide actualcommit P+1')
                self.assertEqual(counts, (self.h.status().inputs, self.h.status().moves))
                self.assertNotEqual(4, self.h.tick()[1].kind)
                self.assertEqual(world, self.world())

    def test_new_potential_keeps_the_original_postunit_crossing_snapshot_bounds(self):
        for fault in (None, 'before_worker', 'before_result_end', 'prefix', 'expired'):
            with self.subTest(fault=fault):
                self.setUp()
                latest, world, _command = self.actual_H1_new_projection()
                source = self.t.q.cycle()
                _job, result = self.p.classify(latest, source.capture_start_ns)
                self.assertEqual((0, 1), (result.outcome, result.partial_safe_no_positive))
                self.assertEqual((1, 0, 1, 0), self.token()[:4])
                release = self.h.now
                crossing_start = source.capture_start_ns+75_729_792
                self.assertLess(crossing_start, release,
                    'this declared frame starts before adoption; only the old V2 exception may qualify it')
                counts = self.h.status().inputs, self.h.status().moves
                self.lib.ng2_begin118_count_reset()
                self.p.crossing(latest, source.capture_start_ns, fault)
                if fault is None:
                    self.assertEqual(4, self.h.status().phase)
                    self.assertGreater(self.lib.ng2_begin118_count(), 0,
                        'new DATA ownership still requires a direct normal zero')
                else:
                    self.assertNotEqual(4, self.h.status().phase)
                    self.assertNotEqual(4, self.h.tick()[1].kind)
                self.assertEqual(counts, (self.h.status().inputs, self.h.status().moves))
                self.assertEqual(self.parent, self.t.q.cycle().continuation_deadline_ns)
                self.assertEqual(world, self.world())


if __name__ == '__main__':
    unittest.main()
