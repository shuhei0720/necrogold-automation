"""Finite observed gold-shop structure; procedural inputs are not phone accuracy."""
import ctypes as C
from pathlib import Path
import tempfile
import unittest

import tests.test_native_ring_bank094 as legacy_bank
from tests.test_native_ring_bank094 import complete_shop, bank_data, auth_data
from tests.test_native_ring094 import Result, Options, Clock, Cancelled
from tests.test_native_perception import NativeScene
from tests.test_target_assessment087 import WIDTH, HEIGHT, FEATURES

ROOT=Path(__file__).resolve().parents[1]


class NativeStructuralShop096Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='structural-shop096-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.lib=legacy_bank.NativeRingBank094Tests.build_library(
            ROOT/'patches/loopctrl/ngg2/NG2Ring.c',Path(cls.tmp.name)/'ring.so')
        cls.lib.ng2_ring_negative_certificate.argtypes=[C.POINTER(Result)]
        cls.lib.ng2_ring_negative_certificate.restype=C.c_int
        cls.entries=bank_data()['entries'][:3]

    def scene(self, mirror=False, ax=-4, ay=-1):
        value=NativeScene(abi_version=1,struct_size=C.sizeof(NativeScene),state=2,gold_state=2,goods=2)
        def put(x,y,kind,protected=0):
            index=(y+5)*23+x+11
            value.tiles[index]=kind;value.protected_cells[index]=protected
        for x in range(ax,ax+3):put(x,ay,6,1)
        put(ax-1,ay,1,1);put(ax+3,ay,1,1)
        reflect=lambda x:2*(ax+1)-x if mirror else x
        for y in range(ay-1,ay+4):put(reflect(ax-2),y,2)
        for x in range(ax-2,ax+4):put(reflect(x),ay+3,2)
        for y in (ay,ay+2):put(reflect(ax+4),y,2)
        put(reflect(ax+4),ay+1,1)
        return value

    def pixels(self, left=301, sy=117, **kwargs):
        source=complete_shop(self.entries,auth=auth_data(),**kwargs)
        # Move the procedural row from360/120 to301/117, aligning the real
        # fixed cell lattice without importing a device image.
        out=bytearray(bytes((0,0,0,255))*(WIDTH*HEIGHT))
        dx,dy=left-360,sy-120
        x0=max(0,-dx);x1=min(WIDTH,WIDTH-dx)
        for y in range(max(0,-dy),min(HEIGHT,HEIGHT-dy)):
            out[4*((y+dy)*WIDTH+x0+dx):4*((y+dy)*WIDTH+x1+dx)]=source[4*(y*WIDTH+x0):4*(y*WIDTH+x1)]
        return bytes(out)

    def assess(self,pixels,scene=None,mode=2):
        scene=scene if scene is not None else self.scene()
        now=Clock(lambda _:100);cancel=Cancelled(lambda _:0)
        options=Options(abi=1,size=C.sizeof(Options),mode=mode,deadline_ns=1000000000,
                        now_ns=now,cancelled=cancel,scene=C.addressof(scene),fast=1)
        result=Result();buf=C.create_string_buffer(pixels)
        status=self.lib.ng2_ring_assess_rgba(buf,len(pixels),WIDTH*4,C.byref(options),C.byref(result))
        return status,result

    def test_complete_structure_authorizes_without_shop_or_merchant_pixel_identity(self):
        status,result=self.assess(self.pixels(missing_shop_glyph=True,wrong_merchant=True))
        self.assertEqual((0,3,2,3),(status,result.outcome,result.coverage,result.certificate.policy_version))
        self.assertEqual(3,result.certificate.board_mode)
        self.assertEqual(1,self.lib.ng2_ring_negative_certificate(C.byref(result)))
        self.assertEqual(0,result.certificate.merchant_score)
        self.assertEqual(0,result.certificate.merchant_coverage)
        self.assertEqual((0,0,0,0),tuple(result.certificate.merchant_box))

    @staticmethod
    def set_tile(scene,x,y,kind):
        scene.tiles[(y+5)*23+x+11]=kind

    def test_mirrored_openings_and_projected_protection_are_preserved(self):
        pixels=self.pixels(missing_shop_glyph=True,wrong_merchant=True)
        for mirror in (False,True):
            for opening in (1,5):
                scene=self.scene(mirror=mirror)
                self.set_tile(scene,-6 if mirror else 0,0,opening)
                self.set_tile(scene,-10,-4,2)  # Additional actual GOLD is allowed.
                before=bytes(scene)
                status,result=self.assess(pixels,scene)
                self.assertEqual((0,3,3),(status,result.outcome,result.certificate.policy_version))
                self.assertEqual(13,result.certificate.actual_gold_cells)
                self.assertEqual(before,bytes(scene))
                self.assertEqual(1,scene.protected_cells[4*23+6])
                self.assertEqual(1,scene.protected_cells[4*23+10])

    def test_each_required_gold_cell_and_opening_must_be_observed(self):
        pixels=self.pixels(missing_shop_glyph=True,missing_merchant=True)
        support={(-6,y) for y in range(-2,3)}|{(x,2) for x in range(-6,0)}|{(0,-1),(0,1)}
        self.assertEqual(12,len(support))
        for x,y in sorted(support):
            for replacement in (0,1,3):
                scene=self.scene();self.set_tile(scene,x,y,replacement)
                self.set_tile(scene,-10,-4,2)  # Keep the count: location matters.
                with self.subTest(cell=(x,y),replacement=replacement):
                    status,result=self.assess(pixels,scene)
                    self.assertEqual(0,status)
                    self.assertNotEqual(3,result.outcome)
        for kind in (0,2,3,4,6):
            scene=self.scene();self.set_tile(scene,0,0,kind)
            self.assertNotEqual(3,self.assess(pixels,scene)[1].outcome)

    def test_items_caps_scene_state_and_positive_gold_are_independent_requirements(self):
        pixels=self.pixels(missing_shop_glyph=True,missing_merchant=True)
        for x in (-5,-4,-3,-2,-1):
            for kind in (0,3):
                scene=self.scene();self.set_tile(scene,x,-1,kind)
                with self.subTest(cell=x,kind=kind):
                    self.assertNotEqual(3,self.assess(pixels,scene)[1].outcome)
        for field,values in (('state',(0,1)),('goods',(0,1)),('gold_state',(0,1))):
            for value in values:
                scene=self.scene();setattr(scene,field,value)
                with self.subTest(field=field,value=value):
                    self.assertNotEqual(3,self.assess(pixels,scene)[1].outcome)

    def test_half_cell_ties_are_rejected_on_both_signed_axes(self):
        for left,ax in ((322,-4),(322,-3),(466,0),(466,1)):
            status,result=self.assess(self.pixels(left=left,missing_shop_glyph=True,missing_merchant=True),self.scene(ax=ax))
            self.assertEqual(0,status)
            self.assertNotEqual(3,result.outcome)
        for sy,ay in ((105,-2),(105,-1),(177,0),(177,1)):
            status,result=self.assess(self.pixels(sy=sy,missing_shop_glyph=True,missing_merchant=True),self.scene(ay=ay))
            self.assertEqual(0,status)
            self.assertNotEqual(3,result.outcome)

    def test_complete_board_roi_and_scene_support_must_fit_observed_bounds(self):
        for left,sy in ((54,117),(301,18),(752,117)):
            scene=self.scene()
            status,result=self.assess(self.pixels(left=left,sy=sy,missing_shop_glyph=True,missing_merchant=True),scene)
            self.assertEqual(0,status)
            self.assertNotEqual(3,result.outcome)

    def test_partial_body_missing_price_extra_board_and_absent_item_are_held(self):
        for kwargs in ({'missing_price':1},{'missing_wall':True},{'extra_board':True},{'extra_object':True}):
            with self.subTest(kwargs=kwargs):
                status,result=self.assess(self.pixels(missing_shop_glyph=True,missing_merchant=True,**kwargs))
                self.assertEqual(0,status)
                self.assertNotEqual(3,result.outcome)
        pixels=bytearray(self.pixels(missing_shop_glyph=True,missing_merchant=True))
        for y in range(141,183):
            for x in range(319,355):
                at=4*(y*WIDTH+x);pixels[at:at+4]=bytes((27,17,12,255))
        self.assertNotEqual(3,self.assess(bytes(pixels))[1].outcome)

    def test_target_between_prices_and_observed_name_veto_are_never_masked(self):
        for has_name,expected in ((True,2),(False,1)):
            status,result=self.assess(self.pixels(target=True,target_name=has_name,missing_shop_glyph=True,missing_merchant=True))
            self.assertEqual((0,expected),(status,result.outcome))
        pixels=bytearray(self.pixels(missing_shop_glyph=True,missing_merchant=True))
        sp=FEATURES['icons'][1];sx=319-sp['width']//2;iy=152
        for y in range(iy,iy+sp['height']):
            for x in range(sx,sx+sp['width']):
                at=4*(y*WIDTH+x);pixels[at:at+4]=bytes((27,17,12,255))
        for dx,dy,r,g,b in sp['bright']:
            at=4*((iy+dy)*WIDTH+sx+dx);pixels[at:at+4]=bytes((r,g,b,255))
        for dx,dy in sp['dark']:
            at=4*((iy+dy)*WIDTH+sx+dx);pixels[at:at+4]=bytes((0,0,0,255))
        status,result=self.assess(bytes(pixels));self.assertEqual((0,1),(status,result.outcome))
        pixels=bytearray(self.pixels(missing_shop_glyph=True,missing_merchant=True))
        for y in range(100,111):
            for x in range(295,379):
                at=4*(y*WIDTH+x);pixels[at:at+4]=bytes((27,17,12,255))
        for dy,row in enumerate(FEATURES['word']['rows_hex']):
            for dx in range(84):
                if int(row,16)>>dx&1:
                    at=4*((100+dy)*WIDTH+295+dx);pixels[at:at+4]=bytes((245,245,245,255))
        status,result=self.assess(bytes(pixels));self.assertEqual((0,1),(status,result.outcome))

    def test_unmatched_items_is_preserved_diagnostic_only_under_policy3(self):
        pixels=bytearray(self.pixels())
        for y in range(141,151):
            for x in range(261,282):
                if (x+2*y)%3:
                    at=4*(y*WIDTH+x);pixels[at:at+4]=bytes((245,245,245,255))
        status,result=self.assess(bytes(pixels))
        self.assertEqual((0,3,3),(status,result.outcome,result.certificate.policy_version))
        self.assertGreater(result.certificate.unmatched_items,0)
        self.assertEqual(1,self.lib.ng2_ring_negative_certificate(C.byref(result)))
        legacy=NativeScene(abi_version=1,struct_size=C.sizeof(NativeScene),state=2,gold_state=2,goods=2)
        legacy.tiles[0]=2
        status,old=self.assess(bytes(pixels),legacy)
        self.assertEqual((0,2),(status,old.certificate.policy_version))
        self.assertNotEqual(3,old.outcome)
        self.assertGreater(old.certificate.unmatched_items,0)

    def test_certificate3_retains_all_numeric_identity_and_coverage_guards(self):
        status,base=self.assess(self.pixels(missing_shop_glyph=True,missing_merchant=True))
        self.assertEqual((0,3),(status,base.outcome))
        mutations=(('negative diagnostic',lambda r:setattr(r.certificate,'unmatched_items',-1)),
            ('large diagnostic',lambda r:setattr(r.certificate,'unmatched_items',503)),
            ('fake merchant',lambda r:setattr(r.certificate,'merchant_score',.94)),
            ('fake glyph',lambda r:r.certificate.sign_iou.__setitem__(0,.94)),
            ('fake border',lambda r:r.certificate.board_edge_counts[0].__setitem__(0,1)),
            ('old board authority',lambda r:setattr(r.certificate,'board_mode',1)),
            ('bad policy',lambda r:setattr(r.certificate,'policy_version',4)),
            ('insufficient gold',lambda r:setattr(r.certificate,'actual_gold_cells',11)),
            ('partial body',lambda r:setattr(r.certificate,'scene_goods',1)),
            ('bad physical face',lambda r:r.certificate.board_boxes[0].__setitem__(2,37)),
            ('bad complete strip',lambda r:r.certificate.strip_box.__setitem__(3,66)),
            ('missing cell',lambda r:setattr(r,'partial_count',1)),
            ('price overflow',lambda r:r.certificate.price_boxes[0].__setitem__(0,313)),
            ('legacy identity',lambda r:setattr(r.rows[0].slots[0],'non_target_id',1)),
            ('target bound',lambda r:setattr(r.partial[1],'icon_upper_bound',.80)),
            ('strong word',lambda r:(setattr(r.partial[0],'word_present',1),setattr(r.partial[0],'word_iou',.82),setattr(r.partial[0],'word_coverage',.90))))
        for name,mutate in mutations:
            value=Result.from_buffer_copy(base);mutate(value)
            with self.subTest(name=name):self.assertEqual(0,self.lib.ng2_ring_negative_certificate(C.byref(value)))
        for count in (0,1,502):
            value=Result.from_buffer_copy(base);value.certificate.unmatched_items=count
            self.assertEqual(1,self.lib.ng2_ring_negative_certificate(C.byref(value)))

    def test_legacy_modes_and_policy2_fallback_keep_their_existing_authority(self):
        pixels=self.pixels()
        for mode in (0,1):
            status,result=self.assess(pixels,mode=mode)
            self.assertEqual((0,3,1),(status,result.outcome,result.certificate.policy_version))
        legacy=NativeScene(abi_version=1,struct_size=C.sizeof(NativeScene),state=2,gold_state=2,goods=2)
        legacy.tiles[0]=2
        status,result=self.assess(pixels,legacy)
        self.assertEqual((0,3,2),(status,result.outcome,result.certificate.policy_version))

    def test_wider_extra_observed_sign_is_not_discarded_by_selected_face_roi(self):
        pixels=bytearray(self.pixels(missing_shop_glyph=True,missing_merchant=True))
        for y in range(166,195):
            for x in range(577,625):
                at=4*(y*WIDTH+x);pixels[at:at+4]=bytes((220,210,10,255))
        status,result=self.assess(bytes(pixels))
        self.assertEqual(0,status)
        self.assertNotEqual(3,result.outcome)
