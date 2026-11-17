"""TEST110 separates an acknowledged passage MOVE from new-input authority.

The received178->189 pair is a partial camera displacement and remains
UNKNOWN. All later views and device clocks below are procedural contracts,
not a reconstruction of an unsaved phone frame or a device arrival claim.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import shutil
import tempfile
import unittest

from tests import test_native_controller as native
from tests import test_native_passage072 as passage
from tests.test_native_stop099 import stop_detail


PROBE = r'''
/* HOST TEST ONLY: read-only; never part of the shipped native source. */
uint64_t test110_passage_ack_probe(const NG2Controller*p,int field){
    if(!p)return 0;
    switch(field){
        case 0:return (uint64_t)p->passage_wait_kind;
        case 1:return p->passage_wait_deadline;
        case 2:return p->passage_wait_horizon;
        case 3:return p->passage_anchor_id;
        case 4:return p->model_capture_id;
        case 5:return p->proof_capture_id;
        case 6:return p->preparation_epoch;
        case 7:return (uint64_t)ng2_beat_model_valid(&p->model);
        case 8:return (uint64_t)p->sample_count;
        case 9:return sync_deadline(p);
        default:return 0;
    }
}
'''


class NativePassageAck110Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core_temp = tempfile.TemporaryDirectory(prefix='passage-ack110-source-')
        cls.addClassCleanup(cls.core_temp.cleanup)
        core = Path(cls.core_temp.name)
        original = Path(os.environ.get('NECRO_TEST110_ACK_CORE', str(native.CORE)))
        for source in original.iterdir():
            if source.suffix in ('.c', '.h'):
                shutil.copyfile(source, core/source.name)
        controller = core/'NG2Controller.c'
        controller.write_text(controller.read_text()+PROBE)
        old = passage.CORE
        try:
            passage.CORE = core
            passage.NativePassage072Tests.setUpClass.__func__(cls)
        finally:
            passage.CORE = old
        cls.lib.test110_passage_ack_probe.argtypes = [C.c_void_p, C.c_int]
        cls.lib.test110_passage_ack_probe.restype = C.c_uint64
        cls.lib.ng2_controller_observe_at.argtypes = [
            *cls.lib.ng2_controller_observe.argtypes, C.c_uint64]

    tearDownClass = classmethod(passage.NativePassage072Tests.tearDownClass.__func__)
    setUp = passage.NativePassage072Tests.setUp
    scene = passage.NativePassage072Tests.scene
    observe = passage.NativePassage072Tests.observe
    status = passage.NativePassage072Tests.status
    events = passage.NativePassage072Tests.events
    tick = passage.NativePassage072Tests.tick
    ack = passage.NativePassage072Tests.ack
    motion_wait = passage.NativePassage072Tests.motion_wait
    fit_clear = passage.NativePassage072Tests.fit_clear
    next_operation = passage.NativePassage072Tests.next_operation
    next_move = passage.NativePassage072Tests.next_move
    fresh_engine = passage.NativePassage072Tests.fresh_engine
    recovery = passage.NativePassage072Tests.recovery

    def probe(self, field):
        return self.lib.test110_passage_ack_probe(self.engine, field)

    def sent(self):
        terrain = self.fit_clear(passage.passage_room(mouth=(-3, 0)))
        command = self.next_move(terrain)
        self.assertEqual(1, command.direction)
        self.ack(command)
        return terrain, command, self.motion_wait()

    def uncertain(self, terrain, raw_unknown=False):
        source = self.scene(terrain, gold=0)
        source.gold_peak = 129
        if raw_unknown:
            source.signature[:] = bytes([40])*23296
        return source

    def first_after(self, command, scene, advance=0, **kwargs):
        self.now = max(self.now, command.target_ns+80_000_002)+advance
        if isinstance(scene, native.Scene) and scene.beat_valid:
            scene.beat_remaining = ((5*native.SECOND-(self.now-1))%native.PERIOD)/native.PERIOD
        return self.observe(scene, **kwargs)

    def held_after_move(self):
        terrain, command, wait = self.sent()
        latest = native.translated(terrain, command.direction)
        self.assertEqual(1, self.first_after(command, self.uncertain(latest)))
        self.assertEqual((1, 0, 0, 1, 1), (self.status().moves, self.status().reason,
            self.status().input_state, self.status().inputs, self.status().lead_confirmed))
        self.assertEqual(4, self.probe(0), 'uncertain GOLD after real MOVED is a no-input route wait')
        return terrain, latest, command, wait

    def test_ack_gold_unknown_keeps_the_original_visual_budget_then_confirms_a_real_unit(self):
        terrain, command, wait = self.sent()
        self.assertEqual(1, self.first_after(command, self.uncertain(terrain, raw_unknown=True)))
        self.assertEqual((0, 3, 0, 1, 1), (self.status().reason, self.status().input_state,
            self.status().moves, self.status().inputs, self.motion_wait().attempts),
            'a new-input GOLD predicate must not abort an existing acknowledged visual comparison')
        self.assertEqual((wait.command_id, wait.source_capture_id, wait.deadline_ns),
            (self.motion_wait().command_id, self.motion_wait().source_capture_id,
             self.motion_wait().deadline_ns))
        self.assertEqual(0, self.tick()[0])
        self.now += native.PERIOD//10+4
        latest = native.translated(terrain, command.direction)
        self.assertEqual(1, self.observe(latest))
        self.assertEqual((1, 0, 0), (self.status().moves, self.status().reason, self.status().input_state))
        self.assertEqual((1, -1, 0), (self.events()[-1].motion,
            self.events()[-1].dx, self.events()[-1].dy))
        self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, command.id,
            self.now, 1, 0, 1), 'the acknowledged command cannot be resent')

    def test_true_moved_with_uncertain_gold_holds_until_fresh_positive_route_and_new_phase(self):
        _, latest, command, wait = self.held_after_move()
        held = (self.probe(1), self.probe(2), self.probe(3))
        self.assertLessEqual(max(held[:2]), wait.deadline_ns)
        self.assertEqual((0, 0, 0), (self.probe(4), self.probe(5), self.probe(6)))
        self.assertEqual(0, self.probe(7))
        self.assertGreaterEqual(self.probe(8), 4, 'old validated HUD remains data, not phase authority')
        self.now += 50_000_000
        self.observe(self.uncertain(latest))
        self.assertEqual((0, 0, 0), (self.tick()[0], self.probe(4), self.probe(7)))
        self.assertEqual(held, (self.probe(1), self.probe(2), self.probe(3)))
        self.now += 50_000_000
        self.observe(latest)
        proof = self.number
        self.assertEqual(0, self.probe(0))
        self.assertGreaterEqual(self.probe(4), proof)
        following = self.next_move(latest)
        self.assertGreater(following.id, command.id)
        self.assertGreater(following.target_ns, self.now+50_000_000)
        self.assertGreaterEqual(following.source_capture_id, proof)
        self.assertEqual((1, 1, 0), (self.status().inputs, self.status().moves, self.status().restarts))

    def test_unknown_ack_comparisons_keep_eight_limit_and_never_resend(self):
        terrain, command, wait = self.sent()
        first = command.target_ns+80_000_002
        for i in range(8):
            self.now = first+i*(native.PERIOD//10+4)
            if i == 7:
                self.now = max(self.now, first+native.PERIOD+4)
            self.observe(self.uncertain(terrain, raw_unknown=True))
            self.assertEqual(i+1, self.motion_wait().attempts)
            self.assertEqual(wait.deadline_ns, self.motion_wait().deadline_ns)
            self.assertEqual((1, 0, 0), (self.status().inputs, self.status().moves, self.status().restarts))
            self.assertNotEqual(3, self.tick()[1].kind)
        self.assertEqual(10, self.status().reason)
        self.assertEqual(1, len([e for e in self.events() if e.command.kind == 4]))

    def test_post_move_wait_is_bounded_by_the_original_visual_deadline_without_new_frames(self):
        _, _, command, wait = self.held_after_move()
        self.now = min(self.probe(1), self.probe(2))
        self.tick()
        self.assertIn(self.status().reason, (8, 12))
        self.assertEqual((1, 1, 0), (self.status().inputs, self.status().moves, self.status().restarts))
        self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, command.id, self.now, 1, 0, 1))

    def test_existing_visual_deadline_and_cancel_do_not_gain_extra_observations(self):
        for fault in ('deadline', 'cancel'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                terrain, command, wait = self.sent()
                self.now = wait.deadline_ns+1 if fault == 'deadline' else self.now+2
                if fault == 'cancel':
                    self.lib.ng2_controller_cancel(self.engine, self.now, 2)
                self.tick()
                self.assertEqual(9 if fault == 'deadline' else 2, self.status().reason)
                self.assertEqual((0, 0), (self.status().moves, self.status().restarts))
                self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, command.id, self.now, 1, 0, 1))

    def test_unstable_foreign_prefix_and_early_frame_do_not_supply_motion_credit(self):
        terrain, command, wait = self.sent()
        self.now += 10
        before = self.motion_wait().attempts
        self.observe(self.uncertain(terrain, raw_unknown=True), prefix=self.prefix+1)
        self.assertEqual(before, self.motion_wait().attempts)
        self.observe(self.uncertain(terrain, raw_unknown=True), stable=0)
        self.assertEqual(before, self.motion_wait().attempts)
        self.now = command.target_ns+80_000_000
        self.observe(self.uncertain(terrain, raw_unknown=True))
        self.assertEqual((0, 3, before), (self.status().reason,
            self.status().input_state, self.motion_wait().attempts))
        self.assertEqual(1, self.first_after(command, self.uncertain(terrain, raw_unknown=True)))
        self.assertEqual((1, 0, wait.deadline_ns), (self.motion_wait().attempts,
            self.status().moves, self.motion_wait().deadline_ns))

    def test_actual_gold_releases_only_to_the_normal_shop_route(self):
        _, latest, command, wait = self.held_after_move()
        revealed = deepcopy(latest)
        revealed.tiles.update({(-1, -2): 'door', (-2, -2): 'gold', (0, -2): 'gold'})
        revealed.gold = {point for point, kind in revealed.tiles.items() if kind == 'gold'}
        self.now += 50_000_000
        self.observe(revealed)
        self.assertEqual((0, 0, 1, 1), (self.probe(0), self.status().reason,
            self.status().moves, self.status().inputs))
        following = self.next_move(revealed)
        self.assertGreater(following.id, command.id)
        self.assertEqual((0, 1), (self.status().restarts, self.status().lead_confirmed))
        self.assertLessEqual(self.now, wait.deadline_ns)

    def test_rejected_wait_frames_never_replace_the_displacement_anchor(self):
        _, latest, _, _ = self.held_after_move()
        anchor = self.probe(3)
        original_bounds = (self.probe(1), self.probe(2))
        for fault in ('prefix', 'unstable', 'nonzero', 'unknown'):
            self.now += 20_000_000
            if fault == 'prefix':
                self.observe(latest, prefix=self.prefix+1)
            elif fault == 'unstable':
                self.observe(latest, stable=0)
            elif fault == 'nonzero':
                self.observe(native.translated(latest, 1))
            else:
                self.observe(self.uncertain(latest))
            self.assertEqual((4, anchor, *original_bounds),
                (self.probe(0), self.probe(3), self.probe(1), self.probe(2)))
            self.assertEqual((0, 0, 0), (self.tick()[0], self.probe(4), self.probe(6)))

    def test_sent_unknown_input_cannot_enter_the_ack_visual_or_post_move_wait(self):
        terrain = self.fit_clear(passage.passage_room(mouth=(-3, 0)))
        command = self.next_move(terrain)
        self.now = command.not_before_ns
        self.assertEqual(1, self.lib.ng2_controller_begin(self.engine, command.id, self.now, 1, 0, 1))
        self.lib.ng2_controller_complete(self.engine, command.id, self.now+1, -1)
        self.now += 100_000_000
        self.observe(self.uncertain(native.translated(terrain, command.direction)))
        self.assertEqual((4, 11, 0, 0), (self.status().input_state, self.status().reason,
            self.status().moves, self.probe(0)))
        self.assertNotIn(self.tick()[1].kind, (3, 4))

    def test_new_goods_protection_or_nonzero_motion_cannot_release_the_fixed_wait(self):
        for fault in ('protection', 'partial', 'moved'):
            with self.subTest(fault=fault):
                self.fresh_engine()
                _, latest, _, _ = self.held_after_move()
                changed = deepcopy(latest)
                if fault == 'protection':
                    changed.protected.add((4, 2))
                elif fault == 'partial':
                    changed.goods = 'partial'
                else:
                    changed = native.translated(latest, 1)
                self.now += 50_000_000
                self.observe(changed)
                self.assertNotIn(self.tick()[1].kind, (3, 4))
                self.assertEqual((1, 1, 0), (self.status().inputs, self.status().moves, self.status().restarts))
