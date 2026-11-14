"""Observed side-entry shop proof on procedural pixels, never phone accuracy."""
import ctypes as C
from pathlib import Path
import tempfile
import unittest

from tests.test_native_ring094 import Result, Options, Clock, Cancelled
from tests import test_native_ring_bank094 as legacy_bank
from tests.test_native_ring_bank094 import bank_data
from tests import test_native_structural_shop096 as structural096
from tests.test_native_perception import NativeScene
from tests.test_target_assessment087 import WIDTH, HEIGHT, FEATURES

ROOT = Path(__file__).resolve().parents[1]


class NativeSideShop100Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='side-shop100-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.lib = legacy_bank.NativeRingBank094Tests.build_library(
            ROOT/'patches/loopctrl/ngg2/NG2Ring.c', Path(cls.tmp.name)/'ring.so')
        cls.lib.ng2_ring_negative_certificate.argtypes = [C.POINTER(Result)]
        cls.lib.ng2_ring_negative_certificate.restype = C.c_int
        cls.entries = bank_data()['entries'][:3]

    @staticmethod
    def put(scene, x, y, kind):
        if -11<=x<=11 and -5<=y<=4:
            scene.tiles[(y+5)*23+x+11] = kind

    def scene(self, mirror=False, ax=-4, ay=-1, opening=1):
        scene = NativeScene(abi_version=1, struct_size=C.sizeof(NativeScene),
                            state=2, gold_state=2, goods=2)
        solid, gate = (ax+4, ax-2) if mirror else (ax-2, ax+4)
        for y in range(ay-3, ay+2):
            self.put(scene, solid, y, 2)
        for y in (ay-2, ay):
            self.put(scene, gate, y, 2)
        self.put(scene, gate, ay-1, opening)
        for x in range(ax, ax+3):
            self.put(scene, x, ay, 6)
            if -11<=x<=11 and -5<=ay<=4:
                scene.protected_cells[(ay+5)*23+x+11] = 1
        for x in (ax-1, ax+3):
            self.put(scene, x, ay, 1)
            if -11<=x<=11 and -5<=ay<=4:
                scene.protected_cells[(ay+5)*23+x+11] = 1
        return scene

    def pixels(self, **kwargs):
        return structural096.NativeStructuralShop096Tests.pixels(self, **kwargs)

    def assess(self, pixels=None, scene=None, mode=2, cancelled=False, deadline=False):
        pixels = self.pixels(missing_shop_glyph=True, missing_merchant=True) if pixels is None else pixels
        scene = self.scene() if scene is None else scene
        now = Clock(lambda _: 100)
        cancel = Cancelled(lambda _: int(cancelled))
        options = Options(abi=1, size=C.sizeof(Options), mode=mode,
                          deadline_ns=100 if deadline else 1000000000,
                          now_ns=now, cancelled=cancel, scene=C.addressof(scene), fast=1)
        result = Result()
        buf = C.create_string_buffer(pixels)
        status = self.lib.ng2_ring_assess_rgba(buf, len(pixels), WIDTH*4,
                                              C.byref(options), C.byref(result))
        return status, result

    def test_seven_observed_side_supports_authorize_complete_target_only_strip(self):
        status, result = self.assess()
        self.assertEqual((0, 3, 2, 4, 4), (status, result.outcome, result.coverage,
                         result.certificate.policy_version, result.certificate.board_mode),
                         'goods below a fully observed side entry need their own finite layout proof')
        self.assertEqual(7, result.certificate.actual_gold_cells)
        self.assertEqual(1, self.lib.ng2_ring_negative_certificate(C.byref(result)))
        for slot in result.rows[result.selected_row].slots:
            self.assertEqual((3, 0, 0), (slot.kind, slot.non_target_id, slot.ignored_container_id))
        self.assertEqual((3, 3, 0), (result.certificate.observed_items,
                         result.certificate.observed_prices, result.certificate.unmatched_prices))

    def test_mirror_opening_material_and_source_protection_are_preserved(self):
        for mirror in (False, True):
            for opening in (1, 5):
                scene = self.scene(mirror=mirror, opening=opening)
                self.put(scene, 10, 4, 2)
                before = bytes(scene)
                status, result = self.assess(scene=scene)
                with self.subTest(mirror=mirror, opening=opening):
                    self.assertEqual((0, 3, 4, 8), (status, result.outcome,
                                     result.certificate.policy_version, result.certificate.actual_gold_cells))
                    self.assertEqual(before, bytes(scene))

    def test_each_side_support_and_observed_opening_is_required_despite_same_gold_count(self):
        supports = {(-6, y) for y in range(-4, 1)} | {(0, -3), (0, -1)}
        for x, y in sorted(supports):
            for kind in (0, 1, 4):
                scene = self.scene()
                self.put(scene, x, y, kind)
                self.put(scene, 10, 4, 2)
                with self.subTest(point=(x, y), replacement=kind):
                    self.assertNotEqual(3, self.assess(scene=scene)[1].outcome)
        for kind in (0, 2, 3, 4, 6):
            with self.subTest(opening=kind):
                self.assertNotEqual(3, self.assess(scene=self.scene(opening=kind))[1].outcome)

    def test_item_cap_scene_ties_and_clipped_support_are_held(self):
        for x in (-5, -4, -3, -2, -1):
            scene = self.scene()
            self.put(scene, x, -1, 0)
            with self.subTest(missing=x):
                self.assertNotEqual(3, self.assess(scene=scene)[1].outcome)
        for name in ('state', 'goods', 'gold_state'):
            scene = self.scene()
            setattr(scene, name, 0)
            with self.subTest(field=name):
                self.assertNotEqual(3, self.assess(scene=scene)[1].outcome)
        for left, sy, ax, ay in ((322,117,-4,-1), (301,105,-4,-1),
                                (54,117,-11,-1), (301,18,-4,-5), (752,117,8,-1)):
            status, result = self.assess(
                self.pixels(left=left, sy=sy, missing_shop_glyph=True, missing_merchant=True),
                self.scene(ax=ax, ay=ay))
            with self.subTest(left=left, sy=sy):
                self.assertEqual(0, status)
                self.assertNotEqual(3, result.outcome)

    @staticmethod
    def white(pixels, x, y, width=1, height=1):
        for yy in range(y, y+height):
            for xx in range(x, x+width):
                at = 4*(yy*WIDTH+xx)
                pixels[at:at+4] = bytes((245,245,245,255))

    def test_isolated_item_edge_is_not_a_price_but_fourth_supported_group_anywhere_is_held(self):
        pixels = bytearray(self.pixels(missing_shop_glyph=True, missing_merchant=True))
        self.white(pixels, 301+88, 117+69)
        status, result = self.assess(bytes(pixels))
        self.assertEqual((0,3,4,3,0), (status, result.outcome, result.certificate.policy_version,
                         result.certificate.observed_prices, result.certificate.unmatched_prices))
        for top in (117+69, 117+78):
            pixels = bytearray(self.pixels(missing_shop_glyph=True, missing_merchant=True))
            self.white(pixels, 301+14, top, 3, 6)
            status, result = self.assess(bytes(pixels))
            with self.subTest(fourth_price_top=top):
                self.assertEqual(0, status)
                self.assertNotEqual(3, result.outcome)
                self.assertTrue(result.certificate.failure_flags & 64)
                self.assertGreater(result.certificate.unmatched_prices, 0)

    def test_missing_shifted_price_extra_board_item_or_endcap_are_held(self):
        for kwargs in ({'missing_price':1}, {'extra_board':True}, {'extra_object':True}, {'missing_wall':True}):
            with self.subTest(kwargs=kwargs):
                self.assertNotEqual(3, self.assess(self.pixels(
                    missing_shop_glyph=True, missing_merchant=True, **kwargs))[1].outcome)
        pixels = bytearray(self.pixels(missing_shop_glyph=True, missing_merchant=True))
        # Shift the middle seven-pixel price down beyond a common nine-pixel row.
        for y in range(117+78, 117+85):
            for x in range(301+36-7, 301+36+9):
                at = 4*(y*WIDTH+x)
                to = 4*((y+5)*WIDTH+x)
                pixels[to:to+4] = pixels[at:at+4]
                pixels[at:at+4] = bytes((27,17,12,255))
        self.assertNotEqual(3, self.assess(bytes(pixels))[1].outcome)

    def test_target_icon_candidate_and_strong_name_keep_positive_priority(self):
        for has_name, expected in ((True,2),(False,1)):
            status, result = self.assess(self.pixels(target=True, target_name=has_name,
                missing_shop_glyph=True, missing_merchant=True))
            self.assertEqual((0,expected),(status,result.outcome))
        pixels = bytearray(self.pixels(missing_shop_glyph=True, missing_merchant=True))
        for y in range(100,111):
            for x in range(295,379):
                at=4*(y*WIDTH+x);pixels[at:at+4]=bytes((27,17,12,255))
        for dy,row in enumerate(FEATURES['word']['rows_hex']):
            for dx in range(84):
                if int(row,16)>>dx&1:
                    self.white(pixels,295+dx,100+dy)
        status,result=self.assess(bytes(pixels))
        self.assertEqual((0,1),(status,result.outcome))

    def test_full_sweep_holds_each_target_template_between_nominal_price_centres(self):
        for sprite in FEATURES['icons']:
            pixels = bytearray(self.pixels(missing_shop_glyph=True, missing_merchant=True))
            cx, top = 301+18, 117+35
            left = cx-sprite['width']//2
            for y in range(top,top+sprite['height']):
                for x in range(left,left+sprite['width']):
                    at=4*(y*WIDTH+x);pixels[at:at+4]=bytes((27,17,12,255))
            for dx,dy,r,g,b in sprite['bright']:
                at=4*((top+dy)*WIDTH+left+dx);pixels[at:at+4]=bytes((r,g,b,255))
            for dx,dy in sprite['dark']:
                at=4*((top+dy)*WIDTH+left+dx);pixels[at:at+4]=bytes((0,0,0,255))
            status,result=self.assess(bytes(pixels))
            with self.subTest(template=(sprite['width'],sprite['height'])):
                self.assertEqual((0,1,4),(status,result.outcome,result.certificate.policy_version),
                    'the unmasked dense policy4 sweep must find a target between nominal slot probes')

    def test_policy4_numeric_certificate_rejects_forgery_and_old_policy3_stays_distinct(self):
        status, base = self.assess()
        self.assertEqual((0,3),(status,base.outcome))
        changes = (
            ('policy', lambda r:setattr(r.certificate,'policy_version',5)),
            ('mode', lambda r:setattr(r.certificate,'board_mode',3)),
            ('gold', lambda r:setattr(r.certificate,'actual_gold_cells',6)),
            ('price', lambda r:setattr(r.certificate,'unmatched_prices',1)),
            ('board', lambda r:setattr(r.certificate,'unmatched_boards',1)),
            ('body', lambda r:setattr(r.certificate,'scene_goods',1)),
            ('strip', lambda r:r.certificate.strip_box.__setitem__(3,66)),
            ('merchant', lambda r:setattr(r.certificate,'merchant_score',.94)),
            ('partial', lambda r:setattr(r,'partial_count',1)),
            ('identity', lambda r:setattr(r.rows[0].slots[0],'non_target_id',1)),
            ('bound', lambda r:setattr(r.partial[0],'icon_upper_bound',.80)),
            ('word', lambda r:(setattr(r.partial[0],'word_present',1),
                setattr(r.partial[0],'word_iou',.82),setattr(r.partial[0],'word_coverage',.90))),
            ('price baseline', lambda r:r.certificate.price_boxes[0].__setitem__(1,117+69)),
        )
        for name, change in changes:
            result = Result.from_buffer_copy(base)
            change(result)
            with self.subTest(damage=name):
                self.assertEqual(0,self.lib.ng2_ring_negative_certificate(C.byref(result)))
        old_scene = structural096.NativeStructuralShop096Tests.scene(self)
        status, result = self.assess(scene=old_scene)
        self.assertEqual((0,3,3),(status,result.outcome,result.certificate.policy_version))
        for mode in (0,1):
            status,result = self.assess(self.pixels(),mode=mode)
            self.assertEqual((0,3,1),(status,result.outcome,result.certificate.policy_version))
        self.assertEqual((1,0,0), self.result_tuple(self.assess(cancelled=True)))
        self.assertEqual((2,0,0), self.result_tuple(self.assess(deadline=True)))

    @staticmethod
    def result_tuple(pair):
        status,result=pair
        return status,result.outcome,result.coverage
