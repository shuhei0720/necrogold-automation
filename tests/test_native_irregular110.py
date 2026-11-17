"""Opt-in irregular retries through public C boundaries.

All Scenes, clocks and companion counts are procedural. These tests do not
claim an iPhone enemy blockage, a known post-death menu, or Runtime callback
drain. The explicit before-feature adapter below ignores the new companion
on old C, so Red is the old BLOCKED behavior rather than a missing symbol.
"""
import ctypes as C
from copy import deepcopy
import os
from pathlib import Path
import unittest

from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests.test_native_ring094 import Result


class Observation(C.Structure):
    _fields_ = [('abi_version', C.c_uint32), ('struct_size', C.c_uint32)] + [
        (name, C.c_int32) for name in ('kind', 'glyph_intersection', 'glyph_union',
            'hud_mask', 'empty_hearts', 'matches', 'left', 'top', 'width', 'height')] + [
        (name, C.c_int32 * 3) for name in ('heart_inter', 'heart_union', 'heart_red',
            'heart_dark', 'heart_bright')] + [('enemy_mask', C.c_uint32)] + [
        (name, C.c_int32 * 4) for name in ('enemy_matches', 'enemy_inter', 'enemy_union',
            'enemy_left', 'enemy_top', 'enemy_body_luma', 'enemy_body_saturation',
            'enemy_red_outside', 'enemy_heart_count', 'enemy_width', 'enemy_height')]


class Motion(C.Structure):
    _fields_ = [(name, C.c_int32) for name in ('kind', 'dx', 'dy')]


class Irregular(C.Structure):
    _fields_ = [('abi_version', C.c_uint32), ('struct_size', C.c_uint32)] + [
        (name, C.c_int32) for name in ('enabled', 'kind', 'stage', 'held_reason', 'episodes')] + [
        (name, C.c_uint64) for name in ('episode_id', 'trigger_capture_id', 'before_capture_id',
            'live_baseline_capture_id', 'prefix', 'trigger_ns', 'parent_deadline_ns',
            'proof_capture_id', 'continue_command_id', 'continue_capture_id', 'pause_capture_id',
            'restart_command_id', 'next_floor_capture_id', 'durable_ns', 'continue_intent_ns',
            'continue_outcome_ns', 'restart_intent_ns', 'outcome_ns')]


def none():
    return Observation(abi_version=1, struct_size=C.sizeof(Observation))


def enemy(direction=1):
    value = none()
    value.kind, value.hud_mask = 3, 15
    d = direction - 1
    dx, dy = native.DIRS[direction]
    cx, cy = 448 + 36 * dx, 207 + 36 * dy
    value.enemy_mask = 1 << d
    for name, number in (('enemy_matches', 1), ('enemy_inter', 137), ('enemy_union', 137),
                         ('enemy_left', cx - 7), ('enemy_top', cy - 25),
                         ('enemy_body_luma', 60), ('enemy_body_saturation', 110),
                         ('enemy_red_outside', 0), ('enemy_heart_count', 1),
                         ('enemy_width', 15), ('enemy_height', 13)):
        getattr(value, name)[d] = number
    return value


def death():
    value = none()
    value.kind, value.glyph_intersection, value.glyph_union = 1, 476, 727
    value.hud_mask, value.empty_hearts, value.matches = 15, 3, 1
    value.left, value.top, value.width, value.height = 312, 312, 270, 24
    for i in range(3):
        value.heart_inter[i], value.heart_union[i] = 374, 397
        value.heart_red[i], value.heart_dark[i], value.heart_bright[i] = 244, 220, 24
    return value


def menu(left=357, top=256):
    value = none()
    value.kind, value.glyph_intersection, value.glyph_union = 2, 223, 223
    value.matches, value.left, value.top, value.width, value.height = 1, left, top, 181, 28
    return value


class NativeIrregular110Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        previous = native.CORE
        try:
            native.CORE = Path(os.environ.get('NECRO_TEST110_IRREGULAR_CORE', str(previous)))
            cycle.NativeCycle094Tests.setUpClass()
        finally:
            native.CORE = previous
        cls.lib = cycle.NativeCycle094Tests.lib
        cls.lib.ng2_controller_observe_at.argtypes = [
            *cls.lib.ng2_controller_observe.argtypes, C.c_uint64]
        cls.lib.ng2_motion.argtypes = [C.POINTER(native.Scene), C.POINTER(native.Scene),
            C.c_int32, C.POINTER(Motion)]
        cls.has_irregular = hasattr(cls.lib, 'ng2_controller_enable_irregular')
        if cls.has_irregular:
            cls.lib.ng2_controller_enable_irregular.argtypes = [C.c_void_p]
            cls.lib.ng2_controller_observe_irregular_at.argtypes = [C.c_void_p,
                C.POINTER(native.Scene), C.POINTER(Observation)] + [C.c_uint64] * 4 + [C.c_int32, C.c_uint64]
            cls.lib.ng2_controller_observe_irregular_at.restype = None
            cls.lib.ng2_controller_irregular_status.argtypes = [C.c_void_p, C.POINTER(Irregular)]
            cls.lib.ng2_controller_irregular_ring_settled.argtypes = [C.c_void_p] + [C.c_uint64] * 4 + [C.POINTER(Result), C.c_uint64]
            cls.lib.ng2_controller_irregular_durable.argtypes = [C.c_void_p] + [C.c_uint64] * 4
            cls.lib.ng2_controller_irregular_intent_commit.argtypes = [C.c_void_p] + [C.c_uint64] * 5
            cls.lib.ng2_controller_irregular_outcome_commit.argtypes = [C.c_void_p,
                C.c_uint64, C.c_int32] + [C.c_uint64] * 4
            cls.lib.ng2_controller_irregular_storage_failed.argtypes = [C.c_void_p] + [C.c_uint64] * 2

    @classmethod
    def tearDownClass(cls):
        cycle.NativeCycle094Tests.tearDownClass()

    def setUp(self):
        self.q = cycle.NativeCycle094Tests(methodName='runTest')
        self.q.setUp()
        self.addCleanup(self.q.doCleanups)
        self.h = self.q.h
        if self.has_irregular:
            self.assertEqual(1, self.lib.ng2_controller_enable_irregular(self.h.engine))
        self.h.observe = lambda scene, **kwargs: self.observe(scene, none(), **kwargs)

    def irregular(self):
        value = Irregular()
        if self.has_irregular:
            self.assertEqual(1, self.lib.ng2_controller_irregular_status(self.h.engine, C.byref(value)))
        return value

    def observe(self, scene, observation=None, number=None, prefix=None, stable=1,
                start=None, end=None, commit=None):
        self.h.number += 1
        cid = self.h.number if number is None else number
        first = self.h.now - 2 if start is None else start
        last = self.h.now if end is None else end
        completed = self.h.prefix if prefix is None else prefix
        now = self.h.now if commit is None else commit
        before = self.h.status().accepted_frames
        if self.has_irregular:
            value = observation if observation is not None else none()
            self.lib.ng2_controller_observe_irregular_at(self.h.engine, C.byref(scene),
                C.byref(value), cid, first, last, completed, stable, now)
            accepted = int(self.h.status().accepted_frames > before)
        else:
            # Deliberate baseline adapter: retain old behavior, not a missing
            # symbol, when measuring the before-feature semantic assertion.
            accepted = self.lib.ng2_controller_observe_at(self.h.engine, C.byref(scene),
                cid, first, last, completed, stable, now)
        if accepted:
            self.h._last_fixture_scene = native.Scene.from_buffer_copy(bytes(scene))
        return accepted

    def stalled_first(self):
        terrain, command = self.h.continuous_walk(moves=1, direction=1)
        self.h.ack(command)
        wait = self.h.motion_wait()
        self.h.now = max(self.h.now + 2, command.target_ns + 80_000_002)
        before = self.h.scene(2, 2, terrain, beat=True)
        motion = Motion()
        self.assertEqual(1, self.lib.ng2_motion(C.byref(before), C.byref(before), 1, C.byref(motion)))
        self.assertEqual((2, 0, 0), (motion.kind, motion.dx, motion.dy))
        self.observe(before, enemy(command.direction))
        return terrain, command, wait, self.h.number

    def advance(self, duration=20_000_000):
        self.h.now += duration

    def death_trigger(self, baseline=True):
        if baseline:
            self.advance()
            self.observe(self.h.scene(2, 2, native.textured(), beat=True), none())
        live = self.h.number if baseline else 0
        self.advance()
        scene = self.h.scene(0)
        scene.restart_label = 0
        self.observe(scene, death())
        return self.irregular(), live

    def checkpoint(self):
        state = self.irregular()
        self.assertEqual(2, state.stage)
        self.assertEqual(0, self.h.tick()[0], 'a trigger has no UI authority before checkpoint fsync')
        self.assertEqual(1, self.lib.ng2_controller_irregular_durable(self.h.engine,
            state.episode_id, state.trigger_capture_id, state.prefix, self.h.now))
        self.assertEqual(0, self.lib.ng2_controller_irregular_durable(self.h.engine,
            state.episode_id, state.trigger_capture_id, state.prefix, self.h.now))
        return self.irregular()

    def stalled_checkpoint(self):
        terrain, command, wait, first = self.stalled_first()
        self.advance(native.PERIOD)
        self.observe(self.h.scene(2, 2, terrain, beat=True), enemy(command.direction))
        initial = self.irregular()
        self.assertEqual((1, 2), (initial.kind, initial.stage))
        self.checkpoint()
        return terrain, command, initial

    def intent(self, command):
        state = self.irregular()
        return self.lib.ng2_controller_irregular_intent_commit(self.h.engine,
            state.episode_id, command.id, command.source_capture_id, self.h.prefix, self.h.now)

    def death_continue(self):
        initial, live = self.death_trigger()
        self.assertEqual((1, 2, 2, live),
            (initial.enabled, initial.kind, initial.stage, initial.live_baseline_capture_id))
        self.checkpoint()
        self.advance()
        scene = self.h.scene(0)
        scene.restart_label = 0
        self.observe(scene, death())
        ready, command = self.h.tick()
        self.assertEqual((1, 5, 90, 447), (ready, command.kind, command.x, command.y))
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, command.id,
            self.h.now, 1, 0, 1), 'CONTINUE needs its own durable intent')
        self.assertEqual(1, self.intent(command))
        return initial, command

    def continued_menu(self, commit_continue=True, left=357, top=256):
        initial, command = self.death_continue()
        before = self.h.status()
        self.h.ack(command)
        self.assertEqual((before.moves, before.restarts), (self.h.status().moves, self.h.status().restarts))
        self.assertEqual(command.id, self.h.status().last_completed_id)
        self.advance()
        self.observe(self.h.scene(0), menu(left, top))
        first = self.h.number
        state = self.irregular()
        self.assertEqual((5, command.id, first),
            (state.stage, state.continue_command_id, state.continue_capture_id))
        self.assertEqual(initial.proof_capture_id, state.proof_capture_id,
            'menu observations cannot replace the episode original zero1 proof')
        if commit_continue:
            self.assertEqual(1, self.lib.ng2_controller_irregular_outcome_commit(self.h.engine,
                state.episode_id, 5, command.id, first, self.h.prefix, self.h.now))
        return initial, command, first

    def restart_from_menu(self):
        initial, command, first = self.continued_menu()
        self.advance()
        self.observe(self.h.scene(0), menu())
        ready, restart = self.h.tick()
        self.assertEqual((1, 3, 144, 448), (ready, restart.kind, restart.x, restart.y))
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, restart.id,
            self.h.now, 1, 0, 1), 'RESTART needs its separate durable intent')
        self.assertEqual(1, self.intent(restart))
        self.assertEqual(initial.parent_deadline_ns, self.irregular().parent_deadline_ns)
        return initial, command, restart

    def new_floor(self, restart, changed=True, goods=0):
        self.h.ack(restart)
        self.advance(210_000_000)
        scene = self.h.scene(2, 2, native.textured(), beat=True)
        scene.fingerprint[:] = bytes([80 if changed else 0]) * 48
        scene.goods = goods
        self.observe(scene, none())
        return self.irregular()

    def goods_scene(self, goods):
        tiles = {(0, 0): 'floor', (-1, 0): 'floor', (0, -1): 'gold', (0, 1): 'gold'}
        items = {(-4, -2), (-3, -2), (-2, -2)}
        tiles.update({point: 'item' for point in items})
        terrain = native.textured(tiles)
        terrain.goods = 'partial' if goods == 1 else 'visible'
        terrain.protected = set(items)
        for x, y in items:
            terrain.protected.update((x + dx, y + dy) for dx, dy in native.DIRS.values())
        scene = self.h.scene(2, 2, terrain, beat=True)
        scene.fingerprint[:] = bytes([80]) * 48
        return scene

    def restart_offer(self, goods):
        initial, continued, restart = self.restart_from_menu()
        self.h.ack(restart)
        self.advance(210_000_000)
        scene = self.goods_scene(goods)
        first_start = self.h.now - 2
        self.observe(scene, none())
        first_id, prefix = self.h.number, self.h.prefix
        state = self.irregular()
        self.assertEqual((8, first_id, 0, 0, 0), (state.stage, state.next_floor_capture_id,
            self.q.cycle().pending, self.h.status().restarts, self.q.cycle().completed_shops))
        return state, restart, first_id, first_start, prefix

    def assert_normal_offer(self, first_id, first_start, prefix, goods):
        job = self.q.cycle()
        self.assertEqual((1, first_id, first_start, prefix, int(goods == 1), int(goods == 2)),
            (job.pending, job.capture_id, job.capture_start_ns, job.prefix, job.partial, job.full_seen),
            'durable restart outcome must immediately classify the preserved first merchandise image')
        self.assertLessEqual(job.deadline_ns, first_start + 150_000_000)
        self.assertEqual((1, 0), (self.h.status().restarts, self.h.status().moves))
        return job

    def test_first_positive_enemy_zero_waits_for_original_period_without_finishing_or_resending(self):
        terrain, command, wait, first = self.stalled_first()
        self.assertEqual((3, 1, 0), (self.h.status().input_state,
            self.h.motion_wait().attempts, self.h.status().reason),
            'the first positive enemy/strict zero must preserve this ACK and wait for its independent second proof')
        self.assertEqual(0, self.h.tick()[0])
        self.assertEqual(wait.deadline_ns, self.h.motion_wait().deadline_ns)

    def test_two_period_separated_enemy_zeros_checkpoint_then_pause_durable_restart(self):
        terrain, command, wait, first = self.stalled_first()
        first_start = self.h.now - 2
        self.advance(native.PERIOD)
        self.observe(self.h.scene(2, 2, terrain, beat=True), enemy(command.direction))
        state = self.irregular()
        self.assertEqual((1, 1, 2, 1, self.h.number, command.source_capture_id),
            (state.enabled, state.kind, state.stage, state.episodes,
             state.trigger_capture_id, state.before_capture_id))
        self.assertGreaterEqual(self.h.now - 2, first_start + native.PERIOD)
        self.assertEqual((0, 1, 0), (self.h.status().input_state,
            self.h.status().moves, self.q.cycle().completed_shops))
        self.assertEqual((0, 0), (self.h.status().beat_period_ns, self.h.status().next_target_ns))
        self.assertLessEqual(state.parent_deadline_ns, state.trigger_ns + 4 * native.SECOND)
        self.checkpoint()
        self.advance()
        self.observe(self.h.scene(2, 2, terrain, beat=True), none())
        ready, pause = self.h.tick()
        self.assertEqual((1, 2), (ready, pause.kind))
        self.h.ack(pause)
        self.advance(210_000_000)
        self.observe(self.h.scene(1), none())
        ready, restart = self.h.tick()
        self.assertEqual((1, 3), (ready, restart.kind))
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, restart.id,
            self.h.now, 1, 0, 1))
        self.assertEqual(1, self.intent(restart))
        outcome = self.new_floor(restart)
        self.assertEqual((8, 0), (outcome.stage, self.h.status().restarts))
        self.assertEqual(1, self.lib.ng2_controller_irregular_outcome_commit(self.h.engine,
            outcome.episode_id, 3, restart.id, outcome.next_floor_capture_id, self.h.prefix, self.h.now))
        self.assertEqual((1, 0), (self.h.status().restarts, self.q.cycle().completed_shops))

    def test_second_enemy_proof_requires_original_period_and_unchanged_parent(self):
        terrain, command, wait, first = self.stalled_first()
        first_now = self.h.now
        self.advance(native.PERIOD - 1)
        self.observe(self.h.scene(2, 2, terrain, beat=True), enemy(command.direction))
        self.assertEqual((0, 0, 3), (self.irregular().kind, self.irregular().episode_id,
            self.h.status().input_state))
        # The ordinary matcher independently enforces period/10 between
        # comparisons. A frame 3ns after the early proof is not a third try.
        self.h.now = first_now + native.PERIOD + native.PERIOD // 10 + 2
        self.observe(self.h.scene(2, 2, terrain, beat=True), enemy(command.direction))
        self.assertEqual((1, 2), (self.irregular().kind, self.irregular().stage))
        self.assertEqual(wait.deadline_ns, self.h.motion_wait().deadline_ns)

    def test_missing_wrong_direction_or_malformed_enemy_never_creates_episode(self):
        for fault in ('missing', 'wrong_direction', 'ambiguous', 'coverage', 'body', 'outside', 'width'):
            with self.subTest(fault=fault):
                self.setUp()
                terrain, command = self.h.continuous_walk(moves=1, direction=1)
                self.h.ack(command)
                self.h.now = max(self.h.now + 2, command.target_ns + 80_000_002)
                value = enemy()
                if fault == 'missing': value = none()
                elif fault == 'wrong_direction': value = enemy(2)
                elif fault == 'ambiguous': value.enemy_matches[0] = 2
                elif fault == 'coverage': value.enemy_inter[0] = 126
                elif fault == 'body': value.enemy_body_luma[0] = 47
                elif fault == 'outside': value.enemy_red_outside[0] = 65
                elif fault == 'width': value.enemy_width[0] = 16
                self.observe(self.h.scene(2, 2, terrain, beat=True), value)
                self.assertEqual((0, 0), (self.irregular().kind, self.irregular().episode_id))
                self.assertNotEqual(5, self.h.tick()[1].kind)

    def test_intervening_moved_or_nonzero_motion_never_becomes_stalled(self):
        for amount in (9, 8):
            with self.subTest(signature_pixels=amount):
                self.setUp()
                terrain, command, wait, first = self.stalled_first()
                latest = native.translated(terrain, 1, amount=amount)
                self.advance(native.PERIOD)
                self.observe(self.h.scene(2, 2, latest, beat=True), enemy())
                self.assertEqual((0, 0), (self.irregular().kind, self.irregular().episode_id))
                if amount == 9:
                    self.assertEqual(2, self.h.status().moves)
                self.assertLessEqual(self.h.motion_wait().attempts, 8)

    def test_death_requires_positive_full_prompt_hearts_and_prior_live_baseline(self):
        state, live = self.death_trigger(baseline=False)
        self.assertEqual((9, 8, 0), (state.stage, state.held_reason, state.live_baseline_capture_id))
        self.assertEqual(0, self.h.tick()[0])
        for fault in ('glyph', 'hud', 'empty', 'shape', 'red', 'dark', 'bright', 'box', 'abi'):
            with self.subTest(fault=fault):
                self.setUp()
                self.advance()
                self.observe(self.h.scene(2, 2, native.textured(), beat=True), none())
                value = death()
                if fault == 'glyph': value.glyph_intersection = 460
                elif fault == 'hud': value.hud_mask = 7
                elif fault == 'empty': value.empty_hearts = 2
                elif fault == 'shape': value.heart_inter[1] = 350
                elif fault == 'red': value.heart_red[2] = 224
                elif fault == 'dark': value.heart_dark[0] = 191
                elif fault == 'bright': value.heart_bright[2] = 49
                elif fault == 'box': value.left = 313
                else: value.abi_version = 2
                self.advance()
                scene = self.h.scene(0)
                scene.restart_label = 0
                self.observe(scene, value)
                self.assertEqual((0, 0), (self.irregular().kind, self.irregular().episode_id))
                self.assertNotEqual(5, self.h.tick()[1].kind)

    def test_death_continue_menu_restart_outcome_uses_each_durable_gate_once(self):
        self.assertEqual((288, 176), (C.sizeof(Observation), C.sizeof(Irregular)))
        initial, continued, restart = self.restart_from_menu()
        before = self.h.status()
        outcome = self.new_floor(restart)
        self.assertEqual((8, self.h.number, before.moves, before.restarts, 0),
            (outcome.stage, outcome.next_floor_capture_id, self.h.status().moves,
             self.h.status().restarts, self.q.cycle().completed_shops))
        self.assertEqual(0, self.h.tick()[0])
        self.assertEqual(1, self.lib.ng2_controller_irregular_outcome_commit(self.h.engine,
            outcome.episode_id, 3, restart.id, outcome.next_floor_capture_id, self.h.prefix, self.h.now))
        self.assertEqual((1, 0), (self.h.status().restarts, self.q.cycle().completed_shops))
        self.assertEqual(0, self.lib.ng2_controller_irregular_outcome_commit(self.h.engine,
            outcome.episode_id, 3, restart.id, outcome.next_floor_capture_id, self.h.prefix, self.h.now))
        self.assertEqual(initial.parent_deadline_ns, outcome.parent_deadline_ns)
        self.assertEqual([5, 3], [event.command.kind for event in self.h.events()])
        self.advance()
        next_scene = self.h.scene(2, 2, native.textured(), beat=True)
        next_scene.fingerprint[:] = bytes([80]) * 48
        self.observe(next_scene, none())
        self.assertEqual(0, self.irregular().stage)
        frozen = bytes(self.irregular()), bytes(self.q.cycle()), bytes(self.h.status())
        self.assertEqual(0, self.lib.ng2_controller_irregular_storage_failed(self.h.engine,
            outcome.episode_id, self.h.now), 'completed episode callbacks cannot stop the next normal level')
        self.assertEqual(frozen, (bytes(self.irregular()), bytes(self.q.cycle()), bytes(self.h.status())))

    def test_continue_outcome_is_saved_before_restart_even_after_two_menu_images(self):
        initial, command, first = self.continued_menu(commit_continue=False)
        self.advance()
        self.observe(self.h.scene(0), menu())
        self.assertNotEqual(3, self.h.tick()[1].kind)
        state = self.irregular()
        self.assertEqual(0, self.lib.ng2_controller_irregular_outcome_commit(self.h.engine,
            state.episode_id, 5, command.id, first + 100, self.h.prefix, self.h.now))
        self.assertEqual(1, self.lib.ng2_controller_irregular_outcome_commit(self.h.engine,
            state.episode_id, 5, command.id, first, self.h.prefix, self.h.now))
        ready, restart = self.h.tick()
        self.assertEqual((1, 3), (ready, restart.kind))

    def test_menu_requires_unique_two_current_boxes_and_never_reuses_pause_coordinates(self):
        for fault in ('one', 'far', 'ambiguous', 'glyph', 'prefix', 'unstable', 'death'):
            with self.subTest(fault=fault):
                self.setUp()
                initial, command, first = self.continued_menu()
                if fault != 'one':
                    self.advance()
                    value = menu()
                    kwargs = {}
                    if fault == 'far': value.left += 3
                    elif fault == 'ambiguous': value.matches = 2
                    elif fault == 'glyph': value.glyph_intersection = 210
                    elif fault == 'prefix': kwargs['prefix'] = self.h.prefix + 100
                    elif fault == 'unstable': kwargs['stable'] = 0
                    else: value = death()
                    self.observe(self.h.scene(0), value, **kwargs)
                self.assertNotEqual(3, self.h.tick()[1].kind)
                self.assertEqual(initial.parent_deadline_ns, self.irregular().parent_deadline_ns)
                self.h.now = initial.parent_deadline_ns + 1
                self.h.tick()
                self.assertEqual((9, 1), (self.irregular().stage, self.irregular().held_reason))

    def test_continue_started_unknown_never_resends_or_advances_restart_credit(self):
        initial, command = self.death_continue()
        self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine, command.id, self.h.now, 1, 0, 1))
        self.advance(1)
        self.assertEqual(1, self.lib.ng2_controller_complete(self.h.engine, command.id, self.h.now, -1))
        self.assertEqual((9, 5, 0, 0), (self.irregular().stage, self.irregular().held_reason,
            self.h.status().moves, self.h.status().restarts))
        self.advance()
        scene = self.h.scene(0)
        scene.restart_label = 0
        self.observe(scene, death())
        self.assertEqual(0, self.h.tick()[0])
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, command.id, self.h.now, 1, 0, 1))
        self.assertEqual(1, len(self.h.events()))

    def test_storage_failure_before_ui_or_after_intent_freezes_without_new_input(self):
        for after_intent in (False, True):
            with self.subTest(after_intent=after_intent):
                self.setUp()
                if after_intent:
                    initial, command = self.death_continue()
                else:
                    initial, live = self.death_trigger()
                state = self.irregular()
                self.assertEqual(1, self.lib.ng2_controller_irregular_storage_failed(self.h.engine,
                    state.episode_id, self.h.now))
                self.assertEqual((9, 3), (self.irregular().stage, self.irregular().held_reason))
                self.assertEqual(0, self.h.tick()[0])
                if after_intent:
                    self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, command.id,
                        self.h.now, 1, 0, 1))
                self.assertEqual(0, self.q.cycle().completed_shops)

    def test_pending_ring_result_quiesces_then_candidate_or_failure_holds_before_ui(self):
        for status, outcome, expected in ((0, 0, 2), (0, 3, 2), (0, 1, 9), (0, 2, 9),
                                          (1, 0, 9), (2, 0, 9), (3, 0, 9), (4, 0, 9), (5, 0, 9)):
            with self.subTest(status=status, outcome=outcome):
                self.setUp()
                self.advance()
                self.observe(self.h.scene(2, 2, native.textured(), beat=True), none())
                self.advance()
                goods = self.h.scene(2, 2, native.textured(), beat=True)
                goods.goods = 2
                self.observe(goods, none())
                job = self.q.cycle()
                self.assertEqual(1, job.pending)
                self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
                    job.job_id, job.capture_id, job.prefix, self.h.now))
                job = self.q.cycle()
                self.advance()
                scene = self.h.scene(0)
                scene.restart_label = 0
                self.observe(scene, death())
                state = self.irregular()
                self.assertEqual(1, state.stage)
                self.assertEqual(0, self.lib.ng2_controller_irregular_durable(self.h.engine,
                    state.episode_id, state.trigger_capture_id, state.prefix, self.h.now))
                finished = self.h.now
                if outcome in (1, 2):
                    # The normal worker finished within its original bound;
                    # only its callback delivery is late. A noncancelled
                    # positive remains conservative after either deadline.
                    finished = job.worker_started_ns + 10_000_000
                    if outcome == 1:
                        self.advance(200_000_000)
                    else:
                        self.h.now = state.parent_deadline_ns + 1
                        self.h.tick()
                        self.assertEqual(0, self.h.status().terminal)
                value = Result(abi=1, size=C.sizeof(Result), status=status, outcome=outcome,
                    selected_row=-1, selected_partial=-1, started_ns=job.worker_started_ns,
                    finished_ns=finished)
                self.assertEqual(1, self.lib.ng2_controller_irregular_ring_settled(self.h.engine,
                    state.episode_id, job.job_id, job.capture_id, job.prefix, C.byref(value), self.h.now))
                self.assertEqual(expected, self.irregular().stage)
                if outcome in (1, 2): self.assertEqual(4, self.irregular().held_reason)
                elif status: self.assertEqual(7, self.irregular().held_reason)
                self.assertEqual(0, self.q.cycle().completed_shops)
                self.assertEqual(0, self.h.tick()[0])

    def test_wrong_episode_prefix_source_and_cancel_never_replay_commits(self):
        state, live = self.death_trigger()
        original = bytes(state), bytes(self.h.status())
        for episode, trigger, prefix in ((state.episode_id + 1, state.trigger_capture_id, state.prefix),
                                        (state.episode_id, state.trigger_capture_id + 1, state.prefix),
                                        (state.episode_id, state.trigger_capture_id, state.prefix + 1)):
            self.assertEqual(0, self.lib.ng2_controller_irregular_durable(self.h.engine,
                episode, trigger, prefix, self.h.now))
            self.assertEqual(original, (bytes(self.irregular()), bytes(self.h.status())))
        self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 2)
        self.assertEqual(0, self.lib.ng2_controller_irregular_durable(self.h.engine,
            state.episode_id, state.trigger_capture_id, state.prefix, self.h.now))
        self.assertEqual(0, self.h.tick()[0])
        for outcome in (0, 1):
            with self.subTest(cancelled_pending_outcome=outcome):
                self.setUp()
                self.advance()
                self.observe(self.h.scene(2, 2, native.textured(), beat=True), none())
                self.advance()
                goods = self.h.scene(2, 2, native.textured(), beat=True)
                goods.goods = 2
                self.observe(goods, none())
                job = self.q.cycle()
                self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(self.h.engine,
                    job.job_id, job.capture_id, job.prefix, self.h.now))
                job = self.q.cycle()
                state, unused = self.death_trigger(baseline=False)
                self.assertEqual(1, state.stage)
                self.lib.ng2_controller_cancel(self.h.engine, self.h.now, 2)
                self.assertEqual(1, self.h.status().terminal)
                frozen = bytes(self.irregular()), bytes(self.q.cycle()), bytes(self.h.status())
                self.advance(1)
                result = Result(abi=1, size=C.sizeof(Result), status=0, outcome=outcome,
                    selected_row=-1, selected_partial=-1,
                    started_ns=job.worker_started_ns, finished_ns=self.h.now)
                self.assertEqual(0, self.lib.ng2_controller_irregular_ring_settled(self.h.engine,
                    state.episode_id, job.job_id, job.capture_id, job.prefix, C.byref(result), self.h.now))
                self.assertEqual(frozen, (bytes(self.irregular()), bytes(self.q.cycle()), bytes(self.h.status())),
                    'a cancelled run cannot adopt even a conservative late Ring hint')

    def test_ui_begin_still_checks_front_lock_and_owner(self):
        for front, locked, owner in ((0, 0, 1), (1, 1, 1), (1, 0, 0)):
            with self.subTest(front=front, locked=locked, owner=owner):
                self.setUp()
                initial, command = self.death_continue()
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, command.id,
                    self.h.now, front, locked, owner))
                self.assertEqual((9, 10), (self.irregular().stage, self.irregular().held_reason))
                self.assertEqual(0, self.h.tick()[0])

    def test_restart_requires_changed_live_floor_and_outcome_before_new_shop(self):
        for changed in (False, True):
            with self.subTest(changed=changed):
                self.setUp()
                initial, continued, restart = self.restart_from_menu()
                state = self.new_floor(restart, changed=changed, goods=2)
                self.assertEqual(0, self.q.cycle().pending)
                self.assertEqual(0, self.h.status().restarts)
                if changed:
                    self.assertEqual(8, state.stage)
                    self.assertEqual(1, self.lib.ng2_controller_irregular_outcome_commit(self.h.engine,
                        state.episode_id, 3, restart.id, state.next_floor_capture_id, self.h.prefix, self.h.now))
                    self.assertEqual(1, self.h.status().restarts)
                else:
                    self.assertEqual(7, state.stage)
                    self.h.now = initial.parent_deadline_ns + 1
                    self.h.tick()
                    self.assertEqual((9, 2), (self.irregular().stage, self.irregular().held_reason))

    def test_old_profile_and_late_or_duplicate_opt_in_preserve_existing_authority(self):
        self.assertEqual(0, self.lib.ng2_controller_enable_irregular(self.h.engine))
        self.advance()
        self.observe(self.h.scene(2, 2, native.textured(), beat=True), none())
        self.assertEqual(0, self.lib.ng2_controller_enable_irregular(self.h.engine))
        legacy = self.lib.ng2_controller_create(native.SECOND)
        self.addCleanup(self.lib.ng2_controller_destroy, legacy)
        self.assertEqual(0, self.lib.ng2_controller_enable_irregular(legacy))
        old_cycle = self.lib.ng2_controller_create_cycle(native.SECOND)
        self.addCleanup(self.lib.ng2_controller_destroy, old_cycle)
        normal = self.h.scene(2, 2, native.textured(), beat=True)
        self.lib.ng2_controller_observe_at(old_cycle, C.byref(normal),
            1, self.h.now - 2, self.h.now, 0, 1, self.h.now)
        self.assertEqual(0, self.lib.ng2_controller_enable_irregular(old_cycle))
        old_scene = self.h.scene(0)
        value = death()
        self.lib.ng2_controller_observe_irregular_at(old_cycle, C.byref(old_scene), C.byref(value),
            2, self.h.now + 1, self.h.now + 3, 0, 1, self.h.now + 3)
        command = native.Command()
        self.lib.ng2_controller_tick(old_cycle, self.h.now + 3, 1, 0, 1, C.byref(command))
        self.assertNotEqual(5, command.kind)

    def test_eighth_attempt_and_expired_visual_parent_cannot_create_enemy_retry(self):
        for fault in ('attempts', 'deadline'):
            with self.subTest(fault=fault):
                self.setUp()
                terrain, command = self.h.continuous_walk(moves=1, direction=1)
                self.h.ack(command)
                wait = self.h.motion_wait()
                self.h.now = max(self.h.now + 2, command.target_ns + 80_000_002)
                if fault == 'attempts':
                    uncertain = deepcopy(terrain)
                    uncertain.signature = bytes([80]) * 23296
                    first_now = self.h.now
                    for i in range(7):
                        self.observe(self.h.scene(2, 2, uncertain, beat=True), none())
                        self.advance(native.PERIOD // 10)
                    self.assertEqual(7, self.h.motion_wait().attempts)
                    self.h.now = max(self.h.now, first_now + native.PERIOD + 2)
                else:
                    self.h.now = wait.deadline_ns + 1
                self.observe(self.h.scene(2, 2, terrain, beat=True), enemy())
                self.assertEqual((0, 0), (self.irregular().kind, self.irregular().episode_id))
                self.assertLessEqual(self.h.motion_wait().attempts, 8)
                self.assertNotEqual(5, self.h.tick()[1].kind)

    def test_death_trigger_requires_fresh_stable_prefix_and_no_reserved_or_started_input(self):
        for fault in ('prefix', 'unstable', 'old_id', 'stale', 'reserved', 'started', 'pre_ack'):
            with self.subTest(fault=fault):
                self.setUp()
                if fault in ('reserved', 'started', 'pre_ack'):
                    terrain, command = self.h.continuous_walk(moves=1, direction=1)
                    if fault == 'started':
                        self.h.now = max(self.h.now, command.not_before_ns)
                        self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine,
                            command.id, self.h.now, 1, 0, 1))
                    elif fault == 'pre_ack':
                        self.h.ack(command)
                        ack_end = self.h.now
                else:
                    self.advance()
                    self.observe(self.h.scene(2, 2, native.textured(), beat=True), none())
                self.advance()
                scene = self.h.scene(0)
                scene.restart_label = 0
                kwargs = {}
                if fault == 'prefix': kwargs['prefix'] = self.h.prefix + 100
                elif fault == 'unstable': kwargs['stable'] = 0
                elif fault == 'old_id': kwargs['number'] = self.h.number
                elif fault == 'stale':
                    old_end = self.h.now
                    self.advance(3_000_000_001)
                    kwargs = {'start': old_end - 2, 'end': old_end, 'commit': self.h.now}
                elif fault == 'pre_ack':
                    kwargs = {'start': ack_end - 4, 'end': ack_end - 2, 'commit': self.h.now}
                self.observe(scene, death(), **kwargs)
                self.assertEqual((0, 0), (self.irregular().kind, self.irregular().episode_id))
                self.assertNotEqual(5, self.h.tick()[1].kind)
                if fault == 'reserved':
                    self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine,
                        command.id, max(self.h.now, command.not_before_ns), 1, 0, 1))

    def test_enemy_occluded_destination_is_data_only_while_origin_and_other_masks_stay_fixed(self):
        for fault in ('destination_unknown', 'origin_unknown', 'gold', 'item', 'protection'):
            with self.subTest(fault=fault):
                self.setUp()
                terrain, command, wait, first = self.stalled_first()
                latest = deepcopy(terrain)
                if fault == 'destination_unknown': latest.tiles.pop((-1, 0), None)
                elif fault == 'origin_unknown': latest.tiles.pop((0, 0), None)
                elif fault == 'gold': latest.tiles[(8, 3)] = 'gold'
                elif fault == 'item': latest.tiles[(8, 3)] = 'item'
                else: latest.protected.add((8, 3))
                self.advance(native.PERIOD)
                scene = self.h.scene(2, 2, latest, beat=True)
                if fault == 'origin_unknown': scene.tiles[5 * 23 + 11] = 0
                if fault == 'destination_unknown':
                    before = self.h.scene(2, 2, terrain, beat=True)
                    motion = Motion()
                    self.assertEqual(1, self.lib.ng2_motion(C.byref(before), C.byref(scene), 1, C.byref(motion)))
                    self.assertEqual((2, 0, 0), (motion.kind, motion.dx, motion.dy))
                self.observe(scene, enemy())
                self.assertEqual(1 if fault == 'destination_unknown' else 0, self.irregular().kind)
                self.assertEqual(1, self.h.status().moves, 'enemy evidence never supplies a gameplay MOVE')

    def test_none_full_death_glyph_vetoes_live_baseline_menu_and_changed_floor_without_continue(self):
        for variant, phase in ((v, p) for v in ('full_neutral', 'legacy_iou', 'ambiguous_death')
                               for p in ('idle', 'idle_pause', 'wait_menu', 'wait_restart')):
            with self.subTest(variant=variant, phase=phase):
                self.setUp()
                if phase == 'wait_menu':
                    initial, continued, first = self.continued_menu()
                elif phase == 'wait_restart':
                    initial, continued, restart = self.restart_from_menu()
                    self.h.ack(restart)
                value = death()
                value.kind = value.empty_hearts = 0
                for name in ('heart_inter', 'heart_union', 'heart_red', 'heart_dark', 'heart_bright'):
                    getattr(value, name)[:] = (0, 0, 0)
                if variant == 'legacy_iou':
                    value.matches, value.glyph_intersection, value.glyph_union = 2, 340, 522
                elif variant == 'ambiguous_death':
                    value = death()
                    value.matches = 2
                self.advance(210_000_000)
                scene = self.h.scene(1 if phase in ('wait_menu', 'idle_pause') else 2,
                    2, native.textured(), beat=True)
                scene.fingerprint[:] = bytes([80]) * 48
                self.observe(scene, value)
                self.assertEqual(0, self.h.tick()[0], 'a weak death glyph never grants CONTINUE, PAUSE or RESTART')
                if phase in ('idle', 'idle_pause'):
                    self.assertEqual((0, 0), (self.irregular().episode_id,
                        self.irregular().live_baseline_capture_id))
                elif phase == 'wait_restart':
                    self.assertEqual((7, 0), (self.irregular().stage,
                        self.irregular().next_floor_capture_id))

    def test_malformed_same_capture_companion_cannot_qualify_live_ui_or_restart_outcome(self):
        for phase in ('idle', 'wait_menu', 'pause', 'wait_restart'):
            for fault in ('abi', 'size', 'range', 'intersection'):
                with self.subTest(phase=phase, fault=fault):
                    self.setUp()
                    if phase == 'wait_menu':
                        self.continued_menu()
                    elif phase == 'wait_restart':
                        initial, continued, restart = self.restart_from_menu()
                        self.h.ack(restart)
                    elif phase == 'pause':
                        terrain, command, wait, first = self.stalled_first()
                        self.advance(native.PERIOD)
                        self.observe(self.h.scene(2, 2, terrain, beat=True), enemy())
                        self.checkpoint()
                        self.advance()
                        self.observe(self.h.scene(2, 2, terrain, beat=True), none())
                        ready, pause = self.h.tick()
                        self.assertEqual((1, 2), (ready, pause.kind))
                        self.h.ack(pause)
                    self.advance(210_000_000)
                    scene = self.h.scene(1 if phase == 'pause' else 2, 2,
                        native.textured(), beat=True)
                    scene.fingerprint[:] = bytes([80]) * 48
                    value = none()
                    if fault == 'abi': value.abi_version = 2
                    elif fault == 'size': value.struct_size -= 4
                    elif fault == 'range': value.enemy_mask = 16
                    else: value.heart_inter[0] = value.heart_union[0] = 383
                    self.observe(scene, value)
                    self.assertEqual(0, self.h.tick()[0], 'invalid companion cannot hide the separate death veto')
                    state = self.irregular()
                    if phase == 'idle':
                        self.assertEqual(0, state.live_baseline_capture_id)
                    elif phase == 'wait_restart':
                        self.assertEqual((0, 0), (state.next_floor_capture_id, self.h.status().restarts))

    def test_durable_unreserved_stalled_episode_upgrades_on_fresh_strong_death_without_new_budget(self):
        terrain, old, initial = self.stalled_checkpoint()
        before = self.irregular()
        preserved = tuple(getattr(before, name) for name in ('episode_id', 'episodes',
            'trigger_capture_id', 'trigger_ns', 'parent_deadline_ns', 'before_capture_id',
            'live_baseline_capture_id', 'proof_capture_id', 'durable_ns'))
        counts = self.h.status().inputs, self.h.status().moves, self.h.status().restarts
        self.advance()
        scene = self.h.scene(0)
        scene.restart_label = 0
        self.observe(scene, death())
        upgraded = self.irregular()
        self.assertEqual((2, 4), (upgraded.kind, upgraded.stage),
            'only a durable, still unreserved STALLED pause may adopt the fresh death UI')
        self.assertEqual(preserved, tuple(getattr(upgraded, name) for name in ('episode_id', 'episodes',
            'trigger_capture_id', 'trigger_ns', 'parent_deadline_ns', 'before_capture_id',
            'live_baseline_capture_id', 'proof_capture_id', 'durable_ns')))
        self.assertEqual(counts, (self.h.status().inputs, self.h.status().moves, self.h.status().restarts))
        ready, continued = self.h.tick()
        self.assertEqual((1, 5, self.h.number), (ready, continued.kind, continued.source_capture_id))
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, continued.id,
            self.h.now, 1, 0, 1))
        self.assertEqual(1, self.intent(continued))
        self.h.ack(continued)
        self.assertEqual(5, self.irregular().stage)
        self.advance()
        self.observe(self.h.scene(0), menu())
        first_menu = self.h.number
        self.assertEqual(initial.proof_capture_id, self.irregular().proof_capture_id)
        self.assertEqual(1, self.lib.ng2_controller_irregular_outcome_commit(self.h.engine,
            initial.episode_id, 5, continued.id, first_menu, self.h.prefix, self.h.now))
        self.advance()
        self.observe(self.h.scene(0), menu())
        self.assertEqual(initial.proof_capture_id, self.irregular().proof_capture_id)
        self.assertEqual((1, 3), (lambda value: (value[0], value[1].kind))(self.h.tick()))

    def test_reserved_started_or_ack_waiting_pause_never_upgrades_to_continue(self):
        for phase in ('reserved', 'started', 'ack_wait'):
            with self.subTest(phase=phase):
                self.setUp()
                terrain, old, initial = self.stalled_checkpoint()
                self.advance()
                self.observe(self.h.scene(2, 2, terrain, beat=True), none())
                ready, pause = self.h.tick()
                self.assertEqual((1, 2), (ready, pause.kind))
                if phase == 'started':
                    self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine,
                        pause.id, self.h.now, 1, 0, 1))
                elif phase == 'ack_wait':
                    self.h.ack(pause)
                self.advance()
                scene = self.h.scene(0)
                scene.restart_label = 0
                self.observe(scene, death())
                state = self.irregular()
                self.assertEqual((1, initial.episode_id, initial.parent_deadline_ns),
                    (state.kind, state.episode_id, state.parent_deadline_ns))
                if phase != 'started': self.assertEqual(9, state.stage)
                self.assertNotEqual(5, self.h.tick()[1].kind)
                if phase == 'started':
                    self.advance(1)
                    self.assertEqual(1, self.lib.ng2_controller_complete(self.h.engine,
                        pause.id, self.h.now, 1))
                    self.h.prefix = pause.id
                    self.advance()
                    self.observe(scene, death())
                    self.assertEqual((1, 9), (self.irregular().kind, self.irregular().stage))
                    self.assertNotEqual(5, self.h.tick()[1].kind)

    def test_started_ui_storage_or_parent_expiry_and_late_begin_cannot_revive_after_ack(self):
        for fault in ('storage', 'started_deadline', 'late_begin'):
            with self.subTest(fault=fault):
                self.setUp()
                initial, command = self.death_continue()
                if fault == 'late_begin':
                    self.h.now = command.deadline_ns + 1
                    self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine,
                        command.id, self.h.now, 1, 0, 1))
                    self.assertEqual((9, 2), (self.irregular().stage, self.irregular().held_reason))
                    self.assertEqual(0, self.h.tick()[0])
                    continue
                self.assertEqual(1, self.lib.ng2_controller_begin(self.h.engine,
                    command.id, self.h.now, 1, 0, 1))
                if fault == 'storage':
                    self.assertEqual(1, self.lib.ng2_controller_irregular_storage_failed(self.h.engine,
                        initial.episode_id, self.h.now))
                    held = 3
                else:
                    self.h.now = initial.parent_deadline_ns + 1
                    self.h.tick()
                    held = 2
                self.assertEqual((9, held, 2), (self.irregular().stage,
                    self.irregular().held_reason, self.h.status().input_state))
                self.advance(1)
                self.assertEqual(1, self.lib.ng2_controller_complete(self.h.engine,
                    command.id, self.h.now, 1), 'a real pending callback still reports its known ACK')
                self.h.prefix = command.id
                self.assertEqual((9, held, command.id), (self.irregular().stage,
                    self.irregular().held_reason, self.h.status().last_completed_id),
                    'drain records the ACK but cannot restore UI permission from HELD')
                self.assertEqual((0, 0, 0), (self.h.status().moves,
                    self.h.status().restarts, self.q.cycle().completed_shops))
                self.assertEqual(0, self.h.tick()[0])

    def test_first_restart_full_or_partial_goods_becomes_bound_job_only_after_durable_outcome(self):
        for goods in (2, 1):
            with self.subTest(goods=goods):
                self.setUp()
                state, restart, first_id, first_start, prefix = self.restart_offer(goods)
                self.assertEqual(0, self.h.tick()[0])
                self.assertEqual(1, self.lib.ng2_controller_irregular_outcome_commit(self.h.engine,
                    state.episode_id, 3, restart.id, first_id, prefix, self.h.now))
                self.assert_normal_offer(first_id, first_start, prefix, goods)

    def test_unknown_tail_cannot_replace_restart_floor_or_goods_target_source_before_durable(self):
        for goods, outcome in ((2, 2), (1, 1)):
            with self.subTest(goods=goods, normal_outcome=outcome):
                self.setUp()
                state, restart, first_id, first_start, prefix = self.restart_offer(goods)
                self.advance()
                unknown = self.h.scene(0)
                unknown.restart_label = 0
                self.observe(unknown, none())
                self.assertEqual((8, first_id, 0, 0), (self.irregular().stage,
                    self.irregular().next_floor_capture_id, self.q.cycle().pending, self.h.status().restarts))
                self.assertEqual(1, self.lib.ng2_controller_irregular_outcome_commit(self.h.engine,
                    state.episode_id, 3, restart.id, first_id, prefix, self.h.now),
                    'a later UNKNOWN cannot erase the immutable changed floor being durably committed')
                job = self.assert_normal_offer(first_id, first_start, prefix, goods)
                self.advance()
                self.observe(unknown, none())
                self.assertEqual((job.job_id, first_id, 1), (self.q.cycle().job_id,
                    self.q.cycle().capture_id, self.q.cycle().pending))
                self.assertEqual(0, self.h.tick()[0], 'UNKNOWN supplies no UI, MOVE or normal exploration source')
                self.q.assess(outcome, 0)
                self.assertEqual((outcome, 1, 7, first_id, 1), (self.q.cycle().outcome,
                    self.q.cycle().candidate_latched, self.q.cycle().state,
                    self.q.cycle().capture_id, self.q.cycle().completed_shops))
                self.assertEqual((1, 0), (self.h.status().restarts, self.h.status().moves))
                self.assertNotEqual(3, self.h.tick()[1].kind)

    def test_goods_after_restart_floor_uses_one_first_source_hint_until_outcome_is_durable(self):
        for goods, outcome in ((2, 2), (1, 1)):
            with self.subTest(goods=goods, normal_outcome=outcome):
                self.setUp()
                initial, continued, restart = self.restart_from_menu()
                floor = self.new_floor(restart, goods=0)
                first_floor = floor.next_floor_capture_id
                job_before = self.q.cycle().job_id
                self.assertEqual((8, 0, 0), (floor.stage, self.q.cycle().pending, self.h.status().restarts))
                self.advance()
                first_goods_start = self.h.now - 2
                self.observe(self.goods_scene(goods), none())
                first_goods = self.h.number
                prefix = self.h.prefix
                self.assertEqual((0, job_before, first_goods, first_goods_start, prefix),
                    (self.q.cycle().pending, self.q.cycle().job_id, self.q.cycle().queued_capture_id,
                     self.q.cycle().queued_capture_start_ns, self.q.cycle().queued_prefix),
                    'OUTCOME exposes one immutable merchandise hint without starting a normal worker')
                self.advance()
                self.observe(self.goods_scene(2), none())
                self.advance()
                unknown = self.h.scene(0)
                unknown.restart_label = 0
                self.observe(unknown, none())
                self.assertEqual((8, first_floor, 0, job_before, first_goods, first_goods_start, prefix),
                    (self.irregular().stage, self.irregular().next_floor_capture_id,
                     self.q.cycle().pending, self.q.cycle().job_id, self.q.cycle().queued_capture_id,
                     self.q.cycle().queued_capture_start_ns, self.q.cycle().queued_prefix),
                    'a later FULL or UNKNOWN cannot overwrite the first potential target source')
                self.assertEqual(1, self.lib.ng2_controller_irregular_outcome_commit(self.h.engine,
                    floor.episode_id, 3, restart.id, first_floor, prefix, self.h.now))
                self.assert_normal_offer(first_goods, first_goods_start, prefix, goods)
                self.assertEqual(0, self.h.tick()[0])
                self.q.assess(outcome, 0)
                self.assertEqual((outcome, 1, first_goods), (self.q.cycle().outcome,
                    self.q.cycle().candidate_latched, self.q.cycle().capture_id))
                self.assertEqual((1, 0), (self.h.status().restarts, self.h.status().moves))
                self.assertNotEqual(3, self.h.tick()[1].kind)

    def test_restart_ticket_keeps_qualified_ui_type_and_coordinates_at_intent_and_begin(self):
        for transition in ('menu_to_pause', 'pause_to_menu', 'pause_to_menu_same_coordinates', 'same_custom_menu'):
            for change_before in ('intent', 'begin'):
                with self.subTest(transition=transition, change_before=change_before):
                    self.setUp()
                    left, top = (357, 256) if transition.endswith('same_coordinates') else (230, 110)
                    initial, continued, first = self.continued_menu(left=left, top=top)
                    self.advance()
                    self.observe(self.h.scene(0), menu(left, top))
                    self.assertEqual(6, self.irregular().stage)
                    if transition.startswith('pause_to_menu'):
                        self.advance()
                        self.observe(self.h.scene(1), none())
                    ready, restart = self.h.tick()
                    expected_coordinates = (290, 321) if transition in ('menu_to_pause', 'same_custom_menu') else (144, 448)
                    self.assertEqual((1, 3, *expected_coordinates),
                        (ready, restart.kind, restart.x, restart.y))
                    if change_before == 'begin': self.assertEqual(1, self.intent(restart))
                    self.advance()
                    if transition == 'menu_to_pause':
                        self.observe(self.h.scene(1), none())
                    else:
                        self.observe(self.h.scene(0), menu(left, top))
                    allowed = int(transition == 'same_custom_menu')
                    if change_before == 'intent':
                        self.assertEqual(allowed, self.intent(restart),
                            'durable intent cannot bind old coordinates to another qualified UI type')
                    self.assertEqual(allowed, self.lib.ng2_controller_begin(self.h.engine,
                        restart.id, self.h.now, 1, 0, 1),
                        'a PAUSE/menu type change invalidates the old ticket even at identical coordinates')
                    self.assertEqual(initial.parent_deadline_ns, self.irregular().parent_deadline_ns)
                    self.assertEqual((0, 0, 0), (self.h.status().moves,
                        self.h.status().restarts, self.q.cycle().completed_shops))
                    self.assertEqual(0, self.h.tick()[0])

    def test_next_death_uses_durable_restart_floor_baseline_without_rewriting_previous_episode(self):
        initial, continued, restart = self.restart_from_menu()
        floor = self.new_floor(restart, goods=0)
        first_floor = floor.next_floor_capture_id
        previous_identity = tuple(getattr(initial, name) for name in
            ('live_baseline_capture_id', 'trigger_capture_id', 'trigger_ns', 'parent_deadline_ns'))
        self.advance()
        unknown = self.h.scene(0)
        unknown.restart_label = 0
        self.observe(unknown, none())
        self.assertEqual(1, self.lib.ng2_controller_irregular_outcome_commit(self.h.engine,
            floor.episode_id, 3, restart.id, first_floor, self.h.prefix, self.h.now))
        self.assertEqual(previous_identity, tuple(getattr(self.irregular(), name) for name in
            ('live_baseline_capture_id', 'trigger_capture_id', 'trigger_ns', 'parent_deadline_ns')))
        self.advance()
        self.observe(unknown, death())
        second = self.irregular()
        self.assertEqual((2, 2, initial.episode_id + 1, first_floor, first_floor),
            (second.kind, second.stage, second.episode_id,
             second.live_baseline_capture_id, second.before_capture_id),
            'the next episode must use the durably proven new live floor, not the previous level')
        self.assertEqual((1, 0), (self.h.status().restarts, self.q.cycle().completed_shops))
        self.checkpoint()
        self.advance()
        self.observe(unknown, death())
        ready, continue_second = self.h.tick()
        self.assertEqual((1, 5), (ready, continue_second.kind))
        self.assertEqual(1, self.intent(continue_second))
        self.h.ack(continue_second)
        self.advance()
        self.observe(unknown, menu())
        state = self.irregular()
        self.assertEqual(1, self.lib.ng2_controller_irregular_outcome_commit(self.h.engine,
            second.episode_id, 5, continue_second.id, state.continue_capture_id, self.h.prefix, self.h.now))
        self.advance()
        self.observe(unknown, menu())
        ready, restart_second = self.h.tick()
        self.assertEqual((1, 3), (ready, restart_second.kind))
        self.assertEqual(1, self.intent(restart_second))
        self.h.ack(restart_second)
        self.advance(210_000_000)
        same_floor = self.h.scene(2, 2, native.textured(), beat=True)
        same_floor.fingerprint[:] = bytes([80]) * 48
        self.observe(same_floor, none())
        self.assertEqual((7, 0, 1), (self.irregular().stage,
            self.irregular().next_floor_capture_id, self.h.status().restarts),
            'an unchanged current-level fingerprint cannot earn a second restart credit')
        self.assertEqual(0, self.h.tick()[0])

    def test_restart_initial_sync_epoch_stays_at_first_floor_without_rewinding_current_unknown(self):
        initial, continued, restart = self.restart_from_menu()
        floor = self.new_floor(restart, goods=0)
        first_floor = floor.next_floor_capture_id
        first_end = self.h.status().last_capture_end_ns
        self.advance()
        unknown = self.h.scene(0)
        unknown.restart_label = 0
        self.observe(unknown, none())
        latest = self.h.status()
        current_metadata = (latest.last_capture_id, latest.last_capture_start_ns, latest.last_capture_end_ns)
        self.assertGreater(current_metadata[0], first_floor)
        self.advance(100_000_000)
        self.assertEqual(1, self.lib.ng2_controller_irregular_outcome_commit(self.h.engine,
            floor.episode_id, 3, restart.id, first_floor, self.h.prefix, self.h.now))
        latest = self.h.status()
        self.assertEqual(current_metadata, (latest.last_capture_id,
            latest.last_capture_start_ns, latest.last_capture_end_ns),
            'saved initial epoch metadata cannot replace the current UNKNOWN UI observation')
        self.advance(100_000_000)
        actual_gold = self.h.scene(2, 2, native.textured(), beat=False)
        actual_gold.fingerprint[:] = bytes([80]) * 48
        self.observe(actual_gold, none())
        self.assertEqual((0, 0), (self.h.status().reason, self.h.status().beat_period_ns))
        self.h.now = first_end + 12 * native.SECOND - 20_000_000
        self.observe(actual_gold, none())
        current_id, current_start, current_end = self.h.number, self.h.now - 2, self.h.now
        self.h.now = first_end + 12 * native.SECOND - 1
        self.assertEqual(0, self.h.tick()[0])
        self.assertEqual(0, self.h.status().reason)
        self.h.now = first_end + 12 * native.SECOND
        ready, command = self.h.tick()
        self.assertEqual(8, self.h.status().reason,
            'the unchanged twelve-second initial sync budget starts at first observed floor, not fsync or a later gold frame')
        latest = self.h.status()
        self.assertEqual((current_id, current_start, current_end), (latest.last_capture_id,
            latest.last_capture_start_ns, latest.last_capture_end_ns))
        self.assertNotEqual(4, command.kind)
        self.assertEqual((0, 0), (latest.moves, latest.beat_period_ns))
