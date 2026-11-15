"""One full SIGN, strong merchant and observed seven-cell side entry; procedural only."""
import ctypes as C
import os
from pathlib import Path
import tempfile
import unittest

from tests.test_native_ring094 import Result
from tests import test_native_ring_bank094 as bank094
from tests.test_native_ring_bank094 import bank_data, auth_data, complete_shop
from tests.test_native_perception import NativeScene
from tests.test_native_shop_coverage102 import draw_faces, normal_assess, _put
from tests.test_target_assessment087 import WIDTH, HEIGHT, FEATURES

ROOT=Path(__file__).resolve().parents[1]


def set_tile(scene,x,y,kind):
    if -11<=x<=11 and -5<=y<=4:scene.tiles[(y+5)*23+x+11]=kind


def shop_scene(ax=-5,ay=0,opening=1,mirror=False):
    scene=NativeScene(abi_version=1,struct_size=C.sizeof(NativeScene),state=2,goods=2,gold_state=2)
    solid,gate=(ax+4,ax-2) if mirror else (ax-2,ax+4)
    for y in range(ay-2,ay+3):set_tile(scene,solid,y,2)
    for y in (ay-1,ay+1):set_tile(scene,gate,y,2)
    set_tile(scene,gate,ay,opening)
    for x in range(ax,ax+3):
        set_tile(scene,x,ay,6)
        for dx,dy in ((0,0),(-1,0),(1,0),(0,-1),(0,1)):
            if -11<=x+dx<=11 and -5<=ay+dy<=4:scene.protected_cells[(ay+dy+5)*23+x+dx+11]=1
    for x in (ax-1,ax+3):set_tile(scene,x,ay,1)
    return scene


def shop_pixels(left=267,sy=153,faces=None,**kwargs):
    source=complete_shop(bank_data()['entries'][:3],auth=auth_data(),missing_shop_glyph=True,**kwargs)
    pixels=bytearray(bytes((0,0,0,255))*(WIDTH*HEIGHT));dx,dy=left-360,sy-120
    x0,x1=max(0,-dx),min(WIDTH,WIDTH-dx)
    for y in range(max(0,-dy),min(HEIGHT,HEIGHT-dy)):
        pixels[4*((y+dy)*WIDTH+x0+dx):4*((y+dy)*WIDTH+x1+dx)]=source[4*(y*WIDTH+x0):4*(y*WIDTH+x1)]
    draw_faces(pixels,left,sy,faces if faces is not None else ((-15,-14,30,29),None))
    if kwargs.get('target') and kwargs.get('target_name',True):
        for yy,row in enumerate(FEATURES['word']['rows_hex']):
            for xx in range(84):
                if int(row,16)>>xx&1:_put(pixels,left-6+xx,sy+7+yy,(245,245,245))
    return bytes(pixels)


class NativeSingleSignShop103Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='single-sign103-');cls.addClassCleanup(cls.tmp.cleanup)
        source=Path(os.environ.get('NECRO103_RING_SOURCE',str(ROOT/'patches/loopctrl/ngg2/NG2Ring.c')))
        cls.lib=bank094.NativeRingBank094Tests.build_library(source,Path(cls.tmp.name)/'ring.so')
        cls.lib.ng2_ring_negative_certificate.argtypes=[C.POINTER(Result)]
        cls.lib.ng2_ring_negative_certificate.restype=C.c_int

    scene=staticmethod(shop_scene)
    pixels=staticmethod(shop_pixels)

    def assess(self,pixels=None,scene=None,**kwargs):
        return normal_assess(self.lib,self.pixels() if pixels is None else pixels,
            self.scene() if scene is None else scene,**kwargs)

    def test_one_real_full_face_and_strong_merchant_certify_only_complete_strip(self):
        scene=self.scene();before=bytes(scene);status,result=self.assess(scene=scene)
        self.assertEqual((0,3,2,7,7),(status,result.outcome,result.coverage,
            result.certificate.policy_version,result.certificate.board_mode),
            'the observed same-row doorway with one complete SIGN needs its own finite proof')
        self.assertEqual((7,3,3,0),(result.certificate.actual_gold_cells,result.certificate.observed_items,
            result.certificate.observed_prices,result.certificate.unmatched_prices))
        self.assertEqual(1,self.lib.ng2_ring_negative_certificate(C.byref(result)))
        self.assertEqual(before,bytes(scene))
        self.assertGreaterEqual(result.certificate.merchant_score,.94)
        self.assertGreaterEqual(result.certificate.merchant_coverage,.95)
        self.assertEqual([0,0,0,0],list(result.certificate.board_boxes[1]))
        self.assertEqual(0,result.certificate.board_counts[1])

    def test_each_fixed_gold_item_cap_and_observed_doorway_is_independent(self):
        supports={(-7,y) for y in range(-2,3)}|{(-1,-1),(-1,1)}
        self.assertEqual(7,len(supports))
        for x,y in sorted(supports):
            for kind in (0,1,4):
                scene=self.scene();set_tile(scene,x,y,kind);set_tile(scene,10,4,2)
                with self.subTest(cell=(x,y),kind=kind):self.assertNotEqual(3,self.assess(scene=scene)[1].outcome)
        for x in (-6,-5,-4,-3,-2):
            scene=self.scene();set_tile(scene,x,0,0)
            self.assertNotEqual(3,self.assess(scene=scene)[1].outcome)
        for opening in (0,2,3,4,6):self.assertNotEqual(3,self.assess(scene=self.scene(opening=opening))[1].outcome)
        self.assertEqual(3,self.assess(scene=self.scene(opening=5))[1].outcome)
        self.assertNotEqual(3,self.assess(scene=self.scene(mirror=True))[1].outcome)

    def test_full_face_size_count_roi_and_no_extra_component_remain_required(self):
        full=(-15,-14,30,29)
        for faces in ((None,None),((-15,-4,30,19),None),((-8,-14,17,29),None),
                      ((-15,0,30,15),None),((-19,-14,37,29),None),(full,full),(None,full)):
            with self.subTest(faces=faces):self.assertNotEqual(3,self.assess(self.pixels(faces=faces))[1].outcome)
        self.assertNotEqual(3,self.assess(self.pixels(extra_board=True))[1].outcome)
        pixels=bytearray(self.pixels());draw_faces(pixels,267,153,(None,None))
        points=[(x,y) for y in range(139,168) for x in range(258,276)]
        keep={(x,y) for x,y in points if x in (258,275) or y in (139,167)}
        for point in points:
            if len(keep)>=149:break
            keep.add(point)
        for x,y in keep:_put(pixels,x,y,(220,210,10))
        self.assertNotEqual(3,self.assess(bytes(pixels))[1].outcome)

    def test_merchant_is_real_strong_bounded_evidence_not_an_optional_field(self):
        for kwargs in ({'missing_merchant':True},{'wrong_merchant':True}):
            self.assertNotEqual(3,self.assess(self.pixels(**kwargs))[1].outcome)
        pixels=bytearray(self.pixels());source=bytes(pixels)
        for y in range(114,150):
            for x in range(285,321):_put(pixels,x,y,(27,17,15))
        for y in range(114,150):
            for x in range(285,321):
                at=4*(y*WIDTH+x);dest=4*((y+8)*WIDTH+x)
                pixels[dest:dest+4]=source[at:at+4]
        self.assertNotEqual(3,self.assess(bytes(pixels))[1].outcome)

    def test_raw_endcaps_prices_extra_groups_and_missing_items_are_held(self):
        for kwargs in ({'missing_price':1},{'missing_wall':True},{'extra_object':True}):
            self.assertNotEqual(3,self.assess(self.pixels(**kwargs))[1].outcome)
        pixels=bytearray(self.pixels())
        for y in range(189,214):
            for x in range(363,388):_put(pixels,x,y,(0,0,0))
        self.assertNotEqual(3,self.assess(bytes(pixels))[1].outcome)
        for top in (222,231):
            pixels=bytearray(self.pixels())
            for y in range(top,top+6):
                for x in range(281,284):_put(pixels,x,y,(245,245,245))
            result=self.assess(bytes(pixels))[1];self.assertNotEqual(3,result.outcome)
            self.assertGreater(result.certificate.unmatched_prices,0)
        pixels=bytearray(self.pixels())
        for y in range(177,219):
            for x in range(285,321):_put(pixels,x,y,(27,17,15))
        self.assertNotEqual(3,self.assess(bytes(pixels))[1].outcome)

    def test_target_full_strip_and_strong_name_keep_positive_priority(self):
        for name,expected in ((True,2),(False,1)):
            self.assertEqual(expected,self.assess(self.pixels(target=True,target_name=name))[1].outcome)
        for sprite in FEATURES['icons']:
            pixels=bytearray(self.pixels());left=319-sprite['width']//2;top=192
            for y in range(top,top+sprite['height']):
                for x in range(left,left+sprite['width']):_put(pixels,x,y,(27,17,12))
            for dx,dy,r,g,b in sprite['bright']:_put(pixels,left+dx,top+dy,(r,g,b))
            for dx,dy in sprite['dark']:_put(pixels,left+dx,top+dy,(0,0,0))
            self.assertEqual(1,self.assess(bytes(pixels))[1].outcome)
        pixels=bytearray(self.pixels())
        for y in range(171,182):
            for x in range(225,309):_put(pixels,x,y,(27,17,12))
        for dy,row in enumerate(FEATURES['word']['rows_hex']):
            for dx in range(84):
                if int(row,16)>>dx&1:_put(pixels,225+dx,171+dy,(245,245,245))
        self.assertEqual(1,self.assess(bytes(pixels))[1].outcome)

    def test_numeric_certificate_rejects_missing_face_fake_merchant_and_old_binary_mutations(self):
        status,base=self.assess();self.assertEqual((0,3,7),(status,base.outcome,base.certificate.policy_version))
        def half_cell_translation(value):
            def shift_box(box):
                if box[2]>0:box[0]+=55
            for row in value.rows[:value.row_count]:
                row.left+=55
                for slot in row.slots:
                    slot.cx+=55
                    for name in ('icon_box','word_box','non_target_icon_box','non_target_name_box','ignored_icon_box'):
                        shift_box(getattr(slot,name))
            for slot in value.partial[:value.partial_count]:
                slot.cx+=55
                for name in ('icon_box','word_box','non_target_icon_box','non_target_name_box','ignored_icon_box'):
                    shift_box(getattr(slot,name))
            witness=value.certificate;witness.row[0]+=55
            shift_box(witness.strip_box);shift_box(witness.merchant_box)
            for name in ('sign_boxes','item_boxes','name_boxes','price_boxes','board_boxes'):
                for box in getattr(witness,name):shift_box(box)
            for end in witness.endcaps:shift_box(end.box)
        changes=(('policy',lambda r:setattr(r.certificate,'policy_version',8)),
            ('mode',lambda r:setattr(r.certificate,'board_mode',6)),
            ('gold',lambda r:setattr(r.certificate,'actual_gold_cells',6)),
            ('extra board',lambda r:r.certificate.board_counts.__setitem__(1,150)),
            ('fake box',lambda r:r.certificate.board_boxes[1].__setitem__(0,324)),
            ('count149',lambda r:r.certificate.board_counts.__setitem__(0,149)),
            ('face shift',lambda r:r.certificate.board_boxes[0].__setitem__(1,145)),
            ('merchant score',lambda r:setattr(r.certificate,'merchant_score',.939999999)),
            ('merchant coverage',lambda r:setattr(r.certificate,'merchant_coverage',.949999999)),
            ('merchant NaN',lambda r:setattr(r.certificate,'merchant_score',float('nan'))),
            ('merchant width',lambda r:r.certificate.merchant_box.__setitem__(2,35)),
            ('merchant x',lambda r:r.certificate.merchant_box.__setitem__(0,289)),
            ('merchant y',lambda r:r.certificate.merchant_box.__setitem__(1,121)),
            ('glyph',lambda r:r.certificate.sign_iou.__setitem__(0,.94)),
            ('cap',lambda r:setattr(r.certificate.endcaps[1],'black_count',63)),
            ('price',lambda r:setattr(r.certificate,'unmatched_prices',1)),
            ('price span',lambda r:r.certificate.price_boxes[1].__setitem__(1,270)),
            ('strip',lambda r:r.certificate.strip_box.__setitem__(3,66)),
            ('bound',lambda r:setattr(r.partial[0],'icon_upper_bound',.8)),
            ('word',lambda r:(setattr(r.partial[0],'word_present',1),setattr(r.partial[0],'word_iou',.82),setattr(r.partial[0],'word_coverage',.90))),
            ('items',lambda r:setattr(r.certificate,'unmatched_items',503)),
            ('half-cell full translation',half_cell_translation))
        for name,mutate in changes:
            value=Result.from_buffer_copy(base);mutate(value)
            with self.subTest(name=name):self.assertEqual(0,self.lib.ng2_ring_negative_certificate(C.byref(value)))

    def test_state_mapping_deadline_cancel_and_legacy_modes_preserve_old_authority(self):
        for name in ('state','goods','gold_state'):
            scene=self.scene();setattr(scene,name,0);self.assertNotEqual(3,self.assess(scene=scene)[1].outcome)
        for left,sy,ax,ay in ((322,153,-5,0),(267,141,-5,0),(54,153,-11,0),(267,18,-5,-5),(752,153,8,0)):
            self.assertNotEqual(3,self.assess(self.pixels(left=left,sy=sy),self.scene(ax=ax,ay=ay))[1].outcome)
        for kwargs,status in (({'cancelled':True},1),({'deadline':True},2)):
            result=self.assess(**kwargs);self.assertEqual((status,0,0),(result[0],result[1].outcome,result[1].coverage))
        for mode in (0,1):self.assertNotEqual(3,self.assess(mode=mode)[1].outcome)
