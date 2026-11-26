"""TEST124 UNKNOWN opening: one remote wall reveal keeps its unsent ID.

Public normal fit/ACK/unit/opening callbacks earn every budget. Procedural
Scenes and future responses are declared components, not missing phone frames.
The C suffix reads earned state and never injects counters/model/history.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from tests import test_native_controller as native
from tests import test_native_recovery as recovery
from tests import test_native_preinput_refresh118 as preinput
from tests.test_native_motion067 import Motion

READ_ONLY_SUFFIX = r'''
int ng2_opened124_earned(const NG2Controller*p,uint64_t*out,size_t count){
 if(!p||!out||count<12)return 0;
 out[0]=(uint64_t)p->continuous_count;out[1]=(uint64_t)p->continuous_chain_count;
 out[2]=p->continuous_ticket.target_ns;out[3]=p->continuous_ticket.not_before_ns;
 out[4]=p->continuous_ticket.deadline_ns;out[5]=p->continuous_ticket.source_start_ns;
 out[6]=p->continuous_ticket.phase_sample_ns;out[7]=p->continuous_motion_deadline;
 out[8]=p->model.period_ns;out[9]=p->preparation_epoch;
 out[10]=p->cycle.job_id;out[11]=p->cycle_retry_used;return 12;
}
int ng2_opened124_old_quiet(const NG2Controller*p,const NG2Scene*scene){
 return p&&scene?quiet_gate_scene(p,scene,NULL):0;
}
'''


class NativeOpenedGoldQuiet124Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='opened-gold124-')
        cls.addClassCleanup(cls.temp.cleanup)
        core = Path(os.environ.get('NECRO124_OPENED_GOLD_CORE', str(native.CORE)))
        staged = Path(cls.temp.name)/'core'; staged.mkdir()
        for path in core.iterdir():
            if path.suffix in ('.c', '.h'):
                shutil.copyfile(path, staged/path.name)
        path = staged/'NG2Controller.c'
        path.write_bytes(path.read_bytes()+READ_ONLY_SUFFIX.encode())
        previous = recovery.CORE
        try:
            recovery.CORE = staged
            recovery.NativeRecoveryTests.setUpClass.__func__(cls)
        finally:
            recovery.CORE = previous
        cls.lib.ng2_controller_create_cycle.argtypes = [C.c_uint64]
        cls.lib.ng2_controller_create_cycle.restype = C.c_void_p
        cls.lib.ng2_controller_observe_at.argtypes = [*cls.lib.ng2_controller_observe.argtypes, C.c_uint64]
        cls.lib.ng2_opened124_earned.argtypes = [C.c_void_p, C.POINTER(C.c_uint64), C.c_size_t]
        cls.lib.ng2_opened124_old_quiet.argtypes = [C.c_void_p, C.POINTER(native.Scene)]
        cls.lib.ng2_controller_scene_details.argtypes = [C.c_void_p, C.POINTER(native.SceneDetail), C.c_size_t]
        cls.lib.ng2_controller_scene_details.restype = C.c_size_t
        cls.lib.ng2_motion.argtypes = [C.POINTER(native.Scene), C.POINTER(native.Scene), C.c_int32, C.POINTER(Motion)]

    tearDownClass = classmethod(recovery.NativeRecoveryTests.tearDownClass.__func__)

    def fresh(self, remote_kind="dirt", neighbor=True):
        self.h = preinput.NativePreinputRefresh118Tests(methodName='runTest')
        self.h.lib = self.lib; self.h.setUp(); self.addCleanup(self.h.doCleanups)
        self.h.engine = self.lib.ng2_controller_create_cycle(native.SECOND)
        self.assertTrue(self.h.engine)
        self.h.addCleanup(self.lib.ng2_controller_destroy, self.h.engine)
        # A fixed observed corridor reaches the same positive bracket. The
        # remote support is present before every input, not added at the end.
        cells = {(x, 0): 'floor' for x in range(-7, 1)}
        cells.update({(-8, 0): 'door', (-8, -1): 'gold', (-8, 1): 'gold',
                      (-9, 0): 'floor', (-10, 0): 'floor',
                      (-9, -3): 'dirt', (-9, -2): 'gold',
                      (-4, -2): 'stone', (5, 1): 'stone'})
        if remote_kind == "unknown":
            cells.pop((-9, -3))
        else:
            cells[(-9, -3)] = remote_kind
        if not neighbor:
            cells.pop((-9, -2))
        self.remote_kind, self.neighbor = remote_kind, neighbor
        world = native.textured(cells)
        original = self.h.continuous_walk
        self.h.continuous_walk = lambda **kwargs: original(terrain=deepcopy(world), **kwargs)

    def earned(self):
        out = (C.c_uint64*12)()
        self.assertEqual(12, self.lib.ng2_opened124_earned(self.h.engine, out, 12))
        return tuple(out)

    def opening(self, exhausted=True, **options):
        self.fresh(**options); h = self.h
        if exhausted:
            terrain, command = h.exhaust_refresh_budget(4)
            self.assertEqual((8, 2), self.earned()[:2], 'all eight replacements must be publicly earned')
        else:
            terrain, command = h.continuous_walk()
        # Complete the remaining observed corridor before opening the gate.
        while self.h.scene(2, 2, terrain).tiles[5*23+10] == 1:
            h.ack(command); terrain = native.translated(terrain, 1)
            h.observed_result(command, terrain); command = h.next_move(terrain)
        self.assertEqual(5, h.scene(2, 2, terrain).tiles[5*23+10])
        h.ack(command); source = deepcopy(terrain); source.tiles[(-1, 0)] = 'floor'
        h.observed_result(command, source)
        self.assertEqual((2, 3, 0, 0), (h.events()[-1].outcome, h.events()[-1].motion,
            h.events()[-1].dx, h.events()[-1].dy), 'the actual opening ACK is zero-unit DOOR_OPENED')
        self.assertEqual((7, 8, 1), (h.status().moves, h.status().inputs, h.status().door_changes))
        ticket = h.next_move(source)
        self.assertEqual((0, 1, ticket.id), (h.status().reason, h.status().input_state, h.status().current_command_id))
        self.assertEqual((8 if exhausted else 0, 0), self.earned()[:2])
        self.assertEqual(0, h.scene(2, 2, source).goods)
        self.reveal_cell = (-2, -3)
        self.assertEqual(self.remote_kind, source.tiles.get(self.reveal_cell, 'unknown'))
        self.assertEqual(self.neighbor, source.tiles.get((-2, -2)) == 'gold')
        return source, ticket

    def reveal(self, source):
        latest = deepcopy(source); latest.tiles[self.reveal_cell] = 'gold'
        latest.gold = {point for point, kind in latest.tiles.items() if kind == 'gold'}
        return latest

    def observe(self, terrain, *, commit=None, **options):
        h = self.h; h.now += 2
        return recovery.NativeRecoveryTests.observe_actual(h, h.scene(2, 2, terrain, beat=True),
            commit=commit, **options)

    def preserved(self, source, ticket):
        h = self.h; latest = self.reveal(source)
        before = (bytes(ticket), bytes(h.motion_wait()), self.earned(), len(h.events()),
                  h.status().inputs, h.status().moves, h.status().door_changes)
        self.assertEqual((2, 0, 0), h.normal_motion(source, latest, 1))
        self.assertEqual(1, self.observe(latest))
        self.assertEqual((0, 0, 1, ticket.id), (h.status().reason, h.status().terminal,
            h.status().input_state, h.status().current_command_id),
            'one supported remote wall reveal must preserve this UNKNOWN opened-floor ID')
        self.assertEqual(before, (bytes(h.events()[-1].command), bytes(h.motion_wait()), self.earned(), len(h.events()),
            h.status().inputs, h.status().moves, h.status().door_changes))
        return latest

    def test_earned_run_eight_keeps_same_UNKNOWN_opening_ticket_and_normal_unit(self):
        source, ticket = self.opening(); latest = self.preserved(source, ticket); h = self.h
        old_moves = h.status().moves
        h.ack(ticket)
        self.assertEqual(old_moves, h.status().moves, 'known ACK is not a unit')
        h.observed_result(ticket, native.translated(latest, 1))
        self.assertEqual((2, 1, -1, 0, old_moves+1), (h.events()[-1].outcome,
            h.events()[-1].motion, h.events()[-1].dx, h.events()[-1].dy, h.status().moves))

    def test_supported_reveal_keeps_original_ID_without_spending_unused_budget(self):
        source, ticket = self.opening(exhausted=False)
        self.preserved(source, ticket)

    def test_accepted_wall_cannot_return_to_source_or_shift_through_any_old_quiet_path(self):
        for fault in ('source_mask_zero', 'old_quiet_palette', 'unknown', 'shifted'):
            with self.subTest(fault=fault):
                source, ticket = self.opening(); latest = self.preserved(source, ticket); h = self.h
                current = deepcopy(source if fault in ('source_mask_zero', 'old_quiet_palette') else latest)
                if fault == 'old_quiet_palette':
                    current.tiles[(6, 3)] = 'floor'
                    old_quiet = h.scene(2, 2, current)
                    self.assertEqual(1, self.lib.ng2_opened124_old_quiet(h.engine, C.byref(old_quiet)),
                        'this reversion really qualifies for the old quiet path without the caller fence')
                elif fault != 'source_mask_zero':
                    current.tiles.pop(self.reveal_cell)
                    if fault == 'shifted': current.tiles[(-3, -3)] = 'gold'
                current.gold = {point for point, kind in current.tiles.items() if kind == 'gold'}
                counts = (h.status().inputs, h.status().moves, self.earned()[:2])
                self.assertEqual(1, self.observe(current))
                self.assertEqual((17, 0, 0), (h.status().reason, h.status().input_state, h.status().current_command_id))
                details = (native.SceneDetail*3)()
                n = self.lib.ng2_controller_scene_details(h.engine, details, 3)
                self.assertGreater(n, 0)
                self.assertEqual(8, details[n-1].validation,
                    'prior accepted GOLD must freeze the ordinary caller even when current equals immutable before')
                self.assertEqual(counts, (h.status().inputs, h.status().moves, self.earned()[:2]))
                self.assertEqual(0, self.lib.ng2_controller_begin(h.engine, ticket.id, ticket.not_before_ns, 1, 0, 1))
                self.assertNotEqual(4, h.tick()[1].kind)

    def test_extra_material_wall_support_and_local_protection_do_not_bypass_run_eight(self):
        faults = ('two_gold', 'old_gold_lost', 'local_gold', 'next', 'protected',
                  'other_palette', 'choice', 'unknown_motion', 'nonzero_motion')
        for fault in faults:
            with self.subTest(fault=fault):
                source, ticket = self.opening(); latest = self.reveal(source); h = self.h
                if fault == 'two_gold': latest.tiles[(-4, -3)] = 'gold'
                elif fault == 'old_gold_lost': latest.tiles[(-2, -2)] = 'dirt'
                elif fault == 'local_gold': latest.tiles[(0, -1)] = 'gold'
                elif fault == 'next': latest.tiles[(-1, 0)] = 'dirt'
                elif fault == 'protected': latest.protected.add(self.reveal_cell)
                elif fault == 'other_palette': latest.tiles[(5, 1)] = 'dirt'
                elif fault == 'choice': latest.tiles[(-1, 0)] = 'stone'
                elif fault == 'unknown_motion': latest.signature = bytes([40])*23296
                elif fault == 'nonzero_motion': latest.signature = native.translated(source, 1).signature
                latest.gold = {point for point, kind in latest.tiles.items() if kind == 'gold'}
                counts = (h.status().inputs, h.status().moves, self.earned()[:2])
                self.observe(latest)
                self.assertNotEqual((1, ticket.id), (h.status().input_state, h.status().current_command_id))
                self.assertEqual(0, self.lib.ng2_controller_begin(h.engine, ticket.id, ticket.not_before_ns, 1, 0, 1))
                self.assertEqual(counts, (h.status().inputs, h.status().moves, self.earned()[:2]))
        for options in ({'neighbor': False}, {'remote_kind': 'unknown'},
                        {'remote_kind': 'floor'}, {'remote_kind': 'stone'}):
            with self.subTest(options=options):
                source, ticket = self.opening(**options); h = self.h
                self.observe(self.reveal(source))
                self.assertNotEqual((1, ticket.id), (h.status().input_state, h.status().current_command_id))
                self.assertEqual(0, self.lib.ng2_controller_begin(h.engine, ticket.id, ticket.not_before_ns, 1, 0, 1))
                self.assertEqual(8, self.earned()[0])

    def test_actual_commit_deadline_equality_and_plus_one_keep_original_window(self):
        for late in (0, 1):
            with self.subTest(late=late):
                source, ticket = self.opening(); latest = self.reveal(source); h = self.h
                h.now = ticket.deadline_ns-1
                scene = h.scene(2, 2, latest, beat=True)
                self.assertEqual(1, recovery.NativeRecoveryTests.observe_actual(h, scene,
                    start=ticket.deadline_ns-2, end=ticket.deadline_ns,
                    commit=ticket.deadline_ns+late))
                self.assertEqual(1-late, int(h.status().input_state == 1 and h.status().current_command_id == ticket.id))
                self.assertEqual(1-late, self.lib.ng2_controller_begin(h.engine, ticket.id,
                    ticket.deadline_ns+late, 1, 0, 1))
                self.assertEqual((8, 0), self.earned()[:2])

    def test_bad_prefix_and_unstable_image_cannot_replace_current_authority(self):
        for fault in ('prefix', 'unstable'):
            with self.subTest(fault=fault):
                source, ticket = self.opening(); h = self.h
                snapshot = (bytes(h.events()[-1].command), self.earned(), len(h.events()))
                self.assertEqual(0, self.observe(self.reveal(source),
                    prefix=h.prefix+int(fault == 'prefix'), stable=int(fault != 'unstable')))
                self.assertEqual(snapshot, (bytes(h.events()[-1].command), self.earned(), len(h.events())))
                self.assertEqual(ticket.id, h.status().current_command_id)

    def test_goods_and_owner_cancel_preempt_the_same_ID(self):
        for fault in ('partial', 'visible', 'cancel', 'owner', 'foreground', 'locked'):
            with self.subTest(fault=fault):
                source, ticket = self.opening(); h = self.h; latest = self.reveal(source)
                if fault in ('partial', 'visible'):
                    latest.goods = fault; self.observe(latest)
                else:
                    self.preserved(source, ticket)
                    if fault == 'cancel': self.lib.ng2_controller_cancel(h.engine, h.now, 2)
                    else:
                        flags = {'front': 1, 'locked': 0, 'owner': 1}
                        flags[{'owner': 'owner', 'foreground': 'front', 'locked': 'locked'}[fault]] = int(fault == 'locked')
                        h.tick(**flags)
                self.assertEqual(0, self.lib.ng2_controller_begin(h.engine, ticket.id, ticket.not_before_ns, 1, 0, 1))
                self.assertEqual((8, 7), (h.status().inputs, h.status().moves))

    def test_started_and_unknown_synth_do_not_gain_quiet_or_resend(self):
        for unknown in (False, True):
            with self.subTest(unknown=unknown):
                source, ticket = self.opening(); h = self.h
                h.now = ticket.not_before_ns
                self.assertEqual(1, self.lib.ng2_controller_begin(h.engine, ticket.id, h.now, 1, 0, 1))
                if unknown:
                    h.now += 1
                    self.assertEqual(1, self.lib.ng2_controller_complete(h.engine, ticket.id, h.now, -1))
                count = len(h.events()); self.observe(self.reveal(source))
                self.assertEqual(count, len(h.events()))
                self.assertEqual(0, self.lib.ng2_controller_begin(h.engine, ticket.id, h.now, 1, 0, 1))
                self.assertNotEqual(4, h.tick()[1].kind)
                self.assertEqual((8, 0), self.earned()[:2])


if __name__ == '__main__':
    unittest.main()
