"""Target-only finite-strip confidence; procedural pixels are not accuracy data."""
import ctypes as C
import json
from pathlib import Path
import tempfile
import unittest
import tests.test_native_ring_bank094 as legacy_bank

from tests.test_native_ring094 import Result, Options, Clock, Cancelled
from tests.test_native_ring_bank094 import complete_shop, bank_data, auth_data
from tests.test_native_perception import NativeScene
from tests.test_target_assessment087 import WIDTH, HEIGHT, FEATURES

ROOT = Path(__file__).resolve().parents[1]


class TargetOnly095Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='target-only095-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.lib = legacy_bank.NativeRingBank094Tests.build_library(
            ROOT/'patches/loopctrl/ngg2/NG2Ring.c', Path(cls.tmp.name)/'ring.so')
        cls.lib.ng2_ring_negative_certificate.argtypes = [C.POINTER(Result)]
        cls.lib.ng2_ring_negative_certificate.restype = C.c_int
        cls.entries = bank_data()['entries'][:3]
        fixture=Path(cls.tmp.name)/'primary.c'
        fixture.write_text('#include '+json.dumps(str(ROOT/'patches/loopctrl/ngg2/NG2Ring.c'))+'\n'
            'int binary095_primary(const unsigned char *rgba, NG2RingResult *out) {'
            'memset(out,0,sizeof(*out));out->rows[0].left=360;out->rows[0].sy=120;'
            'return binary_primary(rgba,NULL,out,&out->rows[0]);}\n'
            'int binary095_word(const unsigned char *rgba, NG2RingResult *out) {'
            'RingObservation observed;if(ring_observe(rgba,&observed))return -1;'
            'memset(out,0,sizeof(*out));out->rows[0].left=360;out->rows[0].sy=120;'
            'return binary_word_veto(&observed,NULL,out,&out->rows[0]);}\n')
        cls.primary=legacy_bank.NativeRingBank094Tests.build_library(fixture,Path(cls.tmp.name)/'primary.so')
        cls.primary.binary095_primary.argtypes=[C.c_void_p,C.POINTER(Result)]
        cls.primary.binary095_primary.restype=C.c_int
        cls.primary.binary095_word.argtypes=[C.c_void_p,C.POINTER(Result)]
        cls.primary.binary095_word.restype=C.c_int

    def shop(self, **kwargs):
        return complete_shop(self.entries, auth=auth_data(), **kwargs)

    def assess(self, pixels, mode=2, goods=2, cancelled=False):
        now = Clock(lambda _: 100)
        cancel = Cancelled(lambda _: int(cancelled))
        scene = NativeScene(abi_version=1, struct_size=C.sizeof(NativeScene),
                            state=2, gold_state=2, goods=goods)
        scene.tiles[0] = 2
        options = Options(abi=1, size=C.sizeof(Options), mode=mode,
                          deadline_ns=1000000000, now_ns=now, cancelled=cancel,
                          scene=C.addressof(scene), fast=1)
        result = Result()
        buf = C.create_string_buffer(pixels)
        status = self.lib.ng2_ring_assess_rgba(buf, len(pixels), WIDTH*4,
                                              C.byref(options), C.byref(result))
        return status, result

    def certificate_fixture(self):
        status, result = self.assess(self.shop(), mode=1)
        self.assertEqual((0, 3, 2), (status, result.outcome, result.coverage))
        row = result.rows[result.selected_row]
        left, sy = row.left, row.sy
        result.certificate.policy_version = 2
        result.certificate.strip_box[:] = (left-54, sy+24, 180, 67)
        for index, cx in enumerate((left, left+36, left+72, left-36, left+108)):
            slot = row.slots[index] if index < 3 else result.partial[index-3]
            C.memset(C.addressof(slot), 0, C.sizeof(slot))
            slot.cx, slot.sy, slot.slot = cx, sy, index if index < 3 else 0
            slot.kind, slot.outcome = 3, 3
            slot.icon_score = slot.icon_upper_bound = .1
            slot.icon_box[:] = (cx-16, sy+35, 32, 28)
            slot.non_target_icon_box[:] = (cx-18, sy+24, 36, 67)
            if index < 3:
                result.certificate.item_boxes[index][:] = slot.non_target_icon_box
                result.certificate.name_boxes[index][:] = (0, 0, 0, 0)
        result.partial_count = 2
        return result

    def test_policy2_certificate_accepts_catalog_free_complete_sweep(self):
        result = self.certificate_fixture()
        self.assertEqual(1, self.lib.ng2_ring_negative_certificate(C.byref(result)))

    def test_complete_uncatalogued_icons_and_missing_names_are_binary_negative(self):
        pixels = bytearray(self.shop(missing_name=0))
        # Unknown turquoise products, not a new learned catalogue entry.
        for cx in (360,396,432):
            for y in range(144,186):
                for x in range(cx-18,cx+18):
                    at=4*(y*WIDTH+x)
                    pixels[at:at+4]=bytes((20,180,150,255))
        status,result=self.assess(bytes(pixels))
        self.assertEqual((0,3,2,2),(status,result.outcome,result.coverage,result.certificate.policy_version))
        self.assertEqual((3,3,3),tuple(s.kind for s in result.rows[result.selected_row].slots))
        self.assertEqual((0,0,0),tuple(s.non_target_id for s in result.rows[result.selected_row].slots))
        self.assertEqual(2,result.partial_count)
        self.assertEqual(1,self.lib.ng2_ring_negative_certificate(C.byref(result)))

    def test_clipped_or_partial_goods_missing_price_and_extra_object_hold(self):
        for options in ({'missing_wall':True},{'missing_price':1},{'extra_object':True},{'extra_board':True}):
            with self.subTest(options=options):
                status,result=self.assess(self.shop(**options))
                self.assertEqual(0,status)
                self.assertNotEqual(3,result.outcome)
                self.assertEqual(0,self.lib.ng2_ring_negative_certificate(C.byref(result)))
        status,result=self.assess(self.shop(),goods=1)
        self.assertEqual((0,1),(status,result.coverage))
        self.assertNotEqual(3,result.outcome)

    def test_shop_glyph_and_merchant_are_independent_layout_requirements(self):
        for options in ({'missing_merchant':True},{'missing_shop_glyph':True},{'wrong_merchant':True}):
            with self.subTest(options=options):
                status,result=self.assess(self.shop(**options))
                self.assertEqual(0,status)
                self.assertNotEqual(3,result.outcome)

    def test_same_probe_target_icon_candidate_and_observed_word_only_veto(self):
        for has_name,expected in ((True,2),(False,1)):
            status,result=self.assess(self.shop(target=True,target_name=has_name))
            self.assertEqual((0,expected),(status,result.outcome))
        pixels=bytearray(self.shop())
        for y in range(140,151):
            for x in range(354,438):
                at=4*(y*WIDTH+x);pixels[at:at+4]=bytes((27,17,12,255))
        for dy,row in enumerate(FEATURES['word']['rows_hex']):
            bits=int(row,16)
            for dx in range(84):
                if bits>>dx&1:
                    at=4*((140+dy)*WIDTH+354+dx);pixels[at:at+4]=bytes((245,245,245,255))
        status,result=self.assess(bytes(pixels))
        self.assertEqual((0,1),(status,result.outcome),'strong observed target name holds even below icon threshold')

    def test_target_between_prices_is_covered_without_slot_identity(self):
        pixels=bytearray(self.shop())
        sp=FEATURES['icons'][1];cx=378;sx=cx-sp['width']//2;iy=155
        for y in range(iy,iy+sp['height']):
            for x in range(sx,sx+sp['width']):
                at=4*(y*WIDTH+x);pixels[at:at+4]=bytes((27,17,12,255))
        for dx,dy,r,g,b in sp['bright']:
            at=4*((iy+dy)*WIDTH+sx+dx);pixels[at:at+4]=bytes((r,g,b,255))
        for dx,dy in sp['dark']:
            at=4*((iy+dy)*WIDTH+sx+dx);pixels[at:at+4]=bytes((0,0,0,255))
        status,result=self.assess(bytes(pixels))
        self.assertEqual((0,1),(status,result.outcome))
        self.assertEqual(0,self.lib.ng2_ring_negative_certificate(C.byref(result)))

    def test_dense_primary_covers_all_template_edge_and_gap_poses(self):
        for sp in FEATURES['icons']:
            # Legal strip boundary poses, +/-8 slot gaps and the lower extra
            # six-pixel band, independent of price/sign detection fixtures.
            for x,y in ((306,144),(486-sp['width'],144),
                        (306,211-sp['height']),(486-sp['width'],211-sp['height']),
                        (378-sp['width']//2,211-sp['height']),(414-sp['width']//2,144)):
                pixels=bytearray(bytes((27,17,12,255))*(WIDTH*HEIGHT))
                for dx,dy,r,g,b in sp['bright']:
                    at=4*((y+dy)*WIDTH+x+dx);pixels[at:at+4]=bytes((r,g,b,255))
                for dx,dy in sp['dark']:
                    at=4*((y+dy)*WIDTH+x+dx);pixels[at:at+4]=bytes((0,0,0,255))
                result=Result();buf=C.create_string_buffer(bytes(pixels))
                status=self.primary.binary095_primary(buf,C.byref(result))
                with self.subTest(size=(sp['width'],sp['height']),pose=(x,y)):
                    self.assertEqual((0,1),(status,result.outcome))

    def test_full_strip_hud_overlap_cannot_be_a_complete_negative(self):
        source=self.shop();pixels=bytearray(bytes((0,0,0,255))*(WIDTH*HEIGHT))
        # Move the whole observed shop down120px: the primary strip now
        # crosses the fixed bottom heart HUD although the top signs remain.
        pixels[120*WIDTH*4:]=source[:(HEIGHT-120)*WIDTH*4]
        status,result=self.assess(bytes(pixels))
        self.assertEqual(0,status)
        self.assertNotEqual(3,result.outcome)
        self.assertEqual(0,self.lib.ng2_ring_negative_certificate(C.byref(result)))

    def test_lower_iou_qualified_name_is_not_hidden_by_higher_iou_low_coverage(self):
        pixels=bytearray(bytes((0,0,0,255))*(WIDTH*HEIGHT))
        ink=[(x,y) for y,row in enumerate(FEATURES['word']['rows_hex'])
             for x in range(84) if int(row,16)>>x&1]
        background=[(x,y) for y,row in enumerate(FEATURES['word']['rows_hex'])
                    for x in range(84) if not(int(row,16)>>x&1)]
        # A:205/239=.85774 IoU but coverage<.90. B:220/262=.83969
        # IoU and220/239=.92050 coverage: B must independently veto.
        for start,points in ((260,ink[:205]),(420,ink[:220]+background[:23])):
            for x,y in points:
                at=4*((150+y)*WIDTH+start+x);pixels[at:at+4]=bytes((245,245,245,255))
        result=Result();buf=C.create_string_buffer(bytes(pixels))
        status=self.primary.binary095_word(buf,C.byref(result))
        self.assertEqual((0,1),(status,result.outcome))

    def test_original_partial_strong_word_is_preserved_before_five_cell_replacement(self):
        pixels=bytearray(self.shop())
        # The original left SHOP's -2-cell partial observation has center288.
        # Its fully visible name starts228, outside selected B's word union.
        for y in range(155,181):
            for x in range(277,300):
                at=4*(y*WIDTH+x);pixels[at:at+4]=bytes((20,180,150,255))
        for dy,row in enumerate(FEATURES['word']['rows_hex']):
            for dx in range(84):
                if int(row,16)>>dx&1:
                    at=4*((127+dy)*WIDTH+228+dx);pixels[at:at+4]=bytes((245,245,245,255))
        status,result=self.assess(bytes(pixels))
        self.assertEqual((0,1),(status,result.outcome))
        self.assertEqual(0,self.lib.ng2_ring_negative_certificate(C.byref(result)))

    def test_original_partial_qualified_word_survives_its_higher_iou_decoy(self):
        pixels=bytearray(self.shop())
        for y in range(155,181):
            for x in range(277,300):
                at=4*(y*WIDTH+x);pixels[at:at+4]=bytes((20,180,150,255))
        ink=[(x,y) for y,row in enumerate(FEATURES['word']['rows_hex'])
             for x in range(84) if int(row,16)>>x&1]
        background=[(x,y) for y,row in enumerate(FEATURES['word']['rows_hex'])
                    for x in range(84) if not(int(row,16)>>x&1)]
        for top,points in ((110,ink[:205]),(127,ink[:220]+background[:23])):
            for x,y in points:
                at=4*((top+y)*WIDTH+228+x);pixels[at:at+4]=bytes((245,245,245,255))
        status,result=self.assess(bytes(pixels))
        self.assertEqual((0,1),(status,result.outcome))

    def test_every_cell_upper_bound_and_structural_field_is_checked(self):
        base=self.certificate_fixture()
        for index in range(5):
            for damage in ('bound','word','identity','pose','cell'):
                result=Result.from_buffer_copy(base)
                slot=result.rows[result.selected_row].slots[index] if index<3 else result.partial[index-3]
                if damage=='bound':slot.icon_score=slot.icon_upper_bound=.80
                elif damage=='word':slot.word_present=1;slot.word_iou=.82;slot.word_coverage=.90
                elif damage=='identity':slot.non_target_id=1
                elif damage=='pose':slot.icon_box[0]=0
                else:slot.non_target_icon_box[2]=35
                with self.subTest(index=index,damage=damage):
                    self.assertEqual(0,self.lib.ng2_ring_negative_certificate(C.byref(result)))

    def test_failure_cancel_alpha_and_legacy_modes_keep_their_distinct_semantics(self):
        status,result=self.assess(self.shop(),cancelled=True)
        self.assertEqual((1,0,0),(status,result.outcome,result.coverage))
        pixels=bytearray(self.shop());pixels[3]=254
        status,result=self.assess(bytes(pixels))
        self.assertEqual((3,0,0),(status,result.outcome,result.coverage))
        for mode in (0,1):
            status,result=self.assess(self.shop(),mode=mode)
            self.assertEqual((0,3,1),(status,result.outcome,result.certificate.policy_version))
