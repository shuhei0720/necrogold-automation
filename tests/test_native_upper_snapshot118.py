"""Post-unit V2 snapshot qualification with CI258's relative capture clocks.

Public C lifecycle, real Motion and Beat; returned safe results and sparse
future responses are declared procedural inputs. The recorded intervals do
not reconstruct the missing actualMac rolling model or iPhone state.
"""
import ctypes as C
from copy import deepcopy
import unittest

from tests import test_native_controller as native
from tests import test_native_irregular110 as irregular
from tests import test_native_upper_begin118 as counted
from tests import test_native_upper118 as upper
from tests.test_native_ring094 import Result


class NativeUpperSnapshot118Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        counted.NativeUpperBegin118Tests.setUpClass()
        cls.lib = counted.NativeUpperBegin118Tests.lib
        cls.lib.ng2_controller_enable_irregular.argtypes = [C.c_void_p]
        cls.lib.ng2_controller_enable_restart_yield.argtypes = [C.c_void_p]
        cls.lib.ng2_controller_observe_irregular_at.argtypes = [C.c_void_p,
            C.POINTER(native.Scene), C.POINTER(irregular.Observation), *([C.c_uint64]*4), C.c_int32, C.c_uint64]

    @classmethod
    def tearDownClass(cls):
        counted.NativeUpperBegin118Tests.tearDownClass()

    def setUp(self):
        self.setup_case()

    def setup_case(self, enabled=True):
        self.t = upper.NativeUpper118Tests(methodName='runTest')
        self.t.lib = self.lib
        self.t.setUp()
        self.addCleanup(self.t.doCleanups)
        self.h = self.t.h
        if enabled:
            self.assertEqual(1, self.lib.ng2_controller_enable_irregular(self.h.engine))
            self.assertEqual(1, self.lib.ng2_controller_enable_restart_yield(self.h.engine))
            companion = irregular.NativeIrregular110Tests(methodName='runTest')
            companion.lib, companion.h, companion.has_irregular = self.lib, self.h, True
            self.h.observe = lambda scene, **kwargs: companion.observe(scene, irregular.none(), **kwargs)
            self.h.observe_actual = self.h.observe
            self.h.observe_actual(self.h.scene(state=1))
            ready,resume = self.h.tick()
            self.assertEqual((1,1),(ready,resume.kind))
            self.h.ack(resume)
            self.h.now += 210_000_000

    def image(self, source, start, end):
        scene = self.h.scene(2, 2, source, beat=True)
        scene.beat_remaining = ((5*native.SECOND-(start+end)//2) % native.PERIOD)/native.PERIOD
        return scene

    def classify(self, source, source_start, hint=0):
        state = self.t.q.cycle()
        worker, release = source_start+61_067_375, source_start+79_577_750
        self.h.now = worker
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            state.job_id, state.capture_id, state.prefix, worker))
        value = Result(abi=1, size=C.sizeof(Result), status=0, outcome=hint,
            coverage=1, reason=1, selected_row=-1, selected_partial=0, partial_count=1,
            partial_safe_no_positive=0 if hint else 1,
            started_ns=worker+2_134_542, finished_ns=release-412_167)
        x,y = max((p for p,k in source.tiles.items() if k=='item'), key=lambda p: abs(p[0]))
        slot = value.partial[0]
        slot.cx, slot.sy = 448+36*x, 203+36*y-48
        slot.icon_score = slot.icon_upper_bound = .660527062
        slot.icon_box[:] = (slot.cx-16, slot.sy+24, 32, 28)
        slot.outcome = hint
        self.h.now = release
        self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine,
            state.job_id, state.capture_id, state.prefix, release, C.byref(value)))
        return state, value

    def post_unit(self, direction=1, moved=1, hint=0):
        source, _base = self.t.pending(direction)
        parent = self.t.q.cycle().continuation_deadline_ns
        for index in range(moved):
            command = self.t.ticket(source)
            wanted = direction if index < 2 else 4
            self.assertEqual(wanted, command.direction)
            self.t.ack(command, source)
            source = native.translated(source, wanted)
            source.tiles[native.DIRS[direction if index+1 < 2 else 4]] = 'floor'
            source.protected = self.t.cross({p for p,k in source.tiles.items() if k=='item'})
            if index+1 < moved:
                self.h.observe_actual(self.h.scene(2, 2, source, beat=True))
                self.t.assess(source)
            else:
                ack = self.h.events()[-1].end_ns
                source_start = ack+9_633_667
                self.h.now = source_start+58_328_917
                self.h.observe_actual(self.image(source, source_start, source_start+39_284_917),
                    start=source_start, end=source_start+39_284_917)
                state, value = self.classify(source, source_start, hint)
        self.assertEqual(parent, self.t.q.cycle().continuation_deadline_ns)
        return source, source_start, state, value, parent

    def crossing(self, source, source_start, fault=None):
        start, end, commit = source_start+75_729_792, source_start+95_917_292, source_start+112_683_625
        if fault == 'before_source':
            start = source_start+39_284_917-1
        elif fault == 'before_worker':
            start = source_start+61_067_375-1
        elif fault == 'before_result_end':
            end = source_start+79_577_750-1
        elif fault == 'expired':
            commit = self.t.q.cycle().continuation_deadline_ns+1
        self.h.now = commit
        return self.h.observe_actual(self.image(source,start,end), start=start, end=end,
            prefix=self.h.prefix+1 if fault=='prefix' else self.h.prefix)

    def test_postunit_crossing_snapshot_qualifies_each_new_job_without_renewing_cap(self):
        for direction, moved in ((d,m) for d in (1,2) for m in (1,2,3)):
            with self.subTest(direction=direction, prior_moves=moved):
                self.setup_case()
                source, start, state, _value, parent = self.post_unit(direction,moved)
                before = (self.h.status().inputs,self.h.status().moves)
                self.lib.ng2_begin118_count_reset()
                self.assertEqual(1,self.crossing(source,start))
                self.assertEqual(4,self.h.status().phase,
                    'the nonoverlapping same-job snapshot committed after real result needs preparation')
                self.assertGreater(self.lib.ng2_begin118_count(),0,'new qualification still requires direct normal zero')
                self.assertEqual(before,(self.h.status().inputs,self.h.status().moves))
                current = self.t.q.cycle()
                self.assertEqual((state.job_id,state.capture_id,state.prefix,parent),
                    (current.job_id,current.capture_id,current.prefix,current.continuation_deadline_ns))

    def test_feature_off_and_bad_metadata_or_positive_floor_cannot_use_the_exception(self):
        for fault in ('feature_off','before_source','before_worker','before_result_end',
                      'prefix','candidate','floor','protected','expired'):
            with self.subTest(fault=fault):
                self.setup_case(enabled=fault!='feature_off')
                source,start,_state,_value,parent = self.post_unit(hint=1 if fault=='candidate' else 0)
                if fault in ('floor','protected'):
                    source=deepcopy(source)
                    if fault=='floor':source.tiles.pop((-1,0),None)
                    else:source.protected.add((-1,0))
                before=(self.h.status().inputs,self.h.status().moves)
                self.crossing(source,start,fault)
                ready,command=self.h.tick()
                self.assertFalse(ready and command.kind==4)
                self.assertEqual(before,(self.h.status().inputs,self.h.status().moves))
                self.assertEqual(parent,self.t.q.cycle().continuation_deadline_ns)

    def test_same_job_result_and_bridge_rebind_do_not_rearm_early_qualification(self):
        source,start,state,value,parent=self.post_unit()
        self.crossing(source,start)
        self.assertEqual(4,self.h.status().phase)
        self.assertEqual(0,self.lib.ng2_controller_cycle_assess(self.h.engine,
            state.job_id,state.capture_id,state.prefix,self.h.now,C.byref(value)))
        self.h.now+=1_000_000
        self.lib.ng2_begin118_count_reset()
        self.h.observe_actual(self.image(source,start+76_729_792,start+96_917_292),
            start=start+76_729_792,end=start+96_917_292)
        self.assertEqual(0,self.lib.ng2_begin118_count(),'same job cannot acquire another early proof')
        self.assertEqual(parent,self.t.q.cycle().continuation_deadline_ns)
        self.setup_case()
        source,start,_state,_value,parent=self.post_unit()
        changed=deepcopy(source)
        changed.tiles[(5,2)]='dirt'
        self.t.frame(changed,20_000_000)
        rebound=self.t.q.cycle()
        self.assertEqual(1,rebound.pending)
        rebound_start=rebound.capture_start_ns
        self.classify(changed,rebound_start)
        self.crossing(changed,rebound_start)
        self.assertNotEqual(4,self.h.status().phase,'bridge1 does not arm the post-unit exception')
        self.assertEqual(parent,self.t.q.cycle().continuation_deadline_ns)
