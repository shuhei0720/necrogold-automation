"""Independent policy5 Controller adoption on procedural, fully seen shops.

The actual217 UNKNOWN endcap is a rejection premise, never filled by this
fixture. Raw pixels remain the Ring producer's separate responsibility.
"""
import ctypes as C
import unittest

from tests import test_native_cycle094 as cycle
from tests import test_native_structural_cycle096 as structural
from tests import test_native_side_shop_controller100 as side


class NativeLowerShopController101Tests(unittest.TestCase):
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

    def scene(self, mirror=False, opening='floor'):
        ax, ay = (2 if mirror else -4), -2
        value = self.h.scene(state=2, gold=2)
        value.goods = 2
        solid, gate = (ax + 4, ax - 2) if mirror else (ax - 2, ax + 4)
        for y in range(ay - 1, ay + 4): value.tiles[self.index(solid, y)] = 2
        for x in range(ax - 2, ax + 5): value.tiles[self.index(x, ay + 3)] = 2
        value.tiles[self.index(gate, ay + 1)] = 2
        value.tiles[self.index(gate, ay + 2)] = 1 if opening == 'floor' else 5
        for x in (ax - 1, ax + 3): value.tiles[self.index(x, ay)] = 1
        for x in range(ax, ax + 3):
            value.tiles[self.index(x, ay)] = 6
            value.protected_cells[self.index(x, ay)] = 1
        return value

    @staticmethod
    def certificate(value, scene, left=304, sy=87):
        structural.NativeStructuralCycle096Tests.certificate(value, scene, left, sy)
        value.certificate.policy_version = value.certificate.board_mode = 5

    def assess(self, scene=None, mirror=False, mutate=None, left=None, sy=87):
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

    def test_twelve_position_shape_mirrors_and_observed_openings_reach_durable_restart_only(self):
        for mirror in (False, True):
            for opening in ('floor', 'door'):
                with self.subTest(mirror=mirror, opening=opening):
                    self.setUp()
                    self.assess(self.scene(mirror, opening), mirror=mirror)
                    self.assertEqual((3, 0), (self.q.cycle().outcome, self.q.cycle().status),
                        'policy5 needs independent twelve-position adoption, not gold-count inference')
                    self.q.pause_observed()
                    self.assertEqual(0, self.h.tick()[0])
                    self.assertEqual(1, self.q.durable())
                    ready, restart = self.h.tick()
                    self.assertEqual((1, 3), (ready, restart.kind))
                    self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, restart.id,
                        restart.not_before_ns, 1, 0, 1))

    def test_each_gold_position_is_required_even_with_equal_total_count(self):
        for mirror in (False, True):
            sample = self.scene(mirror)
            for i, kind in enumerate(sample.tiles):
                if kind != 2: continue
                with self.subTest(mirror=mirror, missing=i):
                    self.setUp()
                    sample = self.scene(mirror)
                    sample.tiles[i] = 0
                    sample.tiles[self.index(10, 4)] = 2
                    self.assess(sample, mirror=mirror)
                    self.held()

    def test_actual217_equivalent_unknown_cap_and_other_material_or_mapping_failures_hold(self):
        for fault in ('right_unknown', 'left_unknown', 'item', 'opening', 'half_x', 'half_y', 'offset'):
            with self.subTest(fault=fault):
                self.setUp()
                sample = self.scene()
                left, sy = 304, 87
                if fault == 'right_unknown': sample.tiles[self.index(-1, -2)] = 0
                elif fault == 'left_unknown': sample.tiles[self.index(-5, -2)] = 0
                elif fault == 'item': sample.tiles[self.index(-3, -2)] = 1
                elif fault == 'opening': sample.tiles[self.index(0, 0)] = 3
                elif fault == 'half_x': left += 18
                elif fault == 'half_y': sy += 18
                elif fault == 'offset': sy += 36
                self.assess(sample, left=left, sy=sy)
                self.held()

    def test_numeric_witness_target_bounds_endcaps_and_extra_objects_remain_strict(self):
        faults = {
            'mode': lambda v: setattr(v.certificate, 'board_mode', 4),
            'count': lambda v: setattr(v.certificate, 'actual_gold_cells', 13),
            'unknown_cap': lambda v: setattr(v.certificate.endcaps[1], 'black_count', 467),
            'incomplete': lambda v: setattr(v, 'coverage', 1),
            'fourth_price': lambda v: setattr(v.certificate, 'unmatched_prices', 1),
            'extra_board': lambda v: setattr(v.certificate, 'unmatched_boards', 1),
            'missing_face': lambda v: v.certificate.board_counts.__setitem__(0, 0),
            'target_upper': lambda v: setattr(v.rows[0].slots[1], 'icon_upper_bound', .8),
            'strong_word': lambda v: (setattr(v.partial[0], 'word_present', 1),
                setattr(v.partial[0], 'word_iou', 1), setattr(v.partial[0], 'word_coverage', 1)),
        }
        for name, mutate in faults.items():
            with self.subTest(fault=name):
                self.setUp()
                self.assess(mutate=mutate)
                self.held()

    def test_old_policy_three_and_four_geometry_remain_distinct(self):
        for policy in (3, 4):
            with self.subTest(policy=policy):
                self.setUp()
                self.assess(mutate=lambda v: (setattr(v.certificate, 'policy_version', policy),
                    setattr(v.certificate, 'board_mode', policy)))
                self.held()
        for helper, left, sy in ((structural.NativeStructuralCycle096Tests, 301, 117),
                                 (side.NativeSideShopController100Tests, 304, 195)):
            with self.subTest(existing=helper.__name__):
                self.setUp()
                sample = helper.scene(self)
                self.assertEqual(1, self.h.observe(sample))
                self.q.assess(3, 2, lambda v: helper.certificate(v, sample, left, sy))
                self.assertEqual((3, 0), (self.q.cycle().outcome, self.q.cycle().status))


if __name__ == '__main__':
    unittest.main()
