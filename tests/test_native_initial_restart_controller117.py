"""Explicit initial UI reset over the public C lifecycle; procedural only.

The explicit before adapter omits only enable_initial_restart; a PAUSE then
emits legacy RESUME instead of RESTART, giving semantic assertion Red.
No distinct-world, iPhone precision or speed acceptance is claimed.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import unittest

from tests import test_native_continuous116 as continuous
from tests import test_native_irregular110 as irregular
from tests import test_native_controller as native
from tests.test_native_ring094 import Result

CORE = native.CORE


class NativeInitialRestartController117Tests(unittest.TestCase):
    engine = continuous.NativeContinuous116Tests.engine
    enable = continuous.NativeContinuous116Tests.enable
    state = continuous.NativeContinuous116Tests.state

    @classmethod
    def setUpClass(cls):
        previous = native.CORE
        try:
            native.CORE = Path(os.environ.get("NECRO117_INITIAL_CORE", str(CORE)))
            continuous.NativeContinuous116Tests.setUpClass.__func__(cls)
        finally:
            native.CORE = previous
        cls.has_initial = hasattr(cls.lib, 'ng2_controller_enable_initial_restart')
        cls.before = os.environ.get('NECRO117_INITIAL_BEFORE') == '1'
        if not cls.has_initial and not cls.before:
            raise RuntimeError('Missing initial API is not semantic Red; use explicit before adapter')
        if cls.has_initial:
            cls.lib.ng2_controller_enable_initial_restart.argtypes = [C.c_void_p]

    @classmethod
    def tearDownClass(cls):
        continuous.NativeContinuous116Tests.tearDownClass.__func__(cls)

    def setUp(self):
        self.engine(enabled=True)
        self.assertEqual(1, self.initial_enable())

    def initial_enable(self):
        return self.lib.ng2_controller_enable_initial_restart(self.h.engine) if self.has_initial else 1

    @staticmethod
    def hud(mask=15):
        value = irregular.none()
        value.hud_mask = mask
        return value

    def observe(self, scene, mask=15, **kwargs):
        return self.f.observe(scene, self.hud(mask), **kwargs)

    def floor(self, goods=0, fingerprint=80, candidate=True):
        terrain = native.textured() if candidate else native.textured({
            (0, 0): 'floor', (0, -1): 'floor', (0, -2): 'floor',
            (-4, -2): 'stone', (5, 1): 'stone'})
        scene = self.h.scene(2, 2 if candidate else 1, terrain, beat=True)
        scene.goods = goods
        scene.fingerprint[:] = bytes([fingerprint])*48
        return scene

    def pause_restart(self):
        pause = self.h.scene(state=1)
        pause.fingerprint[:] = bytes([80])*48
        self.assertEqual(1, self.observe(pause))
        self.first_start = self.h.status().last_capture_start_ns
        ready, command = self.h.tick()
        self.assertEqual((1, 3), (ready, command.kind),
            'explicit first restart must never emit legacy RESUME')
        self.h.ack(command)
        self.restart_ack = self.h.now
        return command

    def first_floor(self, scene=None):
        self.h.now = self.restart_ack+210_000_000
        scene = scene or self.floor()
        self.assertEqual(1, self.observe(scene))
        self.first_end = self.h.now
        self.assertEqual(1, self.h.status().restarts,
            'the first qualified post-ACK frame completes only the initial UI operation')
        return scene

    def test_initial_pause_is_restart_only_and_first_floor_enters_normal_mode(self):
        command = self.pause_restart()
        self.first_floor()
        self.assertEqual((1, 0, 0), (self.h.status().restarts,
            self.h.status().moves, self.h.status().inputs))
        self.assertEqual(0, self.q.cycle().completed_shops)
        self.assertEqual(1, self.q.cycle().level_id)
        self.assertEqual(0, self.h.status().reason)
        self.assertEqual((0, 0), (self.state().pending, self.state().ready))
        self.assertEqual(0, self.initial_enable())
        self.assertTrue(all(e.command.kind != 1 for e in self.h.events()))
        self.assertEqual(command.id, self.h.events()[-1].command.id)
        self.assertEqual((16, self.h.number),
            (self.h.events()[-1].reason, self.h.events()[-1].observed_capture_id))

    def test_initial_floor_unknown_uses_pause_then_restart_without_a_ring_absence_job(self):
        self.assertEqual(1, self.observe(self.floor(candidate=False)))
        self.assertEqual((0, 0), (self.q.cycle().job_id, self.q.cycle().pending))
        ready, pause = self.h.tick()
        self.assertEqual((1, 2), (ready, pause.kind))
        self.h.ack(pause)
        self.h.now += 210_000_000
        self.assertEqual(1, self.observe(self.h.scene(state=1)))
        ready, command = self.h.tick()
        self.assertEqual((1, 3), (ready, command.kind))
        self.assertFalse(any(e.command.kind == 1 for e in self.h.events()))

    def test_initial_visible_or_partial_pending_and_positive_result_never_restart(self):
        for goods in (1, 2):
            with self.subTest(goods=goods):
                self.engine(enabled=True)
                self.assertEqual(1, self.initial_enable())
                self.assertEqual(1, self.observe(self.floor(goods=goods)))
                self.assertEqual(1, self.q.cycle().pending)
                ready, command = self.h.tick()
                self.assertFalse(ready and command.kind in (1, 3, 4))
                self.q.assess(2)
                self.assertEqual(1, self.q.cycle().candidate_latched)
                ready, command = self.h.tick()
                self.assertFalse(ready and command.kind in (1, 3, 4))

    def test_initial_goods_nonpositive_verdict_is_a_skip_without_negative_credit(self):
        for goods in (1, 2):
            with self.subTest(goods=goods):
                self.engine(enabled=True)
                self.assertEqual(1, self.initial_enable())
                self.assertEqual(1, self.observe(self.floor(goods=goods)))
                self.q.assess(0)
                self.assertEqual((0, 0, 0), (self.q.cycle().pending,
                    self.q.cycle().outcome, self.q.cycle().completed_shops))
                ready, pause = self.h.tick()
                self.assertEqual((1, 2), (ready, pause.kind))
                self.h.ack(pause)
                self.h.now += 210_000_000
                self.assertEqual(1, self.observe(self.h.scene(state=1)))
                ready, command = self.h.tick()
                self.assertEqual((1, 3), (ready, command.kind))
                self.assertEqual((0, 0), (self.q.cycle().intent_ns, self.q.cycle().durable_ns))

    def test_wrong_job_and_unaggregated_or_late_positive_never_grant_restart(self):
        for fault in ('job', 'hint', 'late'):
            with self.subTest(fault=fault):
                self.engine(enabled=True)
                self.assertEqual(1, self.initial_enable())
                self.assertEqual(1, self.observe(self.floor(goods=2)))
                source = self.q.cycle()
                self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
                    source.job_id, source.capture_id, source.prefix, self.h.now))
                started = self.h.now
                self.h.now += 101_000_000 if fault == 'late' else 1
                result = Result(abi=1, size=C.sizeof(Result), outcome=2 if fault == 'late' else 0,
                    selected_row=-1, selected_partial=-1, started_ns=started, finished_ns=self.h.now)
                if fault == 'hint':
                    result.partial_count = 1
                    result.partial[0].icon_score = result.partial[0].icon_upper_bound = .8
                accepted = self.lib.ng2_controller_cycle_assess(self.h.engine,
                    source.job_id+int(fault == 'job'), source.capture_id, source.prefix,
                    self.h.now, C.byref(result))
                self.assertEqual(int(fault != 'job'), accepted)
                if fault != 'job':
                    self.assertEqual(1, self.q.cycle().candidate_latched)
                ready, command = self.h.tick()
                self.assertFalse(ready and command.kind in (1, 3, 4))

    def test_first_floor_goods_cannot_be_erased_by_a_later_clear_frame(self):
        self.pause_restart()
        first = self.first_floor(self.floor(goods=2))
        source = self.q.cycle()
        self.assertEqual((1, self.h.number, self.h.prefix),
            (source.pending, source.capture_id, source.prefix))
        second = deepcopy(first)
        second.goods = 0
        self.h.now += 20_000_000
        self.observe(second)
        self.assertEqual((1, 0), (self.h.status().restarts, self.h.status().moves))
        ready, command = self.h.tick()
        self.assertFalse(ready and command.kind in (1, 3, 4))
        self.assertEqual((source.job_id, source.capture_id, source.prefix),
            (self.q.cycle().job_id, self.q.cycle().capture_id, self.q.cycle().prefix))
        self.assertEqual(1, self.q.cycle().pending)
        self.q.assess(2)
        self.assertEqual(1, self.q.cycle().candidate_latched)

    def test_early_post_ack_goods_preserves_first_job_and_input_settle(self):
        for goods in (1, 2):
            with self.subTest(goods=goods):
                self.engine(enabled=True)
                self.assertEqual(1, self.initial_enable())
                self.pause_restart()
                # The public source starts exactly35ms after known ACK,
                # matching the observed normal caller boundary.
                self.h.now = self.restart_ack+35_000_002
                self.assertEqual(1, self.observe(self.floor(goods=goods)))
                source = self.q.cycle()
                self.assertEqual((1, 1, self.h.number, self.h.prefix),
                    (self.h.status().restarts, source.pending, source.capture_id, source.prefix))
                self.assertEqual(1, source.level_id)
                self.assertEqual(0, self.h.tick()[0], 'UI completion must not waive the next PAUSE settle')
                self.h.now += 20_000_000
                self.assertEqual(1, self.observe(self.floor(goods=0)))
                self.assertEqual((source.job_id, source.capture_id, source.prefix),
                    (self.q.cycle().job_id, self.q.cycle().capture_id, self.q.cycle().prefix))
                self.q.assess(2)
                self.assertEqual(1, self.q.cycle().candidate_latched)
                self.assertEqual(0, self.h.tick()[0])
                self.h.now = self.restart_ack+210_000_002
                self.assertEqual(1, self.observe(self.floor(goods=goods)))
                ready, pause = self.h.tick()
                self.assertEqual((1, 2), (ready, pause.kind))
                self.assertEqual(1, self.h.status().restarts)

    def test_initial_ui_completion_does_not_claim_old_fingerprint_change(self):
        for fingerprint in (80, 255):
            with self.subTest(fingerprint=fingerprint):
                self.engine(enabled=True)
                self.assertEqual(1, self.initial_enable())
                self.pause_restart()
                self.first_floor(self.floor(fingerprint=fingerprint))
                self.assertEqual(1, self.q.cycle().level_id)
                self.assertEqual((0, 0), (self.state().pending, self.state().ready))

    def test_fixed_first_source_parent_is_not_renewed_by_fresh_views(self):
        self.pause_restart()
        floor = self.floor()
        for now in (self.first_start+2_000_000_000, self.first_start+2_900_000_000):
            self.h.now = now
            # Wrong HUD is neither UI completion nor a new parent.
            self.observe(deepcopy(floor), mask=7)
        self.h.now = self.first_start+3_000_000_000
        self.observe(deepcopy(floor))
        ready, command = self.h.tick()
        self.assertFalse(ready and command.kind in (1, 3, 4))
        self.assertEqual(0, self.h.status().restarts)

    def test_wrong_prefix_or_missing_hud_does_not_complete_initial_ui(self):
        for fault in ('prefix', 'hud', 'pre_ack_start'):
            with self.subTest(fault=fault):
                self.engine(enabled=True)
                self.assertEqual(1, self.initial_enable())
                self.pause_restart()
                self.h.now = self.restart_ack+210_000_000
                second = self.floor()
                self.observe(second, mask=7 if fault == 'hud' else 15,
                    prefix=0 if fault == 'prefix' else self.h.prefix,
                    start=self.restart_ack-1 if fault == 'pre_ack_start' else None)
                self.assertEqual((0, 0), (self.h.status().restarts, self.h.status().moves))

    def test_unknown_synth_never_reissues_initial_restart(self):
        self.assertEqual(1, self.observe(self.h.scene(state=1)))
        ready, command = self.h.tick()
        self.assertEqual((1, 3), (ready, command.kind))
        self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine, command.id,
            self.h.now, 1, 0, 1))
        self.h.now += 1
        self.assertEqual(1, self.lib.ng2_controller_complete(self.h.engine, command.id, self.h.now, -1))
        self.assertEqual((1, 4, 11), (self.h.status().terminal,
            self.h.status().input_state, self.h.status().reason))
        self.assertEqual(0, self.h.tick()[0])
        self.assertEqual(1, len(self.h.events()))

    def test_live_menu_and_original_parent_are_rechecked_before_begin(self):
        for fault in ('label', 'pre_ack_floor', 'goods_partial', 'goods_full', 'first_parent'):
            with self.subTest(fault=fault):
                self.engine(enabled=True)
                self.assertEqual(1, self.initial_enable())
                scene = self.h.scene(state=1)
                scene.restart_label = int(fault != 'first_parent')
                self.assertEqual(1, self.observe(scene))
                first_start = self.h.status().last_capture_start_ns
                if fault == 'first_parent':
                    self.assertEqual(0, self.h.tick()[0])
                    self.h.now = first_start+2_800_000_000
                    self.assertEqual(1, self.observe(self.h.scene(state=1)))
                ready, command = self.h.tick()
                self.assertEqual((1, 3), (ready, command.kind))
                if fault == 'first_parent':
                    self.assertLessEqual(command.deadline_ns, first_start+2_950_000_000)
                    self.h.now = first_start+3_000_000_000
                else:
                    self.h.now += 1
                    changed = self.h.scene(state=1) if fault == 'label' else self.floor(
                        goods=1 if fault == 'goods_partial' else 2 if fault == 'goods_full' else 0)
                    changed.restart_label = 0
                    self.assertEqual(1, self.observe(changed))
                    if fault in ('goods_partial', 'goods_full'):
                        self.assertEqual((1, self.h.number, self.h.prefix),
                            (self.q.cycle().pending, self.q.cycle().capture_id, self.q.cycle().prefix))
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine,
                    command.id, self.h.now, 1, 0, 1))
                self.assertEqual((0, 0), (self.h.status().restarts, self.h.status().inputs))
                self.assertEqual(3, self.h.events()[-1].outcome)

    def test_default_false_still_resumes_and_continuous_successor_rejects_optin(self):
        self.engine(enabled=True)
        self.assertEqual(1, self.observe(self.h.scene(state=1)))
        self.assertEqual(0, self.initial_enable())
        ready, command = self.h.tick()
        self.assertEqual((1, 1), (ready, command.kind))
        self.engine(enabled=True, successor=True)
        self.assertEqual(0, self.initial_enable())
