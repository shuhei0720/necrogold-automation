"""TEST117 source-cut counterexamples, procedural pixels/Scenes only.

TEST116 962c original188 has one intact face, a fragmented second face,
three complete offers and a positive lower entrance/side rail. 8efc245 has
a complete single face and a closed chest price below the ordinary baseline.
These sparse fixtures do not restore phone private state or future images.
"""
import ctypes as C
import os
from pathlib import Path
import tempfile
import unittest

from tests import test_native_offer_coverage104 as offer
from tests import test_native_ring_bank094 as bank
from tests import test_native_closed_price106 as closed
from tests.test_native_ring094 import Result
from tests.test_target_assessment087 import FEATURES

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT/'patches/loopctrl/ngg2/NG2Ring.c'


def lower_entry_scene(ax=-2, ay=-3, mirror=False):
    """Three real offers, exact protection, one five-cell rail and two posts."""
    scene = offer.shop_scene(ax=ax, ay=ay)
    for i, value in enumerate(scene.tiles):
        if value == 2:
            scene.tiles[i] = 0
    wall = ax-2 if mirror else ax+4
    gate = ax if mirror else ax+2
    for y in range(ay-2, ay+3):
        offer.set_tile(scene, wall, y, 2)
    for x in (gate-1, gate+1):
        offer.set_tile(scene, x, ay+3, 2)
    for y in range(ay+1, ay+4):
        offer.set_tile(scene, gate, y, 1)
    return scene


def single_face_pixels(left=375, sy=43, mirror=False, **kwargs):
    full = (-15, -14, 30, 29)
    pixels = bytearray(offer.shop_pixels(left=left, sy=sy,
        faces=(None, full) if mirror else (full, None), **kwargs))
    # Both fragments fail the old full-component thresholds. No yellow
    # fragment is promoted into an invented second complete face.
    cx = left if mirror else left+72
    for x0, y0, width, height in ((-15, 3, 13, 11), (1, 5, 10, 9)):
        for y in range(sy+y0, sy+y0+height):
            for x in range(cx+x0, cx+x0+width):
                closed.single._put(pixels, x, y, (220, 210, 10))
    return bytes(pixels)


def separate_chest_price_pixels():
    """The two ordinary prices retain their source y; only chest price is lower."""
    pixels = bytearray(closed.shop_pixels(slot=1, price_height=8))
    digit = ('111', '101', '101', '101', '101', '101', '111', '111')
    for slot in range(3):
        cx = 267+36*slot
        # The closed body ends at y235. Its authenticated lower trim is
        # evidence, so clear only the old price below it, never the body.
        for y in range(235 if slot == 1 else 222, 244):
            for x in range(cx-11, cx+12):
                closed.single._put(pixels, x, y, (27, 17, 15))
        top = 235 if slot == 1 else 228
        for column in range(2 if slot == 1 else 1):
            for y, row in enumerate(digit):
                for x, bit in enumerate(row):
                    if bit == '1':
                        closed.single._put(pixels, cx-3+4*column+x, top+y, (245, 245, 245))
    return bytes(pixels)


def partial_five_scene():
    scene = closed.single.shop_scene()
    scene.goods = 1
    for i in range(230):
        scene.protected_cells[i] = 0
        if scene.tiles[i] == 6:
            scene.tiles[i] = 1
    for x in range(-7, -2):
        offer.set_tile(scene, x, 0, 6)
        for dx, dy in ((0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)):
            scene.protected_cells[(5+dy)*23+x+dx+11] = 1
    return scene


def separate_price_scene():
    scene = closed.single.shop_scene()
    # TEST116/245 and247 normally observe all three price-support floors.
    # The old policy7 sparse fixture deliberately did not promise them.
    for x in (-5, -4, -3):
        offer.set_tile(scene, x, 1, 1)
    return scene


class NativeRing117Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='ring117-')
        cls.addClassCleanup(cls.tmp.cleanup)
        source = Path(os.environ.get('NECRO117_RING_SOURCE', str(CORE)))
        cls.lib = bank.NativeRingBank094Tests.build_library(source,
            Path(cls.tmp.name)/'ring.so')
        cls.lib.ng2_ring_negative_certificate.argtypes = [C.POINTER(Result)]
        cls.lib.ng2_ring_negative_certificate.restype = C.c_int

    def test_one_complete_face_with_observed_lower_entrance_certifies_three_offers(self):
        for mirror in (False, True):
            with self.subTest(mirror=mirror):
                # Keep the independently intact right face outside the
                # pause HUD in the mirrored calibration layout.
                left, ax = (267, -5) if mirror else (375, -2)
                scene = lower_entry_scene(ax=ax, mirror=mirror)
                frozen = bytes(scene)
                status, value = offer.normal_assess(self.lib,
                    single_face_pixels(left=left, mirror=mirror), scene)
                self.assertEqual((0, 3, 2, 17), (status, value.outcome,
                    value.coverage, value.certificate.policy_version),
                    'the actual three-offer cut needs independent single-face coverage, not BOARD|ROWS')
                self.assertEqual(1, self.lib.ng2_ring_negative_certificate(C.byref(value)))
                self.assertEqual(7, value.certificate.actual_gold_cells)
                self.assertEqual(frozen, bytes(scene))

    def test_closed_price_recovers_same_row_without_turning_partial_into_absence(self):
        scene = partial_five_scene()
        frozen = bytes(scene)
        status, value = offer.normal_assess(self.lib, separate_chest_price_pixels(), scene)
        self.assertEqual(0, status)
        self.assertIn((267, 153), [(value.rows[i].left, value.rows[i].sy)
                                  for i in range(value.row_count)],
            'an authenticated lower chest price must discover the old sign-anchored row without shifting sy')
        self.assertEqual((0, 1, 1), (value.outcome, value.coverage,
                                    value.partial_safe_no_positive))
        self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)),
                         'row discovery alone cannot certify a PARTIAL five-ITEM source absent')
        self.assertEqual(frozen, bytes(scene))

    def test_three_independent_price_glyphs_do_not_require_identity_of_another_product(self):
        pixels = bytearray(separate_chest_price_pixels())
        # All three exposed products remain bright and fully inside the ROI.
        # This unrelated object's identity is not a curse-ring negative.
        for y in range(202, 235):
            for x in range(285, 321):
                closed.single._put(pixels, x, y, (10, 170, 165))
        status, value = offer.normal_assess(self.lib, bytes(pixels), partial_five_scene())
        self.assertEqual(0, status)
        self.assertIn((267, 153), [(value.rows[i].left, value.rows[i].sy)
                                  for i in range(value.row_count)],
            'separate complete price glyphs discover a row without classifying every unrelated item')
        self.assertEqual((0, 1), (value.outcome, value.coverage))

    def test_new_price_layout_has_generic_absence_and_its_own_numeric_bounds(self):
        status, base = offer.normal_assess(self.lib, separate_chest_price_pixels(),
                                          separate_price_scene())
        self.assertEqual((0, 3, 7, 3), (status, base.outcome,
            base.certificate.policy_version, base.certificate.layout_version))
        self.assertEqual((3, 0), (base.certificate.non_target_items, base.certificate.ignored_containers))
        self.assertEqual(1, self.lib.ng2_ring_negative_certificate(C.byref(base)))
        changes = {
            'row_sy_overflow': lambda r: setattr(r.rows[0], 'sy', 2147483647),
            'row_left_overflow': lambda r: setattr(r.rows[0], 'left', -2147483648),
            'old_layout': lambda r: setattr(r.certificate, 'layout_version', 1),
            'other_policy': lambda r: setattr(r.certificate, 'policy_version', 17),
            'height6': lambda r: r.certificate.price_boxes[1].__setitem__(3, 6),
            'height10': lambda r: r.certificate.price_boxes[1].__setitem__(3, 10),
            'lower_top': lambda r: r.certificate.price_boxes[1].__setitem__(1, 234),
            'lower_end': lambda r: r.certificate.price_boxes[1].__setitem__(1, 237),
            'normal_baseline': lambda r: r.certificate.price_boxes[2].__setitem__(1, 224),
            'ignored_body': lambda r: setattr(r.certificate, 'ignored_containers', 1),
            'bound': lambda r: setattr(r.partial[0], 'icon_upper_bound', .8),
            'abi': lambda r: setattr(r, 'abi', 0),
            'size': lambda r: setattr(r, 'size', 0),
            'status': lambda r: setattr(r, 'status', 5),
            'coverage': lambda r: setattr(r, 'coverage', 0),
            'row_count5': lambda r: (setattr(r, 'row_count', 5), setattr(r, 'selected_row', 4)),
            'row_count100': lambda r: (setattr(r, 'row_count', 100), setattr(r, 'selected_row', 99)),
        }
        for name, mutate in changes.items():
            value = Result.from_buffer_copy(base)
            mutate(value)
            with self.subTest(field=name):
                self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)))

    def test_new_price_layout_requires_exact_projection_and_all_supporting_floors(self):
        def below_unknown(scene):
            offer.set_tile(scene, -4, 1, 0)
        def extra_item(scene):
            offer.set_tile(scene, 5, 2, 6)
        def extra_protection(scene):
            scene.protected_cells[7*23+16] = 1
        for name, mutate in [('below', below_unknown), ('item', extra_item), ('protection', extra_protection)]:
            scene = separate_price_scene()
            mutate(scene)
            with self.subTest(source=name):
                status, value = offer.normal_assess(self.lib, separate_chest_price_pixels(), scene)
                self.assertEqual(0, status)
                self.assertNotEqual(3, value.outcome,
                    'the new generic price geometry cannot replace an exact three-offer visible footprint')

    def test_single_face_requires_each_observed_support_and_complete_merchandise(self):
        points = [(2, y) for y in range(-5, 0)]+[(-1, 0), (1, 0),
            (0, -2), (0, -1), (0, 0), (-3, -3), (1, -3), (-2, -2), (-1, -2)]
        for x, y in points:
            scene = lower_entry_scene()
            offer.set_tile(scene, x, y, 0)
            offer.set_tile(scene, 10, 4, 2)  # Count cannot replace a missing support.
            with self.subTest(missing=(x, y)):
                self.assertNotEqual(3, offer.normal_assess(self.lib,
                    single_face_pixels(), scene)[1].outcome)
        for kwargs in ({'missing_price': 1}, {'missing_wall': True}, {'extra_board': True}):
            with self.subTest(raw=kwargs):
                self.assertNotEqual(3, offer.normal_assess(self.lib,
                    single_face_pixels(**kwargs), lower_entry_scene())[1].outcome)

    def test_original_partial_positive_search_outside_selected_strip_is_retained(self):
        for name in ('icon', 'word'):
            pixels = bytearray(single_face_pixels())
            for y in range(77, 98):
                for x in range(294, 313):
                    closed.single._put(pixels, x, y, (10, 170, 165))
            if name == 'icon':
                sprite = FEATURES['icons'][1]
                for x, y, r, g, b in sprite['bright']:
                    closed.single._put(pixels, 285+x, 77+y, (r, g, b))
                for x, y in sprite['dark']:
                    closed.single._put(pixels, 285+x, 77+y, (0, 0, 0))
            else:
                for y, row in enumerate(FEATURES['word']['rows_hex']):
                    for x in range(84):
                        if int(row, 16)>>x & 1:
                            closed.single._put(pixels, 261+x, 54+y, (245, 245, 245))
            with self.subTest(evidence=name):
                status, value = offer.normal_assess(self.lib, bytes(pixels), lower_entry_scene())
                self.assertEqual(0, status)
                self.assertIn(value.outcome, (1, 2),
                    'the pre-coverage303/43 positive window lies partly outside the selected321..501 strip')
                self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)))

    def test_new_numeric_witness_rejects_field_forgery(self):
        status, base = offer.normal_assess(self.lib, single_face_pixels(), lower_entry_scene())
        self.assertEqual((0, 3, 17), (status, base.outcome, base.certificate.policy_version))
        mutations = {
            'gold': lambda r: setattr(r.certificate, 'actual_gold_cells', 6),
            'face height': lambda r: r.certificate.board_boxes[0].__setitem__(3, 28),
            'face count': lambda r: r.certificate.board_counts.__setitem__(0, 149),
            'invented absent box': lambda r: r.certificate.board_boxes[1].__setitem__(0, 432),
            'invented absent face': lambda r: r.certificate.board_counts.__setitem__(1, 200),
            'price': lambda r: setattr(r.certificate, 'unmatched_prices', 1),
            'cap': lambda r: setattr(r.certificate.endcaps[0], 'black_count', 63),
            'bound': lambda r: setattr(r.partial[0], 'icon_upper_bound', .8),
            'NaN': lambda r: setattr(r.partial[0], 'icon_upper_bound', float('nan')),
            'wrong mode': lambda r: setattr(r.certificate, 'board_mode', 16),
            'strong word': lambda r: (setattr(r.partial[0], 'word_present', 1),
                setattr(r.partial[0], 'word_iou', .82), setattr(r.partial[0], 'word_coverage', .90)),
        }
        for label, mutate in mutations.items():
            value = Result.from_buffer_copy(base)
            mutate(value)
            with self.subTest(field=label):
                self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)))


if __name__ == '__main__':
    unittest.main()
