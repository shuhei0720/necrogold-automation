"""Independent observed three-offer footprint; procedural pixels are not phone results."""
import ctypes as C
import os
from pathlib import Path
import tempfile
import unittest

from tests.test_native_ring094 import Result
from tests import test_native_ring_bank094 as bank094
from tests.test_native_ring_bank094 import bank_data,auth_data,complete_shop
from tests.test_native_perception import NativeScene
from tests.test_native_shop_coverage102 import draw_faces,normal_assess,_put
from tests.test_target_assessment087 import WIDTH,HEIGHT,FEATURES

ROOT=Path(__file__).resolve().parents[1]


def set_tile(scene,x,y,kind):
    if -11<=x<=11 and -5<=y<=4:scene.tiles[(y+5)*23+x+11]=kind


def shop_scene(ax=-3,ay=-3):
    scene=NativeScene(abi_version=1,struct_size=C.sizeof(NativeScene),state=2,goods=2,gold_state=2)
    set_tile(scene,ax+4,ay,2)
    for x in range(ax,ax+3):
        set_tile(scene,x,ay,6);set_tile(scene,x,ay+1,1)
        for dx,dy in ((0,0),(-1,0),(1,0),(0,-1),(0,1)):
            if -11<=x+dx<=11 and -5<=ay+dy<=4:scene.protected_cells[(ay+dy+5)*23+x+dx+11]=1
    for x in (ax-1,ax+3):set_tile(scene,x,ay,1)
    return scene


def shop_pixels(left=339,sy=43,faces=None,closed_container=False,**kwargs):
    entries=bank_data()['entries'][:3]
    if closed_container:entries=[*entries[:2],next(e for e in bank_data()['entries'] if e['id']==9)]
    source=complete_shop(entries,auth=auth_data(),missing_shop_glyph=True,missing_merchant=True,**kwargs)
    pixels=bytearray(bytes((0,0,0,255))*(WIDTH*HEIGHT));dx,dy=left-360,sy-120
    x0,x1=max(0,-dx),min(WIDTH,WIDTH-dx)
    for y in range(max(0,-dy),min(HEIGHT,HEIGHT-dy)):
        pixels[4*((y+dy)*WIDTH+x0+dx):4*((y+dy)*WIDTH+x1+dx)]=source[4*(y*WIDTH+x0):4*(y*WIDTH+x1)]
    full=(-15,-14,30,29);draw_faces(pixels,left,sy,faces if faces is not None else (full,full))
    if kwargs.get('target') and kwargs.get('target_name',True):
        for yy,row in enumerate(FEATURES['word']['rows_hex']):
            for xx in range(84):
                if int(row,16)>>xx&1:_put(pixels,left-6+xx,sy+7+yy,(245,245,245))
    return bytes(pixels)


class NativeOfferCoverage104Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='offer-coverage104-');cls.addClassCleanup(cls.tmp.cleanup)
        source=Path(os.environ.get('NECRO104_RING_SOURCE',str(ROOT/'patches/loopctrl/ngg2/NG2Ring.c')))
        cls.lib=bank094.NativeRingBank094Tests.build_library(source,Path(cls.tmp.name)/'ring.so')
        cls.lib.ng2_ring_negative_certificate.argtypes=[C.POINTER(Result)]
        cls.lib.ng2_ring_negative_certificate.restype=C.c_int

    scene=staticmethod(shop_scene)
    pixels=staticmethod(shop_pixels)

    def assess(self,pixels=None,scene=None,**kwargs):
        return normal_assess(self.lib,self.pixels() if pixels is None else pixels,
            self.scene() if scene is None else scene,**kwargs)

    def test_observed_price_floor_footprint_certifies_without_outside_wall_shape(self):
        scene=self.scene();before=bytes(scene);status,result=self.assess(scene=scene)
        self.assertEqual((0,3,2,9,9),(status,result.outcome,result.coverage,
            result.certificate.policy_version,result.certificate.board_mode),
            'three observed supporting floors authenticate complete offers independently of outside walls')
        self.assertEqual(1,result.certificate.actual_gold_cells)
        self.assertEqual(1,self.lib.ng2_ring_negative_certificate(C.byref(result)))
        self.assertEqual(before,bytes(scene))
        self.assertEqual((0,0),(result.certificate.merchant_score,result.certificate.merchant_coverage))
        scene=self.scene();set_tile(scene,1,-3,0);set_tile(scene,10,4,2)
        self.assertEqual(3,self.assess(scene=scene)[1].outcome)

    def test_every_positive_support_floor_item_cap_and_gold_context_is_required(self):
        for x,y in [*( (x,-2) for x in (-3,-2,-1)),*( (x,-3) for x in (-4,-3,-2,-1,0))]:
            for kind in (0,3,4):
                scene=self.scene();set_tile(scene,x,y,kind)
                with self.subTest(cell=(x,y),kind=kind):self.assertNotEqual(3,self.assess(scene=scene)[1].outcome)
        scene=self.scene();set_tile(scene,1,-3,0)
        self.assertNotEqual(3,self.assess(scene=scene)[1].outcome)
        scene=self.scene();set_tile(scene,10,3,6)
        for dx,dy in ((0,0),(-1,0),(1,0),(0,-1),(0,1)):
            scene.protected_cells[(3+dy+5)*23+10+dx+11]=1
        self.assertNotEqual(3,self.assess(scene=scene)[1].outcome,'a fourth observed ITEM remains potential merchandise')
        scene=self.scene();scene.protected_cells[8*23+1]=1
        self.assertNotEqual(3,self.assess(scene=scene)[1].outcome,'unexplained remote protection is not complete coverage')
        for value in (0,2):
            scene=self.scene();scene.protected_cells[3*23+8]=value
            self.assertNotEqual(3,self.assess(scene=scene)[1].outcome,'the ITEM projection must be complete and exact')
        # The actual evidence supports three floors, not invented cap-under floors.
        self.assertEqual(0,self.scene().tiles[3*23+7])
        self.assertEqual(3,self.assess()[1].outcome)

    def test_legacy_wall_mutations_do_not_gain_missing_positive_price_floors(self):
        from tests import test_native_structural_shop096 as old3
        from tests import test_native_side_shop100 as old4
        from tests import test_native_shop_geometry101 as old5
        from tests import test_native_shop_coverage102 as old6
        from tests import test_native_single_sign_shop103 as old7
        from tests import test_native_bottom_shop103 as old8
        builders=[old3.NativeStructuralShop096Tests().scene,old4.NativeSideShop100Tests().scene,
                  old5.NativeShopGeometry101Tests().scene,old6.shop_scene,old7.shop_scene,old8.shop_scene]
        for build in builders:
            scene=build(ax=-3,ay=-3)
            self.assertLess(sum(scene.tiles[3*23+x+11]==1 for x in (-3,-2,-1)),3)
            set_tile(scene,-5,-4,0);set_tile(scene,10,4,2)
            with self.subTest(legacy=build.__qualname__):self.assertNotEqual(3,self.assess(scene=scene)[1].outcome)

    def test_two_real_full_faces_and_no_extra_component_remain_required(self):
        full=(-15,-14,30,29)
        for faces in ((full,None),(None,full),(full,(-15,-4,30,19)),
                      ((-8,-14,17,29),full),(full,(-15,-10,30,29))):
            self.assertNotEqual(3,self.assess(self.pixels(faces=faces))[1].outcome)
        self.assertNotEqual(3,self.assess(self.pixels(extra_board=True))[1].outcome)

    def test_raw_caps_prices_extra_groups_and_lower_container_price_remain_observed(self):
        for kwargs in ({'missing_price':1},{'missing_wall':True},{'extra_object':True}):
            self.assertNotEqual(3,self.assess(self.pixels(**kwargs))[1].outcome)
        # The registered gray body has known white trim and its complete
        # actual price reaches y132 inside the already swept B strip. Version2
        # positively explains both; the old version still cannot certify it.
        status,result=self.assess(self.pixels(closed_container=True))
        self.assertEqual((0,3,9,2),(status,result.outcome,result.certificate.policy_version,
            result.certificate.layout_version))
        self.assertEqual(9,result.rows[result.selected_row].slots[2].ignored_container_id)
        self.assertEqual((405,126,11,7),tuple(result.certificate.price_boxes[2]))
        self.assertEqual(0,result.certificate.unmatched_prices)
        self.assertEqual(1,self.lib.ng2_ring_negative_certificate(C.byref(result)))
        previous=Result.from_buffer_copy(result);previous.certificate.layout_version=1
        self.assertEqual(0,self.lib.ng2_ring_negative_certificate(C.byref(previous)))
        pixels=bytearray(self.pixels());white=[]
        for y in range(121,128):
            for x in range(405,416):
                at=4*(y*WIDTH+x)
                if min(pixels[at:at+3])>140:white.append((x,y))
                _put(pixels,x,y,(27,17,15))
        for x,y in white:_put(pixels,x,y+5,(245,245,245))
        status,result=self.assess(bytes(pixels))
        self.assertEqual((0,3,9),(status,result.outcome,result.certificate.policy_version))
        self.assertEqual((3,0),(result.certificate.observed_prices,result.certificate.unmatched_prices))
        self.assertGreater(result.certificate.price_boxes[2][1],result.certificate.price_boxes[0][1])
        pixels=bytearray(self.pixels())
        for y in range(112,118):
            for x in range(353,356):_put(pixels,x,y,(245,245,245))
        self.assertNotEqual(3,self.assess(bytes(pixels))[1].outcome)

    def test_all_strip_templates_and_strong_name_keep_target_priority(self):
        for name,expected in ((True,2),(False,1)):
            self.assertEqual(expected,self.assess(self.pixels(target=True,target_name=name))[1].outcome)
        for sprite in FEATURES['icons']:
            pixels=bytearray(self.pixels());left=375-sprite['width']//2;top=81
            for y in range(top,top+sprite['height']):
                for x in range(left,left+sprite['width']):_put(pixels,x,y,(27,17,12))
            for dx,dy,r,g,b in sprite['bright']:_put(pixels,left+dx,top+dy,(r,g,b))
            for dx,dy in sprite['dark']:_put(pixels,left+dx,top+dy,(0,0,0))
            self.assertEqual(1,self.assess(bytes(pixels))[1].outcome)
        pixels=bytearray(self.pixels())
        for y in range(67,78):
            for x in range(333,417):_put(pixels,x,y,(27,17,12))
        for dy,row in enumerate(FEATURES['word']['rows_hex']):
            for dx in range(84):
                if int(row,16)>>dx&1:_put(pixels,333+dx,67+dy,(245,245,245))
        self.assertEqual(1,self.assess(bytes(pixels))[1].outcome)

    def test_numeric_certificate_keeps_mapping_finite_score_box_and_absence_guards(self):
        status,base=self.assess();self.assertEqual((0,3,9),(status,base.outcome,base.certificate.policy_version))
        def translate(value,dx=0,dy=0):
            def move(box):
                if box[2]>0:box[0]+=dx;box[1]+=dy
            for row in value.rows[:value.row_count]:
                row.left+=dx;row.sy+=dy
                for slot in row.slots:
                    slot.cx+=dx;slot.sy+=dy
                    for name in ('icon_box','word_box','non_target_icon_box','non_target_name_box','ignored_icon_box'):
                        move(getattr(slot,name))
            for slot in value.partial[:value.partial_count]:
                slot.cx+=dx;slot.sy+=dy
                for name in ('icon_box','word_box','non_target_icon_box','non_target_name_box','ignored_icon_box'):
                    move(getattr(slot,name))
            witness=value.certificate;witness.row[0]+=dx;witness.row[1]+=dy
            move(witness.strip_box);move(witness.merchant_box)
            for name in ('sign_boxes','item_boxes','name_boxes','price_boxes','board_boxes'):
                for box in getattr(witness,name):move(box)
            for end in witness.endcaps:move(end.box)
        mutations=(('policy',lambda r:setattr(r.certificate,'policy_version',10)),
            ('mode',lambda r:setattr(r.certificate,'board_mode',8)),
            ('gold',lambda r:setattr(r.certificate,'actual_gold_cells',0)),
            ('face',lambda r:r.certificate.board_counts.__setitem__(0,149)),
            ('extra face',lambda r:setattr(r.certificate,'unmatched_boards',1)),
            ('merchant',lambda r:setattr(r.certificate,'merchant_score',.94)),
            ('glyph',lambda r:r.certificate.sign_iou.__setitem__(0,.94)),
            ('cap',lambda r:setattr(r.certificate.endcaps[0],'black_count',63)),
            ('price',lambda r:setattr(r.certificate,'unmatched_prices',1)),
            ('bounds',lambda r:setattr(r.partial[0],'icon_upper_bound',.8)),
            ('NaN',lambda r:setattr(r.partial[0],'icon_upper_bound',float('nan'))),
            ('strong word',lambda r:(setattr(r.partial[0],'word_present',1),setattr(r.partial[0],'word_iou',.82),setattr(r.partial[0],'word_coverage',.90))),
            ('strip',lambda r:r.certificate.strip_box.__setitem__(3,66)),
            ('whole x half-cell',lambda r:translate(r,dx=-17)),
            ('whole y half-cell',lambda r:translate(r,dy=62)),
            ('whole bottom beyond central ROI',lambda r:translate(r,dy=182)))
        for name,mutate in mutations:
            value=Result.from_buffer_copy(base);mutate(value)
            with self.subTest(name=name):self.assertEqual(0,self.lib.ng2_ring_negative_certificate(C.byref(value)))

    def test_state_mapping_bounds_deadline_cancel_and_legacy_modes_are_preserved(self):
        for name in ('state','goods','gold_state'):
            scene=self.scene();setattr(scene,name,0);self.assertNotEqual(3,self.assess(scene=scene)[1].outcome)
        for left,sy,ax,ay in ((322,43,-3,-3),(339,105,-3,-2),(54,43,-11,-3),(339,8,-3,-5),(752,43,8,-3)):
            self.assertNotEqual(3,self.assess(self.pixels(left=left,sy=sy),self.scene(ax=ax,ay=ay))[1].outcome)
        for left,sy,ax,ay in ((196,43,-7,-3),(538,43,2,-3),(339,20,-3,-4),(339,225,-3,2)):
            with self.subTest(HUD_crossing=(left,sy)):
                self.assertNotEqual(3,self.assess(self.pixels(left=left,sy=sy),self.scene(ax=ax,ay=ay))[1].outcome)
        for left,sy,ax,ay in ((197,43,-7,-3),(537,43,2,-3),(339,21,-3,-4),(339,224,-3,2)):
            with self.subTest(HUD_boundary=(left,sy)):
                self.assertEqual(3,self.assess(self.pixels(left=left,sy=sy),self.scene(ax=ax,ay=ay))[1].outcome)
        for kwargs,status in (({'cancelled':True},1),({'deadline':True},2)):
            code,result=self.assess(**kwargs);self.assertEqual((status,0,0),(code,result.outcome,result.coverage))
        for mode in (0,1):self.assertNotEqual(3,self.assess(mode=mode)[1].outcome)
