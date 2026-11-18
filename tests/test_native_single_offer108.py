"""Observed offset-entry walls plus one physical face; procedural proof only.

The received TEST107 be6e source236 has this fourteen-cell gold boundary,
three exact ITEM projections, three lower floors and one complete face.
No captured pixels or item/name identities are embedded in this fixture.
"""
import ctypes as C
from pathlib import Path
import tempfile
import unittest

from tests import test_native_offer_coverage104 as offer
from tests import test_native_ring_bank094 as bank
from tests import test_native_controller as native
from tests import test_native_cycle094 as cycle
from tests.test_native_ring094 import Result

ROOT = Path(__file__).resolve().parents[1]


def boundary(ax=-4, ay=-2, mirror=False):
    wall, gate = (ax + 4, ax - 2) if mirror else (ax - 2, ax + 4)
    return ({(wall, y) for y in range(ay - 3, ay + 4)}
            | {(x, ay + 3) for x in range(ax - 2, ax + 5)}
            | {(gate, ay + 1)})


def shop_scene(ax=-4, ay=-2, mirror=False):
    scene = offer.shop_scene(ax=ax, ay=ay)
    for i, kind in enumerate(scene.tiles):
        if kind == 2:
            scene.tiles[i] = 0
    for x, y in boundary(ax, ay, mirror):
        offer.set_tile(scene, x, y, 2)
    gate = ax - 2 if mirror else ax + 4
    offer.set_tile(scene, gate, ay + 2, 1)
    return scene


def shop_pixels(left=304, sy=87, mirror=False, faces=None, **kwargs):
    full = (-15, -14, 30, 29)
    if faces is None:
        faces = (None, full) if mirror else (full, None)
    return offer.shop_pixels(left=left, sy=sy, faces=faces, **kwargs)


class NativeSingleOffer108Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='single-offer108-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.lib = bank.NativeRingBank094Tests.build_library(
            ROOT / 'patches/loopctrl/ngg2/NG2Ring.c', Path(cls.tmp.name) / 'ring.so')
        cls.lib.ng2_ring_negative_certificate.argtypes = [C.POINTER(Result)]
        cls.lib.ng2_ring_negative_certificate.restype = C.c_int

    def assess(self, pixels=None, scene=None, **kwargs):
        return offer.normal_assess(self.lib,
            shop_pixels() if pixels is None else pixels,
            shop_scene() if scene is None else scene, **kwargs)

    def test_offset_entry_boundary_single_face_and_full_offers_have_normal_negative_proof(self):
        scene = shop_scene()
        before = bytes(scene)
        status, result = self.assess(scene=scene)
        self.assertEqual((0, 3, 2, 11, 11),
            (status, result.outcome, result.coverage,
             result.certificate.policy_version, result.certificate.board_mode),
            'a fully observed offset-entry shop needs its own positive complete-coverage proof')
        self.assertEqual((14, 3, 3, 0),
            (result.certificate.actual_gold_cells, result.certificate.observed_items,
             result.certificate.observed_prices, result.certificate.failure_flags))
        self.assertEqual(1, self.lib.ng2_ring_negative_certificate(C.byref(result)))
        self.assertEqual(before, bytes(scene), 'a certificate never fills missing Scene evidence')

    def test_relative_boundary_supports_other_rows_and_the_mirrored_opening(self):
        for ax, ay, mirror in ((-4, -2, False), (-2, -1, False),
                              (-4, -2, True), (-2, -1, True)):
            left, sy = 448 + 36 * ax, 207 + 36 * ay - 48
            with self.subTest(ax=ax, ay=ay, mirror=mirror):
                status, result = self.assess(shop_pixels(left, sy, mirror), shop_scene(ax, ay, mirror))
                self.assertEqual((0, 3, 11), (status, result.outcome, result.certificate.policy_version))
                self.assertEqual(1, self.lib.ng2_ring_negative_certificate(C.byref(result)))

    def test_each_observed_wall_and_opening_is_required_independently(self):
        for mirror in (False, True):
            for x, y in sorted(boundary(mirror=mirror)):
                scene = shop_scene(mirror=mirror)
                offer.set_tile(scene, x, y, 0)
                offer.set_tile(scene, 10, 4, 2)  # Keep fourteen GOLD cells: count alone is insufficient.
                with self.subTest(mirror=mirror, missing_wall=(x, y)):
                    self.assertNotEqual(3, self.assess(shop_pixels(mirror=mirror), scene)[1].outcome)
            gate = -6 if mirror else 0
            for kind in (0, 2, 3, 4, 5, 6):
                scene = shop_scene(mirror=mirror)
                offer.set_tile(scene, gate, 0, kind)
                with self.subTest(mirror=mirror, opening=kind):
                    self.assertNotEqual(3, self.assess(shop_pixels(mirror=mirror), scene)[1].outcome)

    def test_three_lower_floors_caps_exact_projection_and_no_fourth_offer_remain_required(self):
        points = [(-5, -2), (-1, -2), *((x, y) for x in (-4, -3, -2) for y in (-2, -1))]
        for x, y in points:
            scene = shop_scene()
            offer.set_tile(scene, x, y, 0)
            with self.subTest(missing=(x, y)):
                self.assertNotEqual(3, self.assess(scene=scene)[1].outcome)
        for fault in ('missing_protection', 'extra_protection', 'extra_item', 'old_blob'):
            scene = shop_scene()
            if fault == 'missing_protection':
                scene.protected_cells[2 * 23 + 7] = 0
            elif fault == 'extra_protection':
                scene.protected_cells[8 * 23 + 21] = 1
            elif fault == 'extra_item':
                offer.set_tile(scene, 8, 3, 6)
            else:
                scene = offer.shop_scene(ax=-4, ay=-2)
            with self.subTest(fault=fault):
                self.assertNotEqual(3, self.assess(scene=scene)[1].outcome)

    def test_one_complete_face_is_positive_evidence_and_not_an_arbitrary_blob(self):
        full = (-15, -14, 30, 29)
        for faces in ((None, None), ((-15, -4, 30, 19), None),
                      ((-8, -14, 17, 29), None), ((-15, 0, 30, 15), None),
                      ((-15, -14, 30, 28), None), ((-15, -14, 30, 30), None)):
            with self.subTest(faces=faces):
                self.assertNotEqual(3, self.assess(shop_pixels(faces=faces))[1].outcome)
        self.assertNotEqual(3, self.assess(shop_pixels(extra_board=True))[1].outcome)
        # The old two-face proof remains the producer for its old inputs.
        status, result = self.assess(shop_pixels(faces=(full, full)))
        self.assertEqual((0, 3, 5), (status, result.outcome, result.certificate.policy_version))

    def test_raw_prices_caps_and_full_target_domain_are_not_optional(self):
        for kwargs in ({'missing_price': 1}, {'missing_wall': True}, {'extra_object': True}):
            with self.subTest(kwargs=kwargs):
                self.assertNotEqual(3, self.assess(shop_pixels(**kwargs))[1].outcome)
        # TEST111 permits an exact target image with its own observed price.
        for target_name, outcome in ((True, 2), (False, 2)):
            with self.subTest(target_name=target_name):
                status, result = self.assess(shop_pixels(target=True, target_name=target_name))
                self.assertEqual(outcome, result.outcome)
                if not target_name:
                    self.assertEqual((0, 2, 1), (status, result.outcome, result.coverage))
                    self.assertGreaterEqual(result.selected_row, 0)
                    slot = result.rows[result.selected_row].slots[1]
                    self.assertEqual((2, 1), (slot.outcome, slot.icon_score_exact))
                    self.assertGreaterEqual(slot.icon_score, .94)
                    self.assertEqual(16, result.certificate.policy_version)
                    self.assertEqual((1, 1), (result.certificate.observed_items,
                                              result.certificate.observed_prices))
                    self.assertEqual(tuple(slot.icon_box), tuple(result.certificate.item_boxes[1]))
                    self.assertEqual((334, 165, 11, 7), tuple(result.certificate.price_boxes[1]))
                    self.assertEqual((0, 0, 0, 0), tuple(result.certificate.name_boxes[1]))
                    self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(result)))

    @staticmethod
    def certificate_mutations():
        return {
            'no_face': lambda v: (v.certificate.board_boxes[0].__setitem__(slice(None), (0, 0, 0, 0)),
                                  v.certificate.board_counts.__setitem__(0, 0)),
            'invented_second_face': lambda v: (v.certificate.board_boxes[1].__setitem__(slice(None), (361, 73, 30, 29)),
                                                v.certificate.board_counts.__setitem__(1, 500)),
            'absent_face_has_box': lambda v: v.certificate.board_boxes[1].__setitem__(0, 1),
            'face_count': lambda v: v.certificate.board_counts.__setitem__(0, 149),
            'face_height': lambda v: v.certificate.board_boxes[0].__setitem__(3, 15),
            'face_height28': lambda v: v.certificate.board_boxes[0].__setitem__(3, 28),
            'face_height30': lambda v: v.certificate.board_boxes[0].__setitem__(3, 30),
            'face_y': lambda v: v.certificate.board_boxes[0].__setitem__(1, 60),
            'gold_count': lambda v: setattr(v.certificate, 'actual_gold_cells', 13),
            'missing_price': lambda v: v.certificate.price_boxes[0].__setitem__(slice(None), (0, 0, 0, 0)),
            'extra_price': lambda v: setattr(v.certificate, 'unmatched_prices', 1),
            'extra_board': lambda v: setattr(v.certificate, 'unmatched_boards', 1),
            'cap': lambda v: setattr(v.certificate.endcaps[0], 'black_count', 63),
            'candidate_bound': lambda v: setattr(v.partial[0], 'icon_upper_bound', .8),
            'nonfinite_bound': lambda v: setattr(v.partial[0], 'icon_upper_bound', float('nan')),
            'strong_word': lambda v: (setattr(v.partial[1], 'word_present', 1),
                                      setattr(v.partial[1], 'word_iou', .82),
                                      setattr(v.partial[1], 'word_coverage', .90)),
            'forged_merchant': lambda v: setattr(v.certificate, 'merchant_score', .99),
            'forged_glyph': lambda v: v.certificate.sign_iou.__setitem__(0, .99),
            'wrong_mode': lambda v: setattr(v.certificate, 'board_mode', 9),
            'closed_layout': lambda v: setattr(v.certificate, 'layout_version', 2),
        }

    def test_numeric_validator_rejects_forged_or_incomplete_evidence(self):
        _, base = self.assess()
        self.assertEqual(3, base.outcome)
        for name, mutate in self.certificate_mutations().items():
            value = Result.from_buffer_copy(base)
            mutate(value)
            with self.subTest(name=name):
                self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)))

    def test_mapping_unseen_row_cancel_deadline_and_legacy_modes_are_preserved(self):
        for left, sy in ((322, 87), (304, 105), (196, 87), (538, 87), (304, 225)):
            with self.subTest(left=left, sy=sy):
                self.assertNotEqual(3, self.assess(shop_pixels(left=left, sy=sy))[1].outcome)
        for kwargs, status in (({'cancelled': True}, 1), ({'deadline': True}, 2)):
            code, result = self.assess(**kwargs)
            self.assertEqual((status, 0, 0), (code, result.outcome, result.coverage))
        for mode in (0, 1):
            self.assertNotEqual(3, self.assess(mode=mode)[1].outcome)

    def test_existing_closed_identity_proves_only_its_actual_lower_price(self):
        status, result = self.assess(shop_pixels(closed_container=True))
        self.assertEqual((0, 3, 2, 11, 2),
            (status, result.outcome, result.coverage,
             result.certificate.policy_version, result.certificate.layout_version))
        self.assertEqual((2, 1),
            (result.certificate.non_target_items, result.certificate.ignored_containers))
        self.assertEqual(1, self.lib.ng2_ring_negative_certificate(C.byref(result)))
        forged = Result.from_buffer_copy(result)
        forged.rows[forged.selected_row].slots[2].ignored_icon_score = .5
        self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(forged)))
        scene = shop_scene()
        offer.set_tile(scene, -2, -1, 0)
        self.assertNotEqual(3, self.assess(shop_pixels(closed_container=True), scene)[1].outcome,
            'this policy never fills an unobserved supporting floor, even for a registered container')


class NativeSingleOfferController108Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cycle.NativeCycle094Tests.setUpClass()
        cls.lib = cycle.NativeCycle094Tests.lib
        cls.tmp = tempfile.TemporaryDirectory(prefix='single-offer-controller108-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.ring = bank.NativeRingBank094Tests.build_library(
            ROOT / 'patches/loopctrl/ngg2/NG2Ring.c', Path(cls.tmp.name) / 'ring.so')

    @classmethod
    def tearDownClass(cls):
        cycle.NativeCycle094Tests.tearDownClass()

    def setUp(self):
        self.q = cycle.NativeCycle094Tests(methodName='runTest')
        self.q.setUp()
        self.addCleanup(self.q.doCleanups)
        self.h = self.q.h

    def normal(self, *, scene_change=None, result_change=None, **pixels_kwargs):
        scene = shop_scene()
        status, value = offer.normal_assess(self.ring, shop_pixels(**pixels_kwargs), scene)
        self.assertEqual((0, 0), (status, value.status))
        if scene_change:
            scene_change(scene)
        self.assertEqual(1, self.h.observe(native.Scene.from_buffer_copy(bytes(scene))))
        job = self.q.cycle()
        self.assertEqual(1, self.lib.ng2_controller_cycle_worker_begin(
            self.h.engine, job.job_id, job.capture_id, job.prefix, self.h.now))
        if result_change:
            result_change(value)
        before = Result.from_buffer_copy(value)
        before.started_ns = before.finished_ns = 0
        value.started_ns, value.finished_ns = self.h.now, self.h.now + 1
        normalized = Result.from_buffer_copy(value)
        normalized.started_ns = normalized.finished_ns = 0
        self.assertEqual(bytes(before), bytes(normalized))
        self.h.now += 2
        self.assertEqual(1, self.lib.ng2_controller_cycle_assess(self.h.engine, job.job_id,
            job.capture_id, job.prefix, self.h.now, C.byref(value)))
        return job, value

    def test_normal_producer_joins_durable_pause_intent_restart_ack_and_next_floor(self):
        job, result = self.normal()
        self.assertEqual((3, 2, 11), (result.outcome, result.coverage, result.certificate.policy_version))
        self.assertEqual((3, 0, 4), (self.q.cycle().outcome, self.q.cycle().status, self.q.cycle().state))
        self.q.pause_observed()
        self.assertEqual(0, self.h.tick()[0], 'ordinary durable publication still gates RESTART')
        self.assertEqual(1, self.q.durable())
        ready, restart = self.h.tick()
        self.assertEqual((1, 3), (ready, restart.kind))
        self.assertEqual(0, self.lib.ng2_controller_begin(self.h.engine, restart.id, self.h.now, 1, 0, 1))
        self.assertEqual(1, self.q.intent(restart))
        self.q.next_floor(restart)
        self.assertEqual((1, 0), (self.h.status().restarts, self.h.status().terminal))
        waiting = self.q.cycle()
        self.assertEqual(job.level_id, waiting.level_id)
        self.assertEqual(0, self.h.tick()[0])
        self.assertEqual(1, self.lib.ng2_controller_cycle_outcome_commit(self.h.engine,
            waiting.job_id, waiting.next_floor_capture_id, self.h.prefix, self.h.now))
        self.assertEqual((job.level_id + 1, 0), (self.q.cycle().level_id, self.q.cycle().state))

    def test_controller_rechecks_observed_boundary_floor_projection_and_forged_certificate(self):
        def missing_wall(scene):
            offer.set_tile(scene, -6, -5, 0)
            offer.set_tile(scene, 10, 4, 2)
        scene_changes = {
            'wall_even_with_same_count': missing_wall,
            'opening': lambda s: offer.set_tile(s, 0, 0, 4),
            'below_floor': lambda s: offer.set_tile(s, -3, -1, 0),
            'cap': lambda s: offer.set_tile(s, -5, -2, 0),
            'fourth_item': lambda s: offer.set_tile(s, 8, 3, 6),
            'projection': lambda s: s.protected_cells.__setitem__(2 * 23 + 7, 0),
        }
        for name, mutate in scene_changes.items():
            with self.subTest(scene=name):
                self.setUp()
                self.normal(scene_change=mutate)
                self.assertEqual((0, 3, 7), (self.q.cycle().outcome, self.q.cycle().status, self.q.cycle().state))
                ready, command = self.h.tick()
                self.assertFalse(ready and command.kind in (3, 4))
        for name, mutate in NativeSingleOffer108Tests.certificate_mutations().items():
            with self.subTest(certificate=name):
                self.setUp()
                self.normal(result_change=mutate)
                self.assertEqual((0, 3, 7), (self.q.cycle().outcome, self.q.cycle().status, self.q.cycle().state))
                ready, command = self.h.tick()
                self.assertFalse(ready and command.kind in (3, 4))

    def test_target_candidate_and_unobserved_price_never_receive_restart_authority(self):
        for kwargs in ({'target': True}, {'target': True, 'target_name': False}, {'missing_price': 1}):
            with self.subTest(kwargs=kwargs):
                self.setUp()
                _, result = self.normal(**kwargs)
                self.assertNotEqual(3, result.outcome)
                self.assertNotEqual(3, self.q.cycle().outcome)
                ready, command = self.h.tick()
                self.assertFalse(ready and command.kind in (3, 4))

    def test_existing_closed_price_certificate_is_independently_adopted(self):
        _, result = self.normal(closed_container=True)
        self.assertEqual((3, 11, 2),
            (result.outcome, result.certificate.policy_version, result.certificate.layout_version))
        self.assertEqual((3, 0, 4),
            (self.q.cycle().outcome, self.q.cycle().status, self.q.cycle().state))
        self.setUp()
        self.normal(closed_container=True,
            result_change=lambda v: setattr(v.rows[v.selected_row].slots[2], 'ignored_icon_score', .5))
        self.assertEqual((0, 3, 7),
            (self.q.cycle().outcome, self.q.cycle().status, self.q.cycle().state))
