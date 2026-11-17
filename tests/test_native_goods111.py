"""Independent complete offer proofs; procedural pixels are not phone acceptance.

TEST110 showed a side-policy price hold masking a valid footprint proof and an
upper side opening two cells above the offer row. Expectations follow the
observed three-offer geometry and unchanged exhaustive target search contract.
"""
import ctypes as C
import os
from pathlib import Path
import tempfile
import unittest

from tests import test_native_offer_coverage104 as offer
from tests import test_native_ring_bank094 as bank
from tests.test_native_ring094 import Result, Options, Clock, Cancelled
from tests.test_target_assessment087 import WIDTH, FEATURES

ROOT = Path(__file__).resolve().parents[1]


def upper_scene(mirror=False, opening=1, ax=-4, ay=2):
    scene = offer.shop_scene(ax=ax, ay=ay)
    # shop_scene's context GOLD is replaced by the positively observed roof,
    # solid side and two posts around the higher opening.
    offer.set_tile(scene, ax+4, ay, 0)
    solid, gate = (ax+4, ax-2) if mirror else (ax-2, ax+4)
    for y in range(ay-5, ay+3):
        offer.set_tile(scene, solid, y, 2)
    for k in range(5):
        offer.set_tile(scene, solid-k if mirror else solid+k, ay-5, 2)
    for y in (ay-3, ay-1):
        offer.set_tile(scene, gate, y, 2)
    offer.set_tile(scene, gate, ay-2, opening)
    return scene


def paired_scene():
    """Both old side4 and independent footprint9 premises hold."""
    scene = offer.shop_scene(ax=-4, ay=1)
    for y in range(-2, 3):
        offer.set_tile(scene, -6, y, 2)
    for y in (-1, 1):
        offer.set_tile(scene, 0, y, 2)
    offer.set_tile(scene, 0, 0, 1)
    return scene


def prices(pixels, left, sy, middle_delta=7):
    """Three complete prices: ordinary +75, center +82, all inside old B."""
    pixels = bytearray(pixels)
    for slot in range(3):
        cx=left+36*slot; white=[]
        for y in range(sy+78, sy+85):
            for x in range(cx-7, cx+9):
                at=4*(y*WIDTH+x)
                if min(pixels[at:at+3])>140:
                    white.append((x,y))
                pixels[at:at+4]=bytes((27,17,12,255))
        for x,y in white:
            to=4*((y-3+(middle_delta if slot==1 else 0))*WIDTH+x)
            pixels[to:to+4]=bytes((245,245,245,255))
    return bytes(pixels)


class NativeGoods111Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='goods111-')
        cls.addClassCleanup(cls.tmp.cleanup)
        source=Path(os.environ.get('NECRO111_GOODS_RING_SOURCE',
            str(ROOT/'patches/loopctrl/ngg2/NG2Ring.c')))
        cls.lib=bank.NativeRingBank094Tests.build_library(source,Path(cls.tmp.name)/'ring.so')
        cls.lib.ng2_ring_negative_certificate.argtypes=[C.POINTER(Result)]
        cls.lib.ng2_ring_negative_certificate.restype=C.c_int

    def assess(self, scene=None, pixels=None, sy=225, **kwargs):
        scene=upper_scene() if scene is None else scene
        pixels=prices(offer.shop_pixels(left=301,sy=sy),301,sy) if pixels is None else pixels
        return offer.normal_assess(self.lib,pixels,scene,**kwargs)

    def test_incomplete_earlier_side_does_not_hide_independent_complete_footprint(self):
        status,result=self.assess(scene=paired_scene(),sy=189)
        self.assertEqual((0,3,2,9),(status,result.outcome,result.coverage,
            result.certificate.policy_version),
            'an earlier common-price-row UNKNOWN must not discard a complete independent proof')
        self.assertEqual(1,self.lib.ng2_ring_negative_certificate(C.byref(result)))
        self.assertEqual(3,result.certificate.observed_prices)
        self.assertGreater(result.certificate.price_boxes[1][1],result.certificate.price_boxes[0][1])

    def test_observed_high_side_opening_certifies_full_three_offer_strip(self):
        status,result=self.assess()
        self.assertEqual((0,3,2,15),(status,result.outcome,result.coverage,
            result.certificate.policy_version),
            'a full row at225 needs its observed higher opening proof, not a weaker glyph threshold')
        self.assertEqual((14,3,3,0),(result.certificate.actual_gold_cells,
            result.certificate.observed_items,result.certificate.observed_prices,
            result.certificate.failure_flags))
        self.assertEqual(1,self.lib.ng2_ring_negative_certificate(C.byref(result)))

    def test_upper_opening_is_mirrored_and_keeps_each_support(self):
        for mirror in (False,True):
            for opening in (1,5):
                scene=upper_scene(mirror,opening);before=bytes(scene)
                with self.subTest(mirror=mirror,opening=opening):
                    self.assertEqual((0,3,15),self.result(self.assess(scene=scene)))
                    self.assertEqual(before,bytes(scene))
        support={(-6,y) for y in range(-3,5)}|{(x,-3) for x in range(-6,-1)}|{(0,-1),(0,1)}
        self.assertEqual(14,len(support))
        for x,y in sorted(support):
            scene=upper_scene();offer.set_tile(scene,x,y,0);offer.set_tile(scene,10,4,2)
            with self.subTest(missing=(x,y)):
                self.assertNotEqual(3,self.assess(scene=scene)[1].outcome)
        for kind in (0,2,3,4,6):
            scene=upper_scene(opening=kind)
            with self.subTest(opening=kind):self.assertNotEqual(3,self.assess(scene=scene)[1].outcome)

    def test_exact_projection_and_lower_price_floors_are_required(self):
        for x,y in [*((x,2) for x in range(-5,0)),*((x,3) for x in range(-4,-1))]:
            scene=upper_scene();offer.set_tile(scene,x,y,0)
            with self.subTest(missing=(x,y)):
                self.assertNotEqual(3,self.assess(scene=scene)[1].outcome)
        for index in (0,7*23+7):
            scene=upper_scene();scene.protected_cells[index]^=1
            with self.subTest(protection=index):self.assertNotEqual(3,self.assess(scene=scene)[1].outcome)
        scene=upper_scene();offer.set_tile(scene,8,3,6)
        self.assertNotEqual(3,self.assess(scene=scene)[1].outcome)

    def test_each_raw_price_cap_extra_board_and_extra_object_remains_a_hold(self):
        for kwargs in ({'missing_price':1},{'missing_wall':True},{'extra_board':True},{'extra_object':True}):
            pixels=prices(offer.shop_pixels(left=301,sy=225,**kwargs),301,225)
            with self.subTest(kwargs=kwargs):self.assertNotEqual(3,self.assess(pixels=pixels)[1].outcome)

    def test_upper_entire_strip_preserves_each_target_between_nominal_prices(self):
        for sprite in FEATURES['icons']:
            pixels=bytearray(prices(offer.shop_pixels(left=301,sy=225),301,225))
            left,top=319-sprite['width']//2,260
            for y in range(top,top+sprite['height']):
                for x in range(left,left+sprite['width']):
                    at=4*(y*WIDTH+x);pixels[at:at+4]=bytes((27,17,12,255))
            for dx,dy,r,g,b in sprite['bright']:
                at=4*((top+dy)*WIDTH+left+dx);pixels[at:at+4]=bytes((r,g,b,255))
            for dx,dy in sprite['dark']:
                at=4*((top+dy)*WIDTH+left+dx);pixels[at:at+4]=bytes((0,0,0,255))
            status,result=self.assess(pixels=bytes(pixels))
            with self.subTest(template=(sprite['width'],sprite['height'])):
                self.assertEqual((0,1),(status,result.outcome),
                    'the exhaustive raw strip must retain a target outside the three price probes')

    def test_first_incomplete_proof_is_kept_when_no_independent_proof_completes(self):
        scene=paired_scene();offer.set_tile(scene,-3,2,0)
        status,result=self.assess(scene=scene,sy=189)
        self.assertEqual((0,0,1,4),(status,result.outcome,result.coverage,result.certificate.policy_version))
        self.assertTrue(result.certificate.failure_flags&64)

    def test_target_and_candidate_priority_and_failed_jobs_are_preserved(self):
        for name,outcome in ((True,2),(False,1)):
            pixels=offer.shop_pixels(left=301,sy=225,target=True,target_name=name,
                missing_price=None if name else 1)
            status,result=self.assess(pixels=pixels)
            with self.subTest(name=name):self.assertEqual((0,outcome),(status,result.outcome))
        for kwargs,status in (({'cancelled':True},1),({'deadline':True},2)):
            returned,result=self.assess(**kwargs)
            self.assertEqual((status,status,0),(returned,result.status,result.outcome))

    def test_cancellation_or_deadline_during_independent_fallback_is_not_unknown_success(self):
        pixels=prices(offer.shop_pixels(left=301,sy=189),301,189)
        scene=paired_scene()
        for fault in ('cancel','deadline'):
            result=Result();seen=[0]
            def reached_first_proof():
                if seen[0] or (result.certificate.policy_version==4 and result.certificate.observed_items==3):
                    seen[0]+=1
                return seen[0]>=2
            now=Clock(lambda _: 1000000000 if fault=='deadline' and reached_first_proof() else 100)
            cancel=Cancelled(lambda _: int(fault=='cancel' and reached_first_proof()))
            options=Options(abi=1,size=C.sizeof(Options),mode=2,deadline_ns=1000000000,
                now_ns=now,cancelled=cancel,scene=C.addressof(scene),fast=1)
            status=self.lib.ng2_ring_assess_rgba(pixels,len(pixels),3584,C.byref(options),C.byref(result))
            with self.subTest(fault=fault):
                self.assertGreaterEqual(seen[0],2,'the first incomplete layout must actually have run')
                self.assertEqual((1,1) if fault=='cancel' else (2,2),(status,result.status))
                self.assertNotEqual(3,result.outcome)

    def test_upper_numeric_certificate_rejects_forged_fields(self):
        status,base=self.assess();self.assertEqual((0,3),(status,base.outcome))
        mutations=(
            lambda r:setattr(r.certificate,'policy_version',16),
            lambda r:setattr(r.certificate,'board_mode',9),
            lambda r:setattr(r.certificate,'actual_gold_cells',13),
            lambda r:setattr(r.certificate,'accepted_rows',2),
            lambda r:setattr(r.certificate,'unmatched_prices',1),
            lambda r:setattr(r.certificate,'unmatched_boards',1),
            lambda r:setattr(r.certificate.endcaps[0],'floor_upper',0),
            lambda r:r.certificate.price_boxes[1].__setitem__(1,225+89),
            lambda r:r.certificate.item_boxes[1].__setitem__(2,35),
            lambda r:setattr(r.rows[0].slots[0],'icon_upper_bound',.8),
            lambda r:setattr(r,'partial_count',1),
        )
        for change in mutations:
            result=Result.from_buffer_copy(base);change(result)
            self.assertEqual(0,self.lib.ng2_ring_negative_certificate(C.byref(result)))

    @staticmethod
    def result(pair):
        status,result=pair
        return status,result.outcome,result.certificate.policy_version


if __name__=='__main__':unittest.main()
