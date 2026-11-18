"""Closed-container price height is independent of its shop's proof shape.

Procedural fixed-feature drawings explain the observed failure; not phone runs.
"""
import ctypes as C
import unittest

from tests import test_native_single_sign_shop103 as single
from tests import test_native_closed_offer105 as closed
from tests.test_native_ring094 import Result


def closed_entry(container_id):
    return closed.FEATURE if container_id==11 else next(e for e in single.bank_data()['entries'] if e['id']==container_id)


def shop_pixels(slot=2, variation=False, damage=None, target=False, target_name=True,
                missing_price=None,container_id=11,pose_offset=None,price_height=7):
    pixels=bytearray(single.shop_pixels(target=target,target_name=target_name,
        missing_price=missing_price))
    cx=267+36*slot;entry=closed_entry(container_id);shape=entry['container_shape'];icon=entry['icons'][0]
    top=153+(pose_offset if pose_offset is not None else 49 if container_id==11 else 46)
    for y in range(177,244):
        for x in range(cx-18,cx+18):single._put(pixels,x,y,(27,17,15))
    gold=[int(row,16) for row in shape['gold_rows_hex']];dark=[int(row,16) for row in shape['dark_rows_hex']]
    for y in range(33):
        for x in range(36):
            colour=(220,160,15) if gold[y]>>x&1 else (12,8,7) if dark[y]>>x&1 else (60,60,60)
            single._put(pixels,cx-18+x,top+y,colour)
    for x,y,r,g,b in icon['bright']:single._put(pixels,cx-18+x,top+y,(r,g,b))
    for x,y in icon['dark']:single._put(pixels,cx-18+x,top+y,(0,0,0))
    if variation:
        samples={(x,y) for x,y,*_ in icon['bright']}|{(x,y) for x,y in icon['dark']}
        candidates=[]
        for y in range(33):
            for x in range(36):
                at=4*((top+y)*896+cx-18+x);r,g,b=pixels[at:at+3]
                if gold[y]>>x&1 and r>85 and g>45 and 2*b<g and 50*r<=100*g<=110*r:
                    candidates.append(((x,y) in samples,abs(g-r*.5),x,y,r,b))
        remove=sorted(candidates)[:max(0,len(candidates)-(95*shape['gold_ink'])//100)]
        add=[(x,y) for y in range(3,28) for x in range(3,33)
            if not(gold[y]>>x&1) and not(dark[y]>>x&1) and (x,y) not in samples][:10]
        for _sample,_distance,x,y,r,b in remove:single._put(pixels,cx-18+x,top+y,(r,int(.49*r),b))
        for x,y in add:single._put(pixels,cx-18+x,top+y,(220,160,15))
        background=[(x,y) for y in range(33) for x in range(36)
            if (x in (0,1,34,35) or y<3 or y>29) and not(gold[y]>>x&1)
            and not(dark[y]>>x&1) and (x,y) not in samples][:37]
        for x,y in background:single._put(pixels,cx-18+x,top+y,(12,8,7))
    if damage=='lid':
        for y in range(top+2,top+13):
            for x in range(cx-15,cx+16):single._put(pixels,x,y,(60,60,60))
    elif damage=='recolor':
        for y in range(top,top+33):
            for x in range(cx-18,cx+18):
                at=4*(y*896+x);r,g,b=pixels[at:at+3];single._put(pixels,x,y,(g,b,r))
    elif damage=='band_shift':
        for y in range(top,top+33):
            row=bytes(pixels[4*(y*896+cx-18):4*(y*896+cx+18)])
            for x in range(36):
                r,g,b=row[4*x:4*x+3]
                if r>85 and g>45 and 2*b<g and 50*r<=100*g<=110*r:
                    single._put(pixels,cx-18+x,y,(60,60,60));single._put(pixels,cx-17+x,y,(r,g,b))
    if slot!=missing_price:
        for i in range(3):
            for y,row in enumerate(('111','101','101','101','101','101','111')+('111',)*(price_height-7)):
                for x,bit in enumerate(row):
                    if bit=='1':single._put(pixels,cx-6+4*i+x,235+y,(245,245,245))
    return bytes(pixels)


class NativeClosedPrice106Tests(unittest.TestCase):
    setUpClass=classmethod(single.NativeSingleSignShop103Tests.setUpClass.__func__)

    def assess(self,pixels=None,scene=None,**kwargs):
        return single.normal_assess(self.lib,shop_pixels() if pixels is None else pixels,
            single.shop_scene() if scene is None else scene,**kwargs)

    def test_observed_closed_price_and_background_variation_have_separate_positive_proof(self):
        for slot in range(3):
            for variation in (False,True):
                for height in (7,8,9):
                    with self.subTest(slot=slot,variation=variation,height=height):
                        scene=single.shop_scene();before=bytes(scene)
                        status,result=self.assess(shop_pixels(slot=slot,variation=variation,price_height=height),scene)
                        self.assertEqual((0,3,2,7,2),(status,result.outcome,result.coverage,
                            result.certificate.policy_version,result.certificate.layout_version),
                            'an authenticated closed body explains its separately observed lower price')
                        self.assertEqual((2,1,0),(result.certificate.non_target_items,
                            result.certificate.ignored_containers,result.certificate.unmatched_prices))
                        self.assertEqual(11,result.rows[result.selected_row].slots[slot].ignored_container_id)
                        self.assertEqual((235,height),tuple(result.certificate.price_boxes[slot])[1::2])
                        self.assertEqual(1,self.lib.ng2_ring_negative_certificate(C.byref(result)))
                        self.assertEqual(before,bytes(scene))

    def test_target_missing_extra_price_and_damaged_closed_identity_are_held(self):
        # TEST111 permits an exact target image with its own observed price.
        for named,expected in ((True,2),(False,2)):
            status,result=self.assess(shop_pixels(target=True,target_name=named,price_height=8))
            self.assertEqual(expected,result.outcome)
            if not named:
                self.assertEqual((0,2,1),(status,result.outcome,result.coverage))
                self.assertGreaterEqual(result.selected_row,0)
                slot=result.rows[result.selected_row].slots[1]
                self.assertEqual((2,1),(slot.outcome,slot.icon_score_exact))
                self.assertGreaterEqual(slot.icon_score,.94)
                self.assertEqual(16,result.certificate.policy_version)
                self.assertEqual((1,1),(result.certificate.observed_items,
                    result.certificate.observed_prices))
                self.assertEqual(tuple(slot.icon_box),tuple(result.certificate.item_boxes[1]))
                self.assertEqual((297,231,11,7),tuple(result.certificate.price_boxes[1]))
                self.assertEqual((0,0,0,0),tuple(result.certificate.name_boxes[1]))
                self.assertEqual(0,self.lib.ng2_ring_negative_certificate(C.byref(result)))
        for missing in range(3):
            self.assertNotEqual(3,self.assess(shop_pixels(missing_price=missing,price_height=8))[1].outcome)
        for damage in ('lid','recolor','band_shift'):
            self.assertNotEqual(3,self.assess(shop_pixels(damage=damage,price_height=8))[1].outcome)
        status,value=self.assess(shop_pixels(price_height=10))
        self.assertEqual((0,0,1),(status,value.outcome,value.coverage))
        def late_prices(slots):
            pixels=bytearray(shop_pixels(price_height=8))
            for cx in slots:
                for y in range(222,244):
                    for x in range(cx-11,cx+12):single._put(pixels,x,y,(27,17,15))
                for i in range(3):
                    for y,row in enumerate(('111','101','101','101','101','101','111','111')):
                        for x,bit in enumerate(row):
                            if bit=='1':single._put(pixels,cx-6+4*i+x,235+y,(245,245,245))
            return bytes(pixels)
        # A complete common baseline already accepted by version1 keeps its
        # original authority. One late ordinary price instead requires the
        # new adapter, whose ordinary bound remains sy+89.
        status,value=self.assess(late_prices((267,303)))
        self.assertEqual((0,3,1),(status,value.outcome,value.certificate.layout_version))
        status,value=self.assess(late_prices((267,)))
        self.assertEqual((0,0,1),(status,value.outcome,value.coverage))
        pixels=bytearray(shop_pixels(price_height=8))
        for y in range(222,228):
            for x in range(281,284):single._put(pixels,x,y,(245,245,245))
        self.assertNotEqual(3,self.assess(bytes(pixels))[1].outcome)

    def test_version_two_closed_identity_and_actual_price_pose_cannot_be_forged(self):
        status,base=self.assess(shop_pixels(variation=True))
        self.assertEqual((0,3,2),(status,base.outcome,base.certificate.layout_version))
        changes={
            'old version':lambda r:setattr(r.certificate,'layout_version',1),
            'missing closed':lambda r:setattr(r.rows[r.selected_row].slots[2],'ignored_container_id',0),
            'wrong closed':lambda r:setattr(r.rows[r.selected_row].slots[2],'ignored_container_id',9),
            'score':lambda r:setattr(r.rows[r.selected_row].slots[2],'ignored_icon_score',.994999999),
            'gold coverage':lambda r:setattr(r.rows[r.selected_row].slots[2],'ignored_gold_coverage',.949999999),
            'dark coverage':lambda r:setattr(r.rows[r.selected_row].slots[2],'ignored_dark_coverage',.949999999),
            'impossible iou':lambda r:setattr(r.rows[r.selected_row].slots[2],'ignored_gold_iou',.001),
            'nan':lambda r:setattr(r.rows[r.selected_row].slots[2],'ignored_dark_iou',float('nan')),
            'price on body':lambda r:r.certificate.price_boxes[2].__setitem__(1,225),
            'target upper':lambda r:setattr(r.rows[r.selected_row].slots[2],'icon_upper_bound',.8),
            'extra price':lambda r:setattr(r.certificate,'unmatched_prices',1),
            'closed beyond B':lambda r:r.certificate.price_boxes[2].__setitem__(1,238),
            'ordinary beyond old band':lambda r:r.certificate.price_boxes[0].__setitem__(1,236),
        }
        for label,mutate in changes.items():
            with self.subTest(label=label):
                value=Result.from_buffer_copy(base);mutate(value)
                self.assertEqual(0,self.lib.ng2_ring_negative_certificate(C.byref(value)))

    def test_already_registered_gray_and_purple_closed_bodies_share_the_price_proof(self):
        for identity in (9,10):
            for variation in (False,True):
                for slot in range(3):
                    with self.subTest(identity=identity,variation=variation,slot=slot):
                        status,value=self.assess(shop_pixels(container_id=identity,variation=variation,slot=slot))
                        self.assertEqual((0,3,7,2),(status,value.outcome,
                            value.certificate.policy_version,value.certificate.layout_version))
                        self.assertEqual(identity,value.rows[value.selected_row].slots[slot].ignored_container_id)
                        self.assertEqual(1,self.lib.ng2_ring_negative_certificate(C.byref(value)))

    def test_integer_support_boundaries_are_exact_for_both_masks_and_all_existing_identities(self):
        for identity in (9,10,11):
            _,base=self.assess(shop_pixels(container_id=identity,variation=True))
            self.assertEqual(3,base.outcome)
            for component in ('gold','dark'):
                ink=closed_entry(identity)['container_shape'][component+'_ink'];minimum=95*ink//100
                for count,expected in ((minimum,1),(minimum-1,0)):
                    with self.subTest(identity=identity,component=component,count=count):
                        value=Result.from_buffer_copy(base);slot=value.rows[value.selected_row].slots[2]
                        slot.ignored_gold_iou=slot.ignored_dark_iou=.8
                        setattr(slot,'ignored_'+component+'_coverage',round(count/ink,9))
                        self.assertEqual(expected,self.lib.ng2_ring_negative_certificate(C.byref(value)))

    def test_price_complete_unknown_lower_cell_uses_the_same_versioned_identity(self):
        for identity in (9,10,11):
            with self.subTest(identity=identity):
                pixels=bytearray(shop_pixels(variation=True,container_id=identity))
                scene=closed.shop_scene(ax=-5,ay=0)
                single.draw_faces(pixels,267,153,((-15,-14,30,29),(-15,-14,30,29)))
                # Legacy price counts can already be complete while gray trim
                # overlaps its price box. Positive identity must bind a new
                # actual-price observation, without the target-domain mask.
                for cx in (267,303):
                    for y in range(222,242):
                        for x in range(cx-11,cx+12):single._put(pixels,x,y,(27,17,15))
                    for i in range(3):
                        for y,row in enumerate(('111','101','101','101','101','101','111')):
                            for x,bit in enumerate(row):
                                if bit=='1':single._put(pixels,cx-6+4*i+x,235+y,(245,245,245))
                status,value=self.assess(bytes(pixels),scene)
                self.assertEqual((0,3,2,10,2),(status,value.outcome,value.coverage,
                    value.certificate.policy_version,value.certificate.layout_version))
                self.assertEqual((3,0),(value.certificate.observed_prices,value.certificate.unmatched_prices))
                self.assertEqual((235,7),tuple(value.certificate.price_boxes[2])[1::2])
                self.assertEqual(1,self.lib.ng2_ring_negative_certificate(C.byref(value)))
                # A missing real price is a normal incomplete observation,
                # never a legacy-complete v2 result rejected as KERNEL.
                for y in range(235,242):
                    for x in range(328,350):single._put(pixels,x,y,(27,17,15))
                status,value=self.assess(bytes(pixels),scene)
                self.assertEqual((0,0,1),(status,value.outcome,value.coverage))

    def test_each_existing_shop_shape_uses_the_same_closed_price_adapter(self):
        from tests import test_native_structural_shop096 as p3
        from tests import test_native_side_shop100 as p4
        from tests import test_native_shop_geometry101 as p5
        from tests import test_native_shop_coverage102 as p6
        from tests import test_native_bottom_shop103 as p8
        from tests import test_native_offer_coverage104 as p9
        builders=[]
        for policy,module,klass,left,sy in ((3,p3,'NativeStructuralShop096Tests',301,117),
                (4,p4,'NativeSideShop100Tests',301,117),(5,p5,'NativeShopGeometry101Tests',301,81)):
            value=getattr(module,klass)();value.entries=single.bank_data()['entries'][:3]
            builders.append((policy,value.scene(),value.pixels(missing_shop_glyph=True,missing_merchant=True),left,sy))
        builders.extend(((6,p6.shop_scene(),p6.shop_pixels(),301,117),
            (7,single.shop_scene(),single.shop_pixels(),267,153),
            (8,p8.shop_scene(),p8.shop_pixels(),411,44),
            (9,p9.shop_scene(),p9.shop_pixels(),339,43)))
        closed_pixels=shop_pixels(variation=True,container_id=9,pose_offset=49)
        for policy,scene,pixels,left,sy in builders:
            with self.subTest(policy=policy):
                pixels=bytearray(pixels);shift_x=left-267;shift_y=sy-153
                for y in range(177,244):
                    a=4*(y*896+321);b=4*((y+shift_y)*896+321+shift_x)
                    pixels[b:b+144]=closed_pixels[a:a+144]
                status,value=self.assess(bytes(pixels),scene)
                self.assertEqual((0,3,policy,2),(status,value.outcome,
                    value.certificate.policy_version,value.certificate.layout_version))
                self.assertEqual(1,self.lib.ng2_ring_negative_certificate(C.byref(value)))


if __name__=='__main__':unittest.main()
