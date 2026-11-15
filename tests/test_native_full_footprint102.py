"""Actual one-cell framing footprint, with exact Perception protection masks.

Procedural source254-like geometry establishes C transitions; future frames
are synthetic and do not claim physical arrival or unknown item accuracy.
"""
from copy import deepcopy
import unittest

from tests import test_native_controller as native
from tests import test_native_full_framing101 as prior


class NativeFullFootprint102Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        prior.NativeFullFraming101Tests.setUpClass()
        cls.lib = prior.NativeFullFraming101Tests.lib

    @classmethod
    def tearDownClass(cls):
        prior.NativeFullFraming101Tests.tearDownClass()

    def setUp(self):
        self.p = prior.NativeFullFraming101Tests(methodName='runTest')
        self.p.setUp()
        self.addCleanup(self.p.doCleanups)
        self.p.full_source = self.source
        self.p.result = self.result

    @staticmethod
    def source():
        value = prior.NativeFullFraming101Tests.full_source()
        for point in ((-4, -2), (-3, -2), (-2, -2), (-1, -2)):
            value.tiles[point] = 'floor'
        for x in range(-6, 1): value.tiles[(x, 2)] = 'gold'
        for x in range(-5, 0): value.tiles[(x, 1)] = 'floor'
        value.tiles[(-2, 2)] = 'door'
        items = {(-4, -1), (-3, -1), (-2, -1)}
        value.protected = set(items)
        for point in items: value.tiles[point] = 'item'
        for x, y in items:
            value.protected.update((x + dx, y + dy) for dx, dy in native.DIRS.values())
        return value

    @staticmethod
    def result(value):
        prior.NativeFullFraming101Tests.result(value)
        value.row_count = 2
        for r, sy in enumerate((117, 122)):
            row = value.rows[r]
            row.left, row.sy, row.word_slot = 304, sy, -1
            for i, slot in enumerate(row.slots):
                slot.cx, slot.sy, slot.slot = 304 + 36 * i, sy, i
                slot.icon_score = slot.icon_upper_bound = .1
        value.partial[0].cx, value.partial[0].sy = 232, 117
        value.partial[1].cx, value.partial[1].sy = 448, 122

    def test_neighbor_only_goods_protection_allows_one_fresh_move_then_new_candidate_job(self):
        source = self.source()
        self.assertNotIn((-1, 0), source.protected)
        self.assertTrue({(-2, 0), (-1, -1)} <= source.protected)
        self.p.test_full_unknown_later_static_fresh_ticket_actual_moved_then_new_candidate()

    def test_exact_dilation_cannot_be_bypassed_by_removing_all_old_buffer_conflicts(self):
        for fault in ('self', 'neighbor', 'all_buffer', 'extra', 'origin', 'destination', 'target_item', 'target_unknown'):
            with self.subTest(fault=fault):
                self.setUp()
                def source():
                    value = self.source()
                    if fault == 'self': value.protected.discard((-2, -1))
                    elif fault == 'neighbor': value.protected.discard((-2, 0))
                    elif fault == 'all_buffer': value.protected.difference_update({(-2, 0), (-1, -1)})
                    elif fault == 'extra': value.protected.add((7, 3))
                    elif fault == 'origin': value.protected.add((0, 0))
                    elif fault == 'destination': value.protected.add((-1, 0))
                    elif fault == 'target_item': value.tiles[(-1, 0)] = 'item'
                    elif fault == 'target_unknown': value.tiles.pop((-1, 0), None)
                    return value
                self.p.full_source = source
                self.p.pending()
                self.assertEqual(7, self.p.q.cycle().state)
                self.assertNotEqual(4, self.p.h.tick()[1].kind)

    def test_new_footprint_keeps_original_static_roi_horizon_candidate_and_unknown_guards(self):
        self.p.test_candidate_target_upper_bound_or_strong_word_is_held_before_observation_input()
        for fault in ('item', 'material', 'protection', 'motion', 'unknown'):
            with self.subTest(fault=fault):
                self.setUp()
                source, _, _, _ = self.p.admitted()
                latest = deepcopy(source)
                if fault == 'item': latest.tiles[(-3, -1)] = 'floor'
                elif fault == 'material': latest.tiles[(-2, 0)] = 'dirt'
                elif fault == 'protection': latest.protected.discard((-4, -2))
                elif fault == 'motion': latest.signature = native.translated(source, 1).signature
                elif fault == 'unknown': latest.signature = bytes([80]) * 23296
                self.assertNotEqual((source.tiles, source.protected, source.signature),
                    (latest.tiles, latest.protected, latest.signature),
                    'each negative must actually change this row-1 source')
                self.p.h.now += 10_000_000
                self.p.h.observe_actual(self.p.h.scene(2, 2, latest, beat=True))
                self.assertEqual((7, 5, 17), (self.p.q.cycle().state,
                    self.p.q.cycle().status, self.p.h.status().reason),
                    'reject the actual later static comparison, independently of publication timing')
        self.setUp()
        _, old, _, _, command = self.p.ticket()
        self.assertEqual((4, 1), (command.kind, command.direction))
        self.assertGreater(command.id, old.id, 'an unchanged independent frame reaches a real future ticket')
        self.setUp()
        self.p.test_original_horizon_prefix_cancel_and_input_unknown_never_remint_a_move()

    def test_new_footprint_does_not_release_partial_or_second_unknown_after_its_only_move(self):
        self.p.test_fresh_partial_after_local_move_is_classified_truthfully_but_never_navigates()
        self.setUp()
        self.p.test_second_unknown_in_same_level_does_not_restore_framing()
