"""TEST117 one earned fixed support, with original authority and bounds intact.

The fixed camera and material are defined by a procedural physical world.
Illumination phases change; the late fixed grain is held, not translated.
This is a C/Scene contract test, not an iPhone or RGBA pipeline replay.
"""
import ctypes as C
from copy import deepcopy
import math
import random
from unittest.mock import patch
import unittest

from tests import test_native_controller as native
from tests import test_native_plural_wait103 as plural
from tests import test_native_stationary117 as stationary
from tests import test_native_single_gold117 as single
from tests.test_native_motion067 import Motion


def light_triplet(scene=None):
    if scene is None:
        scenes=[*single.gold_dirt_pair()];scenes.append(deepcopy(scenes[1]))
        scene=scenes[0]
    else:scenes=[deepcopy(scene)for _ in range(3)]
    width,height=224,104
    def known(x,y):
        if not(40<=x<179 and 20<=y<85)or(103<=x<122 and 43<=y<61)or(101<=x<123 and y>=80):return False
        for oy in range(-2,3):
            for ox in range(-2,3):
                if abs(ox)==2 and abs(oy)==2:continue
                xx,yy=x+ox,y+oy
                if not(40<=xx<179 and 20<=yy<85)or(103<=xx<122 and 43<=yy<61)or(101<=xx<123 and yy>=80):return False
                ax,ay=(4*xx-34)//36-11,(4*yy-9)//36-5
                if not(-11<=ax<=11 and -5<=ay<=4):return False
                i=(ay+5)*23+ax+11
                if scene.tiles[i]not in (1,2,3,4)or scene.protected_cells[i]:return False
        return True
    rng=random.Random(85085);world=[rng.randrange(14,35)for _ in range(width*height)]
    for lower,upper in ((23,34),(68,80)):
        domain=[(x,y)for y in range(lower,upper)for x in range(44,174)if known(x,y)]
        rng.shuffle(domain);islands=[]
        for x,y in domain:
            if all(max(abs(x-px),abs(y-py))>=5 for px,py in islands):
                islands.append((x,y))
                if len(islands)==17:break
        if len(islands)!=17:raise AssertionError('observed fixed band must support17 independently spaced islands')
        for x,y in islands:world[y*width+x]=rng.randrange(160,200)
    noise=random.Random(85086);grain=[noise.randrange(-17,18)for _ in world]
    for phase,out in enumerate(scenes):
        out.signature[:]=bytes(max(7,min(255,round(value+36*(1+math.sin(2*math.pi*((i%width)-phase)/48)))
            +(grain[i]if phase else 0)))for i,value in enumerate(world))
    return scenes


class NativeFixedSupport117Tests(unittest.TestCase):
    setUpClass=classmethod(stationary.NativeClearProof117Tests.setUpClass.__func__)
    tearDownClass=classmethod(stationary.NativeClearProof117Tests.tearDownClass.__func__)

    def support_cut(self,earned=True):
        pixels=[]
        def render(frame):
            images=light_triplet(frame);pixels[:]=[bytes(s.signature)for s in images]
            return pixels[0],pixels[1 if earned else 2]
        with patch.object(plural,'room_phase_pair',side_effect=render):
            before,support,old=self.start_gold_cut()
        current=deepcopy(support);current.signature=pixels[2]
        a,b,c=self.frame(before),self.frame(support),self.frame(current)
        self.lib.ng2_single_gold_dirt_motion_zero.argtypes=[C.POINTER(native.Scene),C.POINTER(native.Scene),C.c_int32,C.POINTER(Motion),C.POINTER(C.c_int32)]
        for x,y,expected in ((a,b,1 if earned else 0),(a,c,0)):
            motion=Motion();zero=C.c_int32(99)
            self.lib.ng2_single_gold_dirt_motion_zero(C.byref(x),C.byref(y),old.direction,C.byref(motion),C.byref(zero))
            self.assertEqual((0,0,0,expected),(motion.kind,motion.dx,motion.dy,zero.value))
        self.assertEqual((2,0,0),self.motion(support,current,old.direction))
        return before,support,current,old

    def test_first_direct_support_stays_fixed_and_funds_only_current_zero(self):
        before,support,current,old=self.support_cut()
        self.cut_observe(support,start=10_700_083,end=22_107_292,commit=45_736_417)
        # A later direct original zero must not replace the FIRST support.
        later=deepcopy(support);later.signature=before.signature
        self.assertEqual((2,0,0),self.motion(before,later,old.direction))
        self.cut_observe(later,start=55_814_292,end=66_476_083,commit=90_950_250)
        self.cut_observe(current,start=138_665_250,end=149_785_167,commit=175_623_458)
        new=self.reacquire_fixed_cadence(current)
        self.assertEqual(self.saved_credit,self.credit())
        self.assertGreater(new.id,old.id)
        self.assertLess(new.deadline_ns,self.parent_deadline)
        self.now=new.not_before_ns
        self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1))
        self.assertEqual((2,2),(self.status().inputs,self.status().moves),'begin/ACK are not displacement')
        self.reject_old_callbacks_without_mutation(old)

    def test_adjacent_zero_without_direct_original_qualification_cannot_create_support(self):
        _,_,current,old=self.support_cut(earned=False)
        self.cut_observe(current,start=10_700_083,end=22_107_292,commit=45_736_417)
        self.cut_observe(current,start=138_665_250,end=149_785_167,commit=175_623_458)
        self.assertEqual(0,self.tick()[0])
        offset=self.wait_deadline-self.trigger_commit
        self.cut_observe(current,start=offset-18_000_000,end=offset-6_000_000,commit=offset)
        self.assertEqual((8,2,2),(self.status().reason,self.status().inputs,self.status().moves))
        self.assertEqual(0,next(e for e in self.events()if e.command.id==old.id).begin_ns)

    def test_original_geometry_remains_required_even_when_fixed_support_is_strict_zero(self):
        _,support,current,old=self.support_cut()
        self.cut_observe(support,start=10_700_083,end=22_107_292,commit=45_736_417)
        current.tiles[(5,-3)]='floor'  # Lost old wall, outside origin/dest3x3.
        self.assertEqual((2,0,0),self.motion(support,current,old.direction))
        self.cut_observe(current,start=138_665_250,end=149_785_167,commit=175_623_458)
        self.assertEqual(0,self.tick()[0])
        self.assertEqual(self.saved_credit,self.credit())


for name in ('setUp','scene','frame','observe','observe_actual','tick','status','events','ack','fit',
    'next_move','publish_procedural_candidate','fresh_engine','recovery','recovery_samples',
    'all_public_bytes','reject_old_callbacks_without_mutation','motion_wait','credit','choice',
    'observed_vantage','observed_result','preparation_epoch','armed','motion','assert_waiting',
    'next_operation','start_gold_cut','cut_observe','reacquire_fixed_cadence'):
    setattr(NativeFixedSupport117Tests,name,getattr(stationary.NativeClearProof117Tests,name))


if __name__=='__main__':unittest.main()
