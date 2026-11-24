"""V2 begin reuses only its direct normal-zero proof, through public C calls.

The counter wrapper delegates to the real Motion kernel. It counts Controller
calls only; no Motion result, clock, pixel or threshold is replaced. Sparse
future responses are procedural and do not certify iPhone timing.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests import test_native_controller as native
from tests import test_native_upper118 as upper
from tests import test_native_upper_entry112 as old
from tests.test_native_cycle094 import Cycle
from tests.test_native_observation072 import Motion
from tests.test_native_ring094 import Result


class NativeUpperBegin118Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='native-upper-begin118-')
        folder = Path(cls.tmp.name)
        core = Path(os.environ.get('NECRO118_BEGIN_CORE', str(native.CORE)))
        wrapper = folder/'count.c'
        wrapper.write_text('''#include "NG2Core.h"
static unsigned calls;
void ng2_begin118_count_reset(void){calls=0;}
unsigned ng2_begin118_count(void){return calls;}
int ng2_begin118_count_motion(const NG2Scene *a,const NG2Scene *b,int32_t d,NG2Motion *out){
 ++calls;return ng2_motion(a,b,d,out);
}
''')
        objects = []
        for name in ('NG2Controller', 'NG2Perception', 'NG2Navigation', 'NG2Beat', 'count'):
            source = wrapper if name == 'count' else core/(name+'.c')
            profile = ['-O2', '-fno-fast-math', '-ffp-contract=off'] if name in (
                'NG2Perception', 'NG2Navigation') else ['-O0']
            rename = ['-Dng2_motion=ng2_begin118_count_motion'] if name == 'NG2Controller' else []
            obj = folder/(name+'.o')
            subprocess.run(['cc', '-std=c99', *profile, *rename, '-Wall', '-Wextra', '-Werror',
                '-pedantic', '-fPIC', '-I'+str(core), '-c', str(source), '-o', str(obj)], check=True)
            objects.append(str(obj))
        library = folder/'controller.so'
        subprocess.run(['cc', '-shared', *objects, '-lm', '-o', str(library)], check=True)
        cls.lib = l = C.CDLL(str(library))
        for name in ('create', 'create_cycle'):
            fn = getattr(l, 'ng2_controller_'+name)
            fn.argtypes = [C.c_uint64]
            fn.restype = C.c_void_p
        l.ng2_controller_destroy.argtypes = [C.c_void_p]
        l.ng2_controller_observe.argtypes = [C.c_void_p, C.POINTER(native.Scene), *([C.c_uint64]*4), C.c_int32]
        l.ng2_controller_observe_at.argtypes = [*l.ng2_controller_observe.argtypes, C.c_uint64]
        l.ng2_controller_tick.argtypes = [C.c_void_p, C.c_uint64, *([C.c_int32]*3), C.POINTER(native.Command)]
        l.ng2_controller_begin.argtypes = [C.c_void_p, *([C.c_uint64]*2), *([C.c_int32]*3)]
        l.ng2_controller_complete.argtypes = [C.c_void_p, *([C.c_uint64]*2), C.c_int32]
        l.ng2_controller_cancel.argtypes = [C.c_void_p, C.c_uint64, C.c_int32]
        l.ng2_controller_status.argtypes = [C.c_void_p, C.POINTER(native.Status)]
        l.ng2_controller_motion_wait.argtypes = [C.c_void_p, C.POINTER(native.MotionWait)]
        l.ng2_controller_events.argtypes = [C.c_void_p, C.POINTER(native.Event), C.c_size_t]
        l.ng2_controller_events.restype = C.c_size_t
        l.ng2_controller_cycle_status.argtypes = [C.c_void_p, C.POINTER(Cycle)]
        l.ng2_controller_cycle_worker_begin.argtypes = [C.c_void_p, *([C.c_uint64]*4)]
        l.ng2_controller_cycle_assess.argtypes = [C.c_void_p, *([C.c_uint64]*4), C.POINTER(Result)]
        l.ng2_motion.argtypes = [C.POINTER(native.Scene), C.POINTER(native.Scene), C.c_int32, C.POINTER(Motion)]
        l.ng2_begin118_count.restype = C.c_uint
        l.ng2_reason_name.argtypes = [C.c_int32]
        l.ng2_reason_name.restype = C.c_char_p

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.t = upper.NativeUpper118Tests(methodName='runTest')
        self.t.lib = self.lib
        self.t.setUp()
        self.addCleanup(self.t.doCleanups)
        self.h = self.t.h

    def ready(self, direction=1, moved=0):
        source, _base = self.t.pending(direction)
        for index in range(moved):
            wanted = direction if index < 2 else 4
            first = self.t.ticket(source)
            self.assertEqual(wanted, first.direction)
            self.t.ack(first, source)
            source = native.translated(source, wanted)
            source.tiles[native.DIRS[direction if index+1 < 2 else 4]] = 'floor'
            source.protected = self.t.cross({p for p, kind in source.tiles.items() if kind == 'item'})
            self.h.observe_actual(self.h.scene(2, 2, source, beat=True))
            self.t.assess(source)
        command = self.t.ticket(source)
        self.assertEqual(direction if moved < 2 else 4, command.direction)
        while self.h.now < command.not_before_ns:
            self.t.frame(source, min(20_000_000, command.not_before_ns-self.h.now))
        return source, command

    def count(self):
        return self.lib.ng2_begin118_count()

    def reset_count(self):
        self.lib.ng2_begin118_count_reset()

    def test_exact_V2_pair_reuses_normal_zero_at_begin_with_newer_current(self):
        for direction, moved in ((d, m) for d in (1, 2) for m in (0, 1, 2)):
            with self.subTest(direction=direction, prior_moves=moved):
                self.setUp()
                source, command = self.ready(direction, moved=moved)
                self.assertGreater(self.h.status().last_capture_id, command.source_capture_id)
                self.reset_count()
                self.t.frame(source, 1)
                self.assertGreater(self.count(), 0, 'a new current needs a real direct Motion proof')
                before = (self.h.status().inputs, self.h.status().moves)
                self.reset_count()
                self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine, command.id, self.h.now, 1, 0, 1))
                self.assertEqual(0, self.count(), 'the exact C-owned pair already passed normal Motion')
                self.assertEqual(before, (self.h.status().inputs, self.h.status().moves), 'begin is not ACK or motion credit')

    def test_discarded_new_capture_cannot_use_the_old_pair_cache(self):
        source, command = self.ready()
        self.h.now += 1
        self.h.observe_actual(self.h.scene(2, 2, source, beat=True), stable=0)
        self.reset_count()
        self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine, command.id, self.h.now, 1, 0, 1))
        self.assertEqual(1, self.count(), 'an uncertified new observation retains the old normal fallback')

    def test_new_nonzero_signature_cannot_borrow_a_previous_zero(self):
        source, command = self.ready()
        changed = deepcopy(source)
        changed.signature = native.translated(source, command.direction).signature
        self.reset_count()
        self.t.frame(changed, 1)
        self.assertGreater(self.count(), 0, 'changed pixels must run normal Motion')
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, command.id, self.h.now, 1, 0, 1))
        self.assertEqual(0, self.h.status().input_state)

    def test_changed_floor_protection_or_old_gold_never_borrows_cached_zero(self):
        for fault in ('floor', 'protection', 'gold'):
            with self.subTest(fault=fault):
                self.setUp()
                source, command = self.ready()
                changed = deepcopy(source)
                if fault == 'floor':
                    changed.tiles[native.DIRS[command.direction]] = 'dirt'
                elif fault == 'protection':
                    changed.protected.add(native.DIRS[command.direction])
                else:
                    changed.tiles[(-4, -1)] = 'floor'
                before = (self.h.status().inputs, self.h.status().moves)
                self.t.frame(changed, 1)
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, command.id, self.h.now, 1, 0, 1))
                self.assertEqual(before, (self.h.status().inputs, self.h.status().moves))

    def test_candidate_target_and_new_job_preempt_the_old_cached_command(self):
        for hint in (1, 2):
            with self.subTest(hint=hint):
                self.setUp()
                source, command = self.ready()
                changed = deepcopy(source)
                changed.goods = 'visible'
                self.t.frame(changed, 1)
                self.assertEqual(1, self.t.q.cycle().pending)
                self.t.assess(changed, hint=hint)
                self.assertEqual(1, self.t.q.cycle().candidate_latched)
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, command.id, self.h.now, 1, 0, 1))

    def test_owner_cancel_and_original_deadline_still_revoke_begin(self):
        for fault in ('owner', 'cancel', 'deadline', 'model'):
            with self.subTest(fault=fault):
                self.setUp()
                source, command = self.ready()
                if fault == 'cancel':
                    self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 2)
                if fault == 'deadline':
                    self.h.now = command.deadline_ns+1
                elif fault == 'model':
                    self.h.now += 1
                    image = self.h.scene(2, 2, source, beat=True)
                    image.beat_remaining = (image.beat_remaining+.49) % 1
                    self.h.observe_actual(image)
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, command.id, self.h.now,
                    1, 0, 0 if fault == 'owner' else 1))

    def test_old_id_is_inert_and_begin_attempt_consumes_only_its_own_proof(self):
        for outcome in (0, -1):
            with self.subTest(outcome=outcome):
                self.setUp()
                _source, command = self.ready()
                self.reset_count()
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, command.id-1, self.h.now, 1, 0, 1))
                self.assertEqual(0, self.count())
                self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine, command.id, self.h.now, 1, 0, 1))
                self.assertEqual(0, self.count())
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, command.id, self.h.now, 1, 0, 1))
                self.assertEqual(1, self.lib.ng2_controller_complete(self.h.engine, command.id, self.h.now+1, outcome))
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, command.id, self.h.now+1, 1, 0, 1))
                self.assertEqual(0, self.count(), 'NOT_SENT or UNKNOWN cannot reuse the consumed proof')

    def test_V1_retains_its_normal_begin_motion_call(self):
        q = old.NativeUpperEntry112Tests(methodName='runTest')
        q.lib = self.lib
        q.setUp()
        self.addCleanup(q.doCleanups)
        source, _opening, _parent = q.pending()
        command = q.ticket(source)
        while q.h.now < command.not_before_ns:
            q.independent(source, min(10_000_000, command.not_before_ns-q.h.now))
        self.reset_count()
        self.assertEqual(1, self.lib.ng2_controller_begin(q.h.engine, command.id, q.h.now, 1, 0, 1))
        self.assertEqual(1, self.count(), 'V1 remains outside the V2 cache contract')
