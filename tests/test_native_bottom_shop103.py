"""Observed bottom entry and two full faces, without glyph identities; procedural only."""
import ctypes as C
import os
from pathlib import Path
import tempfile
import unittest

from tests.test_native_ring094 import Result
from tests import test_native_ring_bank094 as bank094
from tests.test_native_perception import NativeScene
from tests.test_native_shop_coverage102 import shop_pixels as pixels102, normal_assess, _put
from tests.test_target_assessment087 import FEATURES

ROOT=Path(__file__).resolve().parents[1]


def set_tile(scene,x,y,kind):
    if -11<=x<=11 and -5<=y<=4:scene.tiles[(y+5)*23+x+11]=kind


def shop_scene(ax=-1,ay=-3,opening=1):
    scene=NativeScene(abi_version=1,struct_size=C.sizeof(NativeScene),state=2,goods=2,gold_state=2)
    for x in (ax-2,ax+4):
        for y in range(ay-2,ay+2):set_tile(scene,x,y,2)
    for x in (ax,ax+2):set_tile(scene,x,ay+3,2)
    for y in (ay+1,ay+2):set_tile(scene,ax+1,y,1)
    set_tile(scene,ax+1,ay+3,opening)
    for x in range(ax,ax+3):
        set_tile(scene,x,ay,6)
        for dx,dy in ((0,0),(-1,0),(1,0),(0,-1),(0,1)):
            if -11<=x+dx<=11 and -5<=ay+dy<=4:scene.protected_cells[(ay+dy+5)*23+x+dx+11]=1
    for x in (ax-1,ax+3):set_tile(scene,x,ay,1)
    return scene


def shop_pixels(left=411,sy=44,**kwargs):
    return pixels102(left=left,sy=sy,truncated_side=None,**kwargs)


class NativeBottomShop103Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='bottom-shop103-');cls.addClassCleanup(cls.tmp.cleanup)
        source=Path(os.environ.get('NECRO103_RING_SOURCE',str(ROOT/'patches/loopctrl/ngg2/NG2Ring.c')))
        cls.lib=bank094.NativeRingBank094Tests.build_library(source,Path(cls.tmp.name)/'ring.so')
        cls.lib.ng2_ring_negative_certificate.argtypes=[C.POINTER(Result)]
        cls.lib.ng2_ring_negative_certificate.restype=C.c_int

    scene=staticmethod(shop_scene)
    pixels=staticmethod(shop_pixels)

    def assess(self,pixels=None,scene=None,**kwargs):
        return normal_assess(self.lib,self.pixels() if pixels is None else pixels,
            self.scene() if scene is None else scene,**kwargs)

    def test_ten_fixed_gold_bottom_entry_and_two_full_faces_have_separate_proof(self):
        for opening in (1,5):
            scene=self.scene(opening=opening);before=bytes(scene);status,result=self.assess(scene=scene)
            self.assertEqual((0,3,2,8,8),(status,result.outcome,result.coverage,
                result.certificate.policy_version,result.certificate.board_mode),
                'the fully observed vertical entry needs its own ten-position proof')
            self.assertEqual(10,result.certificate.actual_gold_cells)
            self.assertEqual(1,self.lib.ng2_ring_negative_certificate(C.byref(result)))
            self.assertEqual(before,bytes(scene))
            self.assertEqual((0,0),(result.certificate.merchant_score,result.certificate.merchant_coverage))

    def test_every_fixed_gold_center_floor_item_cap_and_gate_is_required(self):
        supports={(-3,y) for y in range(-5,-1)}|{(3,y) for y in range(-5,-1)}|{(-1,0),(1,0)}
        self.assertEqual(10,len(supports))
        for x,y in sorted(supports):
            for kind in (0,1,4):
                scene=self.scene();set_tile(scene,x,y,kind);set_tile(scene,10,4,2)
                with self.subTest(cell=(x,y),kind=kind):self.assertNotEqual(3,self.assess(scene=scene)[1].outcome)
        for x,y in ((0,-2),(0,-1),(-2,-3),(-1,-3),(0,-3),(1,-3),(2,-3)):
            scene=self.scene();set_tile(scene,x,y,0)
            self.assertNotEqual(3,self.assess(scene=scene)[1].outcome)
        for opening in (0,2,3,4,6):self.assertNotEqual(3,self.assess(scene=self.scene(opening=opening))[1].outcome)

    def test_two_complete_faces_not_partial_missing_shifted_or_extra_are_required(self):
        full=(-14,-14,29,29)
        for boxes in ((full,None),(None,full),(full,(-14,-4,29,19)),
                      ((-8,-14,17,29),full),(full,(-14,-10,29,29))):
            self.assertNotEqual(3,self.assess(self.pixels(face_boxes=boxes))[1].outcome)
        self.assertNotEqual(3,self.assess(self.pixels(extra_board=True))[1].outcome)
        for kwargs in ({'missing_price':1},{'missing_wall':True},{'extra_object':True}):
            self.assertNotEqual(3,self.assess(self.pixels(**kwargs))[1].outcome)

    def test_full_strip_target_and_strong_word_remain_held(self):
        for name,expected in ((True,2),(False,1)):
            self.assertEqual(expected,self.assess(self.pixels(target=True,target_name=name))[1].outcome)
        for sprite in FEATURES['icons']:
            pixels=bytearray(self.pixels());left=447-sprite['width']//2;top=82
            for y in range(top,top+sprite['height']):
                for x in range(left,left+sprite['width']):_put(pixels,x,y,(27,17,12))
            for dx,dy,r,g,b in sprite['bright']:_put(pixels,left+dx,top+dy,(r,g,b))
            for dx,dy in sprite['dark']:_put(pixels,left+dx,top+dy,(0,0,0))
            self.assertEqual(1,self.assess(bytes(pixels))[1].outcome)
        pixels=bytearray(self.pixels())
        for y in range(68,79):
            for x in range(405,489):_put(pixels,x,y,(27,17,12))
        for dy,row in enumerate(FEATURES['word']['rows_hex']):
            for dx in range(84):
                if int(row,16)>>dx&1:_put(pixels,405+dx,68+dy,(245,245,245))
        self.assertEqual(1,self.assess(bytes(pixels))[1].outcome)

    def test_numeric_certificate_rejects_forgery_with_same_old_binary_guards(self):
        status,base=self.assess();self.assertEqual((0,3,8),(status,base.outcome,base.certificate.policy_version))
        mutations=(('gold',lambda r:setattr(r.certificate,'actual_gold_cells',9)),
            ('policy',lambda r:setattr(r.certificate,'policy_version',9)),
            ('mode',lambda r:setattr(r.certificate,'board_mode',7)),
            ('face',lambda r:r.certificate.board_counts.__setitem__(1,149)),
            ('partial face',lambda r:(r.certificate.board_boxes[1].__setitem__(1,40),r.certificate.board_boxes[1].__setitem__(3,19))),
            ('glyph',lambda r:r.certificate.sign_iou.__setitem__(0,.94)),
            ('merchant',lambda r:setattr(r.certificate,'merchant_score',1)),
            ('merchant box',lambda r:r.certificate.merchant_box.__setitem__(2,36)),
            ('border',lambda r:r.certificate.board_corner_counts[0].__setitem__(0,1)),
            ('raw cap',lambda r:setattr(r.certificate.endcaps[0],'floor_lower',0)),
            ('black cap',lambda r:setattr(r.certificate.endcaps[0],'black_count',63)),
            ('price',lambda r:setattr(r.certificate,'unmatched_prices',1)),
            ('bound',lambda r:setattr(r.partial[1],'icon_upper_bound',.8)),
            ('word',lambda r:(setattr(r.partial[0],'word_present',1),setattr(r.partial[0],'word_iou',.82),setattr(r.partial[0],'word_coverage',.90))),
            ('diagnostic',lambda r:setattr(r.certificate,'unmatched_items',503)))
        for name,mutate in mutations:
            value=Result.from_buffer_copy(base);mutate(value)
            with self.subTest(name=name):self.assertEqual(0,self.lib.ng2_ring_negative_certificate(C.byref(value)))

    def test_mapping_state_deadline_cancel_and_legacy_modes_keep_old_rules(self):
        for name in ('state','goods','gold_state'):
            scene=self.scene();setattr(scene,name,0);self.assertNotEqual(3,self.assess(scene=scene)[1].outcome)
        for left,sy,ax,ay in ((430,44,-1,-3),(411,33,-1,-3),(54,44,-11,-3),(411,8,-1,-5),(752,44,8,-3)):
            self.assertNotEqual(3,self.assess(self.pixels(left=left,sy=sy),self.scene(ax=ax,ay=ay))[1].outcome)
        for kwargs,status in (({'cancelled':True},1),({'deadline':True},2)):
            code,result=self.assess(**kwargs);self.assertEqual((status,0,0),(code,result.outcome,result.coverage))
        for mode in (0,1):self.assertNotEqual(3,self.assess(mode=mode)[1].outcome)
