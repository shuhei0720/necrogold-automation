"""Observed lower side opening; procedural future views are not phone results."""
import ctypes as C
from pathlib import Path
import tempfile
import unittest

from tests.test_native_ring094 import Result
from tests import test_native_ring_bank094 as legacy_bank
from tests.test_native_ring_bank094 import bank_data
from tests import test_native_structural_shop096 as structural096
from tests import test_native_side_shop100 as side100
from tests.test_native_perception import NativeScene
from tests.test_target_assessment087 import WIDTH, FEATURES

ROOT = Path(__file__).resolve().parents[1]


class NativeShopGeometry101Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='lower-side-shop101-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.lib = legacy_bank.NativeRingBank094Tests.build_library(
            ROOT/'patches/loopctrl/ngg2/NG2Ring.c', Path(cls.tmp.name)/'ring.so')
        cls.lib.ng2_ring_negative_certificate.argtypes = [C.POINTER(Result)]
        cls.lib.ng2_ring_negative_certificate.restype = C.c_int
        cls.entries = bank_data()['entries'][:3]

    put = staticmethod(side100.NativeSideShop100Tests.put)

    def scene(self, mirror=False, ax=-4, ay=-2, opening=1):
        value = NativeScene(abi_version=1, struct_size=C.sizeof(NativeScene),
                            state=2, gold_state=2, goods=2)
        solid, gate = (ax+4, ax-2) if mirror else (ax-2, ax+4)
        for y in range(ay-1, ay+4):
            self.put(value, solid, y, 2)
        for x in range(ax-2, ax+5):
            self.put(value, x, ay+3, 2)
        self.put(value, gate, ay+1, 2)
        self.put(value, gate, ay+2, opening)
        for x in range(ax, ax+3):
            self.put(value, x, ay, 6)
            if -11<=x<=11 and -5<=ay<=4:
                value.protected_cells[(ay+5)*23+x+11] = 1
        for x in (ax-1, ax+3):
            self.put(value, x, ay, 1)
            if -11<=x<=11 and -5<=ay<=4:
                value.protected_cells[(ay+5)*23+x+11] = 1
        return value

    def pixels(self, left=301, sy=81, **kwargs):
        return structural096.NativeStructuralShop096Tests.pixels(self, left=left, sy=sy, **kwargs)

    assess = side100.NativeSideShop100Tests.assess
    white = staticmethod(side100.NativeSideShop100Tests.white)

    def blank_identity(self, **kwargs):
        return self.pixels(missing_shop_glyph=True, missing_merchant=True, **kwargs)

    def test_observed_twelve_cell_lower_opening_authorizes_only_complete_strip(self):
        for mirror in (False, True):
            for opening in (1, 5):
                scene = self.scene(mirror=mirror, opening=opening)
                before = bytes(scene)
                status, result = self.assess(self.blank_identity(), scene)
                with self.subTest(mirror=mirror, opening=opening):
                    self.assertEqual((0,3,2,5,5,12), (status,result.outcome,result.coverage,
                        result.certificate.policy_version,result.certificate.board_mode,
                        result.certificate.actual_gold_cells),
                        'a fully illuminated shop with opening two cells below offers needs its own proof')
                    self.assertEqual(1, self.lib.ng2_ring_negative_certificate(C.byref(result)))
                    self.assertEqual(before, bytes(scene))
                    self.assertEqual((3,3,0,0), (result.certificate.observed_items,
                        result.certificate.observed_prices,result.certificate.unmatched_prices,
                        result.certificate.unmatched_boards))

    def test_each_positive_wall_and_opening_is_required_despite_equal_gold_count(self):
        supports = {(-6,y) for y in range(-3,2)} | {(x,1) for x in range(-6,1)} | {(0,-1)}
        self.assertEqual(12, len(supports))
        for x,y in sorted(supports):
            for replacement in (0,1,3):
                scene = self.scene(); self.put(scene,x,y,replacement); self.put(scene,10,4,2)
                with self.subTest(cell=(x,y), replacement=replacement):
                    self.assertNotEqual(3, self.assess(self.blank_identity(),scene)[1].outcome)
        for opening in (0,2,3,4,6):
            with self.subTest(opening=opening):
                self.assertNotEqual(3, self.assess(self.blank_identity(),self.scene(opening=opening))[1].outcome)

    def test_caps_items_state_and_mapping_keep_original_shadowed_view_unknown(self):
        for x in (-5,-4,-3,-2,-1):
            for kind in (0,3):
                scene = self.scene(); self.put(scene,x,-2,kind)
                with self.subTest(cell=x, kind=kind):
                    self.assertNotEqual(3, self.assess(self.blank_identity(),scene)[1].outcome)
        # Original217's positive geometry exists, but its right cap is unseen.
        # This procedural shape is not the original device Scene/pixel dump.
        scene = self.scene(); self.put(scene,-6,-5,2); self.put(scene,-6,-4,2); self.put(scene,-1,-2,0)
        status,result = self.assess(self.blank_identity(),scene)
        self.assertEqual((0,0), (status,result.outcome))
        self.assertEqual(0, self.lib.ng2_ring_negative_certificate(C.byref(result)))
        for name in ('state','goods','gold_state'):
            scene = self.scene(); setattr(scene,name,0)
            with self.subTest(field=name):
                self.assertNotEqual(3, self.assess(self.blank_identity(),scene)[1].outcome)
        for left,sy,ax,ay in ((322,81,-4,-2),(466,81,0,-2),
                             (301,105,-4,-2),(301,177,-4,0),
                             (54,81,-11,-2),(752,81,8,-2),(301,0,-4,-4)):
            with self.subTest(left=left,sy=sy):
                self.assertNotEqual(3, self.assess(self.blank_identity(left=left,sy=sy),
                                                   self.scene(ax=ax,ay=ay))[1].outcome)

    def test_complete_pixels_prices_and_unique_faces_are_independent_requirements(self):
        for kwargs in ({'missing_wall':True},{'missing_price':1},
                       {'extra_board':True},{'extra_object':True}):
            with self.subTest(kwargs=kwargs):
                self.assertNotEqual(3, self.assess(self.blank_identity(**kwargs))[1].outcome)
        pixels = bytearray(self.blank_identity())
        for y in range(117,142):
            for x in range(397,422):
                at=4*(y*WIDTH+x); pixels[at:at+4]=bytes((0,0,0,255))
        self.assertNotEqual(3, self.assess(bytes(pixels))[1].outcome,
                            'positive Scene caps cannot substitute for a black raw endcap')
        pixels = bytearray(self.blank_identity())
        for y in range(61,101):
            for x in range(355,391):
                at=4*(y*WIDTH+x); pixels[at:at+4]=bytes((27,17,12,255))
        self.assertNotEqual(3, self.assess(bytes(pixels))[1].outcome)
        pixels = bytearray(self.blank_identity()); self.white(pixels,315,150,3,6)
        result = self.assess(bytes(pixels))[1]
        self.assertNotEqual(3,result.outcome)
        self.assertGreater(result.certificate.unmatched_prices,0)

    def test_full_strip_target_and_strong_word_keep_positive_priority(self):
        for has_name,expected in ((True,2),(False,1)):
            status,result = self.assess(self.blank_identity(target=True,target_name=has_name))
            self.assertEqual((0,expected),(status,result.outcome))
        for sprite in FEATURES['icons']:
            pixels=bytearray(self.blank_identity()); top=116; left=319-sprite['width']//2
            for y in range(top,top+sprite['height']):
                for x in range(left,left+sprite['width']):
                    at=4*(y*WIDTH+x);pixels[at:at+4]=bytes((27,17,12,255))
            for dx,dy,r,g,b in sprite['bright']:
                at=4*((top+dy)*WIDTH+left+dx);pixels[at:at+4]=bytes((r,g,b,255))
            for dx,dy in sprite['dark']:
                at=4*((top+dy)*WIDTH+left+dx);pixels[at:at+4]=bytes((0,0,0,255))
            status,result=self.assess(bytes(pixels))
            with self.subTest(template=(sprite['width'],sprite['height'])):
                self.assertEqual((0,1,5),(status,result.outcome,result.certificate.policy_version))
        pixels=bytearray(self.blank_identity())
        for y in range(64,75):
            for x in range(295,379):
                at=4*(y*WIDTH+x);pixels[at:at+4]=bytes((27,17,12,255))
        for dy,row in enumerate(FEATURES['word']['rows_hex']):
            for dx in range(84):
                if int(row,16)>>dx&1:self.white(pixels,295+dx,64+dy)
        self.assertEqual((0,1), (lambda pair:(pair[0],pair[1].outcome))(self.assess(bytes(pixels))))

    def test_numeric_certificate_and_old_policies_remain_distinct(self):
        status,base=self.assess(self.blank_identity());self.assertEqual((0,3),(status,base.outcome))
        mutations=(('mode',lambda r:setattr(r.certificate,'board_mode',3)),
            ('policy',lambda r:setattr(r.certificate,'policy_version',2)),
            ('gold',lambda r:setattr(r.certificate,'actual_gold_cells',11)),
            ('prices',lambda r:setattr(r.certificate,'unmatched_prices',1)),
            ('boards',lambda r:setattr(r.certificate,'unmatched_boards',1)),
            ('partial',lambda r:setattr(r,'partial_count',1)),
            ('cap',lambda r:setattr(r.certificate.endcaps[1],'black_count',63)),
            ('strip',lambda r:r.certificate.strip_box.__setitem__(3,66)),
            ('face',lambda r:r.certificate.board_boxes[0].__setitem__(2,37)),
            ('identity',lambda r:setattr(r.rows[0].slots[0],'non_target_id',1)),
            ('bound',lambda r:setattr(r.partial[1],'icon_upper_bound',.80)),
            ('word',lambda r:(setattr(r.partial[0],'word_present',1),
                setattr(r.partial[0],'word_iou',.82),setattr(r.partial[0],'word_coverage',.90))))
        for name,mutate in mutations:
            value=Result.from_buffer_copy(base);mutate(value)
            with self.subTest(damage=name):
                self.assertEqual(0,self.lib.ng2_ring_negative_certificate(C.byref(value)))
        old3=structural096.NativeStructuralShop096Tests.scene(self,ay=-2)
        old4=side100.NativeSideShop100Tests.scene(self,ay=-2)
        for scene,policy in ((old3,3),(old4,4)):
            status,result=self.assess(self.blank_identity(),scene)
            self.assertEqual((0,3,policy),(status,result.outcome,result.certificate.policy_version))
        for mode in (0,1):
            status,result=self.assess(self.pixels(),mode=mode)
            self.assertEqual((0,3,1),(status,result.outcome,result.certificate.policy_version))


if __name__=='__main__':unittest.main()
