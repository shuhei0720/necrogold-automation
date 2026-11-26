"""TEST122: finite domain-two side reveal with remote blocker loss.

Independent procedural worlds qualify the real public Motion assertion. Phone
frames remain private calibration; public Controller tests earn ACK normally.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import random
import shutil
import subprocess
import tempfile
import unittest

from tests import test_native_controller as controller
from tests import test_native_revealed_ack113 as ack113
from tests import test_native_recovery as recovery_fixture
from tests.test_native_motion067 import Motion
from tests.test_native_revealed_domain113 import pair as domain_pair, SHIM as DOMAIN_SHIM
from tests.test_native_revealed_motion108 import DIRS, cell, W, H
from tests.test_native_recovery import RecoveryStatus

CORE = Path(os.environ.get('NG2_TEST122_CORE', str(controller.CORE)))
CONTROLLER_CORE = Path(os.environ.get('NG2_TEST122_CONTROLLER_CORE', str(CORE)))


def pair(direction=3, loss='both', **kwargs):
    before, after = domain_pair(direction, **kwargs)
    dx, dy = DIRS[direction]
    remote = {1: (7, 3), 2: (-7, 3), 3: (7, 3), 4: (7, -3)}[direction]
    outside = {1: (11, 3), 2: (-11, 3), 3: (7, 4), 4: (7, -5)}[direction]
    if loss in ('dirt', 'unknown', 'both'):
        x, y = remote
        before.tiles[cell(x, y)] = 3
        after.tiles[cell(x-dx, y-dy)] = 0 if loss == 'unknown' else 4
    if loss in ('outside', 'both'):
        before.tiles[cell(*outside)] = 3
    return before, after


SHIM = r'''
int test122_proof(const NG2Scene *a,const NG2Scene *b,int direction,NG2Motion *out){
#if HAS122
    View *v=calloc(2,sizeof(*v));Candidate c[73];int n=1,amount,d;
    if(!v)return 0;
    view(a->signature,v);view(b->signature,v+1);
    c[0].sx=c[0].sy=0;c[0].score=intensity(v,v+1,0,0);
    for(amount=1;amount<=18;++amount)for(d=1;d<=4;++d){
        c[n].sx=amount*ddx[d];c[n].sy=amount*ddy[d];
        c[n].score=intensity(v,v+1,c[n].sx,c[n].sy);++n;
    }
    qsort(c,73,sizeof(*c),ranked);
    singleton_dependency_motion122(a,b,direction,v,c,out);free(v);
#else
    (void)a;(void)b;(void)direction;(void)out;
#endif
    return 1;
}
'''


class SingletonDependency122Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.libraries = {}
        has = int('static void singleton_dependency_motion122(' in
                  (CORE/'NG2Navigation.c').read_text())
        for label, flags in (('O0', ['-O0']), ('strictO2',
                ['-O2', '-fno-fast-math', '-ffp-contract=off', '-frounding-math'])):
            source = Path(cls.temp.name)/(label+'.c')
            source.write_text('#define HAS122 '+str(has)+'\n#include "NG2Navigation.c"\n'
                              + DOMAIN_SHIM + SHIM)
            binary = source.with_suffix('.so')
            subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-pedantic',
                '-shared', '-fPIC', *flags, '-I', str(CORE), str(source), '-lm',
                '-o', str(binary)], check=True, capture_output=True)
            lib = C.CDLL(str(binary));ptr = C.POINTER(controller.Scene)
            lib.ng2_motion.argtypes = [ptr, ptr, C.c_int, C.POINTER(Motion)]
            lib.test122_proof.argtypes = lib.ng2_motion.argtypes
            lib.test113_domain_stats.argtypes = [ptr, ptr, C.c_int,
                C.POINTER(C.c_double), C.POINTER(C.c_int)]
            cls.libraries[label] = lib

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def stats(self, lib, before, after, direction=3):
        scores, metrics = (C.c_double*4)(), (C.c_int*23)()
        self.assertEqual(1, lib.test113_domain_stats(C.byref(before), C.byref(after),
            direction, scores, metrics))
        return tuple(scores), tuple(metrics)

    def result(self, lib, before, after, direction=3, proof=False, prior=None):
        out = prior if prior is not None else Motion()
        call = lib.test122_proof if proof else lib.ng2_motion
        self.assertEqual(1, call(C.byref(before), C.byref(after), direction, C.byref(out)))
        return out.kind, out.dx, out.dy

    def qualify(self, lib, before, after, direction):
        scores, m = self.stats(lib, before, after, direction)
        dx, dy = DIRS[direction]
        self.assertEqual((2, -9*dx, -9*dy, 1, 0), m[:5])
        self.assertEqual(73, m[22])
        self.assertGreater(scores[0], .45);self.assertGreaterEqual(scores[1], .08)
        self.assertLess(m[5], 300, 'old narrow blur remains insufficient')
        self.assertGreaterEqual(m[9], 300);self.assertLessEqual(20*m[10], m[9])
        self.assertGreaterEqual(min(m[11:13]), 100)
        self.assertGreaterEqual(m[13], 300)
        self.assertEqual((0, 0), m[14:16]);self.assertGreaterEqual(scores[2], 15)
        self.assertGreaterEqual(m[16], 300);self.assertLessEqual(20*m[17], m[16])
        self.assertGreaterEqual(min(m[18:20]), 100);self.assertEqual(0, m[21])

    def test_public_motion_proves_unit_with_only_remote_blocker_losses(self):
        for label, lib in self.libraries.items():
            for direction, (dx, dy) in DIRS.items():
                for loss in ('dirt', 'unknown', 'outside', 'both'):
                    with self.subTest(profile=label, direction=direction, loss=loss):
                        before, after = pair(direction, loss)
                        original = bytes(before), bytes(after)
                        self.qualify(lib, before, after, direction)
                        self.assertEqual((1, dx, dy), self.result(lib, before, after, direction))
                        self.assertEqual(original, (bytes(before), bytes(after)))

    def test_one_unavailable_dependency_alternative_remains_unknown(self):
        for label, lib in self.libraries.items():
            with self.subTest(profile=label):
                before, after = pair(3, right=101, top=37)
                scores, m = self.stats(lib, before, after)
                self.assertEqual((2, 0, 9, 1, 0), m[:5]);self.assertEqual(73, m[22])
                self.assertGreaterEqual(m[9], 300);self.assertLessEqual(20*m[10], m[9])
                self.assertGreaterEqual(min(m[11:13]), 100)
                self.assertLess(m[13], 300);self.assertGreater(m[14], 0)
                self.assertGreaterEqual(m[16], 300);self.assertLessEqual(20*m[17], m[16])
                self.assertGreaterEqual(min(m[18:20]), 100)
                self.assertEqual((0, 0, 0), self.result(lib, before, after))

    def test_independent_signed_planes_require_their_own_quality(self):
        for label, lib in self.libraries.items():
            for plane, box in (('dependency', (43, 59, 36, 79)),
                               ('axis', (80, 90, 54, 72))):
                with self.subTest(profile=label, plane=plane):
                    before, after = pair(3);signature = bytearray(after.signature)
                    rng = random.Random(113099)
                    left, right, top, bottom = box
                    for y in range(top, bottom):
                        for x in range(left, right):signature[(y+9)*W+x] = rng.randrange(74, 183)
                    after.signature[:] = signature
                    scores, m = self.stats(lib, before, after)
                    self.assertEqual((2, 0, 9, 1, 0), m[:5]);self.assertEqual(73, m[22])
                    self.assertGreaterEqual(m[13], 300);self.assertEqual((0, 0), m[14:16])
                    self.assertGreaterEqual(scores[2], 15)
                    self.assertTrue(min(m[11:13]) >= 100 and min(m[18:20]) >= 100)
                    self.assertTrue(m[9] >= 300 and m[16] >= 300)
                    ix = 9 if plane == 'dependency' else 16
                    other = 16 if ix == 9 else 9
                    self.assertGreater(20*m[ix+1], m[ix])
                    self.assertLessEqual(20*m[other+1], m[other])
                    self.assertEqual((0, 0, 0), self.result(lib, before, after, proof=True))

    def test_missing_axis_support_and_band_cannot_be_replaced_by_dependency(self):
        for label, lib in self.libraries.items():
            for fault in ('support', 'band'):
                with self.subTest(profile=label, fault=fault):
                    before, after = pair(3, extra_dirt=fault != 'support')
                    if fault == 'band':
                        for i, kind in enumerate(before.tiles):
                            x, y = i%23-11, i//23-5
                            if kind == 4 and y >= 0:
                                before.tiles[i] = 0
                                if y < 4:after.tiles[cell(x, y+1)] = 0
                        for y in (-2, -1):
                            for x in range(-6, 0):
                                if before.tiles[cell(x, y)] == 0:
                                    before.tiles[cell(x, y)] = 4
                                    if after.tiles[cell(x, y+1)] == 0:after.tiles[cell(x, y+1)] = 4
                    scores, m = self.stats(lib, before, after)
                    self.assertEqual((2, 0, 9, 1, 0), m[:5])
                    self.assertGreaterEqual(m[13], 300);self.assertEqual((0, 0), m[14:16])
                    self.assertGreaterEqual(scores[2], 15)
                    self.assertGreaterEqual(m[9], 300);self.assertLessEqual(20*m[10], m[9])
                    self.assertGreaterEqual(min(m[11:13]), 100)
                    if fault == 'support':self.assertLess(m[16], 300)
                    else:
                        self.assertGreaterEqual(m[16], 300);self.assertLess(m[19], 100)
                    self.assertEqual((0, 0, 0), self.result(lib, before, after, proof=True))

    def test_supported_axis_competitor_requires_its_own_lead(self):
        for label, lib in self.libraries.items():
            with self.subTest(profile=label):
                before, after = pair(3);world = bytearray(before.signature)
                rng = random.Random(113105)
                for y in range(36, 80):
                    for x in range(80, 115):
                        sign = 1 if (x//2+y//2)%2 else -1
                        world[y*W+x] = 128+16*sign+rng.randrange(-2, 3)
                moved = bytearray([128]*(W*H))
                for y in range(H-9):
                    for x in range(W):moved[(y+9)*W+x] = 128+3*(world[y*W+x]-128)
                before.signature[:], after.signature[:] = world, moved
                scores, m = self.stats(lib, before, after)
                self.assertEqual((2, 0, 9, 1, 0), m[:5]);self.assertEqual(73, m[22])
                self.assertGreaterEqual(m[13], 300);self.assertEqual((0, 0), m[14:16])
                self.assertGreaterEqual(scores[2], 15)
                self.assertTrue(m[9] >= 300 and m[16] >= 300)
                self.assertTrue(min(m[11:13]) >= 100 and min(m[18:20]) >= 100)
                self.assertLessEqual(20*m[10], m[9]);self.assertLessEqual(20*m[17], m[16])
                self.assertGreater(m[21], 0);self.assertLess(scores[3], 15)
                self.assertEqual((0, 0, 0), self.result(lib, before, after, proof=True))

    def test_unique_old_world_and_safe_remote_loss_are_required(self):
        faults = ('one_survivor', 'collinear_survivors', 'few_dirt', 'lost_gold', 'no_gate', 'old_door',
            'protected', 'item', 'source_goods', 'observed_goods', 'source_state',
            'observed_state', 'source_clear', 'observed_clear', 'source_origin',
            'source_next', 'observed_origin', 'near_loss', 'contradictory_loss')
        for label, lib in self.libraries.items():
            for fault in faults:
                with self.subTest(profile=label, fault=fault):
                    before, after = pair(3)
                    if fault == 'one_survivor':
                        old = next(i for i, k in enumerate(before.tiles) if k == 3 and i%23-11 < 7)
                        x, y = old%23-11, old//23-5;before.tiles[old] = 4;after.tiles[cell(x, y+1)] = 4
                    elif fault == 'collinear_survivors':
                        before.tiles[cell(0, 1)] = 4;after.tiles[cell(0, 2)] = 4
                        before.tiles[cell(-2, 2)] = 3;after.tiles[cell(-2, 3)] = 3
                        self.qualify(lib, before, after, 3)
                    elif fault == 'few_dirt':
                        kept = 0
                        for i, kind in enumerate(before.tiles):
                            if kind == 4:
                                kept += 1
                                if kept > 8:
                                    before.tiles[i] = 0;x, y = i%23-11, i//23-5
                                    if y < 4:after.tiles[cell(x, y+1)] = 0
                    elif fault == 'lost_gold':
                        i = next(i for i, k in enumerate(before.tiles) if k == 2)
                        after.tiles[cell(i%23-11, i//23-4)] = 0
                    elif fault == 'no_gate':after.tiles[next(i for i, k in enumerate(after.tiles) if k == 5)] = 0
                    elif fault == 'old_door':before.tiles[cell(4, 1)] = 5
                    elif fault == 'protected':after.protected_cells[cell(4, 1)] = 1
                    elif fault == 'item':after.tiles[cell(4, 1)] = 6
                    elif fault.endswith('goods'):(before if fault.startswith('source') else after).__setattr__('goods', 1)
                    elif fault.endswith('state'):(before if fault.startswith('source') else after).__setattr__('state', 1)
                    elif fault.endswith('clear'):(before if fault.startswith('source') else after).__setattr__('gold_state', 1)
                    elif fault == 'source_origin':before.tiles[cell(0, 0)] = 4
                    elif fault == 'source_next':before.tiles[cell(0, -1)] = 0
                    elif fault == 'observed_origin':after.tiles[cell(0, 0)] = 0
                    elif fault == 'near_loss':before.tiles[cell(1, 0)] = 3;after.tiles[cell(1, 1)] = 4
                    else:after.tiles[cell(7, 4)] = 1
                    original = bytes(before), bytes(after)
                    self.assertEqual((0, 0, 0), self.result(lib, before, after, proof=True))
                    self.assertEqual(original, (bytes(before), bytes(after)))

    def test_raw_nonunit_wrong_direction_and_known_results_remain_unchanged(self):
        for label, lib in self.libraries.items():
            old_before, old_after = domain_pair(3)
            self.assertEqual((1, 0, -1), self.result(lib, old_before, old_after))
            self.assertEqual((0, 0, 0), self.result(lib, old_before, old_after, proof=True))
            before, after = pair(3)
            for direction in (0, 1, 2, 4, 5):
                with self.subTest(profile=label, direction=direction):
                    self.assertEqual((0, 0, 0), self.result(lib, before, after, direction, True))
            for kind in (1, 2, 3, 4, 5, 6):
                prior = Motion(kind, 7, -6)
                self.assertEqual((kind, 7, -6), self.result(lib, before, after, 3, True, prior))
            for pixels in (0, 8, 18):
                with self.subTest(profile=label, pixels=pixels):
                    moved = bytearray([128]*(W*H))
                    for y in range(H-pixels):
                        for x in range(W):moved[(y+pixels)*W+x] = 128+3*(before.signature[y*W+x]-128)
                    after.signature[:] = moved
                    self.assertEqual((0, 0, 0), self.result(lib, before, after, proof=True))


class SingletonAck122Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stage = tempfile.TemporaryDirectory()
        core = Path(cls.stage.name)
        for p in CONTROLLER_CORE.iterdir():
            if p.suffix in ('.c', '.h'):shutil.copyfile(p, core/p.name)
        shutil.copyfile(CORE/'NG2Navigation.c', core/'NG2Navigation.c')
        old = controller.CORE
        try:
            controller.CORE = core
            controller.NativeControllerTests.setUpClass.__func__(cls)
        finally:controller.CORE = old
        cls.lib.ng2_controller_observe_at.argtypes = [*cls.lib.ng2_controller_observe.argtypes, C.c_uint64]
        cls.lib.ng2_controller_recovery_status.argtypes = [C.c_void_p, C.POINTER(RecoveryStatus)]

    @classmethod
    def tearDownClass(cls):
        controller.NativeControllerTests.tearDownClass.__func__(cls);cls.stage.cleanup()

    frame = ack113.NativeRevealedAck113Tests.frame
    recovery = recovery_fixture.NativeRecoveryTests.recovery
    observe_actual = recovery_fixture.NativeRecoveryTests.observe_actual

    def armed(self):
        before, after = pair(3)
        # Earn the preceding LEFT and lead through public ACK/normal Motion.
        # This procedural prior camera is explicit setup, not a reconstructed
        # missing phone frame or a private Controller state injection.
        before.tiles[cell(1, 0)] = 1;after.tiles[cell(1, 1)] = 1
        prelude = deepcopy(before);prelude.tiles[:] = [0]*230
        for y in range(-5, 5):
            for x in range(-11, 11):prelude.tiles[cell(x, y)] = before.tiles[cell(x+1, y)]
        prelude.tiles[cell(0, 0)] = 1
        signature = bytearray([128]*(W*H))
        for y in range(H):
            signature[y*W:y*W+W-9] = bytes(before.signature[y*W+9:(y+1)*W])
        prelude.signature[:] = signature
        for _ in range(27):
            self.now += 100_000_000;self.observe(self.frame(prelude))
        first = self.next_move();self.assertEqual(1, first.direction);self.ack(first)
        self.now = max(self.now+2, first.target_ns+80_000_002)
        self.observe(self.frame(before))
        self.assertEqual((1, 1, 1, 0), (self.status().inputs, self.status().moves,
            self.status().lead_confirmed, self.status().reason))
        status = self.status()
        self.now = max(self.now, status.next_target_ns-status.lead_ns-100_000_000)
        self.observe(self.frame(before))
        command = self.next_move()
        self.assertEqual((4, 3, 1, 1), (command.kind, command.direction,
            self.status().inputs, self.status().moves))
        return before, after, command

    def test_eighth_qualified_unit_credits_once_after_seven_unknowns_and_old_schedule(self):
        _, after, command = self.armed();deadline = self.motion_wait().deadline_ns
        self.ack(command);schedule = self.recovery().schedule_deadline_ns
        first = max(self.now+2, command.target_ns+80_000_002)
        early = deepcopy(after)
        early.signature[:] = [128]*(W*H)
        for i in range(7):
            self.now = first+i*60_000_000;self.observe(self.frame(early))
            self.assertEqual((i+1, 1, 3), (self.motion_wait().attempts,
                self.status().moves, self.status().input_state))
        self.now = first+548_448_166
        self.assertGreater(self.now, schedule);self.assertLess(self.now, deadline)
        self.observe(self.frame(after))
        self.assertEqual((8, 2, 0, 2), (self.motion_wait().attempts,
            self.status().moves, self.status().input_state, self.status().inputs))
        self.assertEqual((deadline, command.id), (self.motion_wait().deadline_ns,
            self.motion_wait().command_id))
        event = next(e for e in self.events() if e.command.id == command.id)
        self.assertEqual((1, 0, -1, self.number),
            (event.motion, event.dx, event.dy, event.observed_capture_id))
        self.assertEqual(bytes(command), bytes(event.command))
        self.tick();self.assertEqual((2, 1), (self.recovery().mode,
            self.recovery().post_move_reacquisitions))
        self.now += 2;self.observe(self.frame(after))
        self.assertEqual((2, 2), (self.status().moves, self.status().inputs))
        self.assertEqual(2, len([e for e in self.events() if e.command.kind == 4]))

    def test_capture_and_actual_commit_respect_visual_before_equal_and_after(self):
        for end_offset, commit_offset, expected in ((-1, -1, 1), (-1, 0, 1),
                (0, 0, 1), (-1, 1, 0), (1, 1, 0)):
            with self.subTest(end_offset=end_offset, commit_offset=commit_offset):
                self.fresh_engine();_, after, command = self.armed()
                deadline = self.motion_wait().deadline_ns;self.ack(command)
                self.now = deadline+commit_offset
                self.observe_actual(self.frame(after), start=deadline-20_000_000,
                    end=deadline+end_offset, commit=self.now)
                self.assertEqual(1+expected, self.status().moves)
                self.assertEqual(2, self.status().inputs)
                self.assertEqual(deadline, self.motion_wait().deadline_ns)
                if not expected:self.assertEqual(9, self.status().reason)

    def test_missing_ack_wrong_prefix_and_unknown_synth_never_credit_or_resend(self):
        for fault in ('missing_ack', 'wrong_prefix', 'unknown_synth'):
            with self.subTest(fault=fault):
                self.fresh_engine();_, after, command = self.armed()
                self.now = max(self.now, command.not_before_ns)
                if fault == 'missing_ack':
                    self.assertEqual(1, self.lib.ng2_controller_begin(self.engine,
                        command.id, self.now, 1, 0, 1))
                elif fault == 'unknown_synth':
                    self.assertEqual(1, self.lib.ng2_controller_begin(self.engine,
                        command.id, self.now, 1, 0, 1))
                    self.now += 50_000_000
                    self.lib.ng2_controller_complete(self.engine, command.id, self.now, -1)
                    self.prefix = command.id
                else:self.ack(command)
                self.now = max(self.now+2, command.target_ns+80_000_002)
                self.observe(self.frame(after), prefix=self.prefix-1 if fault == 'wrong_prefix' else self.prefix)
                self.assertEqual(1, self.status().moves)
                self.assertNotEqual(4, self.tick()[1].kind)
                self.assertEqual(2, len([e for e in self.events() if e.command.kind == 4]))


for _name in ('setUp', 'observe', 'status', 'events', 'tick', 'ack', 'next_move',
              'motion_wait', 'fresh_engine'):
    setattr(SingletonAck122Tests, _name, getattr(controller.NativeControllerTests, _name))

if __name__ == '__main__':unittest.main()
