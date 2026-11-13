"""Independent negative witnesses and coverage guards on procedural shops.

These fixtures redraw published numeric bank features. They test joining,
uncertainty, and bounded complete coverage, not unknown-run item accuracy.
The optional fixture path exists only to run the pre-product assertion Red.
"""
import ctypes as C
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from tests.test_native_ring094 import Result, Options, Clock as NOW, Cancelled as CANCELLED
from tests.test_native_perception import NativeScene
from tests.test_target_assessment087 import FEATURES, WIDTH, HEIGHT

ROOT=Path(__file__).resolve().parents[1]
def bank_data():
    path=Path(os.environ.get('NECRO094_BANK_FIXTURE',str(ROOT/'necroprobe/non_target_features094.json')))
    return json.loads(path.read_text())

def auth_data():
    return json.loads((ROOT/'necroprobe/goldshop_auth_features094.json').read_text())

def complete_shop(entries, *, missing_name=None, wrong_name_slot=False, target=False,
                  target_name=True, extra_object=False, missing_wall=False,
                  auth=None, missing_merchant=False, missing_shop_glyph=False,
                  missing_price=None, container_damage=False, extra_board=False,
                  wrong_merchant=False, framed_boards=False, broken_frame=None,
                  right_board_delta=0, exterior_frame_extension=False,
                  name_y_offsets=None):
    """Draw a fully observed product strip between direct physical end walls."""
    pixels=bytearray(bytes((0,0,0,255))*(WIDTH*HEIGHT));left,sy=360,120
    def put(x,y,rgb):
        if 0<=x<WIDTH and 0<=y<HEIGHT:
            at=4*(y*WIDTH+x);pixels[at:at+4]=bytes((*rgb,255))
    for y in range(sy-35,sy+111):
        for x in range(left-90,left+163):
            if left-54<=x<left+126:
                phase=(x//6+y//6)%3
                put(x,y,(25+4*phase,17+2*phase,15+2*phase))
            elif not (missing_wall and x>=left+126):
                put(x,y,(205,160,40) if x%12 and y%6 else (80,58,15))
    for side,cx in enumerate((left,left+72+right_board_delta)):
        if framed_boards:
            for y in range(sy-18,sy+18):
                for x in range(cx-18,cx+18):put(x,y,(205,160,40))
        for y in range(sy-14,sy+15):
            for x in range(cx-15,cx+15):
                put(x,y,(205,160,40) if framed_boards and side==1 and y>=sy+4 else (220,210,10))
        if framed_boards and side==1:
            if exterior_frame_extension:
                for y in range(sy-18,sy-3):
                    for x in range(cx+18,cx+21):put(x,y,(205,160,40))
            if broken_frame=='corner':
                for y in range(sy-18,sy-16):
                    for x in range(cx+16,cx+18):put(x,y,(0,0,0))
            if broken_frame=='edge':
                for y in range(sy-14,sy+15):put(cx-18,y,(0,0,0))
    if auth:
        if not missing_shop_glyph:
            glyph=auth['shop_glyphs'][0]
            for cx in (left,left+72+right_board_delta):
                for dy,row in enumerate(glyph['rows_hex']):
                    bits=int(row,16)
                    for dx in range(glyph['width']):
                        if bits>>dx&1:put(cx-12+dx,sy-3+dy,(0,0,0))
        if not missing_merchant:
            merchant=auth['merchant_icons'][0];sx=left+36-18;iy=sy-39
            for dx,dy,r,g,b in merchant['bright']:
                put(sx+dx,iy+dy,(g,b,r) if wrong_merchant else (r,g,b))
            for dx,dy in merchant['dark']:put(sx+dx,iy+dy,(0,0,0))
    digits={'1':('010','110','010','010','010','010','111'),
            '0':('111','101','101','101','101','101','111')}
    def price(cx,offset=78):
        for index,char in enumerate('100'):
            for dy,line in enumerate(digits[char]):
                for dx,b in enumerate(line):
                    if b=='1':put(cx-6+4*index+dx,sy+offset+dy,(245,245,245))
    for slot,entry in enumerate(entries):
        cx=left+36*slot;sp=entry['icons'][0];sx=cx-sp['width']//2;iy=sy+35
        if entry.get('kind')=='ignored_container':
            iy=sy+49
            shape=entry['container_shape']
            for dy in range(shape['height']):
                dark=int(shape['dark_rows_hex'][dy],16);gold=int(shape['gold_rows_hex'][dy],16)
                for dx in range(shape['width']):
                    colour=(12,8,7) if dark>>dx&1 else (60,60,60)
                    if gold>>dx&1:colour=(220,160,15)
                    put(sx+dx,iy+dy,colour)
        for dx,dy,r,g,b in sp['bright']:put(sx+dx,iy+dy,(r,g,b))
        for dx,dy in sp['dark']:put(sx+dx,iy+dy,(0,0,0))
        if container_damage and entry.get('kind')=='ignored_container':
            protected={(point[0],point[1]) for point in sp['bright']+sp['dark']}
            for dy,row in enumerate(entry['container_shape']['dark_rows_hex']):
                bits=int(row,16)
                for dx in range(sp['width']):
                    if bits>>dx&1 and (dx,dy) not in protected:put(sx+dx,iy+dy,(60,60,60))
        if slot!=missing_price:price(cx,83 if entry.get('kind')=='ignored_container' else 78)
        if slot!=missing_name and entry['word'] is not None:
            word=entry['word'];name_cx=left+36*((slot+1)%3 if wrong_name_slot else slot)
            start=name_cx-word['width']//2;name_y=sy+23-13*slot
            name_y+=(name_y_offsets or {}).get(slot,0)
            for dy,row in enumerate(word['rows_hex']):
                bits=int(row,16)
                for dx in range(word['width']):
                    if bits>>dx&1:put(start+dx,name_y+dy,(245,245,245))
    if target:
        cx=left+36;sp=FEATURES['icons'][1];sx=cx-18;iy=sy+35
        for y in range(iy,iy+36):
            for x in range(cx-18,cx+18):put(x,y,(27,17,12))
        for dx,dy,r,g,b in sp['bright']:put(sx+dx,iy+dy,(r,g,b))
        for dx,dy in sp['dark']:put(sx+dx,iy+dy,(0,0,0))
        if target_name:
            for y in range(sy+7,sy+20):
                for x in range(cx-48,cx+48):put(x,y,(27,17,12))
            for dy,row in enumerate(FEATURES['word']['rows_hex']):
                bits=int(row,16)
                for dx in range(84):
                    if bits>>dx&1:put(cx-42+dx,sy+7+dy,(245,245,245))
    if extra_object:
        cx=left+108
        for y in range(sy+35,sy+61):
            for x in range(cx-11,cx+12):put(x,y,(20,180,150))
        price(cx)
    if extra_board:
        cx,board_sy=600,180
        for y in range(board_sy-14,board_sy+15):
            for x in range(cx-15,cx+15):put(x,y,(220,210,10))
        glyph=auth['shop_glyphs'][0]
        for dy,row in enumerate(glyph['rows_hex']):
            bits=int(row,16)
            for dx in range(glyph['width']):
                if bits>>dx&1:put(cx-12+dx,board_sy-3+dy,(0,0,0))
    if missing_wall:
        # The required outer product endcap itself is unobserved. A missing
        # roof or a wall beyond the observed strip alone is not this case.
        for y in range(sy+24,sy+89):
            for x in range(left+96,left+163):put(x,y,(0,0,0))
    return bytes(pixels)


class NativeRingBank094Tests(unittest.TestCase):
    @staticmethod
    def build_library(source,path,include=()):
        subprocess.run(['cc','-std=c11','-O2','-fno-fast-math','-ffp-contract=off',
            '-frounding-math','-Wall','-Wextra','-Werror','-shared','-fPIC',
            *['-I'+str(folder) for folder in include],
            '-I'+str(ROOT/'patches/loopctrl/ngg2'),str(source),
            *[str(ROOT/'tools/ring_native'/name) for name in ('observe.c','icon.c','word.c')],
            '-lm','-o',str(path)],check=True,capture_output=True)
        lib=C.CDLL(str(path));lib.ng2_ring_assess_rgba.argtypes=[C.c_void_p,C.c_size_t,C.c_size_t,C.POINTER(Options),C.POINTER(Result)]
        lib.ng2_ring_assess_rgba.restype=C.c_int
        return lib
    @classmethod
    def setUpClass(cls):
        cls.bank=bank_data();cls.byid={e['id']:e for e in cls.bank['entries']}
        cls.tmp=tempfile.TemporaryDirectory(prefix='native-ring-bank094-');cls.addClassCleanup(cls.tmp.cleanup)
        path=Path(cls.tmp.name)/'ring.so'
        source=os.environ.get('NECRO094_RING_SOURCE',str(ROOT/'patches/loopctrl/ngg2/NG2Ring.c'))
        cls.lib=cls.build_library(source,path)
    def assess(self,pixels,library=None,scene=False):
        now=NOW(lambda _context:100);cancelled=CANCELLED(lambda _context:0)
        options=Options(abi=1,size=C.sizeof(Options),mode=1,deadline_ns=1000000000,
                        now_ns=now,cancelled=cancelled)
        if scene:
            # Matching procedural input metadata; real calibration uses the
            # actual Perception result and is cached outside Git separately.
            observed=NativeScene(abi_version=1,struct_size=C.sizeof(NativeScene),
                                 state=2,gold_state=2,goods=2)
            observed.tiles[0]=2
            options.scene=C.addressof(observed)
        result=Result();buf=C.create_string_buffer(pixels)
        self.assertEqual(0,(library or self.lib).ng2_ring_assess_rgba(buf,len(pixels),WIDTH*4,C.byref(options),C.byref(result)))
        self.assertEqual(0,result.status)
        return result
    def shop(self,ids=(1,2,3),**options):
        return complete_shop([self.byid[i] for i in ids],auth=auth_data(),**options)
    def known_row(self,result):
        rows=[row for row in result.rows[:result.row_count] if (row.left,row.sy)==(360,120)]
        self.assertTrue(rows,'the observed three-price row must exist before checking its witnesses')
        return rows[0]
    def test_known_bank_identities_require_independent_same_slot_names_and_icons(self):
        for ids in ((1,2,3),(6,7,8)):
            with self.subTest(identities=ids):
                row=self.known_row(self.assess(self.shop(ids)))
                self.assertEqual(ids,tuple(slot.non_target_id for slot in row.slots))
                for slot in row.slots:
                    self.assertGreaterEqual(slot.non_target_icon_score,.94)
                    self.assertGreaterEqual(slot.non_target_name_iou,.94)
                    self.assertGreaterEqual(slot.non_target_name_coverage,.95)
                    self.assertEqual(0,slot.non_target_conflict)
        row=self.known_row(self.assess(self.shop(wrong_name_slot=True)))
        self.assertEqual((0,0,0),tuple(slot.non_target_id for slot in row.slots),
                         'a matching name borrowed from another slot cannot identify this icon')
    def test_torch_word_inside_a_longer_name_cannot_identify_the_torch(self):
        pixels=bytearray(self.shop((1,4,8),missing_name=1));cx,sy=396,120
        # Keep an exact known torch suffix inside a longer, uncatalogued name.
        # Its +18px center is within the normal bounded word window. The
        # preceding four glyphs rule out a whole-name match independently.
        prefix=self.byid[3]['word'];suffix=self.byid[4]['word']
        for word,start,width in ((prefix,cx-48,48),(suffix,cx,suffix['width'])):
            for dy,row in enumerate(word['rows_hex']):
                bits=int(row,16)
                for dx in range(width):
                    if bits>>dx&1:
                        at=4*((sy+10+dy)*WIDTH+start+dx)
                        pixels[at:at+4]=bytes((245,245,245,255))
        row=self.known_row(self.assess(bytes(pixels)))
        self.assertNotEqual(4,row.slots[1].non_target_id,
                            'a recognized suffix is not the complete displayed product name')
    def test_two_matching_bank_ids_are_unknown_instead_of_first_id_winning(self):
        # A private compiled bank fixture gives the same identity two IDs. The
        # shipped eight-entry data and fixed production features are untouched.
        folder=Path(self.tmp.name)/'conflicting-bank';folder.mkdir()
        native=ROOT/'patches/loopctrl/ngg2'
        source=folder/'NG2Ring.c';source.write_bytes((native/'NG2Ring.c').read_bytes())
        count=len(self.byid)
        text=(native/'NG2RingBank.h').read_text().replace('#define R94_BANK_COUNT '+str(count),'#define R94_BANK_COUNT '+str(count+1))
        rows=text.splitlines();marker='static const R94BankEntry r94_bank_entries[] = {'
        index=next(i for i,line in enumerate(rows) if line.startswith(marker))
        entry=self.byid[4];word=entry['word']
        duplicate='{16,"conflicting_fixture",r94_bank_4_icons,1,%d,%d,%d,r94_bank_4_word,R94_BANK_NONTARGET,0}'%(word['width'],word['height'],word['ink'])
        rows[index]=rows[index][:-2]+','+duplicate+'};'
        (folder/'NG2RingBank.h').write_text('\n'.join(rows)+'\n')
        (folder/'NG2RingCoverage.h').write_bytes((native/'NG2RingCoverage.h').read_bytes())
        lib=self.build_library(source,folder/'conflict.so',(folder,))
        row=self.known_row(self.assess(self.shop((1,4,8)),lib))
        self.assertEqual(0,row.slots[1].non_target_id)
        self.assertEqual(1,row.slots[1].non_target_conflict)
    def test_two_complete_named_shop_sets_are_negative(self):
        for ids in ((1,2,3),(6,7,8)):
            with self.subTest(identities=ids):
                result=self.assess(self.shop(ids),scene=True)
                self.assertEqual(3,result.outcome,'complete observed goods and independent non-target identities must permit the negative cycle')
                self.assertEqual(2,result.coverage)
                self.assertEqual(1,result.certificate.board_mode)
                self.assertGreaterEqual(result.selected_row,0)
                self.assertEqual(ids,tuple(slot.non_target_id for slot in result.rows[result.selected_row].slots))
    def test_complete_coverage_certificate_joins_the_selected_row(self):
        for ids in ((1,2,3),(6,7,8)):
            with self.subTest(identities=ids):
                result=self.assess(self.shop(ids),scene=True)
                self.assertEqual(2,result.coverage)
                self.assertEqual(result.selected_row,result.certificate.row_index)
                row=result.rows[result.selected_row]
                self.assertEqual((row.left,row.sy),tuple(result.certificate.row))
                self.assertEqual((3,3,0,0),(result.certificate.observed_items,
                    result.certificate.observed_prices,result.certificate.unmatched_items,
                    result.certificate.unmatched_prices))
    def test_extra_authenticated_shop_board_blocks_complete_coverage(self):
        result=self.assess(self.shop(extra_board=True),scene=True)
        self.assertNotEqual(2,result.coverage,
                            'a third authenticated SHOP board cannot be ignored outside the chosen strip')
        self.assertNotEqual(3,result.outcome)
    def test_gold_frame_defines_the_board_when_lower_yellow_pixels_are_gold(self):
        result=self.assess(self.shop(framed_boards=True),scene=True)
        self.assertEqual(2,result.coverage,
                         'the complete physical gold frame remains the board authority when its yellow interior shrinks')
        self.assertEqual(2,result.certificate.board_mode)
    def test_broken_frame_wrong_spacing_or_clipped_board_cannot_complete_coverage(self):
        for options in ({'broken_frame':'corner'},{'broken_frame':'edge'},
                        {'right_board_delta':3},{'right_board_delta':4},
                        {'right_board_delta':5},{'right_board_delta':450}):
            with self.subTest(options=options):
                result=self.assess(self.shop(framed_boards=True,**options),scene=True)
                self.assertNotEqual(2,result.coverage)
                self.assertNotEqual(3,result.outcome)
    def test_gold_continuation_outside_board_roi_is_not_a_closed_frame(self):
        result=self.assess(self.shop(framed_boards=True,exterior_frame_extension=True),scene=True)
        self.assertNotEqual(2,result.coverage,
                            'a board whose gold continues outside the fixed ROI has an unobserved physical extent')
        self.assertNotEqual(3,result.outcome)
    def test_different_merchant_colours_and_hud_overlap_do_not_authenticate_layout(self):
        wrong=self.assess(self.shop(wrong_merchant=True),scene=True)
        self.assertNotEqual(2,wrong.coverage)
        self.assertNotEqual(3,wrong.outcome)
        original=self.shop();shifted=bytearray(bytes((0,0,0,255))*(WIDTH*HEIGHT))
        for y in range(HEIGHT-180):
            for x in range(WIDTH-350):
                old=4*(y*WIDTH+x);new=4*((y+180)*WIDTH+x+350)
                shifted[new:new+4]=original[old:old+4]
        covered=self.assess(bytes(shifted),scene=True)
        self.assertNotEqual(2,covered.coverage)
        self.assertNotEqual(3,covered.outcome)
    def test_separated_small_foreground_specks_do_not_create_a_fourth_item(self):
        pixels=bytearray(self.shop())
        for start in (314,458):
            points=[(start+4*x,158+4*y) for y in range(3) for x in range(5)][:13]
            for x,y in points:
                at=4*(y*WIDTH+x);pixels[at:at+4]=bytes((70,70,70,255))
        result=self.assess(bytes(pixels),scene=True)
        self.assertEqual(2,result.coverage,
                         'two distant groups of thirteen isolated floor specks are not a local extra item')
        self.assertEqual(0,result.certificate.unmatched_items)
    def test_local_disconnected_foreground_23_is_allowed_and_24_is_held(self):
        points=[(314+2*x,186+2*y) for y in range(6) for x in range(5)]
        for count in (23,24):
            with self.subTest(bright_pixels=count):
                pixels=bytearray(self.shop())
                for x,y in points[:count]:
                    at=4*(y*WIDTH+x);pixels[at:at+4]=bytes((10,170,165,255))
                result=self.assess(bytes(pixels),scene=True)
                if count==23:self.assertEqual(2,result.coverage)
                else:
                    self.assertNotEqual(2,result.coverage)
                    self.assertNotEqual(3,result.outcome)
    def test_missing_or_wrong_slot_name_uncatalogued_object_and_unseen_end_hold(self):
        for options in ({'missing_name':1},{'wrong_name_slot':True},
                        {'extra_object':True},{'missing_wall':True},
                        {'missing_price':2},{'missing_merchant':True},
                        {'missing_shop_glyph':True}):
            with self.subTest(options=options):
                result=self.assess(self.shop(**options),scene=True)
                self.assertNotEqual(3,result.outcome,'unknown name/coverage/extra object cannot authorize restart')
    def test_target_template_and_ringlike_icon_keep_target_or_candidate(self):
        for name,expected in ((True,2),(False,1)):
            with self.subTest(target_name=name):
                result=self.assess(self.shop(target=True,target_name=name))
                self.assertEqual(expected,result.outcome)
                self.assertNotEqual(3,result.outcome)
    def test_off_row_partial_target_or_candidate_vetoes_complete_main_shop(self):
        for named,expected in ((True,2),(False,1)):
            with self.subTest(isolated_target_name=named):
                pixels=bytearray(self.shop());cx,sy=650,200
                def put(x,y,rgb):
                    at=4*(y*WIDTH+x);pixels[at:at+4]=bytes((*rgb,255))
                for y in range(sy-14,sy+15):
                    for x in range(cx-15,cx+15):put(x,y,(220,210,10))
                sprite=FEATURES['icons'][1]
                for dx,dy,r,g,b in sprite['bright']:put(cx-18+dx,sy+34+dy,(r,g,b))
                for dx,dy in sprite['dark']:put(cx-18+dx,sy+34+dy,(0,0,0))
                if named:
                    for dy,row in enumerate(FEATURES['word']['rows_hex']):
                        bits=int(row,16)
                        for dx in range(84):
                            if bits>>dx&1:put(cx-42+dx,sy+11+dy,(245,245,245))
                result=self.assess(bytes(pixels),scene=True)
                self.assertEqual(expected,result.outcome,
                                 'an isolated partial target outside the complete main row must hold the whole result')
                self.assertGreaterEqual(result.selected_partial,0)
                self.assertNotEqual(3,result.outcome)
    def test_different_known_ring_requires_its_own_name_and_does_not_prove_target(self):
        result=self.assess(self.shop((6,7,8),missing_name=0))
        self.assertEqual(0,result.outcome)
        self.assertNotEqual(3,result.outcome)
    def test_confirmed_closed_containers_are_distinct_ignored_evidence(self):
        for ident in (9,10):
            with self.subTest(container=ident):
                row=self.known_row(self.assess(self.shop((4,5,ident))))
                slot=row.slots[2]
                self.assertEqual(4,slot.outcome)
                self.assertEqual(2,slot.kind)
                self.assertEqual(ident,slot.ignored_container_id)
                self.assertEqual(0,slot.non_target_id,'ignored contents are not judged non-target')
                self.assertGreaterEqual(slot.ignored_icon_score,.94)
    def test_complete_container_shop_certifies_exposed_scope_without_judging_contents(self):
        for ident in (9,10):
            with self.subTest(container=ident):
                # The short named items leave both physical board frames
                # observed; container contents remain outside the scope.
                result=self.assess(self.shop((1,2,ident)),scene=True)
                self.assertEqual(2,result.coverage)
                self.assertEqual(3,result.outcome,
                                 'complete exposed scope advances even when confirmed closed-container contents are ignored')
                certificate=result.certificate
                self.assertEqual(1,certificate.board_mode)
                self.assertEqual((2,1),(certificate.non_target_items,certificate.ignored_containers))
                self.assertGreater(certificate.policy_version,0)
                self.assertEqual(result.selected_row,certificate.row_index)
                slot=result.rows[certificate.row_index].slots[2]
                self.assertEqual(tuple(slot.ignored_icon_box),tuple(certificate.item_boxes[2]))
                self.assertEqual((0,0,0,0),tuple(certificate.name_boxes[2]),
                                 'a confirmed ignored chest has no fabricated product-name witness')
    def test_long_product_name_occluding_a_board_edge_keeps_coverage_incomplete(self):
        for ident in (9,10):
            with self.subTest(container=ident):
                # The shortened right yellow face makes raw-pair authority
                # unavailable; an occluded physical edge cannot complete the
                # independent strict-frame fallback.
                # Full glyph row eight covers thirteen of the thirty-six
                # bottom-edge pixels; both named identities remain readable.
                result=self.assess(self.shop((4,5,ident),framed_boards=True,
                                             name_y_offsets={1:-1}),scene=True)
                row=self.known_row(result)
                self.assertEqual((4,5),tuple(slot.non_target_id for slot in row.slots[:2]))
                self.assertEqual(ident,row.slots[2].ignored_container_id)
                self.assertNotEqual(2,result.coverage)
                self.assertNotEqual(3,result.outcome)
    def test_nameless_blob_or_damaged_container_shape_is_not_ignored(self):
        for ident in (9,10):
            with self.subTest(container=ident):
                row=self.known_row(self.assess(self.shop((4,5,ident),container_damage=True)))
                self.assertEqual(0,row.slots[2].ignored_container_id)
                self.assertNotEqual(4,row.slots[2].outcome)

if __name__=='__main__':unittest.main()
