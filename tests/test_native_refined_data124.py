"""A refined same-direction passage ticket retires into independent DATA.

The cycle/irregular/continuous/initial-RS profile, first normal unit and
FRESH/SAME chain are earned with public calls. Procedural room/signatures,
clocks and future frames model a component boundary, not missing root4 raw
captures or the original opaque caller history. The C suffix only reads
state earned by those public calls.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import random
import shutil
import tempfile
import unittest

from tests import test_native_controller as native
from tests import test_native_irregular110 as irregular
from tests import test_native_passage072 as passage
from tests import test_native_passage_navigation072 as geometry
from tests.test_native_motion075 import Motion
from tests.test_native_cycle094 import Cycle
from tests.test_native_ring094 import Result
from tests.test_native_observation072 import Entrance


READ_ONLY_SUFFIX = r'''
int ng2_refined124_earned(const NG2Controller *p,uint64_t *out,size_t count){
 if(!p||!out||count<8)return 0;
 out[0]=(uint64_t)p->sample_count;out[1]=p->model.period_ns;
 out[2]=p->model_capture_id;out[3]=(uint64_t)p->model.mode;
 out[4]=p->recovery_slot_target;out[5]=p->preparation_epoch;
 out[6]=(uint64_t)p->continuous_count;out[7]=(uint64_t)p->continuous_chain_count;
 return 8;
}
size_t ng2_refined124_samples(const NG2Controller*p,void*out,size_t size){
 if(!p)return 0;
 if(out&&size==sizeof(p->samples))memcpy(out,p->samples,size);
 return sizeof(p->samples);
}
'''


class NativeRefinedData124Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='refined-data124-')
        cls.addClassCleanup(cls.temp.cleanup)
        source = Path(os.environ.get('NECRO124_REFINED_CORE', str(native.CORE)))
        staged = Path(cls.temp.name)/'core'
        staged.mkdir()
        for file in source.iterdir():
            if file.suffix in ('.c', '.h'):
                shutil.copyfile(file, staged/file.name)
        controller = staged/'NG2Controller.c'
        controller.write_bytes(controller.read_bytes()+READ_ONLY_SUFFIX.encode())
        prior = native.CORE
        try:
            native.CORE = staged
            native.NativeControllerTests.setUpClass.__func__(cls)
        finally:
            native.CORE = prior
        cls.lib.ng2_controller_create_cycle.argtypes = [C.c_uint64]
        cls.lib.ng2_controller_create_cycle.restype = C.c_void_p
        cls.lib.ng2_controller_enable_irregular.argtypes = [C.c_void_p]
        cls.lib.ng2_controller_enable_continuous.argtypes = [C.c_void_p, C.c_int32, C.c_uint64]
        cls.lib.ng2_controller_enable_initial_restart.argtypes = [C.c_void_p]
        cls.lib.ng2_controller_observe_irregular_at.argtypes = [C.c_void_p,
            C.POINTER(native.Scene), C.POINTER(irregular.Observation),
            *([C.c_uint64]*4), C.c_int32, C.c_uint64]
        cls.lib.ng2_motion.argtypes = [C.POINTER(native.Scene)]*2 + [C.c_int32, C.POINTER(Motion)]
        cls.lib.ng2_choose_passage.argtypes = [C.POINTER(native.Scene),
            *([C.c_int32]*4), C.POINTER(geometry.Decision)]
        cls.lib.ng2_choose.argtypes = [C.POINTER(native.Scene), C.c_int32, C.c_int32,
            C.POINTER(C.c_uint16), C.c_size_t, C.POINTER(Entrance), C.POINTER(geometry.Decision)]
        cls.lib.ng2_refined124_earned.argtypes = [C.c_void_p, C.POINTER(C.c_uint64), C.c_size_t]
        cls.lib.ng2_refined124_samples.argtypes = [C.c_void_p, C.c_void_p, C.c_size_t]
        cls.lib.ng2_refined124_samples.restype = C.c_size_t
        cls.lib.ng2_controller_cycle_status.argtypes = [C.c_void_p, C.POINTER(Cycle)]
        cls.lib.ng2_controller_cycle_worker_begin.argtypes = [C.c_void_p]+[C.c_uint64]*4
        cls.lib.ng2_controller_cycle_assess.argtypes = [C.c_void_p]+[C.c_uint64]*4+[C.POINTER(Result)]
        cls.lib.ng2_controller_cycle_durable.argtypes = [C.c_void_p]+[C.c_uint64]*4

    tearDownClass = classmethod(native.NativeControllerTests.tearDownClass.__func__)
    scene = native.NativeControllerTests.scene
    status = native.NativeControllerTests.status
    events = native.NativeControllerTests.events
    tick = native.NativeControllerTests.tick
    motion_wait = native.NativeControllerTests.motion_wait
    recovery = native.NativeControllerTests.recovery
    preparation_epoch = native.NativeControllerTests.preparation_epoch
    next_operation = passage.NativePassage072Tests.next_operation

    def setUp(self):
        self.now = native.SECOND+100_000_000
        self.number = self.prefix = 0
        self.engine = self.lib.ng2_controller_create_cycle(native.SECOND)
        self.assertTrue(self.engine)
        self.addCleanup(self.lib.ng2_controller_destroy, self.engine)
        self.assertEqual(1, self.lib.ng2_controller_enable_irregular(self.engine))
        self.assertEqual(1, self.lib.ng2_controller_enable_continuous(self.engine, 0,
            native.SECOND+2880*native.SECOND))
        self.assertEqual(1, self.lib.ng2_controller_enable_initial_restart(self.engine))
        self.assertEqual(1, self.observe(self.scene(state=1)))
        ready, restart = self.tick()
        self.assertEqual((1, 3), (ready, restart.kind), 'the real profile earns initial RS')
        self.ack(restart)
        self.now += 210_000_000

    def frame(self, terrain):
        return self.scene(2, 2 if terrain.gold else 1, terrain, beat=True)

    def observe(self, terrain, *, start=None, end=None, commit=None, prefix=None,
                stable=1, number=None):
        frame = terrain if isinstance(terrain, native.Scene) else self.frame(terrain)
        self.number += 1
        before = self.status().accepted_frames
        value = irregular.none()
        value.hud_mask = 15
        self.lib.ng2_controller_observe_irregular_at(self.engine, C.byref(frame), C.byref(value),
            self.number if number is None else number,
            self.now-2 if start is None else start, self.now if end is None else end,
            self.prefix if prefix is None else prefix, stable,
            self.now if commit is None else commit)
        return int(self.status().accepted_frames > before)

    def ack(self, command):
        self.now = max(self.now, command.not_before_ns)
        self.assertEqual(1, self.lib.ng2_controller_begin(self.engine, command.id, self.now, 1, 0, 1))
        self.now += 275_000_000
        self.assertEqual(1, self.lib.ng2_controller_complete(self.engine, command.id, self.now, 1))
        self.prefix = command.id

    def motion(self, before, after, direction=1):
        a, b, result = self.frame(before), self.frame(after), Motion()
        self.assertEqual(1, self.lib.ng2_motion(C.byref(a), C.byref(b), direction, C.byref(result)))
        return result.kind, result.dx, result.dy

    def choice(self, terrain):
        value, frame = geometry.Decision(), self.frame(terrain)
        self.assertGreater(self.lib.ng2_choose_passage(C.byref(frame),
            self.status().x, self.status().y, -3, -2, C.byref(value)), 0)
        return tuple(getattr(value, field) for field, _ in value._fields_)

    def normal_choice(self, terrain):
        visits = (C.c_uint16*1089)()
        x = y = 0
        visits[16*33+16] = 1
        for event in self.events():
            if event.motion == 1:
                x += event.dx
                y += event.dy
                visits[(y+16)*33+x+16] += 1
        frame, value, entrance = self.frame(terrain), geometry.Decision(), Entrance()
        self.assertEqual(1, self.lib.ng2_choose(C.byref(frame), x, y, visits,
            len(visits), C.byref(entrance), C.byref(value)))
        return tuple(getattr(value, field) for field, _ in value._fields_)

    def earned(self):
        out = (C.c_uint64*8)()
        self.assertEqual(8, self.lib.ng2_refined124_earned(self.engine, out, 8))
        return tuple(out)

    def cycle(self):
        out = Cycle()
        self.lib.ng2_controller_cycle_status(self.engine, C.byref(out))
        return out

    def raw_samples(self):
        count = self.lib.ng2_refined124_samples(self.engine, None, 0)
        out = C.create_string_buffer(count)
        self.assertEqual(count, self.lib.ng2_refined124_samples(self.engine, out, count))
        return bytes(out)

    def refined_chain(self):
        # The outside cell remains UNKNOWN; only the positive inside mouth
        # is a route target. This matches SHOP-03's observed-floor boundary.
        room = passage.passage_room(mouth=(-3, -2), outside=False)
        room.tiles[(0, 2)] = 'dirt'
        self.assertEqual(1, self.observe(room))
        self.assertEqual(1, self.status().restarts)
        for _ in range(27):
            self.now += 100_000_000
            self.assertEqual(1, self.observe(room))
        first = self.next_operation(room)
        self.assertEqual((4, 1), (first.kind, first.direction))
        self.ack(first)
        anchor = native.translated(room, first.direction)
        self.now = max(self.now+60_000_000, first.target_ns+80_000_002)
        self.assertEqual((1, -1, 0), self.motion(room, anchor))
        self.assertEqual(1, self.observe(anchor))
        self.assertEqual((1, 1, -1, 0, 1), (self.status().inputs, self.status().moves,
            self.status().x, self.status().y, self.status().lead_confirmed))
        old = self.next_operation(anchor)
        self.assertEqual((4, 1), (old.kind, old.direction))
        self.old_schedule = self.recovery().schedule_deadline_ns
        self.old_visual = self.motion_wait().deadline_ns
        self.old_period = self.status().beat_period_ns
        noise = random.Random(124124)
        other = bytes(noise.randrange(20, 100) for _ in anchor.signature)
        def blend(alpha):
            return bytes(round(a*(1-alpha)+b*alpha) for a, b in zip(anchor.signature, other))
        refined = deepcopy(anchor)
        self.assertEqual('dirt', refined.tiles[(4, 2)])
        refined.tiles[(4, 2)] = 'stone'
        refined.signature = blend(.15)
        self.assertEqual((2, 0, 0), self.motion(anchor, refined))
        self.now += 2
        self.assertEqual(1, self.observe(refined))
        ready, fresh = self.tick()
        self.assertEqual((1, 4), (ready, fresh.kind))
        self.assertGreater(fresh.id, old.id)
        self.now += 60_000_000
        self.assertEqual(1, self.observe(refined))
        ready, same = self.tick()
        self.assertEqual((1, 4), (ready, same.kind))
        self.assertGreater(same.id, fresh.id)
        self.assertEqual((2, 2), self.earned()[6:8], 'the existing chain budget is earned, not increased')
        for command in (fresh, same):
            self.assertEqual((old.target_ns, old.not_before_ns, old.deadline_ns, old.ordinal, old.direction),
                (command.target_ns, command.not_before_ns, command.deadline_ns, command.ordinal, command.direction))
        current = deepcopy(refined)
        current.signature = blend(.4)
        self.assertEqual(('dirt', 'dirt'), (current.tiles[(4, 0)], current.tiles[(1, 2)]))
        current.tiles[(4, 0)] = 'stone'
        current.tiles[(1, 2)] = 'floor'
        self.assertEqual((0, 0, 0), self.motion(anchor, current), 'the immutable source stays UNKNOWN')
        self.assertEqual((2, 0, 0), self.motion(refined, current), 'only the current source has direct zero')
        self.assertEqual((1, 10, -2, -2, 1), self.choice(refined))
        self.assertEqual(self.choice(refined), self.choice(current))
        return anchor, refined, current, old, fresh, same

    def enter_data(self, *, arm=True):
        _anchor, _refined, current, old, fresh, same = self.refined_chain()
        count, raw, earned = len(self.events()), self.raw_samples(), self.earned()
        credit = self.status().inputs, self.status().moves, self.status().x, self.status().y
        self.now += 2
        self.trigger_ns = self.now
        self.retired_ticket = same
        self.data_W = min(old.source_start_ns+2*self.old_period, self.old_visual)
        self.assertLess(self.now, same.not_before_ns)
        self.assertEqual(1, self.observe(current))
        self.assertEqual((0, 0, 0), (self.status().reason, self.status().input_state,
            self.status().current_command_id),
            'a same-route current zero retires the UNKNOWN original ticket into DATA, without sending')
        self.assertEqual(count, len(self.events()))
        self.assertEqual(credit, (self.status().inputs, self.status().moves, self.status().x, self.status().y))
        retired = self.events()[-1]
        self.assertEqual((same.id, 3, 0, 0),
            (retired.command.id, retired.outcome, retired.begin_ns, retired.motion))
        self.assertEqual(bytes(same), bytes(retired.command))
        self.assertEqual(raw, self.raw_samples(), 'only prior immutable HUD data survive retirement')
        after = self.earned()
        self.assertEqual((earned[0], 0, 0, 0, 0, 0), after[:6], 'old model, slot and epoch are revoked')
        self.assertEqual((2, 0), after[6:8], 'DATA retirement cannot add a reissue')
        if arm:
            self.assertEqual(0, self.tick()[0], 'the trigger image is not an independent DATA pair')
        for command in (old, fresh, same):
            before = bytes(self.status())
            self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, command.id, self.now, 1, 0, 1))
            self.assertEqual(before, bytes(self.status()))
        return current, (old, fresh, same)

    def independent(self, terrain, offset, **options):
        self.now = self.trigger_ns+offset
        return self.observe(terrain, **options)

    def ready_pair(self, current):
        self.assertEqual(1, self.independent(current, 40_000_000))
        self.assertEqual(1, self.earned()[3], 'A earns a new ordinary acquired fit, not old-model tracking')
        self.assertEqual(0, self.tick()[0], 'A alone cannot authorize the new ticket')
        self.assertEqual(1, self.independent(current, 80_000_000))
        self.assertEqual((self.number, 2), self.earned()[2:4], 'B is adopted by the newly earned model')

    def test_same_direction_mixed_material_retires_ticket_before_independent_DATA(self):
        self.enter_data()

    def confirm_next_unit(self, current, old):
        replacement = self.next_operation(current)
        self.assertEqual((4, 1), (replacement.kind, replacement.direction))
        self.assertGreater(replacement.id, old[-1].id)
        self.assertGreater(replacement.target_ns, old[-1].target_ns)
        self.assertGreaterEqual(replacement.not_before_ns, self.now+50_000_000)
        self.assertLessEqual(replacement.not_before_ns, replacement.deadline_ns)
        self.assertLessEqual(replacement.deadline_ns, self.old_schedule)
        self.assertLessEqual(self.recovery().schedule_deadline_ns, self.old_schedule)
        self.assertLessEqual(self.motion_wait().deadline_ns, self.old_visual)
        self.ack(replacement)
        self.assertEqual((2, 1), (self.status().inputs, self.status().moves), 'ACK is not movement')
        moved = native.translated(current, replacement.direction)
        self.now = max(self.now+60_000_000, replacement.target_ns+80_000_002)
        self.assertLess(self.now, self.old_visual)
        self.assertEqual((1, -1, 0), self.motion(current, moved))
        self.assertEqual(1, self.observe(moved))
        self.assertEqual((0, 2, 2, -2, 0), (self.status().reason, self.status().inputs,
            self.status().moves, self.status().x, self.status().y))
        event = self.events()[-1]
        self.assertEqual((replacement.id, 2, 1, -1, 0),
            (event.command.id, event.outcome, event.motion, event.dx, event.dy))
        return moved, replacement

    def test_post_retirement_pair_new_fit_and_next_physical_ticket_confirm_one_normal_unit(self):
        current, old = self.enter_data()
        self.ready_pair(current)
        self.confirm_next_unit(current, old)

    def test_one_level_allowance_is_not_recreated_by_new_source_model_or_real_unit(self):
        current, old = self.enter_data()
        self.ready_pair(current)
        anchor, _replacement = self.confirm_next_unit(current, old)
        ticket = self.next_operation(anchor)
        self.assertEqual(4, ticket.kind)
        rng = random.Random(124125)
        other = bytes(rng.randrange(20, 100) for _ in anchor.signature)
        def blend(alpha):
            return bytes(round(a*(1-alpha)+b*alpha) for a, b in zip(anchor.signature, other))
        refined = deepcopy(anchor)
        self.assertEqual('dirt', refined.tiles[(5, -1)])
        refined.tiles[(5, -1)] = 'stone'
        refined.signature = blend(.15)
        self.assertEqual((2, 0, 0), self.motion(anchor, refined, ticket.direction))
        self.now += 2
        self.observe(refined)
        ready, new = self.tick()
        self.assertEqual((1, 4), (ready, new.kind))
        changed = deepcopy(refined)
        self.assertEqual(('dirt', 'dirt'), (changed.tiles[(5, 1)], changed.tiles[(0, 3)]))
        changed.tiles[(5, 1)] = 'stone'
        changed.tiles[(0, 3)] = 'floor'
        changed.signature = blend(.4)
        self.assertEqual((0, 0, 0), self.motion(anchor, changed, ticket.direction))
        self.assertEqual((2, 0, 0), self.motion(refined, changed, ticket.direction))
        self.assertEqual(self.choice(refined), self.choice(changed))
        self.now += 2
        self.observe(changed)
        self.assertEqual(17, self.status().reason, 'the level already consumed this DATA qualification')
        self.assertEqual((2, 2), (self.status().inputs, self.status().moves))
        self.assertEqual((new.id, 0), (self.events()[-1].command.id, self.events()[-1].begin_ns))

    def test_A_only_old_prefix_unstable_and_pre_retirement_frames_do_not_replace_pair(self):
        current, _old = self.enter_data()
        for options in ({'prefix': 99}, {'stable': 0}, {'number': self.number}):
            with self.subTest(options=options):
                self.assertEqual(0, self.independent(current, 20_000_000, **options))
                self.assertEqual(0, self.tick()[0])
                self.assertEqual(0, self.earned()[1])
        self.assertEqual(1, self.independent(current, 40_000_000))
        self.assertEqual(1, self.earned()[3])
        self.assertEqual(0, self.tick()[0])
        count = len(self.events())
        self.assertEqual(0, self.independent(current, 60_000_000, prefix=99))
        self.assertEqual(count, len(self.events()))
        self.assertEqual(1, self.independent(current, 80_000_000))
        self.assertEqual(self.number, self.earned()[2])
        self.assertEqual(4, self.next_operation(current).kind)

    def test_C_entry_time_cannot_admit_parallel_capture_before_guarded_return_tick(self):
        current, _old = self.enter_data(arm=False)
        raw = self.raw_samples()
        # Both captures start after observeStart but before any actual tick
        # can certify the C-retirement return. They supply no A/B or fit.
        self.assertEqual(1, self.independent(current, 20_000_000))
        self.assertEqual(1, self.independent(current, 40_000_000))
        self.assertEqual(raw, self.raw_samples())
        self.assertEqual((0, 0), self.earned()[1:3])
        self.now = self.trigger_ns+60_000_000
        self.assertEqual(0, self.tick()[0])
        self.assertEqual(1, self.independent(current, 80_000_000))
        self.assertEqual(1, self.earned()[3])
        self.assertEqual(0, self.tick()[0], 'pre-arm frames cannot become the first proof later')
        self.assertEqual(1, self.independent(current, 100_000_000))
        self.assertEqual(self.number, self.earned()[2])
        replacement = self.next_operation(current)
        self.assertEqual(4, replacement.kind)
        self.assertLessEqual(replacement.deadline_ns, self.old_schedule)

    def test_repeated_unknown_cannot_replace_anchor_or_renew_original_bound(self):
        current, _old = self.enter_data()
        noisy = deepcopy(current)
        rng = random.Random(124991)
        noisy.signature = bytes(rng.randrange(20, 100) for _ in current.signature)
        self.assertEqual((0, 0, 0), self.motion(current, noisy))
        raw, credit = self.raw_samples(), (self.status().inputs, self.status().moves)
        for offset in (40_000_000, 80_000_000, 120_000_000):
            self.assertEqual(1, self.independent(noisy, offset))
            self.assertEqual(0, self.tick()[0])
            self.assertEqual(raw, self.raw_samples())
        self.now = min(self.old_schedule+1, self.data_W, self.old_visual)
        self.observe(current)
        self.assertNotEqual(0, self.status().reason)
        ready, command = self.tick()
        self.assertFalse(ready and command.kind == 4)
        self.assertEqual(credit, (self.status().inputs, self.status().moves))

    def test_new_fit_that_misses_fifty_ms_preparation_cannot_extend_original_schedule(self):
        current, old = self.enter_data()
        self.assertEqual(1, self.independent(current, 40_000_000))
        self.now = self.old_schedule-30_000_000
        self.assertLess(self.now, self.data_W)
        self.assertEqual(1, self.observe(current))
        self.assertGreater(self.earned()[1], 0)
        ready, command = self.tick()
        self.assertFalse(ready and command.kind == 4)
        self.assertNotEqual(0, self.status().reason, 'a later physical beat exceeds the frozen schedule')
        self.assertEqual(old[-1].id, self.events()[-1].command.id)
        self.assertEqual((1, 1), (self.status().inputs, self.status().moves))

    def test_new_ticket_owner_foreground_lock_and_unknown_synth_keep_no_resend(self):
        for fault in ('owner', 'foreground', 'locked', 'unknown'):
            with self.subTest(fault=fault):
                if fault != 'owner':
                    self.setUp()
                current, _old = self.enter_data()
                self.ready_pair(current)
                command = self.next_operation(current)
                self.assertEqual(4, command.kind)
                self.now = command.not_before_ns
                if fault == 'unknown':
                    self.assertEqual(1, self.lib.ng2_controller_begin(self.engine, command.id,
                        self.now, 1, 0, 1))
                    self.now += 275_000_000
                    self.assertEqual(1, self.lib.ng2_controller_complete(self.engine, command.id,
                        self.now, -1))
                    self.assertEqual((4, 2, 1),
                        (self.status().input_state, self.status().inputs, self.status().moves))
                else:
                    front, locked, owner = int(fault != 'foreground'), int(fault == 'locked'), int(fault != 'owner')
                    self.assertEqual(0, self.lib.ng2_controller_begin(self.engine, command.id,
                        self.now, front, locked, owner))
                    self.assertEqual((1, 1), (self.status().inputs, self.status().moves))
                count = len(self.events())
                self.now += 2
                self.observe(current)
                ready, next_command = self.tick()
                self.assertFalse(ready and next_command.kind == 4)
                self.assertEqual(count, len(self.events()))

    def test_mixed_witness_cannot_erase_protected_roles_near_floor_or_known_stone(self):
        for fault in ('protected', 'gold', 'item', 'door', 'near_floor', 'stone_loss', 'only_floor'):
            with self.subTest(fault=fault):
                if fault != 'protected':
                    self.setUp()
                anchor, refined, current, _old, _fresh, same = self.refined_chain()
                if fault == 'protected': current.protected.add((8, 3))
                elif fault in ('gold', 'item', 'door'):
                    current.tiles[(8, 3)] = fault
                    if fault == 'gold': current.gold.add((8, 3))
                elif fault == 'near_floor': current.tiles[(0, 0)] = 'dirt'
                elif fault == 'stone_loss': current.tiles[(4, 2)] = 'floor'
                elif fault == 'only_floor': current.tiles[(4, 0)] = refined.tiles[(4, 0)]
                self.now += 2
                self.observe(current)
                self.assertEqual((1, 1), (self.status().inputs, self.status().moves))
                self.assertNotEqual((0, 0, 0), (self.status().reason,
                    self.status().input_state, self.status().current_command_id))
                ready, command = self.tick()
                self.assertFalse(ready and command.kind == 4)
                retired = next(event for event in self.events() if event.command.id == same.id)
                self.assertEqual(0, retired.begin_ns)

    def test_goods_candidate_and_cancel_revoke_DATA_before_any_future_move_or_durability(self):
        for fault in ('candidate', 'cancel'):
            with self.subTest(fault=fault):
                if fault != 'candidate': self.setUp()
                current, _old = self.enter_data()
                if fault == 'cancel':
                    self.now += 1
                    self.lib.ng2_controller_cancel(self.engine, self.now, 2)
                    self.independent(current, 80_000_000)
                else:
                    goods = deepcopy(current)
                    goods.goods = 'visible'
                    goods.tiles[(8, -4)] = 'item'
                    goods.protected.add((8, -4))
                    self.assertEqual(1, self.independent(goods, 40_000_000))
                    source = self.cycle()
                    self.assertEqual(1, source.pending)
                    self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.engine,
                        source.job_id, source.capture_id, source.prefix, self.now))
                    result = Result(abi=1, size=C.sizeof(Result), outcome=2,
                        selected_row=-1, selected_partial=-1, started_ns=self.now, finished_ns=self.now+1)
                    self.now += 1
                    self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.engine,
                        source.job_id, source.capture_id, source.prefix, self.now, C.byref(result)))
                    self.assertEqual(1, self.cycle().candidate_latched)
                    self.assertEqual(0, self.lib.ng2_controller_cycle_durable(self.engine,
                        source.job_id, source.capture_id, source.prefix, self.now))
                ready, command = self.tick()
                self.assertFalse(ready and command.kind in (1, 3, 4))
                self.assertEqual((1, 1), (self.status().inputs, self.status().moves))

    def test_new_input_cannot_credit_unit_when_capture_ends_before_P_but_actual_commit_is_late(self):
        current, _old = self.enter_data()
        self.ready_pair(current)
        command = self.next_operation(current)
        self.assertEqual(4, command.kind)
        self.ack(command)
        moved = native.translated(current, command.direction)
        self.assertEqual((1, -1, 0), self.motion(current, moved))
        self.now = self.old_visual+1
        self.observe(moved, start=self.old_visual-20_000_000,
            end=self.old_visual-10_000_000, commit=self.now)
        self.assertEqual((2, 1), (self.status().inputs, self.status().moves))
        self.assertNotEqual(0, self.status().reason)
        self.assertEqual(0, self.events()[-1].motion,
            'a pre-P image cannot backdate a late actual observation into unit credit')

    def test_new_actual_gold_revokes_clear_DATA_then_independent_gold_proofs_use_normal_shop_route(self):
        for ready in (False, True):
            with self.subTest(ready=ready):
                if ready: self.setUp()
                current, old = self.enter_data()
                if ready: self.ready_pair(current)
                gold = deepcopy(current)
                gold.gold.add((6, 0))
                gold.tiles[(6, 0)] = 'gold'
                self.assertEqual((2, 8, 3, 0, 1), self.normal_choice(gold))
                self.assertEqual((2, 0, 0), self.motion(gold, gold, 2))
                raw = self.raw_samples()
                offset = 100_000_000 if ready else 20_000_000
                self.assertEqual(1, self.independent(gold, offset))
                self.assertEqual((1, 1), (self.status().inputs, self.status().moves))
                self.assertEqual(raw, self.raw_samples(), 'the GOLD trigger is not its independent proof')
                self.assertEqual((0, 0, 0, 0, 0), self.earned()[1:6],
                    'new GOLD revokes the old clear model/slot/proof before normal shop reacquisition')
                self.assertEqual(0, self.tick()[0])
                self.assertEqual(1, self.independent(gold, offset+40_000_000))
                self.assertEqual(1, self.earned()[3])
                self.assertEqual(0, self.tick()[0])
                self.assertEqual(1, self.independent(gold, offset+80_000_000))
                self.assertEqual(self.number, self.earned()[2])
                command = self.next_operation(gold)
                self.assertEqual((4, 2), (command.kind, command.direction))
                self.assertGreater(command.target_ns, old[-1].target_ns)
                self.assertLessEqual(command.deadline_ns, self.old_schedule)
                self.assertLessEqual(self.motion_wait().deadline_ns, self.old_visual)
                self.ack(command)
                self.assertEqual((2, 1), (self.status().inputs, self.status().moves))
                moved = native.translated(gold, command.direction)
                self.now = max(self.now+60_000_000, command.target_ns+80_000_002)
                self.assertEqual((1, 1, 0), self.motion(gold, moved, 2))
                self.observe(moved)
                self.assertEqual((0, 2, 2, 0, 0), (self.status().reason, self.status().inputs,
                    self.status().moves, self.status().x, self.status().y))

    def test_gold_handoff_keeps_normal_adjacent_door_and_dirt_openings_at_zero_steps(self):
        # NG2Core.h keeps DOOR_OPENED=3 and TERRAIN_OPENED=4.
        for obstacle, tile, motion in (('door', 5, 3), ('dirt', 4, 4)):
            with self.subTest(obstacle=obstacle):
                if obstacle != 'door': self.setUp()
                current, old = self.enter_data()
                gold = deepcopy(current)
                for point in ((-1, -1), (-1, 1)):
                    gold.gold.add(point)
                    gold.tiles[point] = 'gold'
                gold.tiles[(-1, 0)] = obstacle
                self.assertEqual((1, 5, -1, 0, tile), self.normal_choice(gold))
                self.assertEqual((2, 0, 0), self.motion(gold, gold, 1))
                self.assertEqual(1, self.independent(gold, 20_000_000))
                self.assertEqual(0, self.tick()[0])
                self.assertEqual(1, self.independent(gold, 60_000_000))
                self.assertEqual(1, self.earned()[3])
                self.assertEqual(0, self.tick()[0])
                self.assertEqual(1, self.independent(gold, 100_000_000))
                command = self.next_operation(gold)
                self.assertEqual((4, 1), (command.kind, command.direction))
                self.assertGreater(command.target_ns, old[-1].target_ns)
                self.assertLessEqual(command.deadline_ns, self.old_schedule)
                self.assertLessEqual(self.motion_wait().deadline_ns, self.old_visual)
                self.ack(command)
                self.assertEqual((2, 1, 0, 0), (self.status().inputs, self.status().moves,
                    self.status().door_changes, self.status().terrain_changes), 'ACK is not opening')
                opened = deepcopy(gold)
                opened.tiles[(-1, 0)] = 'floor'
                self.assertEqual((motion, 0, 0), self.motion(gold, opened, 1))
                self.now = max(self.now+60_000_000, command.target_ns+80_000_002)
                self.observe(opened)
                self.assertEqual((0, 2, 1, -1, 0), (self.status().reason, self.status().inputs,
                    self.status().moves, self.status().x, self.status().y))
                self.assertEqual((int(obstacle == 'door'), int(obstacle == 'dirt')),
                    (self.status().door_changes, self.status().terrain_changes))
                self.assertEqual((motion, 0, 0),
                    (self.events()[-1].motion, self.events()[-1].dx, self.events()[-1].dy))

    def test_gold_handoff_requires_its_own_fixed_pair_and_never_rearms_issued_or_late_authority(self):
        for fault in ('one_frame', 'gold_loss', 'material', 'late_fit', 'issued'):
            with self.subTest(fault=fault):
                if fault != 'one_frame': self.setUp()
                current, _old = self.enter_data()
                gold = deepcopy(current)
                gold.gold.add((6, 0))
                gold.tiles[(6, 0)] = 'gold'
                if fault == 'issued':
                    self.ready_pair(current)
                    ticket = self.next_operation(current)
                    self.assertEqual(4, ticket.kind)
                    self.now += 2
                    self.observe(gold)
                    self.assertNotEqual(0, self.status().reason)
                    self.assertEqual((ticket.id, 3, 0), (self.events()[-1].command.id,
                        self.events()[-1].outcome, self.events()[-1].begin_ns))
                else:
                    self.independent(gold, 20_000_000)
                    self.assertEqual(0, self.tick()[0])
                    proof = deepcopy(gold)
                    if fault == 'gold_loss': proof = current
                    elif fault == 'material': proof.tiles[(6, 2)] = 'floor'
                    self.independent(proof, 60_000_000)
                    self.assertEqual(0, self.tick()[0])
                    if fault == 'late_fit':
                        self.now = self.old_schedule-30_000_000
                        self.observe(gold)
                        ready, command = self.tick()
                        self.assertFalse(ready and command.kind == 4)
                        self.assertNotEqual(0, self.status().reason)
                    else:
                        self.now = min(self.old_schedule+1, self.data_W, self.old_visual)
                        self.observe(gold)
                        self.assertNotEqual(0, self.status().reason)
                self.assertEqual((1, 1), (self.status().inputs, self.status().moves))
                ready, command = self.tick()
                self.assertFalse(ready and command.kind in (1, 3, 4))


if __name__ == '__main__':
    unittest.main()
