"""TEST100 independent Controller policy4 witness on procedural Scenes.

Worker pixels/price ink remain producer obligations; the Controller recomputes
the new seven-GOLD side geometry from the exact bound immutable Scene.
"""
import ctypes as C
from copy import deepcopy
import math
import unittest

from tests import test_native_cycle094 as cycle
from tests import test_native_structural_cycle096 as structural


class NativeSideShopController100Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cycle.NativeCycle094Tests.setUpClass()
        cls.lib = cycle.NativeCycle094Tests.lib

    @classmethod
    def tearDownClass(cls):
        cycle.NativeCycle094Tests.tearDownClass()

    def setUp(self):
        self.q = cycle.NativeCycle094Tests(methodName='runTest')
        self.q.setUp()
        self.addCleanup(self.q.doCleanups)
        self.h = self.q.h

    index = staticmethod(structural.NativeStructuralCycle096Tests.index)

    def scene(self, mirror=False, ax=None, ay=1):
        ax = (2 if mirror else -4) if ax is None else ax
        value = self.h.scene(state=2, gold=2)
        value.goods = 2
        solid, gate = (ax + 4, ax - 2) if mirror else (ax - 2, ax + 4)
        for y in range(ay - 3, ay + 2): value.tiles[self.index(solid, y)] = 2
        for y in (ay - 2, ay): value.tiles[self.index(gate, y)] = 2
        value.tiles[self.index(gate, ay - 1)] = 1
        for x in (ax - 1, ax + 3): value.tiles[self.index(x, ay)] = 1
        for x in range(ax, ax + 3):
            value.tiles[self.index(x, ay)] = 6
            value.protected_cells[self.index(x, ay)] = 1
        return value

    @staticmethod
    def certificate(value, scene, left=304, sy=195):
        structural.NativeStructuralCycle096Tests.certificate(value, scene, left, sy)
        value.certificate.policy_version = value.certificate.board_mode = 4

    def assess(self, scene=None, mirror=False, mutate=None, left=None, sy=195):
        scene = self.scene(mirror=mirror) if scene is None else scene
        left = (520 if mirror else 304) if left is None else left
        self.assertEqual(1, self.h.observe(scene))
        def build(value):
            self.certificate(value, scene, left, sy)
            if mutate: mutate(value)
        return self.q.assess(3, 2, build)

    def held(self):
        self.assertNotEqual(3, self.q.cycle().outcome)
        self.assertEqual(0, self.h.status().restarts)
        ready, command = self.h.tick()
        self.assertFalse(ready and command.kind in (3, 4))

    def test_seven_observed_gold_side_shape_reaches_only_existing_durable_restart(self):
        for mirror in (False, True):
            with self.subTest(mirror=mirror):
                self.setUp()
                value = self.assess(mirror=mirror)
                self.assertEqual((3, 0), (self.q.cycle().outcome, self.q.cycle().status),
                                 'policy4 side geometry must be checked independently and adopted')
                self.assertEqual(7, value.certificate.actual_gold_cells)
                self.q.pause_observed()
                self.assertEqual(0, self.h.tick()[0])
                self.assertEqual(1, self.q.durable())
                ready, restart = self.h.tick()
                self.assertEqual((1, 3), (ready, restart.kind))
                self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, restart.id,
                    restart.not_before_ns, 1, 0, 1), 'numeric witness does not replace exact durable intent')

    def test_every_required_gold_position_is_recomputed_even_with_equal_numeric_count(self):
        for mirror in (False, True):
            original = self.scene(mirror=mirror)
            for i, kind in enumerate(original.tiles):
                if kind != 2: continue
                with self.subTest(mirror=mirror, missing=i):
                    self.setUp()
                    scene = self.scene(mirror=mirror)
                    scene.tiles[i] = 0
                    scene.tiles[self.index(10, 4)] = 2
                    self.assess(scene, mirror=mirror)
                    self.held()

    def test_offer_cells_endcaps_gate_and_rounded_row_must_belong_to_actual_source(self):
        for fault in ('item', 'left_cap', 'right_cap', 'gate', 'half_x', 'half_y', 'bounds', 'old_shape'):
            with self.subTest(fault=fault):
                self.setUp()
                scene = self.scene()
                left, sy = 304, 195
                if fault == 'item': scene.tiles[self.index(-3, 1)] = 1
                elif fault == 'left_cap': scene.tiles[self.index(-5, 1)] = 0
                elif fault == 'right_cap': scene.tiles[self.index(-1, 1)] = 0
                elif fault == 'gate': scene.tiles[self.index(0, 0)] = 4
                elif fault == 'half_x': left = 322
                elif fault == 'half_y': sy = 213
                elif fault == 'bounds': left = 88
                elif fault == 'old_shape': scene = structural.NativeStructuralCycle096Tests.scene(self)
                self.assess(scene, left=left, sy=sy)
                self.held()

    def test_policy_price_baseline_extra_objects_and_complete_bounds_are_strict(self):
        faults = {
            'mode': lambda v: setattr(v.certificate, 'board_mode', 3),
            'count': lambda v: setattr(v.certificate, 'actual_gold_cells', 8),
            'partial': lambda v: setattr(v, 'coverage', 1),
            'candidate': lambda v: setattr(v, 'outcome', 1),
            'row_count': lambda v: setattr(v.certificate, 'accepted_rows', 2),
            'price_count': lambda v: setattr(v.certificate, 'observed_prices', 2),
            'fourth_price': lambda v: setattr(v.certificate, 'unmatched_prices', 1),
            'extra_board': lambda v: setattr(v.certificate, 'unmatched_boards', 1),
            # Each box stays in the old20px band; their union alone exceeds9.
            'baseline': lambda v: v.certificate.price_boxes[2].__setitem__(1, 273),
            'missing_face': lambda v: v.certificate.board_counts.__setitem__(0, 0),
            'glyph_launder': lambda v: v.certificate.sign_iou.__setitem__(0, 1),
            'merchant_launder': lambda v: setattr(v.certificate, 'merchant_score', 1),
            'nan_bound': lambda v: setattr(v.rows[0].slots[0], 'icon_upper_bound', math.nan),
            'target_bound': lambda v: setattr(v.rows[0].slots[0], 'icon_upper_bound', .8),
            'strong_word': lambda v: (setattr(v.rows[0].slots[0], 'word_present', 1),
                setattr(v.rows[0].slots[0], 'word_iou', 1), setattr(v.rows[0].slots[0], 'word_coverage', 1)),
            'missing_partial': lambda v: setattr(v, 'partial_count', 1),
        }
        for name, mutate in faults.items():
            with self.subTest(fault=name):
                self.setUp()
                self.assess(mutate=mutate)
                self.held()

    def test_correct_source_does_not_authorize_wrong_policy_and_old_policy3_stays_independent(self):
        self.assess(mutate=lambda v: (setattr(v.certificate, 'policy_version', 3),
            setattr(v.certificate, 'board_mode', 3)))
        self.held()
        self.setUp()
        old = structural.NativeStructuralCycle096Tests.scene(self)
        self.assertEqual(1, self.h.observe(old))
        self.q.assess(3, 2, lambda v: structural.NativeStructuralCycle096Tests.certificate(v, old))
        self.assertEqual((3, 0), (self.q.cycle().outcome, self.q.cycle().status))


if __name__ == '__main__':
    unittest.main()
