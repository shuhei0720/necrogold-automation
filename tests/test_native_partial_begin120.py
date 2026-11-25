"""Ordinary PARTIAL begin reuses only an earned zero for its unbegun ticket.

The public lifecycle enables the Runtime irregular/yield profile. The borrowed
counter delegates every Motion calculation to the real kernel; it never
changes an outcome or a clock. The small private fault hook changes one
existing identity at a time, solely to check cache misses/fallbacks.
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
from tests import test_native_partial_entry097 as partial
from tests import test_native_current_view114 as current
from tests import test_native_irregular110 as irregular
from tests import test_native_upper_begin118 as counter


class NativePartialBegin120Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source_temp = tempfile.TemporaryDirectory(prefix='partial120-core-')
        core = Path(cls.source_temp.name)
        original = Path(os.environ.get('NECRO120_PARTIAL_CORE', str(native.CORE)))
        for source in original.iterdir():
            if source.is_file():
                shutil.copy2(source, core/source.name)
        source = core/'NG2Controller.c'
        body = source.read_text()
        # Old subjects have no anchor-end field/cache. Their normal fallback
        # still runs; this adapter does not manufacture an evaluation result.
        anchor_end_fault = ('p->cycle_partial_anchor_end=0;' if
                            'cycle_partial_anchor_end' in body else '')
        source.write_text(body + r'''
void ng2_partial120_fault(NG2Controller *p,int f){
 switch(f){
 case 1:++p->cycle.job_id;break;
 case 2:++p->cycle.level_id;break;
 case 3:++p->s.started_ns;break;
 case 4:++p->cycle.capture_id;break;
 case 5:++p->cycle.capture_start_ns;break;
 case 6:++p->cycle.prefix;break;
 case 7:++p->s.last_capture_id;++p->seen_id;break;
 case 8:--p->s.last_capture_start_ns;--p->seen_start;break;
 case 9:--p->s.last_capture_end_ns;--p->seen_end;break;
 case 10:++p->last_observed_prefix;break;
 case 11:++p->command.x;break;
 case 12:p->preparation_epoch^=1;break;
 case 13:p->cycle_anchor.fingerprint[0]^=1;break;
 case 14:p->scene.fingerprint[0]^=1;break;
 case 15:ANCHOR_END break;
 case 16:++p->command.target_ns;break;
 case 17:++p->s.inputs;break;
 case 18:++p->s.restarts;break;
 case 19:p->preparation_epoch=1;break;
 case 20:p->preparation_epoch=0;break;
 }
}
uint64_t ng2_partial120_raw_epoch(const NG2Controller *p){return p->preparation_epoch;}
'''.replace('ANCHOR_END', anchor_end_fault))
        previous = os.environ.get('NECRO118_BEGIN_CORE')
        try:
            os.environ['NECRO118_BEGIN_CORE'] = str(core)
            counter.NativeUpperBegin118Tests.setUpClass.__func__(cls)
        finally:
            if previous is None:
                os.environ.pop('NECRO118_BEGIN_CORE', None)
            else:
                os.environ['NECRO118_BEGIN_CORE'] = previous
        cls.lib.ng2_partial120_fault.argtypes = [C.c_void_p, C.c_int]
        cls.lib.ng2_partial120_raw_epoch.argtypes = [C.c_void_p]
        cls.lib.ng2_partial120_raw_epoch.restype = C.c_uint64
        cls.lib.ng2_controller_enable_irregular.argtypes = [C.c_void_p]
        cls.lib.ng2_controller_enable_restart_yield.argtypes = [C.c_void_p]
        cls.lib.ng2_controller_observe_irregular_at.argtypes = [C.c_void_p,
            C.POINTER(native.Scene), C.POINTER(irregular.Observation)] + [C.c_uint64]*4 + [C.c_int32, C.c_uint64]
        cls.lib.ng2_controller_preparation_epoch.argtypes = [C.c_void_p, C.c_uint64, C.c_uint64]
        cls.lib.ng2_controller_preparation_epoch.restype = C.c_uint64

    @classmethod
    def tearDownClass(cls):
        counter.NativeUpperBegin118Tests.tearDownClass.__func__(cls)
        cls.source_temp.cleanup()

    def setUp(self):
        self.fresh()

    def fresh(self):
        self.driver = current.current_view_fixture(self.lib)
        self.addCleanup(self.driver.doCleanups)
        self.h = self.driver.harness()
        self.q = cycle.NativeCycle094Tests('runTest')
        self.q.lib, self.q.h = self.lib, self.h
        self.p = partial.NativePartialEntry097Tests('runTest')
        self.p.lib, self.p.h, self.p.q = self.lib, self.h, self.q

    def frame(self, terrain, advance=10_000_000, **kwargs):
        self.h.now += advance
        return self.h.observe_actual(self.h.scene(2, 2, terrain, beat=True), **kwargs)

    def ready(self, *, direction=1, post_observation=True):
        side = 1 if direction == 1 else -1
        items = {(side*x, 2) for x in range(-7, 0)}
        cells = {point: 'item' for point in items}
        cells.update({(side*-7, y): 'gold' for y in range(-2, 2)})
        mask = set().union(*(set((x+dx, y+dy) for dx, dy in native.DIRS.values()) | {(x, y)}
                                 for x, y in items))
        source, opening = self.p.pending(direction=direction, extra=cells, protected=mask)
        self.frame(source)
        command = self.h.next_move(source)
        self.assertEqual((4, direction), (command.kind, command.direction))
        if post_observation:
            while self.h.now < command.not_before_ns:
                self.frame(source, min(20_000_000, command.not_before_ns-self.h.now))
            self.assertGreater(self.h.status().last_capture_id, command.source_capture_id)
        else:
            self.h.now = command.not_before_ns
        return source, opening, command

    def reset_count(self):
        self.lib.ng2_begin118_count_reset()

    def count(self):
        return self.lib.ng2_begin118_count()

    def begin(self, command, *, front=1, owner=1):
        return self.lib.ng2_controller_begin(self.h.engine, command.id, self.h.now, front, 0, owner)

    def test_reserved_partial_new_current_reuses_zero_without_changing_the_move(self):
        for direction in (1, 2):
            with self.subTest(direction=direction):
                self.fresh()
                source, _, command = self.ready(direction=direction)
                latest = deepcopy(source)
                latest.tiles[((1 if direction == 1 else -1)*8, 1)] = 'dirt'
                ticket = bytes(command)
                before = self.h.status().inputs, self.h.status().moves
                self.reset_count()
                self.assertEqual(1, self.frame(latest, 1))
                self.assertGreater(self.count(), 0, 'every new image still needs its original-anchor normal proof')
                self.reset_count()
                self.assertEqual(1, self.begin(command))
                self.assertEqual(0, self.count(), 'begin must reuse this exact already-earned zero')
                self.assertEqual(before, (self.h.status().inputs, self.h.status().moves))
                self.assertEqual(ticket, bytes(self.h.events()[-1].command))
                self.h.now += 1
                self.assertEqual(1, self.lib.ng2_controller_complete(self.h.engine, command.id, self.h.now, 1))
                self.h.prefix = command.id
                self.h.observed_result(command, native.translated(latest, direction))
                self.assertEqual((before[0]+1, before[1]+1),
                                 (self.h.status().inputs, self.h.status().moves))

    def test_each_identity_full_scene_and_epoch_mismatch_uses_fallback_or_refuses(self):
        for fault in range(1, 19):
            with self.subTest(fault=fault):
                self.fresh()
                source, _, command = self.ready()
                if fault == 12:
                    self.lib.ng2_partial120_fault(self.h.engine, 19)
                    self.frame(source, 1)
                    self.assertEqual(1, self.lib.ng2_partial120_raw_epoch(self.h.engine))
                    self.lib.ng2_partial120_fault(self.h.engine, 20)
                    self.assertEqual(0, self.lib.ng2_partial120_raw_epoch(self.h.engine))
                else:
                    self.lib.ng2_partial120_fault(self.h.engine, fault)
                self.reset_count()
                accepted = self.begin(command)
                self.assertTrue(accepted == 0 or self.count() >= 1,
                                'a mismatched key may not accept using cached zero')

    def test_unproved_or_discarded_current_keeps_the_old_normal_motion(self):
        for fault in ('no_later_image', 'discarded'):
            with self.subTest(fault=fault):
                self.fresh()
                source, _, command = self.ready(post_observation=fault != 'no_later_image')
                if fault == 'discarded':
                    self.frame(source, 1, stable=0)
                self.reset_count()
                self.assertEqual(1, self.begin(command))
                self.assertEqual(1, self.count())

    def test_new_static_or_nonzero_observation_cannot_use_the_previous_fact(self):
        for fault in ('floor', 'protection', 'gold', 'item', 'unknown', 'unit'):
            with self.subTest(fault=fault):
                self.fresh()
                source, _, command = self.ready()
                changed = deepcopy(source)
                if fault == 'floor': changed.tiles[(-1, 0)] = 'dirt'
                elif fault == 'protection': changed.protected.add((-1, 0))
                elif fault == 'gold': changed.tiles[(-1, -1)] = 'floor'
                elif fault == 'item': changed.tiles[(-4, 2)] = 'floor'
                elif fault == 'unknown': changed.signature = bytes([80])*23296
                else: changed.signature = native.translated(source, 1).signature
                before = self.h.status().inputs, self.h.status().moves
                self.frame(changed, 1)
                self.reset_count()
                self.assertEqual(0, self.begin(command))
                self.assertEqual(before, (self.h.status().inputs, self.h.status().moves))

    def test_candidate_job_owner_cancel_and_original_deadline_preempt_begin(self):
        for fault in ('candidate', 'target', 'owner', 'cancel', 'deadline'):
            with self.subTest(fault=fault):
                self.fresh()
                source, _, command = self.ready()
                if fault in ('candidate', 'target'):
                    source.goods = 'visible'
                    self.frame(source, 1)
                    self.q.assess(1 if fault == 'target' else 2, 1)
                    self.assertTrue(self.q.cycle().candidate_latched)
                elif fault == 'cancel': self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 2)
                elif fault == 'deadline': self.h.now = command.deadline_ns+1
                self.assertEqual(0, self.begin(command, owner=0 if fault == 'owner' else 1))

    def test_stale_id_is_inert_true_begin_consumes_and_post_getter_does_not_recalculate(self):
        for outcome in (0, -1):
            with self.subTest(outcome=outcome):
                self.fresh()
                _, opening, command = self.ready()
                self.reset_count()
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, opening.id, self.h.now, 1, 0, 1))
                self.assertEqual(0, self.count())
                self.assertEqual(1, self.begin(command))
                self.assertEqual(0, self.count())
                self.assertEqual(0, self.lib.ng2_controller_preparation_epoch(self.h.engine, command.id, self.h.now))
                self.assertEqual(0, self.count(), 'the post-begin getter has no Motion work')
                self.assertEqual(0, self.begin(command))
                self.h.now += 1
                self.assertEqual(1, self.lib.ng2_controller_complete(self.h.engine, command.id, self.h.now, outcome))
                self.assertEqual(0, self.begin(command))
                self.assertEqual(0, self.count(), 'NOT_SENT/UNKNOWN may not rearm this proof')


if __name__ == '__main__':
    unittest.main()
