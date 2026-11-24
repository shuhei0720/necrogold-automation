"""One observed face and high entrance: raw-free policy18 counterexamples.

The TEST117 upper-entry path needs a fifth physical DOWN before all three
support floors are visible. Its independent procedural future then observes
a seven-cell roof, seven-cell solid side and opposite lower entrance post.
No phone pixels, unknown floors or private Controller state are restored.
"""
import ctypes as C
import os
from pathlib import Path
import tempfile
import unittest

from tests import test_native_offer_coverage104 as offer
from tests import test_native_single_offer108 as single
from tests import test_native_floor_moments118 as floor
from tests import test_native_ring_bank094 as bank
from tests.test_native_ring094 import Result
from tests.test_target_assessment087 import FEATURES

ROOT = Path(__file__).resolve().parents[1]


def boundary(ax=-3, ay=1, mirror=False):
    solid, gate = (ax+4, ax-2) if mirror else (ax-2, ax+4)
    return ({(solid, y) for y in range(ay-5, ay+2)}
            | {(x, ay-5) for x in range(ax-2, ax+5)}
            | {(gate, ay-3)})


def shop_scene(ax=-3, ay=1, mirror=False, opening=1):
    scene = offer.shop_scene(ax=ax, ay=ay)
    for i, kind in enumerate(scene.tiles):
        if kind == 2:
            scene.tiles[i] = 0
    for x, y in boundary(ax, ay, mirror):
        offer.set_tile(scene, x, y, 2)
    offer.set_tile(scene, ax-2 if mirror else ax+4, ay-4, opening)
    return scene


def shop_pixels(left=340, sy=195, mirror=False, fragment=0, moment=False, **kwargs):
    pixels = bytearray((floor.mottled_floor_pixels if moment else single.shop_pixels)(
        left=left, sy=sy, mirror=mirror, **kwargs))
    for i in range(fragment):
        offer._put(pixels, left+16+i % 3, sy+69+i // 3, (245, 245, 245))
    return bytes(pixels)


class NativeUpperSingleFace118Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='upper-single-face118-')
        cls.addClassCleanup(cls.tmp.cleanup)
        source = Path(os.environ.get('NECRO118_UPPER_RING_SOURCE',
            str(ROOT/'patches/loopctrl/ngg2/NG2Ring.c')))
        cls.lib = bank.NativeRingBank094Tests.build_library(source, Path(cls.tmp.name)/'ring.so')
        cls.lib.ng2_ring_negative_certificate.argtypes = [C.POINTER(Result)]
        cls.lib.ng2_ring_negative_certificate.restype = C.c_int

    def assess(self, pixels=None, scene=None, *, mirror=False, **kwargs):
        if scene is None:
            scene = shop_scene(mirror=mirror)
        before = bytes(scene)
        status, value = offer.normal_assess(self.lib,
            shop_pixels(mirror=mirror, **kwargs) if pixels is None else pixels, scene)
        self.assertEqual(0, status)
        self.assertEqual(before, bytes(scene), 'coverage cannot fill or relabel observed cells')
        return value

    def negative(self, **kwargs):
        value = self.assess(**kwargs)
        self.assertEqual((3, 2, 18, 18, 0), (value.outcome, value.coverage,
            value.certificate.policy_version, value.certificate.board_mode,
            value.certificate.failure_flags),
            'one complete face and the independently observed high entrance need a distinct proof')
        self.assertEqual(1, self.lib.ng2_ring_negative_certificate(C.byref(value)))
        return value

    def test_mirrored_four_rows_high_entrance_and_small_measured_offsets(self):
        for mirror in (False, True):
            for opening in (1, 5):
                for left, sy in ((339, 194), (340, 195), (341, 196)):
                    with self.subTest(mirror=mirror, opening=opening, left=left, sy=sy):
                        value = self.negative(pixels=shop_pixels(left, sy, mirror),
                            scene=shop_scene(mirror=mirror, opening=opening))
                        self.assertEqual(14, value.certificate.actual_gold_cells)
                        self.assertEqual((3, 3, 0), (value.certificate.observed_items,
                            value.certificate.observed_prices, value.certificate.unmatched_prices))
        scene = shop_scene()
        offer.set_tile(scene, 10, 4, 2)
        self.assertEqual(15, self.negative(scene=scene).certificate.actual_gold_cells,
            'the certificate records all observed GOLD, not merely its fourteen required supports')

    def test_every_one_of_fourteen_supports_and_the_opening_is_required(self):
        for mirror in (False, True):
            self.assertEqual(14, len(boundary(mirror=mirror)))
            for x, y in sorted(boundary(mirror=mirror)):
                scene = shop_scene(mirror=mirror)
                offer.set_tile(scene, x, y, 0)
                offer.set_tile(scene, 10, 4, 2)
                with self.subTest(mirror=mirror, missing=(x, y)):
                    self.assertNotEqual(3, self.assess(scene=scene, mirror=mirror).outcome,
                        'an unrelated GOLD cell cannot replace a missing enclosure support')
            for kind in (0, 2, 3, 4, 6):
                with self.subTest(mirror=mirror, opening=kind):
                    self.assertNotEqual(3, self.assess(mirror=mirror,
                        scene=shop_scene(mirror=mirror, opening=kind)).outcome)

    def test_three_items_lower_floors_caps_exact_halo_and_row_one_stay_required(self):
        for x, y in [*((x, y) for x in (-3, -2, -1) for y in (1, 2)), (-4, 1), (0, 1)]:
            scene = shop_scene()
            offer.set_tile(scene, x, y, 0)
            with self.subTest(missing=(x, y)):
                self.assertNotEqual(3, self.assess(scene=scene).outcome)
        for field in ('extra_item', 'extra_protection', 'missing_protection'):
            scene = shop_scene()
            if field == 'extra_item':
                offer.set_tile(scene, 10, 3, 6)
            elif field == 'extra_protection':
                scene.protected_cells[9*23+21] = 1
            else:
                scene.protected_cells[6*23+8] = 0
            with self.subTest(field=field):
                self.assertNotEqual(3, self.assess(scene=scene).outcome)
        for ay in (0, 2):
            with self.subTest(row=ay):
                self.assertNotEqual(3, self.assess(scene=shop_scene(ay=ay),
                    pixels=shop_pixels(sy=159+36*ay)).outcome)

    def test_one_full_face_three_prices_and_uncovered_objects_stay_observed(self):
        full = (-15, -14, 30, 29)
        for faces in ((None, None), ((-15, -14, 30, 28), None),
                      ((-8, -14, 17, 29), None), (full, full)):
            with self.subTest(faces=faces):
                value = self.assess(faces=faces)
                self.assertNotEqual(18, value.certificate.policy_version)
        for kwargs in ({'missing_price': 1}, {'missing_wall': True},
                       {'extra_board': True}, {'extra_object': True}):
            with self.subTest(raw=kwargs):
                self.assertNotEqual(3, self.assess(**kwargs).outcome)
        self.assertNotEqual(3, self.assess(pixels=shop_pixels(left=537, sy=21)).outcome,
            'a pixel placement against HUD cannot borrow the row-one Scene')

    def test_eighteen_ink_price_support_and_dual_floor_moments_are_inherited(self):
        for mirror in (False, True):
            for fragment in (0, 1, 2, 17):
                with self.subTest(mirror=mirror, fragment=fragment):
                    self.negative(mirror=mirror, fragment=fragment, moment=True)
        for fragment in (18, 24):
            with self.subTest(fourth_price=fragment):
                value = self.assess(fragment=fragment)
                self.assertNotEqual(3, value.outcome)
                self.assertEqual((18, 4, 1), (value.certificate.policy_version,
                    value.certificate.observed_prices, value.certificate.unmatched_prices))
        self.assertNotEqual(3, self.assess(moment=True, fault='mixture').outcome,
            'matching mean color cannot hide unrelated pixel hues')

    def test_strong_target_and_priceless_candidate_precede_any_negative(self):
        for named in (False, True):
            with self.subTest(named=named):
                value = self.assess(target=True, target_name=named, fragment=2)
                self.assertEqual(2, value.outcome)
                self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)))
        value = self.assess(target=True, target_name=False, missing_price=1)
        self.assertEqual(1, value.outcome,
            'a genuine target image without its price remains a held candidate')
        self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)))
        pixels = bytearray(shop_pixels(target=True, target_name=False))
        # A fixed sparse omission degrades the public target sprite; the
        # measured candidate must survive even with its complete own price.
        for i, (x, y, _r, _g, _b) in enumerate(FEATURES['icons'][1]['bright']):
            if i % 8 == 0:
                offer._put(pixels, 358+x, 230+y, (0, 0, 0))
        value = self.assess(pixels=bytes(pixels))
        self.assertEqual(1, value.outcome)
        score = max(value.rows[i].slots[s].icon_score
            for i in range(value.row_count) for s in range(3))
        self.assertGreaterEqual(score, .80)
        self.assertLess(score, .94)
        self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)))

    def test_numeric_evidence_cannot_be_forged_or_relabelled_from_another_row(self):
        base = self.negative()
        changes = single.NativeSingleOffer108Tests.certificate_mutations()
        changes.update({
            # Numeric data has no wall grid: agreement with actual geometry
            # is the independent Controller validator's responsibility.
            'policy_mode_mismatch': lambda v: setattr(v.certificate, 'policy_version', 17),
            'row0': lambda v: setattr(v.rows[v.selected_row], 'sy', 159),
            'row2': lambda v: setattr(v.rows[v.selected_row], 'sy', 231),
            'overflow': lambda v: setattr(v.rows[v.selected_row], 'sy', 2147483647),
        })
        for label, mutate in changes.items():
            value = Result.from_buffer_copy(base)
            mutate(value)
            with self.subTest(forgery=label):
                self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(value)))


if __name__ == '__main__':
    unittest.main()
