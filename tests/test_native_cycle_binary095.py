"""TEST095 catalog-free certificate adoption with procedural Controller inputs.

The native worker owns pixel coverage and conservative primary-template bounds.
These certificates test its strict Controller boundary and old durable restart
sequence; they do not establish visual accuracy or device arrival.
"""
import ctypes as C
import math
import unittest

from tests import test_native_cycle094 as cycle094


class NativeCycleBinary095Tests(unittest.TestCase):
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
    def binary(value):
        row, witness = value.rows[0], value.certificate
        witness.policy_version = 2
        witness.strip_box[:] = (row.left - 54, row.sy + 24, 180, 67)
        witness.non_target_items, witness.ignored_containers = 3, 0
        value.partial_count = 2
        for index, offset in enumerate((0, 36, 72, -36, 108)):
            slot = row.slots[index] if index < 3 else value.partial[index - 3]
            C.memset(C.addressof(slot), 0, C.sizeof(slot))
            slot.cx, slot.sy, slot.slot = row.left + offset, row.sy, index if index < 3 else 0
            slot.kind, slot.outcome = 3, 3
            slot.icon_score = slot.icon_upper_bound = .1
            slot.icon_box[:] = (slot.cx - 16, slot.sy + 35, 32, 28)
            slot.non_target_icon_box[:] = (slot.cx - 18, slot.sy + 24, 36, 67)
            if index < 3:
                witness.item_boxes[index][:] = slot.non_target_icon_box[:]
                witness.name_boxes[index][:] = (0, 0, 0, 0)

    def assess_binary(self, mutate=None, partial=False):
        self.q.goods(partial=partial)
        def changed(value):
            self.binary(value)
            if mutate:
                mutate(value)
        return self.q.assess(3, 2, changed)

    def held(self, status=3):
        q = self.q
        self.assertEqual((0, status), (q.cycle().outcome, q.cycle().status))
        q.pause_observed()
        self.assertEqual(1, q.durable())
        self.assertEqual(0, self.h.tick()[0])
        self.assertEqual(0, self.h.status().restarts)

    def test_complete_generic_five_cell_bounds_reach_only_the_existing_durable_restart(self):
        self.assess_binary()
        q = self.q
        self.assertEqual((3, 0), (q.cycle().outcome, q.cycle().status),
                         'all five complete conservative target bounds need no other-item identities')
        q.pause_observed()
        self.assertEqual(0, self.h.tick()[0])
        self.assertEqual(1, q.durable())
        ready, restart = self.h.tick()
        self.assertEqual((1, 3), (ready, restart.kind))
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, restart.id,
            restart.not_before_ns, 1, 0, 1), 'binary evidence cannot bypass durable intent')

    def test_missing_cell_partial_source_failure_or_layout_uncertainty_stays_held(self):
        faults = {
            'one_endcap': lambda v: setattr(v, 'partial_count', 1),
            'extra_partial': lambda v: setattr(v, 'partial_count', 3),
            'partial_selected': lambda v: setattr(v, 'selected_partial', 0),
            'incomplete': lambda v: setattr(v, 'coverage', 1),
            'worker_failure': lambda v: setattr(v, 'status', 5),
            'certificate_failure': lambda v: setattr(v.certificate, 'failure_flags', 1),
            'two_accepted_rows': lambda v: setattr(v.certificate, 'accepted_rows', 2),
            'wrong_policy': lambda v: setattr(v.certificate, 'policy_version', 3),
            'missing_product': lambda v: setattr(v.certificate, 'observed_items', 2),
            'extra_product': lambda v: setattr(v.certificate, 'unmatched_items', 1),
            'missing_price': lambda v: setattr(v.certificate, 'observed_prices', 2),
            'unobserved_edge': lambda v: setattr(v.certificate.endcaps[0], 'floor_full', 0),
            'no_shop_sign': lambda v: [setattr(v.certificate, name, (C.c_double * 2)(0, 0))
                                      for name in ('sign_iou', 'sign_coverage')],
            'invalid_shop_boxes': lambda v: [v.certificate.sign_boxes[i].__setitem__(2, 0) for i in range(2)],
            'nonfinite_sign': lambda v: v.certificate.sign_iou.__setitem__(1, math.nan),
            'nonfloor': lambda v: setattr(v.certificate, 'scene_state', 1),
            'partial_scene': lambda v: setattr(v.certificate, 'scene_goods', 1),
            'named_count': lambda v: setattr(v.certificate, 'non_target_items', 2),
            'ignored_count': lambda v: setattr(v.certificate, 'ignored_containers', 1),
        }
        for fault, mutate in faults.items():
            with self.subTest(fault=fault):
                self.setUp(); self.assess_binary(mutate)
                self.held(status=5 if fault == 'worker_failure' else 3)
        with self.subTest(fault='actual_partial_source'):
            self.setUp(); self.assess_binary(partial=True); self.held()

    def test_all_five_maxima_require_finite_equal_conservative_bounds_below_candidate(self):
        for index in range(5):
            for score, upper, exact in ((.8, .8, 0), (.1, .8, 0),
                    (.2, .1, 0), (.1, .2, 0), (.1, .1, 1),
                    (math.nan, .1, 0), (.1, math.inf, 0), (-.1, -.1, 0)):
                with self.subTest(cell=index, score=score, upper=upper, exact=exact):
                    self.setUp()
                    def malformed(v):
                        slot = v.rows[0].slots[index] if index < 3 else v.partial[index-3]
                        slot.icon_score, slot.icon_upper_bound, slot.icon_score_exact = score, upper, exact
                    self.assess_binary(malformed); self.held()
        self.setUp()
        def boundary(v):
            for slot in list(v.rows[0].slots) + list(v.partial)[:2]:
                slot.icon_score = slot.icon_upper_bound = math.nextafter(.8, 0)
        self.assess_binary(boundary)
        self.assertEqual((3, 0), (self.q.cycle().outcome, self.q.cycle().status))

    def test_generic_domain_and_representative_pose_have_exact_finite_geometry(self):
        faults = {
            'cell_plus_one': lambda v: v.rows[0].slots[1].non_target_icon_box.__setitem__(0, 319),
            'cell_clipped': lambda v: v.rows[0].slots[0].non_target_icon_box.__setitem__(3, 66),
            'certificate_cell': lambda v: v.certificate.item_boxes[1].__setitem__(2, 35),
            'endcap_center': lambda v: setattr(v.partial[1], 'cx', 407),
            'wrong_endcap_slot': lambda v: setattr(v.partial[0], 'slot', 1),
            'wrong_sy': lambda v: setattr(v.partial[0], 'sy', 91),
            'unsupported_template': lambda v: v.rows[0].slots[0].icon_box.__setitem__(2, 31),
            'template_outside_strip': lambda v: v.partial[0].icon_box.__setitem__(0, 245),
            'template_other_cell': lambda v: v.rows[0].slots[0].icon_box.__setitem__(0, 302),
            'strip_plus_one': lambda v: v.certificate.strip_box.__setitem__(3, 68),
            'price_bottom_plus_one': lambda v: v.certificate.price_boxes[0].__setitem__(1, 173),
            'name_box_not_zero': lambda v: v.certificate.name_boxes[0].__setitem__(0, 1),
            'catalog_id': lambda v: setattr(v.rows[0].slots[0], 'non_target_id', 1),
            'container_id': lambda v: setattr(v.partial[0], 'ignored_container_id', 9),
            'catalog_score': lambda v: setattr(v.rows[0].slots[1], 'non_target_icon_score', .1),
            'container_score': lambda v: setattr(v.partial[1], 'ignored_icon_score', .1),
            'catalog_name_box': lambda v: v.rows[0].slots[0].non_target_name_box.__setitem__(0, 1),
            'container_box': lambda v: v.rows[0].slots[0].ignored_icon_box.__setitem__(0, 1),
            'wrong_kind': lambda v: setattr(v.rows[0].slots[2], 'kind', 1),
            'unknown_outcome': lambda v: setattr(v.partial[0], 'outcome', 0),
        }
        for fault, mutate in faults.items():
            with self.subTest(fault=fault):
                self.setUp(); self.assess_binary(mutate); self.held()

    def test_target_candidate_or_strong_word_anywhere_vetoes_binary_absence(self):
        for source in ('selected', 'endcap', 'other_row'):
            for signal in ('target', 'candidate', 'word', 'malformed_outcome'):
                with self.subTest(source=source, signal=signal):
                    self.setUp()
                    def positive(v):
                        slot = v.rows[0].slots[0] if source == 'selected' else v.partial[1]
                        if source == 'other_row':
                            v.row_count = 2
                            slot = v.rows[1].slots[0]
                        if signal == 'target': slot.outcome = 2
                        elif signal == 'candidate': slot.outcome = 1
                        elif signal == 'malformed_outcome': slot.outcome = 5
                        else:
                            slot.word_present = 1
                            slot.word_iou, slot.word_coverage = .82, .90
                            slot.word_box[:] = (270, 90, 60, 15)
                    self.assess_binary(positive); self.held()


if __name__ == '__main__':
    unittest.main()
