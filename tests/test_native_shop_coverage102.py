"""Finite shop rail and top-prefix SIGN proof; procedural pixels are not phone accuracy."""
import ctypes as C
import os
from pathlib import Path
import tempfile
import unittest

from tests.test_native_ring094 import Result, Options, Clock, Cancelled
from tests import test_native_ring_bank094 as legacy_bank
from tests.test_native_ring_bank094 import bank_data, auth_data, complete_shop
from tests.test_native_perception import NativeScene
from tests.test_target_assessment087 import WIDTH, HEIGHT, FEATURES

ROOT = Path(__file__).resolve().parents[1]


def set_tile(scene, x, y, kind):
    if -11 <= x <= 11 and -5 <= y <= 4:
        scene.tiles[(y+5)*23+x+11] = kind


def shop_scene(mirror=False, bottom_door=True, ax=-4, ay=-1, opening=1, door_offset=2):
    scene = NativeScene(abi_version=1, struct_size=C.sizeof(NativeScene),
                        state=2, gold_state=2, goods=2)
    reflect = lambda x: 2*(ax+1)-x if mirror else x
    for y in range(ay-1, ay+4):
        set_tile(scene, reflect(ax-2), y, 2)
    for x in range(ax-2, ax+4):
        set_tile(scene, reflect(x), ay+3, 2)
    for y in (ay, ay+2):
        set_tile(scene, reflect(ax+4), y, 2)
    set_tile(scene, reflect(ax+4), ay+1, opening)
    if bottom_door:
        set_tile(scene, reflect(ax+door_offset), ay+3, 5)
        set_tile(scene, reflect(ax-2), ay-2, 2)
    for x in range(ax, ax+3):
        set_tile(scene, x, ay, 6)
    for x in (ax-1, ax+3):
        set_tile(scene, x, ay, 1)
    for x in range(ax, ax+3):
        for dx, dy in ((0,0),(-1,0),(1,0),(0,-1),(0,1)):
            xx, yy = x+dx, ay+dy
            if -11 <= xx <= 11 and -5 <= yy <= 4:
                scene.protected_cells[(yy+5)*23+xx+11] = 1
    return scene


def _put(pixels, x, y, colour):
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        at = 4*(y*WIDTH+x)
        pixels[at:at+4] = bytes((*colour,255))


def draw_faces(pixels, left=301, sy=117, boxes=None):
    """Draw only positive SIGN components, including one missing top prefix."""
    boxes = boxes if boxes is not None else ((-14,-14,29,29),(-14,-4,29,19))
    for side, box in enumerate(boxes):
        cx = left+72*side
        for y in range(sy-20, sy+20):
            for x in range(cx-18, cx+18):
                _put(pixels,x,y,(27,17,15))
        if box is not None:
            dx,dy,width,height = box
            for y in range(sy+dy, sy+dy+height):
                for x in range(cx+dx,cx+dx+width):
                    _put(pixels,x,y,(220,210,10))


def shop_pixels(left=301, sy=117, truncated_side=1, face_boxes=None, **kwargs):
    source = complete_shop(bank_data()['entries'][:3],auth=auth_data(),
                           missing_shop_glyph=True,missing_merchant=True,**kwargs)
    pixels = bytearray(bytes((0,0,0,255))*(WIDTH*HEIGHT))
    dx,dy = left-360,sy-120
    x0,x1 = max(0,-dx),min(WIDTH,WIDTH-dx)
    for y in range(max(0,-dy),min(HEIGHT,HEIGHT-dy)):
        pixels[4*((y+dy)*WIDTH+x0+dx):4*((y+dy)*WIDTH+x1+dx)] = source[4*(y*WIDTH+x0):4*(y*WIDTH+x1)]
    if face_boxes is None:
        face_boxes = [(-14,-14,29,29),(-14,-14,29,29)]
        if truncated_side is not None:
            face_boxes[truncated_side] = (-14,-4,29,19)
    draw_faces(pixels,left,sy,face_boxes)
    if kwargs.get('target') and kwargs.get('target_name',True):
        for dy,row in enumerate(FEATURES['word']['rows_hex']):
            bits = int(row,16)
            for dx in range(84):
                if bits>>dx&1:
                    _put(pixels,left+36-42+dx,sy+7+dy,(245,245,245))
    return bytes(pixels)


def normal_assess(lib, pixels, scene, mode=2, cancelled=False, deadline=False):
    now = Clock(lambda _: 100)
    cancel = Cancelled(lambda _: int(cancelled))
    options = Options(abi=1,size=C.sizeof(Options),mode=mode,
                      deadline_ns=100 if deadline else 1000000000,
                      now_ns=now,cancelled=cancel,scene=C.addressof(scene),fast=1)
    result = Result()
    buf = C.create_string_buffer(pixels)
    status = lib.ng2_ring_assess_rgba(buf,len(pixels),WIDTH*4,C.byref(options),C.byref(result))
    return status,result


class NativeShopCoverage102Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='shop-coverage102-')
        cls.addClassCleanup(cls.tmp.cleanup)
        source = Path(os.environ.get('NECRO102_RING_SOURCE',str(ROOT/'patches/loopctrl/ngg2/NG2Ring.c')))
        cls.lib = legacy_bank.NativeRingBank094Tests.build_library(source,Path(cls.tmp.name)/'ring.so')
        cls.lib.ng2_ring_negative_certificate.argtypes = [C.POINTER(Result)]
        cls.lib.ng2_ring_negative_certificate.restype = C.c_int

    scene = staticmethod(shop_scene)
    pixels = staticmethod(shop_pixels)

    def assess(self,pixels=None,scene=None,**kwargs):
        return normal_assess(self.lib,self.pixels() if pixels is None else pixels,
                             self.scene() if scene is None else scene,**kwargs)

    def test_bottom_door_and_top_prefix_have_independent_complete_proof(self):
        for bottom_door,truncated_side,expected in ((True,1,6),(True,None,6),(False,1,6),(False,None,3)):
            scene = self.scene(bottom_door=bottom_door)
            before = bytes(scene)
            status,result = self.assess(self.pixels(truncated_side=truncated_side),scene)
            with self.subTest(door=bottom_door,truncated=truncated_side):
                self.assertEqual((0,3,2,expected,expected),(status,result.outcome,result.coverage,
                    result.certificate.policy_version,result.certificate.board_mode),
                    'a positively bounded second doorway and SIGN top prefix need a separate complete proof')
                self.assertEqual(12,result.certificate.actual_gold_cells)
                self.assertEqual(1,self.lib.ng2_ring_negative_certificate(C.byref(result)))
                self.assertEqual(before,bytes(scene))

    def test_each_twelve_fixed_gold_and_door_is_required_despite_remote_count(self):
        supports = {(-6,y) for y in range(-3,3)} | {(x,2) for x in (-5,-4,-3,-1)} | {(0,-1),(0,1)}
        self.assertEqual(12,len(supports))
        for x,y in sorted(supports):
            for replacement in (0,1,3):
                scene = self.scene();set_tile(scene,x,y,replacement);set_tile(scene,10,4,2)
                with self.subTest(cell=(x,y),replacement=replacement):
                    self.assertNotEqual(3,self.assess(scene=scene)[1].outcome)
        for replacement in (0,1,3,4,6):
            scene = self.scene();set_tile(scene,-2,2,replacement)
            with self.subTest(door=replacement):
                self.assertNotEqual(3,self.assess(scene=scene)[1].outcome)

    def test_mirrors_interior_doors_and_observed_side_openings(self):
        for mirror in (False,True):
            for opening in (1,5):
                for offset in (-1,0,1,2):
                    scene = self.scene(mirror=mirror,opening=opening,door_offset=offset)
                    status,result = self.assess(scene=scene)
                    with self.subTest(mirror=mirror,opening=opening,offset=offset):
                        self.assertEqual((0,3,6),(status,result.outcome,result.certificate.policy_version))
                for offset in (-2,3):
                    scene = self.scene(mirror=mirror,opening=opening,door_offset=offset)
                    set_tile(scene,10,4,2)
                    self.assertNotEqual(3,self.assess(scene=scene)[1].outcome)
        scene = self.scene();set_tile(scene,-4,2,5);set_tile(scene,10,4,2)
        self.assertNotEqual(3,self.assess(scene=scene)[1].outcome)
        for opening in (0,2,3,4,6):
            self.assertNotEqual(3,self.assess(scene=self.scene(opening=opening))[1].outcome)

    def test_prefix_faces_preserve_anchor_width_bottom_and_unique_components(self):
        full = (-14,-14,29,29)
        invalid = ((None,(-14,-4,29,19)),((-14,-4,29,19),(-14,-4,29,19)),
            (full,(-13,-4,27,19)),(full,(-14,-4,29,15)),(full,(-14,-4,29,16)),
            (full,(-14,-4,29,24)),(full,(-14,-18,29,33)),(full,(-14,-4,29,23)),
            (full,(-14,-4,29,14)),(full,(-14,-9,29,19)))
        for boxes in invalid:
            with self.subTest(boxes=boxes):
                self.assertNotEqual(3,self.assess(self.pixels(face_boxes=boxes))[1].outcome)
        for truncated in (0,1):
            status,result = self.assess(self.pixels(truncated_side=truncated))
            self.assertEqual((0,3,6),(status,result.outcome,result.certificate.policy_version))

    def test_bottom_alignment_selects_one_canonical_row_without_deleting_evidence(self):
        status,result = self.assess()
        self.assertEqual((0,3,6),(status,result.outcome,result.certificate.policy_version))
        self.assertEqual([(301,117),(301,122)],[(r.left,r.sy) for r in result.rows[:result.row_count]])
        self.assertEqual((1,0,117),(result.certificate.accepted_rows,result.selected_row,result.certificate.row[1]))
        self.assertEqual([29,19],[b[3] for b in result.certificate.board_boxes])

    def test_scene_items_caps_states_and_half_cell_mapping_are_required(self):
        for x in (-5,-4,-3,-2,-1):
            scene = self.scene();set_tile(scene,x,-1,0)
            self.assertNotEqual(3,self.assess(scene=scene)[1].outcome)
        for name in ('state','goods','gold_state'):
            scene = self.scene();setattr(scene,name,0)
            self.assertNotEqual(3,self.assess(scene=scene)[1].outcome)
        for left,sy,ax,ay in ((322,117,-4,-1),(301,105,-4,-1),(54,117,-11,-1),(301,18,-4,-5),(752,117,8,-1)):
            with self.subTest(left=left,sy=sy):
                self.assertNotEqual(3,self.assess(self.pixels(left=left,sy=sy),self.scene(ax=ax,ay=ay))[1].outcome)

    def test_complete_prices_caps_and_extra_boards_are_independent(self):
        for kwargs in ({'missing_price':1},{'missing_wall':True},{'extra_board':True},{'extra_object':True}):
            with self.subTest(kwargs=kwargs):
                self.assertNotEqual(3,self.assess(self.pixels(**kwargs))[1].outcome)
        pixels = bytearray(self.pixels())
        for y in range(153,178):
            for x in range(397,422):_put(pixels,x,y,(0,0,0))
        self.assertNotEqual(3,self.assess(bytes(pixels))[1].outcome)
        pixels = bytearray(self.pixels())
        for y in range(186,192):
            for x in range(315,318):_put(pixels,x,y,(245,245,245))
        result = self.assess(bytes(pixels))[1]
        self.assertNotEqual(3,result.outcome)
        self.assertGreater(result.certificate.unmatched_prices,0)

    def test_two_independently_complete_rows_are_not_unique_coverage(self):
        first = bytearray(self.pixels(left=301,sy=81))
        second = self.pixels(left=625,sy=189)
        for y in range(144,300):
            for x in range(535,790):
                at=4*(y*WIDTH+x);first[at:at+4]=second[at:at+4]
        scene = self.scene(ax=-4,ay=-2)
        extra = self.scene(ax=5,ay=1)
        for i in range(len(scene.tiles)):
            if extra.tiles[i]:scene.tiles[i]=extra.tiles[i]
            scene.protected_cells[i] |= extra.protected_cells[i]
        result = self.assess(bytes(first),scene)[1]
        self.assertNotEqual(3,result.outcome)
        self.assertEqual(2,result.certificate.accepted_rows)

    def test_target_icon_and_strong_word_keep_positive_priority(self):
        for name,expected in ((True,2),(False,1)):
            with self.subTest(name=name):
                self.assertEqual(expected,self.assess(self.pixels(target=True,target_name=name))[1].outcome)
        for sprite in FEATURES['icons']:
            pixels = bytearray(self.pixels());top=154;left=319-sprite['width']//2
            for y in range(top,top+sprite['height']):
                for x in range(left,left+sprite['width']):_put(pixels,x,y,(27,17,12))
            for dx,dy,r,g,b in sprite['bright']:_put(pixels,left+dx,top+dy,(r,g,b))
            for dx,dy in sprite['dark']:_put(pixels,left+dx,top+dy,(0,0,0))
            self.assertEqual(1,self.assess(bytes(pixels))[1].outcome)
        pixels = bytearray(self.pixels())
        for y in range(100,111):
            for x in range(295,379):_put(pixels,x,y,(27,17,12))
        for dy,row in enumerate(FEATURES['word']['rows_hex']):
            for dx in range(84):
                if int(row,16)>>dx&1:_put(pixels,295+dx,100+dy,(245,245,245))
        self.assertEqual(1,self.assess(bytes(pixels))[1].outcome)

    def test_certificate6_rechecks_every_existing_numeric_and_binary_guard(self):
        status,base = self.assess()
        self.assertEqual((0,3,6),(status,base.outcome,base.certificate.policy_version))
        mutations = (
            ('bad policy',lambda r:setattr(r.certificate,'policy_version',7)),
            ('old board mode',lambda r:setattr(r.certificate,'board_mode',3)),
            ('gold count',lambda r:setattr(r.certificate,'actual_gold_cells',11)),
            ('rows',lambda r:setattr(r.certificate,'accepted_rows',2)),
            ('extra face',lambda r:setattr(r.certificate,'unmatched_boards',1)),
            ('count149',lambda r:r.certificate.board_counts.__setitem__(1,149)),
            ('width',lambda r:r.certificate.board_boxes[1].__setitem__(2,28)),
            ('bottom',lambda r:r.certificate.board_boxes[1].__setitem__(1,117)),
            ('no anchor',lambda r:(r.certificate.board_boxes[0].__setitem__(1,113),r.certificate.board_boxes[0].__setitem__(3,19))),
            ('raw cap',lambda r:setattr(r.certificate.endcaps[1],'floor_upper',0)),
            ('black cap',lambda r:setattr(r.certificate.endcaps[1],'black_count',63)),
            ('price',lambda r:setattr(r.certificate,'observed_prices',2)),
            ('strip',lambda r:r.certificate.strip_box.__setitem__(3,66)),
            ('merchant',lambda r:setattr(r.certificate,'merchant_score',.94)),
            ('glyph',lambda r:r.certificate.sign_iou.__setitem__(0,.94)),
            ('target bound',lambda r:setattr(r.partial[1],'icon_upper_bound',.80)),
            ('strong word',lambda r:(setattr(r.partial[0],'word_present',1),setattr(r.partial[0],'word_iou',.82),setattr(r.partial[0],'word_coverage',.90))),
            ('diagnostic',lambda r:setattr(r.certificate,'unmatched_items',503)))
        for name,mutate in mutations:
            value = Result.from_buffer_copy(base);mutate(value)
            with self.subTest(name=name):
                self.assertEqual(0,self.lib.ng2_ring_negative_certificate(C.byref(value)))

    def test_existing_size_count_thresholds_are_not_lowered(self):
        full = (-14,-14,29,29)
        status,result = self.assess(self.pixels(face_boxes=(full,(-14,-1,29,16))))
        self.assertEqual((0,3,6),(status,result.outcome,result.certificate.policy_version))
        for box in ((-8,-4,17,19),(-14,0,29,15),(-19,-4,37,19)):
            with self.subTest(box=box):
                self.assertNotEqual(3,self.assess(self.pixels(face_boxes=(full,box)))[1].outcome)
        pixels = bytearray(self.pixels())
        # 149 connected yellow pixels in a18x16 bounding box cannot be a canonical face.
        draw_faces(pixels,boxes=(full,None))
        points = [(x,y) for y in range(116,132) for x in range(365,383)]
        selected = {(x,y) for x,y in points if x in (365,382) or y in (116,131)}
        for point in points:
            if len(selected)>=149:break
            selected.add(point)
        for x,y in selected:_put(pixels,x,y,(220,210,10))
        self.assertNotEqual(3,self.assess(bytes(pixels))[1].outcome)
        pixels = bytearray(self.pixels())
        draw_faces(pixels,boxes=(None,None))
        for cx,top,height in ((301,103,29),(373,116,16)):
            points = [(x,y) for y in range(top,top+height) for x in range(cx-9,cx+9)]
            selected = {(x,y) for x,y in points if x in (cx-9,cx+8) or y in (top,top+height-1)}
            for point in points:
                if len(selected)>=150:break
                selected.add(point)
            self.assertEqual(150,len(selected))
            for x,y in selected:_put(pixels,x,y,(220,210,10))
        status,result = self.assess(bytes(pixels))
        self.assertEqual((0,3,6),(status,result.outcome,result.certificate.policy_version))
        self.assertEqual([150,150],list(result.certificate.board_counts))

    def test_cancel_deadline_and_legacy_modes_keep_original_authority(self):
        for kwargs,expected in (({'cancelled':True},1),({'deadline':True},2)):
            status,result = self.assess(**kwargs)
            self.assertEqual((expected,0,0),(status,result.outcome,result.coverage))
        for mode in (0,1):
            result = self.assess(mode=mode)[1]
            self.assertNotEqual(6,result.certificate.policy_version)
            self.assertNotEqual(3,result.outcome)
