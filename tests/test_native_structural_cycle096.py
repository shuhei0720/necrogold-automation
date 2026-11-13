"""Policy3 Controller authority on procedural lower gold-shop geometry.

The worker's full pixel scan is separate. These tests bind its bounded numeric
certificate to the exact original Scene and existing durable UI authority;
they do not assert phone arrival or unknown visual accuracy.
"""
import ctypes as C
import math
import unittest

from tests import test_native_cycle094 as cycle094
from tests import test_native_cycle_binary095 as binary095


class NativeStructuralCycle096Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cycle094.NativeCycle094Tests.setUpClass()
        cls.lib = cycle094.NativeCycle094Tests.lib

    @classmethod
    def tearDownClass(cls):
        cycle094.NativeCycle094Tests.tearDownClass()

    def setUp(self):
        self.q = cycle094.NativeCycle094Tests(methodName='runTest')
        self.q.setUp()
        self.addCleanup(self.q.doCleanups)
        self.h = self.q.h

    @staticmethod
    def index(x, y):
        return (y + 5) * 23 + x + 11

    def scene(self, mirror=False, ax=None, ay=-1):
        value = self.h.scene(state=2, gold=2)
        value.goods = 2
        ax = (2 if mirror else -4) if ax is None else ax
        solid, opening = (ax + 4, ax - 2) if mirror else (ax - 2, ax + 4)
        for y in range(ay - 1, ay + 4):
            value.tiles[self.index(solid, y)] = 2
        for x in (range(ax - 1, ax + 5) if mirror else range(ax - 2, ax + 4)):
            value.tiles[self.index(x, ay + 3)] = 2
        for y in (ay, ay + 2):
            value.tiles[self.index(opening, y)] = 2
        value.tiles[self.index(opening, ay + 1)] = 1
        for x in (ax - 1, ax + 3):
            value.tiles[self.index(x, ay)] = 1
            value.protected_cells[self.index(x, ay)] = 1
        for x in range(ax, ax + 3):
            value.tiles[self.index(x, ay)] = 6
            value.protected_cells[self.index(x, ay)] = 1
        return value

    @staticmethod
    def certificate(value, scene, left=301, sy=117, residual=1):
        row, witness = value.rows[0], value.certificate
        row.left, row.sy = left, sy
        binary095.NativeCycleBinary095Tests.binary(value)
        witness.policy_version, witness.board_mode = 3, 3
        witness.row[:] = (left, sy)
        witness.actual_gold_cells = sum(kind == 2 for kind in scene.tiles)
        witness.unmatched_items = residual
        witness.merchant_score = witness.merchant_coverage = 0
        witness.merchant_box[:] = (0, 0, 0, 0)
        for side in range(2):
            witness.sign_boxes[side][:] = (0, 0, 0, 0)
            witness.sign_iou[side] = witness.sign_coverage[side] = 0
            witness.board_boxes[side][:] = (left + 72 * side - 12, sy - 10, 24, 20)
            witness.board_counts[side] = 200
            witness.board_edge_counts[side][:] = (0, 0, 0, 0)
            witness.board_corner_counts[side][:] = (0, 0, 0, 0)
            witness.board_exterior_count[side] = 0
            witness.endcaps[side].box[:] = (left + (96 if side else -48), sy + 36, 25, 25)
        for index in range(3):
            witness.price_boxes[index][:] = (left + 36 * index - 4, sy + 75, 9, 7)

    def assess(self, scene=None, mutate=None, mirror=False, left=None, sy=117, residual=1):
        scene = self.scene(mirror=mirror) if scene is None else scene
        left = (520 if mirror else 301) if left is None else left
        self.assertEqual(1, self.h.observe(scene))
        def changed(value):
            self.certificate(value, scene, left=left, sy=sy, residual=residual)
            if mutate:
                mutate(value)
        return self.q.assess(3, 2, changed)

    def held(self):
        self.assertEqual((0, 3), (self.q.cycle().outcome, self.q.cycle().status))
        self.q.pause_observed()
        self.assertEqual(1, self.q.durable())
        self.assertEqual(0, self.h.tick()[0])
        self.assertEqual(0, self.h.status().restarts)

    def test_complete_structural_source_and_generic_bounds_reach_existing_durable_restart(self):
        for mirror in (False, True):
            with self.subTest(mirror=mirror):
                self.setUp()
                value = self.assess(mirror=mirror)
                self.assertEqual((3, 0), (self.q.cycle().outcome, self.q.cycle().status),
                                 'complete finite gold structure and target-only bounds need no glyph/item identity')
                self.assertEqual(1, value.certificate.unmatched_items,
                                 'ordinary name residual remains diagnostic, never coerced to zero')
                self.q.pause_observed()
                self.assertEqual(0, self.h.tick()[0], 'undurable structural result cannot restart')
                self.assertEqual(1, self.q.durable())
                ready, restart = self.h.tick()
                self.assertEqual((1, 3), (ready, restart.kind))
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, restart.id,
                    restart.not_before_ns, 1, 0, 1), 'exact durable intent is still mandatory')

    def test_source_gold_positions_and_offer_cells_are_recomputed_not_inferred_from_count(self):
        for mirror in (False, True):
            for point in ((x, y) for y in range(-5, 5) for x in range(-11, 12)):
                sample = self.scene(mirror=mirror)
                if sample.tiles[self.index(*point)] != 2:
                    continue
                with self.subTest(mirror=mirror, missing_gold=point):
                    self.setUp()
                    sample.tiles[self.index(*point)] = 0
                    sample.tiles[self.index(10, 4)] = 2
                    self.assertEqual(12, sum(kind == 2 for kind in sample.tiles))
                    self.assess(scene=sample, mirror=mirror)
                    self.held()
        for point in ((-4, -1), (-3, -1), (-2, -1), (-5, -1), (-1, -1)):
            for kind in (0, 2, 3, 4, 5):
                with self.subTest(point=point, kind=kind):
                    self.setUp()
                    sample = self.scene()
                    sample.tiles[self.index(*point)] = kind
                    self.assess(scene=sample)
                    self.held()
        for state in (0, 1):
            with self.subTest(gold_state=state):
                self.setUp()
                sample = self.scene(); sample.gold_state = state
                self.assess(scene=sample); self.held()
        self.setUp()
        sample = self.scene(); sample.gold_state = 3
        self.assess(scene=sample)
        self.assertEqual((3, 0), (self.q.cycle().outcome, self.q.cycle().status))

    def test_opening_must_be_observed_floor_or_door_and_unseen_corner_is_not_filled(self):
        for opening in (1, 5):
            with self.subTest(opening=opening):
                self.setUp()
                sample = self.scene()
                sample.tiles[self.index(0, 0)] = opening
                self.assertEqual(0, sample.tiles[self.index(0, 2)], 'stepped corner stays unknown')
                self.assess(scene=sample)
                self.assertEqual((3, 0), (self.q.cycle().outcome, self.q.cycle().status))
                self.assertEqual(0, sample.tiles[self.index(0, 2)], 'no source tile may be rewritten')
        for opening in (0, 2, 3, 4, 6):
            with self.subTest(opening=opening):
                self.setUp()
                sample = self.scene(); sample.tiles[self.index(0, 0)] = opening
                self.assess(scene=sample); self.held()
        for mirror in (False, True):
            with self.subTest(extra_unrelated_gold=mirror):
                self.setUp()
                sample = self.scene(mirror=mirror)
                sample.tiles[self.index(10, 4)] = 2
                self.assess(scene=sample, mirror=mirror)
                self.assertEqual((3, 0), (self.q.cycle().outcome, self.q.cycle().status))

    def test_nearest_grid_mapping_is_symmetric_and_exact_half_cells_are_ambiguous(self):
        for ax in (-4, 1):
            for offset_x, offset_y in ((-17, -17), (0, 0), (17, 17)):
                with self.subTest(ax=ax, offset_x=offset_x, offset_y=offset_y):
                    self.setUp()
                    sample = self.scene(ax=ax)
                    self.assess(scene=sample, left=448+36*ax+offset_x, sy=123+offset_y)
                    self.assertEqual((3, 0), (self.q.cycle().outcome, self.q.cycle().status))
            for axis in ('x', 'y'):
                for offset in (-18, 18):
                    with self.subTest(ax=ax, axis=axis, half=offset):
                        self.setUp()
                        sample = self.scene(ax=ax)
                        self.assess(scene=sample, left=448+36*ax+(offset if axis=='x' else 0),
                                    sy=123+(offset if axis=='y' else 0))
                        self.held()
        self.setUp()
        self.assess(left=337)
        self.held()
        self.setUp()
        sample = self.scene()
        sample.tiles[self.index(10, 4)] = 2
        self.assess(scene=sample, mutate=lambda value: setattr(value.certificate, 'actual_gold_cells', 12))
        self.held()

    def test_raw_residual_is_bounded_diagnostic_only_for_policy3(self):
        for residual in (0, 1, 502):
            with self.subTest(residual=residual):
                self.setUp(); value = self.assess(residual=residual)
                self.assertEqual((3, 0), (self.q.cycle().outcome, self.q.cycle().status))
                self.assertEqual(residual, value.certificate.unmatched_items)
        for residual in (-1, 503, 2**31-1):
            with self.subTest(residual=residual):
                self.setUp(); self.assess(residual=residual); self.held()
        for policy in (1, 2):
            with self.subTest(legacy_policy=policy):
                self.setUp(); self.q.goods()
                def old(value):
                    if policy == 2:
                        binary095.NativeCycleBinary095Tests.binary(value)
                    value.certificate.unmatched_items = 1
                self.q.assess(3, 2, old); self.held()

    def test_structural_numeric_certificate_still_requires_all_bounds_faces_and_observed_goods(self):
        faults = {
            'incomplete': lambda v: setattr(v, 'coverage', 1),
            'one_cap': lambda v: setattr(v, 'partial_count', 1),
            'extra_cap': lambda v: setattr(v, 'partial_count', 3),
            'row_index': lambda v: setattr(v.certificate, 'row_index', 1),
            'two_rows': lambda v: setattr(v.certificate, 'accepted_rows', 2),
            'failure': lambda v: setattr(v.certificate, 'failure_flags', 1),
            'wrong_board_mode': lambda v: setattr(v.certificate, 'board_mode', 1),
            'merchant_score': lambda v: setattr(v.certificate, 'merchant_score', .94),
            'merchant_box': lambda v: v.certificate.merchant_box.__setitem__(0, 1),
            'glyph_score': lambda v: v.certificate.sign_iou.__setitem__(0, .94),
            'glyph_nonfinite': lambda v: v.certificate.sign_coverage.__setitem__(1, math.nan),
            'glyph_box': lambda v: v.certificate.sign_boxes[0].__setitem__(2, 1),
            'frame_edges': lambda v: v.certificate.board_edge_counts[0].__setitem__(0, 1),
            'frame_corner': lambda v: v.certificate.board_corner_counts[1].__setitem__(0, 1),
            'frame_exterior': lambda v: v.certificate.board_exterior_count.__setitem__(0, 1),
            'face_small': lambda v: v.certificate.board_boxes[0].__setitem__(2, 17),
            'face_sparse': lambda v: v.certificate.board_counts.__setitem__(0, 149),
            'face_count': lambda v: v.certificate.board_counts.__setitem__(0, 481),
            'face_outside_roi': lambda v: [v.certificate.board_boxes[0].__setitem__(1, 99),
                                          v.certificate.board_boxes[0].__setitem__(3, 40)],
            'wrong_center': lambda v: v.certificate.board_boxes[1].__setitem__(0, 364),
            'missing_item': lambda v: setattr(v.certificate, 'observed_items', 2),
            'missing_price': lambda v: setattr(v.certificate, 'observed_prices', 2),
            'extra_price': lambda v: setattr(v.certificate, 'unmatched_prices', 1),
            'extra_board': lambda v: setattr(v.certificate, 'unmatched_boards', 1),
            'unseen_cap': lambda v: setattr(v.certificate.endcaps[1], 'floor_lower', 0),
            'bad_scene': lambda v: setattr(v.certificate, 'scene_goods', 1),
            'policy_unknown': lambda v: setattr(v.certificate, 'policy_version', 4),
            'strip_clipped': lambda v: v.certificate.strip_box.__setitem__(3, 66),
            'price_too_low': lambda v: v.certificate.price_boxes[0].__setitem__(1, 200),
            'cell_domain': lambda v: v.partial[0].non_target_icon_box.__setitem__(2, 35),
            'named_identity': lambda v: setattr(v.rows[0].slots[0], 'non_target_id', 1),
        }
        for fault, mutate in faults.items():
            with self.subTest(fault=fault):
                self.setUp(); self.assess(mutate=mutate); self.held()
        self.setUp()
        sample = self.scene(); sample.goods = 1
        self.assess(scene=sample); self.held()

    def test_target_candidate_or_strong_word_in_any_original_cell_remains_a_veto(self):
        for origin in ('selected', 'endcap', 'other_row'):
            for signal in ('bound', 'candidate', 'target', 'word', 'nonfinite'):
                with self.subTest(origin=origin, signal=signal):
                    self.setUp()
                    def positive(value):
                        slot = value.rows[0].slots[0] if origin=='selected' else value.partial[1]
                        if origin=='other_row':
                            value.row_count = 2; slot = value.rows[1].slots[0]
                        if signal=='bound':slot.icon_score=slot.icon_upper_bound=.80
                        elif signal=='candidate':slot.outcome=1
                        elif signal=='target':slot.outcome=2
                        elif signal=='nonfinite':slot.icon_upper_bound=math.nan
                        else:
                            slot.word_present=1;slot.word_iou=.82;slot.word_coverage=.90
                            slot.word_box[:]=(270,130,84,11)
                    self.assess(mutate=positive); self.held()


if __name__ == '__main__':
    unittest.main()
