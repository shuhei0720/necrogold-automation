"""Direct C aggregation contract. Procedural fixtures are not device accuracy."""
import ctypes as C
import math
from pathlib import Path
import subprocess
import tempfile
import unittest
from necroprobe import target_assessment as target
from tests.test_target_assessment087 import shop
from tests.test_native_controller import Scene

ROOT = Path(__file__).resolve().parents[1]
Clock=C.CFUNCTYPE(C.c_uint64,C.c_void_p)
Cancelled=C.CFUNCTYPE(C.c_int,C.c_void_p)
class Options(C.Structure):
    _fields_=[('abi',C.c_uint32),('size',C.c_uint32),('mode',C.c_int32),('reserved',C.c_uint32),
              ('deadline_ns',C.c_uint64),('now_ns',Clock),('cancelled',Cancelled),('context',C.c_void_p),
              ('scene',C.c_void_p),('fast',C.c_uint32)]

class Slot(C.Structure):
    _fields_ = [('cx',C.c_int32),('sy',C.c_int32),('slot',C.c_int32),('word_present',C.c_int32),
                ('icon_score',C.c_double),('word_iou',C.c_double),('word_coverage',C.c_double),
                ('icon_box',C.c_int32*4),('word_box',C.c_int32*4),
                ('icon_score_exact',C.c_uint32),('icon_upper_bound',C.c_double),
                ('outcome',C.c_uint32),('non_target_id',C.c_uint32),
                ('non_target_icon_score',C.c_double),('non_target_name_iou',C.c_double),
                ('non_target_name_coverage',C.c_double),('non_target_icon_box',C.c_int32*4),
                ('non_target_name_box',C.c_int32*4),('non_target_conflict',C.c_uint32),
                ('kind',C.c_uint32),('ignored_container_id',C.c_uint32)]+[
                (name,C.c_double) for name in ('ignored_icon_score','ignored_gold_iou','ignored_gold_coverage',
                                             'ignored_dark_iou','ignored_dark_coverage')]+[('ignored_icon_box',C.c_int32*4)]
class Row(C.Structure):
    _fields_ = [('left',C.c_int32),('sy',C.c_int32),('word_slot',C.c_int32),
                ('outcome',C.c_uint32),('reason',C.c_uint32),('slots',Slot*3)]
class Endcap(C.Structure):
    _fields_=[('box',C.c_int32*4)]+[(name,C.c_int32) for name in (
        'r','g','b','spread','black_count','count','bright_count','price_ink_count',
        'floor_full','floor_upper','floor_lower')]
class Coverage(C.Structure):
    _fields_=[('layout_version',C.c_uint32)]+[(name,C.c_int32) for name in (
        'accepted_rows','observed_items','observed_prices','unmatched_items','unmatched_prices',
        'scene_state','scene_goods','actual_gold_cells')]+[('row',C.c_int32*2),
        ('strip_box',C.c_int32*4),('merchant_box',C.c_int32*4),('sign_boxes',(C.c_int32*4)*2),
        ('merchant_score',C.c_double),('merchant_coverage',C.c_double),
        ('sign_iou',C.c_double*2),('sign_coverage',C.c_double*2),('endcaps',Endcap*2),
        ('item_boxes',(C.c_int32*4)*3),('name_boxes',(C.c_int32*4)*3),('price_boxes',(C.c_int32*4)*3),
        ('policy_version',C.c_uint32),('failure_flags',C.c_uint32)]+[(name,C.c_int32) for name in (
        'row_index','non_target_items','ignored_containers','unmatched_boards')]+[
        ('board_boxes',(C.c_int32*4)*2),('board_counts',C.c_int32*2),
        ('board_edge_counts',(C.c_int32*4)*2),('board_corner_counts',(C.c_int32*4)*2),
        ('board_exterior_count',C.c_int32*2),('board_mode',C.c_uint32)]
class Result(C.Structure):
    _fields_ = [(name,C.c_uint32) for name in ('abi','size','status','outcome','coverage','reason')]+[
        (name,C.c_int32) for name in ('row_count','selected_row','partial_count','selected_partial')]+[
        ('partial_safe_no_positive',C.c_uint32)]+[
        (name,C.c_uint64) for name in ('started_ns','finished_ns','checks')]+[
        ('rows',Row*4),('partial',Slot*12),('certificate',Coverage)]

class NativeRing094Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='native-ring094-')
        cls.addClassCleanup(cls.tmp.cleanup)
        path=Path(cls.tmp.name)/'ring.so'
        subprocess.run(['cc','-std=c11','-O2','-fno-fast-math','-ffp-contract=off',
            '-frounding-math','-Wall','-Wextra','-Werror','-shared','-fPIC',
            str(ROOT/'patches/loopctrl/ngg2/NG2Ring.c'),
            *[str(ROOT/'tools/ring_native'/name) for name in ('observe.c','icon.c','word.c')],
            '-lm','-o',str(path)],check=True,capture_output=True)
        cls.lib=C.CDLL(str(path))
        cls.lib.ng2_ring_aggregate.argtypes=[C.POINTER(Result)]
        cls.lib.ng2_ring_aggregate.restype=C.c_int
        cls.lib.ng2_ring_round9.argtypes=[C.c_double]
        cls.lib.ng2_ring_round9.restype=C.c_double
        cls.lib.ng2_ring_assess_rgba.argtypes=[C.c_void_p,C.c_size_t,C.c_size_t,C.POINTER(Options),C.POINTER(Result)]
        cls.lib.ng2_ring_assess_rgba.restype=C.c_int
        cls.lib.ng2_ring_negative_certificate.argtypes=[C.POINTER(Result)]
        cls.lib.ng2_ring_negative_certificate.restype=C.c_int

    def raw(self,*scores):
        value=Result(abi=1,size=C.sizeof(Result),row_count=len(scores))
        for index,items in enumerate(scores):
            row=value.rows[index];row.left=200+index*36;row.sy=120
            for slot,score in enumerate(items):
                row.slots[slot].slot=slot;row.slots[slot].icon_score=score
        return value

    def aggregate(self,value):
        self.assertEqual(0,self.lib.ng2_ring_aggregate(C.byref(value)))
        return value

    def test_same_slot_icon_and_name_precedes_a_stronger_unpaired_icon(self):
        value=self.raw((.99,.2,.1),(.1,.88,.2))
        item=value.rows[1].slots[1];item.word_present=1;item.word_iou=.82;item.word_coverage=.90
        value=self.aggregate(value)
        self.assertEqual(2,value.outcome,'GOODS-02 requires target before a stronger unpaired icon')
        self.assertEqual(1,value.selected_row)
        self.assertEqual(1,value.rows[1].word_slot)

    def test_partial_visible_target_and_candidate_survive_missing_three_column_row(self):
        value=self.raw();value.partial_count=1
        item=value.partial[0];item.slot=0;item.icon_score=.9
        self.assertEqual(1,self.aggregate(value).outcome,'partial target-like icon must be held')
        item.word_present=1;item.word_iou=.9;item.word_coverage=.95
        self.assertEqual(2,self.aggregate(value).outcome)
        self.assertEqual(0,value.selected_partial)

    def test_round9_matches_python_at_binary64_thresholds_and_decimal_ties(self):
        for number in (0.,1.,.8,.88,.82,.9,.7999999995,.8799999995,
                       .8199999995,.8999999995,1.000001,0.1234567885,0.1234567895):
            for value in (number,math.nextafter(number,-math.inf),math.nextafter(number,math.inf)):
                if value>=0:
                    self.assertEqual(round(value,9),self.lib.ng2_ring_round9(value),repr(value))

    def test_no_match_and_three_rows_never_prove_negative(self):
        value=self.aggregate(self.raw((.2,.3,.4),(.1,.2,.3),(.4,.3,.2)))
        self.assertEqual(0,value.outcome)
        self.assertNotEqual(2,value.coverage)

    def assess(self,pixels,options=None):
        value=Result();pixels=C.create_string_buffer(pixels)
        status=self.lib.ng2_ring_assess_rgba(pixels,len(pixels)-1,896*4,
                                           C.byref(options) if options else None,C.byref(value))
        self.assertEqual(status,value.status)
        return value

    def test_direct_opaque_rgba_same_slot_target_and_raw_word_all_slots(self):
        value=self.assess(shop())
        self.assertEqual(0,value.status)
        self.assertEqual(2,value.outcome)
        self.assertEqual(1,value.row_count)
        row=value.rows[value.selected_row]
        self.assertEqual((470,120),(row.left,row.sy))
        self.assertEqual([.344309933,1.,.344309933],[slot.icon_score for slot in row.slots])
        self.assertTrue(all(slot.word_present for slot in row.slots),'raw word must be computed for every slot')
        self.assertEqual((1.,1.),(row.slots[1].word_iou,row.slots[1].word_coverage))

    def test_pixel_failure_cancellation_and_deadline_never_become_completed_unknown(self):
        pixels=bytearray(shop());pixels[3]=254
        self.assertEqual(3,self.assess(bytes(pixels)).status)
        options=Options(abi=1,size=C.sizeof(Options),mode=0,now_ns=Clock(lambda _:100),
                        cancelled=Cancelled(lambda _:1))
        self.assertEqual(1,self.assess(shop(),options).status)
        options.cancelled=Cancelled(lambda _:0);options.deadline_ns=100
        self.assertEqual(2,self.assess(shop(),options).status)

    def test_partial_pixels_keep_single_icon_name_even_without_a_complete_row(self):
        pixels=bytearray(shop())
        for cx in (470,542):
            for y in range(144,205):
                for x in range(cx-17,cx+18):
                    pixels[4*(y*896+x):4*(y*896+x)+4]=bytes((12,8,7,255))
        value=self.assess(bytes(pixels))
        self.assertEqual(0,value.status)
        self.assertEqual(0,value.row_count)
        self.assertEqual(2,value.outcome,'missing adjacent slots must not discard the visible target')
        self.assertGreater(value.partial_count,0)
        self.assertNotEqual(2,value.coverage)

    def test_partial_visible_target_is_retained_when_price_ink_is_occluded(self):
        pixels=bytearray(shop())
        for y in range(189,209):
            for x in range(450,564):
                pixels[4*(y*896+x):4*(y*896+x)+4]=bytes((12,8,7,255))
        value=self.assess(bytes(pixels))
        self.assertEqual(0,value.status)
        self.assertEqual(2,value.outcome,'the price is not a prerequisite for retaining a visible target')
        self.assertNotEqual(2,value.coverage)

    def test_only_completed_observed_partial_without_a_positive_may_continue(self):
        scene=Scene(abi_version=1,struct_size=C.sizeof(Scene),state=2,goods=1)
        options=Options(abi=1,size=C.sizeof(Options),scene=C.addressof(scene))
        value=self.assess(shop(icon=False,name=False),options)
        self.assertEqual((0,0,1,1),(value.status,value.outcome,value.coverage,value.partial_safe_no_positive))
        for pixels in (shop(),bytes((0,0,0,255))*(896*414)):
            self.assertEqual(0,self.assess(pixels,options).partial_safe_no_positive)
        options.cancelled=Cancelled(lambda _:1)
        self.assertEqual(0,self.assess(shop(icon=False,name=False),options).partial_safe_no_positive)

    def test_partial_icon_above_hud_is_retained_when_only_price_overlaps_hud(self):
        value=self.assess(shop(left=250,sign_y=300))
        self.assertEqual(0,value.status)
        self.assertEqual(0,value.row_count)
        self.assertEqual(2,value.outcome,'HUD overlap of the price cannot discard a clear icon and name')

    def test_raw_aggregation_cannot_retain_stale_identity_or_coverage_witnesses(self):
        value=self.raw((.1,.2,.3));value.partial_safe_no_positive=1
        value.certificate.accepted_rows=1;value.certificate.policy_version=1
        item=value.rows[0].slots[0];item.non_target_id=4;item.non_target_icon_score=1.
        item.non_target_conflict=1;item.ignored_container_id=9;item.ignored_icon_score=1.;item.kind=2
        value=self.aggregate(value)
        self.assertEqual(0,value.partial_safe_no_positive)
        self.assertEqual(0,value.certificate.accepted_rows)
        self.assertEqual((0,0.,0,0,0.,0),(item.non_target_id,item.non_target_icon_score,
            item.non_target_conflict,item.ignored_container_id,item.ignored_icon_score,item.kind))

    def test_fast_upper_bounds_preserve_positive_and_explicitly_qualify_pruned_scores(self):
        options=Options(abi=1,size=C.sizeof(Options),fast=1)
        unknown=self.assess(shop(icon=False,name=False),options)
        self.assertEqual((0,0),(unknown.status,unknown.outcome))
        slots=list(unknown.rows[0].slots)
        self.assertTrue(any(not slot.icon_score_exact for slot in slots))
        for slot in slots:
            if not slot.icon_score_exact:
                self.assertLess(slot.icon_upper_bound,.80)
                self.assertEqual(slot.icon_upper_bound,slot.icon_score)
        for pixels,expected in ((shop(),2),(shop(name=False),1)):
            value=self.assess(pixels,options)
            self.assertEqual((0,expected),(value.status,value.outcome))
            self.assertEqual(1,value.rows[value.selected_row].slots[1].icon_score_exact)

    def test_more_than_twelve_observed_sign_hypotheses_fail_instead_of_dropping_candidates(self):
        pixels=bytearray(bytes((12,8,7,255))*(896*414))
        for cy in (100,180,260):
            for cx in (200,300,500,600,700):
                for y in range(cy-14,cy+15):
                    for x in range(cx-15,cx+15):
                        pixels[4*(y*896+x):4*(y*896+x)+4]=bytes((220,210,10,255))
        value=self.assess(bytes(pixels))
        self.assertEqual(5,value.status,'finite adapter overflow must hold failure, never silently skip a possible target')
        self.assertEqual(0,value.partial_safe_no_positive)

    def test_negative_finalizer_rejects_missing_identity_foreign_row_and_any_candidate(self):
        from tests.test_native_ring_bank094 import bank_data,auth_data,complete_shop
        bank=bank_data();byid={item['id']:item for item in bank['entries']}
        scene=Scene(abi_version=1,struct_size=C.sizeof(Scene),state=2,goods=2);scene.tiles[0]=2
        options=Options(abi=1,size=C.sizeof(Options),scene=C.addressof(scene),fast=1)
        original=self.assess(complete_shop([byid[i] for i in (1,2,3)],auth=auth_data()),options)
        self.assertEqual((0,3,2),(original.status,original.outcome,original.coverage))
        self.assertEqual(1,self.lib.ng2_ring_negative_certificate(C.byref(original)))
        def mutate(value,case):
            selected=value.rows[value.selected_row]
            if case=='identity':selected.slots[0].non_target_id=0
            elif case=='name':selected.slots[0].non_target_name_iou=.5
            elif case=='row':value.certificate.row_index+=1
            elif case=='coverage':value.coverage=1
            elif case=='candidate':
                value.partial_count=1;value.partial[0].outcome=1
                value.partial[0].icon_score=.9;value.partial[0].icon_score_exact=1
            elif case=='box_overflow':value.certificate.board_boxes[0][2]=2**31-1
            elif case=='colour_overflow':value.certificate.endcaps[0].r=2**31-1
            elif case=='row_overflow':selected.left=-(2**31)
        for case in ('identity','name','row','coverage','candidate','box_overflow','colour_overflow','row_overflow'):
            with self.subTest(fault=case):
                value=Result.from_buffer_copy(bytes(original));mutate(value,case)
                self.assertEqual(0,self.lib.ng2_ring_negative_certificate(C.byref(value)))

if __name__=='__main__': unittest.main()
