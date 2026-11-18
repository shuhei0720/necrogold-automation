"""TEST117 partial entry footprint and immutable single-face proof, public C.

Sparse procedural textures/clocks are source-cut tests, not phone-state
restoration or missing later game images.
"""
import ctypes as C
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests import test_native_partial_refresh104 as refresh
from tests import test_native_ring117 as ring117
from tests import test_native_offer_coverage104 as offer
from tests import test_native_ring_bank094 as bank
from tests.test_native_ring094 import Result
from tests import test_native_goods113 as goods
from tests import test_native_current_view114 as current
from tests import test_native_irregular110 as irregular

ROOT = Path(__file__).resolve().parents[1]


class NativePartialFootprint117Tests(unittest.TestCase):
    setUpClass = classmethod(refresh.NativePartialRefresh104Tests.setUpClass.__func__)
    tearDownClass = classmethod(refresh.NativePartialRefresh104Tests.tearDownClass.__func__)
    setUp = refresh.NativePartialRefresh104Tests.setUp
    fresh = refresh.NativePartialRefresh104Tests.fresh

    def pending(self):
        items = {(x, 0) for x in range(-7, -2)}
        protection = set().union(*(refresh.NativePartialRefresh104Tests.cross(p) for p in items))
        cells = {point: 'item' for point in items}
        cells.update({(-2, 0): 'floor', (2, 3): 'floor'})
        return self.p.pending(direction=1, initial='floor', extra=cells, protected=protection)[0]

    def test_exact_item_halo_is_not_dilated_again_over_actual_entry_destination(self):
        source = self.pending()
        before = self.q.cycle()
        counts = self.h.status().inputs, self.h.status().moves
        self.p.observe(source)
        state = self.q.cycle()
        self.assertEqual((0, 0, 0), (state.state, self.h.status().reason, state.pending),
            'actual source/destination floors are unprotected; the halo at(-2,0) is not another collision radius')
        self.assertEqual((before.job_id, before.capture_id, before.continuation_deadline_ns),
                         (state.job_id, state.capture_id, state.continuation_deadline_ns))
        self.assertEqual(counts, (self.h.status().inputs, self.h.status().moves))

    def test_remote_observed_wall_retires_old_partial_into_new_data_with_original_horizon(self):
        source = self.pending()
        before = self.q.cycle()
        counts = self.h.status().inputs, self.h.status().moves
        latest = deepcopy(source)
        latest.tiles[(-7, -1)] = 'gold'
        latest.tiles[(2, 3)] = 'dirt'
        self.p.observe(latest)
        state = self.q.cycle()
        self.assertEqual((before.job_id+1, self.h.number, 1),
                         (state.job_id, state.capture_id, state.pending),
                         'the valid exact footprint must make the existing DATA rebind reachable')
        self.assertLessEqual(state.continuation_deadline_ns, before.continuation_deadline_ns)
        self.assertEqual(counts, (self.h.status().inputs, self.h.status().moves))

    def test_actual_walk_cells_unexplained_masks_and_parent_deadline_still_veto_entry(self):
        for fault in ('origin', 'destination', 'extra_mask', 'unknown_floor', 'new_item', 'deadline'):
            with self.subTest(fault=fault):
                self.fresh()
                source = self.pending()
                parent = self.q.cycle()
                counts = self.h.status().inputs, self.h.status().moves
                latest = deepcopy(source)
                if fault == 'origin':
                    latest.protected.add((0, 0))
                elif fault == 'destination':
                    latest.protected.add((-1, 0))
                elif fault == 'extra_mask':
                    latest.protected.add((8, 4))
                elif fault == 'unknown_floor':
                    latest.tiles.pop((-1, 0))
                elif fault == 'new_item':
                    latest.tiles[(-2, 0)] = 'item'
                    latest.protected.update(refresh.NativePartialRefresh104Tests.cross((-2, 0)))
                else:
                    self.h.now = parent.continuation_deadline_ns+1
                self.p.observe(latest)
                ready, command = self.h.tick()
                self.assertFalse(ready and command.kind in (3, 4))
                self.assertEqual(counts, (self.h.status().inputs, self.h.status().moves))


class NativeSingleLowerEntryController117Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cycle.NativeCycle094Tests.setUpClass()
        cls.lib = cycle.NativeCycle094Tests.lib
        cls.tmp = tempfile.TemporaryDirectory(prefix='single-lower-controller117-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.ring = bank.NativeRingBank094Tests.build_library(
            ROOT/'patches/loopctrl/ngg2/NG2Ring.c', Path(cls.tmp.name)/'ring.so')

    tearDownClass = classmethod(cycle.NativeCycle094Tests.tearDownClass.__func__)

    def setUp(self):
        self.q = cycle.NativeCycle094Tests(methodName='runTest')
        self.q.setUp()
        self.addCleanup(self.q.doCleanups)
        self.h = self.q.h

    def normal(self, scene_change=None, result_change=None, separate_price=False):
        scene = ring117.separate_price_scene() if separate_price else ring117.lower_entry_scene()
        pixels = ring117.separate_chest_price_pixels() if separate_price else ring117.single_face_pixels()
        status, value = offer.normal_assess(self.ring, pixels, scene)
        self.assertEqual((0, 3, 7 if separate_price else 17),
                         (status, value.outcome, value.certificate.policy_version))
        if scene_change:
            scene_change(scene)
        self.assertEqual(1, self.h.observe(native.Scene.from_buffer_copy(bytes(scene))))
        job = self.q.cycle()
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(
            self.h.engine, job.job_id, job.capture_id, job.prefix, self.h.now))
        if result_change:
            result_change(value)
        value.started_ns, value.finished_ns = self.h.now, self.h.now+1
        self.h.now += 2
        self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine,
            job.job_id, job.capture_id, job.prefix, self.h.now, C.byref(value)))
        return job

    def test_ordinary_producer_certificate_reaches_durable_restart_and_next_floor(self):
        self.normal()
        self.assertEqual((3, 0, 4),
                         (self.q.cycle().outcome, self.q.cycle().status, self.q.cycle().state),
                         'Controller independently accepts the observed one-face seven-GOLD entry proof')
        self.q.pause_observed()
        self.assertEqual(0, self.h.tick()[0])
        self.assertEqual(1, self.q.durable())
        ready, restart = self.h.tick()
        self.assertEqual((1, 3), (ready, restart.kind))
        self.assertEqual(1, self.q.intent(restart))
        self.q.next_floor(restart)
        self.assertEqual((1, 0), (self.h.status().restarts, self.h.status().terminal))

    def test_shared_lower_price_geometry_reaches_independent_adoption_and_real_restart(self):
        self.normal(separate_price=True)
        self.assertEqual((3, 0, 4),
                         (self.q.cycle().outcome, self.q.cycle().status, self.q.cycle().state),
                         'the new native layout3 producer is independently checked by the C consumer')
        self.q.pause_observed()
        self.assertEqual(1, self.q.durable())
        ready, restart = self.h.tick()
        self.assertEqual((1, 3), (ready, restart.kind))
        self.assertEqual(1, self.q.intent(restart))
        self.q.next_floor(restart)
        self.assertEqual((1, 0), (self.h.status().restarts, self.h.status().terminal))

    def test_layout3_rechecks_exact_anchor_and_each_separate_price_boundary(self):
        scenes={
            'below_unknown': lambda s: offer.set_tile(s,-4,1,0),
            'extra_item': lambda s: offer.set_tile(s,5,2,6),
            'extra_halo': lambda s: s.protected_cells.__setitem__((2+5)*23+5+11,1),
            'missing_cap': lambda s: offer.set_tile(s,-6,0,0),
            'missing_wall': lambda s: offer.set_tile(s,-7,-1,0),
        }
        results={
            'old_layout': lambda r: setattr(r.certificate,'layout_version',2),
            'row_sy_overflow': lambda r: setattr(r.rows[0],'sy',2147483647),
            'price_y_overflow': lambda r: r.certificate.price_boxes[1].__setitem__(1,2147483647),
            'wrong_policy': lambda r: setattr(r.certificate,'policy_version',17),
            'ignored': lambda r: setattr(r.certificate,'ignored_containers',1),
            'short_price': lambda r: r.certificate.price_boxes[1].__setitem__(3,6),
            'tall_price': lambda r: r.certificate.price_boxes[1].__setitem__(3,10),
            'lower_top': lambda r: r.certificate.price_boxes[1].__setitem__(1,234),
            'lower_bottom': lambda r: r.certificate.price_boxes[1].__setitem__(1,237),
            'ambiguous_lower': lambda r: r.certificate.price_boxes[0].__setitem__(1,235),
            'bound': lambda r: setattr(r.partial[0],'icon_upper_bound',.8),
        }
        for name,change in scenes.items():
            with self.subTest(scene=name):
                self.setUp();self.normal(scene_change=change,separate_price=True)
                self.assertEqual((0,3,7),(self.q.cycle().outcome,self.q.cycle().status,self.q.cycle().state))
        for name,change in results.items():
            with self.subTest(result=name):
                self.setUp();self.normal(result_change=change,separate_price=True)
                self.assertEqual((0,3,7),(self.q.cycle().outcome,self.q.cycle().status,self.q.cycle().state))

    def test_layout3_complete_certificate_translation_cannot_cross_central_pixel_domain(self):
        def shift_scene(scene):
            tiles,protected=list(scene.tiles),list(scene.protected_cells)
            scene.tiles[:]=[0]*230;scene.protected_cells[:]=[0]*230
            for y in range(8):
                for x in range(23):
                    scene.tiles[(y+2)*23+x]=tiles[y*23+x]
                    scene.protected_cells[(y+2)*23+x]=protected[y*23+x]
        def box(value):
            if value[2] and value[3]:value[1]+=72
        def slot(value):
            value.sy+=72
            for name in ('icon_box','word_box','non_target_icon_box','non_target_name_box','ignored_icon_box'):
                box(getattr(value,name))
        def shift_result(value):
            for row in value.rows[:value.row_count]:
                row.sy+=72
                for cell in row.slots:slot(cell)
            for cell in value.partial[:value.partial_count]:slot(cell)
            witness=value.certificate;witness.row[1]+=72
            for name in ('strip_box','merchant_box'):box(getattr(witness,name))
            for name in ('sign_boxes','item_boxes','name_boxes','price_boxes','board_boxes'):
                for entry in getattr(witness,name):box(entry)
            for endcap in witness.endcaps:box(endcap.box)
        # A normal producer is translated uniformly as a numeric forgery.
        # Its strip bottom316 is beyond the declared central domain315.
        self.normal(scene_change=shift_scene,result_change=shift_result,separate_price=True)
        self.assertEqual((0,3,7),(self.q.cycle().outcome,self.q.cycle().status,self.q.cycle().state))

    def test_immutable_anchor_and_numeric_fields_are_rechecked_independently(self):
        def missing_wall(scene):
            offer.set_tile(scene, 2, -4, 0)
            offer.set_tile(scene, 10, 4, 2)
        scenes = {
            'same_count_wrong_wall': missing_wall,
            'entry_unknown': lambda s: offer.set_tile(s, 0, 0, 0),
            'lower_floor': lambda s: offer.set_tile(s, -1, -2, 0),
            'cap': lambda s: offer.set_tile(s, -3, -3, 0),
            'extra_item': lambda s: offer.set_tile(s, 8, 3, 6),
            'inexact_projection': lambda s: s.protected_cells.__setitem__(2*23+9, 0),
        }
        results = {
            'invented_face': lambda r: r.certificate.board_counts.__setitem__(1, 200),
            'absent_box': lambda r: r.certificate.board_boxes[1].__setitem__(0, 432),
            'wrong_height': lambda r: r.certificate.board_boxes[0].__setitem__(3, 28),
            'price': lambda r: setattr(r.certificate, 'unmatched_prices', 1),
            'bound': lambda r: setattr(r.partial[0], 'icon_upper_bound', .8),
            'nonfinite': lambda r: setattr(r.partial[0], 'icon_upper_bound', float('nan')),
        }
        for name, change in scenes.items():
            with self.subTest(scene=name):
                self.setUp()
                self.normal(scene_change=change)
                self.assertEqual((0, 3, 7), (self.q.cycle().outcome,
                    self.q.cycle().status, self.q.cycle().state))
        for name, change in results.items():
            with self.subTest(certificate=name):
                self.setUp()
                self.normal(result_change=change)
                self.assertEqual((0, 3, 7), (self.q.cycle().outcome,
                    self.q.cycle().status, self.q.cycle().state))


if __name__ == '__main__':
    unittest.main()


class NativeFullCurrentData117Tests(goods.Goods113Base):
    """Latest complete offer DATA does not claim zero or restore UP credit."""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.lib.ng2_controller_create_cycle.argtypes = [C.c_uint64]
        cls.lib.ng2_controller_create_cycle.restype = C.c_void_p
        cls.lib.ng2_controller_enable_irregular.argtypes = [C.c_void_p]
        cls.lib.ng2_controller_enable_restart_yield.argtypes = [C.c_void_p]
        cls.lib.ng2_controller_observe_irregular_at.argtypes = [C.c_void_p,
            C.POINTER(native.Scene), C.POINTER(irregular.Observation)] + [C.c_uint64]*4 + [C.c_int32,C.c_uint64]
        cls.lib.ng2_controller_observe_irregular_at.restype = None

    def setUp(self):
        self.p = current.current_view_fixture(self.lib)
        self.addCleanup(self.p.doCleanups)

    def source(self, variant='price', prepared=False):
        self.h, _, old, _ = self.p.armed(direction=1 if variant=='price' else 3)
        self.q = cycle.NativeCycle094Tests(methodName='runTest')
        self.q.lib, self.q.h = self.lib, self.h
        self.h.ack(old)
        self.h.now = max(self.h.now+2, old.target_ns+100_000_000)
        value = ring117.separate_price_scene() if variant=='price' else ring117.lower_entry_scene()
        self.a = native.Scene.from_buffer_copy(bytes(value))
        self.a.signature[:] = goods.NativeGoodsUpView113Tests.source().signature
        if variant=='price':
            offer.set_tile(self.a,-7,-1,0)
            offer.set_tile(self.a,0,0,1)  # Observed player floor is explicit in this DATA fixture.
        else: offer.set_tile(self.a,7,4,1)
        self.pixels = ring117.separate_chest_price_pixels() if variant=='price' else ring117.single_face_pixels()
        status,self.old_result = offer.normal_assess(self.ring,self.pixels,self.a)
        self.assertEqual((0,0 if variant=='price' else 3), (status,self.old_result.outcome))
        self.assertEqual(1,self.h.observe_actual(self.a))
        self.root = self.q.cycle()
        self.assertEqual(1,self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
            self.root.job_id,self.root.capture_id,self.root.prefix,self.h.now))
        self.pause = None
        if prepared:
            ready,self.pause = self.h.tick()
            self.assertEqual((1,2),(ready,self.pause.kind))
        self.b = native.Scene.from_buffer_copy(bytes(self.a))
        if variant=='price': offer.set_tile(self.b,-7,-1,2)
        else:
            offer.set_tile(self.b,7,4,4)
            self.b.signature[:] = bytes((i*17+23)%220+20 for i in range(23296))
        self.counts = self.h.status().inputs,self.h.status().moves
        return old

    def frame(self, value):
        self.h.now += 10_000_000
        self.assertEqual(1,self.h.observe_actual(value))
        return self.h.number

    def commit_result(self,value):
        state = self.q.cycle()
        if not state.worker_started_ns:
            self.assertEqual(1,self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
                state.job_id,state.capture_id,state.prefix,self.h.now))
        value.started_ns=self.h.now;self.h.now+=1;value.finished_ns=self.h.now
        self.assertEqual(1,self.lib.ng2_controller_cycle_assess(self.h.engine,
            state.job_id,state.capture_id,state.prefix,self.h.now,C.byref(value)))
        return state

    def assert_current(self):
        fresh = self.q.cycle()
        self.assertEqual((self.root.job_id+1,self.h.number,1),
            (fresh.job_id,fresh.capture_id,fresh.pending))
        self.assertLessEqual(fresh.continuation_deadline_ns,self.root.continuation_deadline_ns)
        self.assertEqual(self.counts,(self.h.status().inputs,self.h.status().moves))
        self.assertEqual(0,self.lib.ng2_controller_cycle_assess(self.h.engine,
            self.root.job_id,self.root.capture_id,self.root.prefix,self.h.now,C.byref(self.old_result)))
        return fresh

    def test_finite_latest_full_data_accepts_normal_negative_in_both_callback_orders(self):
        for variant in ('price','lower'):
            for order in ('result_first','observe_first'):
                with self.subTest(variant=variant,order=order):
                    self.setUp();self.source(variant)
                    if order=='result_first': self.commit_result(self.old_result)
                    self.frame(self.b)
                    if order=='observe_first': self.commit_result(self.old_result)
                    if variant=='lower' and order=='result_first':
                        self.assertEqual((3,4),(self.q.cycle().outcome,self.q.cycle().state))
                    else:
                        self.assert_current()
                        status,value=offer.normal_assess(self.ring,self.pixels,self.b)
                        self.assertEqual((0,3),(status,value.outcome))
                        self.commit_result(value)
                    self.assertEqual((3,0,4),(self.q.cycle().outcome,self.q.cycle().status,self.q.cycle().state))
                    self.q.pause_observed();self.assertEqual(1,self.q.durable())
                    ready,restart=self.h.tick();self.assertEqual((1,3),(ready,restart.kind))
                    self.assertEqual(1,self.q.intent(restart));before=self.h.status().moves
                    self.q.next_floor(restart)
                    self.assertEqual(before,self.h.status().moves)
                    self.assertEqual(self.counts,(self.h.status().inputs,self.h.status().moves))

    def test_current_unknown_is_held_without_phase_proofs_or_move_credit(self):
        self.source('price');self.frame(self.b);self.commit_result(self.old_result)
        fresh=self.assert_current()
        # An ordinary incomplete classification is not changed into absence.
        unknown=deepcopy(self.old_result)
        self.commit_result(unknown)
        self.assertEqual((0,7,0),(self.q.cycle().outcome,self.q.cycle().state,self.q.cycle().pending))
        for _ in range(3):
            self.frame(self.b)
            ready,command=self.h.tick()
            self.assertFalse(ready and command.kind in (3,4))
        self.assertEqual(self.counts,(self.h.status().inputs,self.h.status().moves))
        self.assertEqual(fresh.job_id,self.q.cycle().job_id)

    def test_changed_goods_masks_player_neighborhood_walls_and_old_candidates_veto_data(self):
        for fault in ('cap','below','old_gold','new_near_gold','door','extra_item','mask','candidate','target'):
            with self.subTest(fault=fault):
                self.setUp();self.source('price')
                if fault=='cap':offer.set_tile(self.b,-6,0,0)
                elif fault=='below':offer.set_tile(self.b,-4,1,0)
                elif fault=='old_gold':offer.set_tile(self.b,-7,-2,1)
                elif fault=='new_near_gold':offer.set_tile(self.b,0,-1,2)
                elif fault=='door':offer.set_tile(self.b,8,4,5)
                elif fault=='extra_item':offer.set_tile(self.b,8,4,6)
                elif fault=='mask':self.b.protected_cells[0]=1
                else:self.old_result.outcome=1 if fault=='candidate' else 2
                self.frame(self.b);self.commit_result(self.old_result)
                self.assertEqual(self.root.job_id,self.q.cycle().job_id)
                self.assertEqual(0,self.q.cycle().pending)
                self.assertEqual(fault in ('candidate','target'),bool(self.q.cycle().candidate_latched))
                ready,command=self.h.tick()
                self.assertFalse(ready and command.kind in (3,4))
                self.assertEqual(self.counts,(self.h.status().inputs,self.h.status().moves))

    def test_prepared_pause_is_retired_only_while_definitely_unbegun(self):
        self.source('price',prepared=True)
        old_pause=self.pause
        self.frame(self.b);self.commit_result(self.old_result);self.assert_current()
        retired=next(e for e in self.h.events() if e.command.id==old_pause.id)
        self.assertEqual((0,3),(retired.begin_ns,retired.outcome))
        self.assertEqual(0,self.lib.ng2_controller_begin(self.h.engine,
            old_pause.id,max(self.h.now,old_pause.not_before_ns),1,0,1))
        self.assertEqual(self.counts,(self.h.status().inputs,self.h.status().moves))

    def test_new_current_epoch_invalidates_negative_but_keeps_bound_positive_priority(self):
        for outcome in (3,1,2):
            with self.subTest(outcome=outcome):
                self.setUp();self.source('price');self.frame(self.b);self.commit_result(self.old_result)
                fresh=self.assert_current()
                self.assertEqual(1,self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
                    fresh.job_id,fresh.capture_id,fresh.prefix,self.h.now))
                changed=deepcopy(self.b);offer.set_tile(changed,-7,-2,1)
                self.frame(changed)
                status,value=offer.normal_assess(self.ring,self.pixels,self.b)
                self.assertEqual((0,3),(status,value.outcome))
                # Typed positive-priority boundary; classification accuracy is
                # covered by the normal pixel target tests, independently.
                value.outcome=outcome
                self.commit_result(value)
                self.assertEqual(outcome in (1,2),bool(self.q.cycle().candidate_latched))
                self.assertEqual(0,self.q.cycle().pending)
                ready,command=self.h.tick()
                self.assertFalse(ready and command.kind in (3,4))
                self.assertEqual(self.counts,(self.h.status().inputs,self.h.status().moves))

    def test_parent_equality_or_stale_latest_cannot_start_a_new_data_epoch(self):
        for fault in ('parent_equality','stale_latest','begun_pause'):
            with self.subTest(fault=fault):
                self.setUp();self.source('price',prepared=fault=='begun_pause')
                if fault=='begun_pause':
                    self.h.now=max(self.h.now,self.pause.not_before_ns)
                    self.assertEqual(1,self.lib.ng2_controller_begin(self.h.engine,self.pause.id,self.h.now,1,0,1))
                    self.h.now+=10_000_000
                    self.assertEqual(0,self.h.observe_actual(self.b), 'begun UI rejects new DATA observations')
                elif fault=='parent_equality':
                    self.h.now=self.root.continuation_deadline_ns
                    self.assertEqual(1,self.h.observe_actual(self.b,start=self.h.now-2,end=self.h.now))
                else:
                    self.h.now+=10_000_000
                    end=self.h.now
                    self.assertEqual(1,self.h.observe_actual(self.b,start=end-2,end=end))
                    self.h.now+=150_000_001
                self.commit_result(self.old_result)
                self.assertEqual(self.root.job_id,self.q.cycle().job_id)
                ready,command=self.h.tick()
                self.assertFalse(ready and command.kind in (3,4))
                self.assertEqual(self.counts,(self.h.status().inputs,self.h.status().moves))
