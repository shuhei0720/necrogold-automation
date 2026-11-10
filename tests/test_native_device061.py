"""Focused TEST061 regressions using actual C and explicitly synthetic clocks.

The recorded images establish the observed failure; these procedural scenes
exercise its safe initial-ticket boundary without inventing future game frames.
"""
import ctypes as C
from copy import deepcopy
import unittest

from tests import test_native_controller as fixture

CORE = fixture.CORE
MS = 1_000_000


class _Entrance(C.Structure):
    _fields_ = [(name, C.c_int32) for name in ('valid', 'x', 'y', 'direction')]


class _Decision(C.Structure):
    _fields_ = [(name, C.c_int32) for name in
                ('direction', 'reason', 'target_x', 'target_y', 'obstacle')]


class NativeDevice061Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.CORE = CORE
        fixture.NativeControllerTests.setUpClass()
        cls.lib = fixture.NativeControllerTests.lib
        cls.lib.ng2_controller_observe_at.argtypes = [
            C.c_void_p, C.POINTER(fixture.Scene), C.c_uint64, C.c_uint64,
            C.c_uint64, C.c_uint64, C.c_int32, C.c_uint64]
        cls.lib.ng2_choose.argtypes = [
            C.POINTER(fixture.Scene), C.c_int32, C.c_int32,
            C.POINTER(C.c_uint16), C.c_size_t, C.POINTER(_Entrance),
            C.POINTER(_Decision)]

    @classmethod
    def tearDownClass(cls):
        fixture.NativeControllerTests.tearDownClass()

    def setUp(self):
        # Compose helpers rather than inheriting the historical184 methods.
        self.fx = fixture.NativeControllerTests(
            'test_initial_slot_waits_before_publishing_a_far_first_beat')
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)

    def initial(self):
        terrain = fixture.textured({
            **{(x, 0): 'floor' for x in range(-7, 1)},
            (-7, 0): 'stone', (-8, 0): 'door',
            (-8, -1): 'gold', (-8, 1): 'gold',
            (10, -1): 'dirt', (9, 0): 'floor', (-2, 4): 'floor'})
        self.fx.fit(terrain)
        command = self.fx.next_move()
        self.assertEqual(1, command.direction)
        return terrain, command

    def observe_at(self, terrain, commit, *, capture_end=None, stable=1, prefix=None):
        self.fx.now = commit
        frame = self.fx.scene(2, 2, terrain, beat=True)
        end = commit if capture_end is None else capture_end
        # The HUD value belongs to acquisition, independent of the CPU clock.
        frame.beat_remaining = ((5 * fixture.SECOND - (end - 1)) %
                                fixture.PERIOD) / fixture.PERIOD
        self.fx.number += 1
        return self.lib.ng2_controller_observe_at(
            self.fx.engine, C.byref(frame), self.fx.number, end - 2, end,
            self.fx.prefix if prefix is None else prefix, stable, commit)

    def choice(self, terrain):
        scene = self.fx.scene(2, 2, terrain, beat=True)
        visits = (C.c_uint16 * 1089)()
        visits[16 * 33 + 16] = 1
        decision = _Decision()
        self.assertEqual(1, self.lib.ng2_choose(C.byref(scene), 0, 0,
            visits, len(visits), C.byref(_Entrance()), C.byref(decision)))
        return tuple(getattr(decision, name) for name, _ in decision._fields_)

    def assert_same_ticket(self, command, events, wait):
        status = self.fx.status()
        self.assertEqual((0, 1, command.id, 0, 0),
                         (status.reason, status.input_state,
                          status.current_command_id, status.inputs, status.moves),
                         'late irrelevant flicker must retain the issued ticket')
        self.assertEqual(events, b''.join(bytes(e) for e in self.fx.events()))
        self.assertEqual(wait, bytes(self.fx.motion_wait()))
        self.assertEqual(0, self.fx.preparation_epoch(command))

    def test_late_initial_irrelevant_flickers_preserve_ticket_and_reach_ack(self):
        terrain, original = self.initial()
        # A new remote stone still uses the bounded reissue policy. TEST064
        # coalesces only harmless UNKNOWN/FLOOR/DIRT palette changes throughout
        # the published ticket window; it does not admit new blockers.
        terrain = deepcopy(terrain)
        terrain.tiles[(9, 0)] = 'stone'
        del terrain.tiles[(-2, 4)]
        self.observe_at(terrain, original.not_before_ns - 88 * MS)
        ready, command = self.fx.tick()
        self.assertEqual((1, 4), (ready, command.kind))
        self.assertNotEqual(original.id, command.id)
        self.assertEqual(1, self.fx.scene_changes()[-1].replan_count)
        frozen_events = b''.join(bytes(e) for e in self.fx.events())
        frozen_wait = bytes(self.fx.motion_wait())
        for offset, kind in [(-46 * MS, None), (-4 * MS, 'dirt'), (5 * MS, None)]:
            with self.subTest(offset=offset):
                changed = deepcopy(terrain)
                if kind is None:
                    changed.tiles.pop((10, -1), None)
                else:
                    changed.tiles[(10, -1)] = kind
                self.assertEqual(self.choice(terrain), self.choice(changed))
                self.observe_at(changed, command.not_before_ns + offset)
                self.assert_same_ticket(command, frozen_events, frozen_wait)
                self.assertEqual((0, 0), (self.fx.tick()[0], self.fx.status().inputs))
        # Source/before remain immutable; all late observations are comparisons
        # to that source, and a real signed unit movement is still required.
        self.fx.ack(command)
        self.fx.observed_result(command, fixture.translated(terrain, 1))
        self.assertEqual((1, 1, 1),
            (self.fx.status().inputs, self.fx.status().moves,
             self.fx.status().lead_confirmed))

    def test_late_initial_coalescing_window_and_actual_commit_boundaries(self):
        # TEST064 aligns harmless coalescing with the full100ms publication
        # window. Earlier times have no issued authority; publication-negative
        # boundaries remain covered by the public initial-slot tests.
        cases = [(-100 * MS, None, True), (-90 * MS, None, True),
                 (-50 * MS, None, True), (-50 * MS - 1, None, True),
                 (-49 * MS, -60 * MS, True), (10 * MS, None, True)]
        for offset, capture_offset, retained in cases:
            with self.subTest(offset=offset, capture=capture_offset):
                self.fx.fresh_engine()
                terrain, command = self.initial()
                changed = deepcopy(terrain)
                changed.tiles.pop((10, -1))
                before = b''.join(bytes(e) for e in self.fx.events())
                wait = bytes(self.fx.motion_wait())
                self.observe_at(changed, command.not_before_ns + offset,
                    capture_end=None if capture_offset is None else
                        command.not_before_ns + capture_offset)
                if retained:
                    self.assert_same_ticket(command, before, wait)
                else:
                    ready, replacement = self.fx.tick()
                    self.assertEqual((1, 4), (ready, replacement.kind))
                    self.assertNotEqual(command.id, replacement.id)
                    self.assertEqual(1, self.fx.scene_changes()[-1].replan_count)

    def test_late_initial_coalescing_rejects_changed_authority(self):
        cases = ('near', 'protected', 'gold', 'stone', 'door', 'item',
                 'full_choice', 'unknown_motion', 'unstable', 'wrong_prefix')
        for case in cases:
            with self.subTest(case=case):
                self.fx.fresh_engine()
                terrain, command = self.initial()
                changed = deepcopy(terrain)
                changed.tiles.pop((10, -1))
                stable, prefix = 1, self.fx.prefix
                if case == 'near':
                    changed.tiles[(-1, 1)] = 'floor'
                elif case == 'protected':
                    changed.protected.add((-1, 1))
                elif case == 'gold':
                    del changed.tiles[(-8, -1)]
                    changed.gold.remove((-8, -1))
                elif case in ('stone', 'door', 'item'):
                    changed.tiles[(10, -1)] = case
                elif case == 'full_choice':
                    del changed.tiles[(-4, 0)]
                    a, b = self.choice(terrain), self.choice(changed)
                    self.assertEqual(a[0], b[0])
                    self.assertNotEqual(a, b)
                elif case == 'unknown_motion':
                    changed.signature = bytes([40]) * 23296
                elif case == 'unstable':
                    stable = 0
                else:
                    prefix += 1
                self.observe_at(changed, command.not_before_ns - 30 * MS,
                                stable=stable, prefix=prefix)
                if case in ('unstable', 'wrong_prefix'):
                    self.assertEqual(command.id, self.fx.status().current_command_id)
                    self.assertEqual(1, self.fx.status().discarded_frames)
                    self.assertNotEqual(self.fx.number, self.fx.status().last_capture_id)
                else:
                    self.fx.tick()
                    self.assertNotEqual(command.id, self.fx.status().current_command_id,
                        'changed authority must not be coalesced into the old ticket')
                    self.assertEqual(0, self.lib.ng2_controller_begin(
                        self.fx.engine, command.id, command.not_before_ns, 1, 0, 1))
                self.assertEqual((0, 0),
                    (self.fx.status().inputs, self.fx.status().moves))


if __name__ == '__main__':
    unittest.main()
