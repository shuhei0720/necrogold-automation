"""TEST117 qualify a current C-owned Scene once, revalidate its ownership live.

Execution counters live only in the copied test translation unit. No timing
threshold or selected matcher result supplies positive authorization.
"""
import ctypes as C
from pathlib import Path
import shutil
import tempfile
import unittest

from tests import test_native_stationary117 as stationary
from tests import test_native_stationary_support117 as support


class NativeStationaryQualification117Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.instrumented=tempfile.TemporaryDirectory(prefix='qualification117-')
        directory=Path(cls.instrumented.name)
        for p in stationary.CORE.glob('NG2*'):
            if p.suffix in ('.c','.h'):shutil.copyfile(p,directory/p.name)
        p=directory/'NG2Navigation.c';source=p.read_text()
        for signature,counter in (
            ('static void view(const unsigned char raw[N],View *out) {','views'),
            ('static double intensity(const View *a,const View *b,int sx,int sy) {','raw')):
            if source.count(signature)!=1:raise AssertionError('one instrumented primitive is required')
            source=source.replace(signature,signature+'++qualification117_'+counter+';')
        source='#include <stdint.h>\nstatic uint64_t qualification117_views,qualification117_raw;\n'+source
        source+='\nvoid qualification117_reset(void){qualification117_views=qualification117_raw=0;}\n'
        source+='uint64_t qualification117_count(int field){return field?qualification117_raw:qualification117_views;}\n'
        p.write_text(source)
        previous=stationary.CORE
        try:
            stationary.CORE=directory
            stationary.NativeClearProof117Tests.setUpClass.__func__(cls)
        finally:stationary.CORE=previous
        cls.lib.qualification117_count.argtypes=[C.c_int];cls.lib.qualification117_count.restype=C.c_uint64

    @classmethod
    def tearDownClass(cls):
        stationary.NativeClearProof117Tests.tearDownClass.__func__(cls)
        cls.instrumented.cleanup()

    def prepared_current(self, supported):
        if supported:
            before,fixed,current,old=self.support_cut()
            self.cut_observe(fixed,start=10_700_083,end=22_107_292,commit=45_736_417)
            self.cut_observe(current,start=138_665_250,end=149_785_167,commit=175_623_458)
        else:
            _,current,old,_=self.lose_ready()
        new=self.reacquire_fixed_cadence(current)
        return current,old,new

    def test_exact_owned_current_Scene_begin_does_not_repeat_matchers(self):
        for supported in (False,True):
            with self.subTest(supported=supported):
                self.fresh_engine();current,old,new=self.prepared_current(supported)
                # A new real source is independently classified first. Mutating
                # its caller buffer afterwards cannot mutate C-owned p.scene.
                self.now+=20_000_000
                caller=self.frame(current)
                self.assertEqual(1,self.observe(caller))
                caller.signature[:]=bytes(len(caller.signature))
                caller.tiles[:]=bytes(len(caller.tiles))
                self.lib.qualification117_reset()
                self.reject_old_callbacks_without_mutation(old)
                self.now=new.not_before_ns
                self.assertEqual(1,self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1))
                self.assertEqual((0,0),(self.lib.qualification117_count(0),self.lib.qualification117_count(1)),
                    'a live ownership check of the exact C-owned qualified source must not repeat pixel matching')
                self.assertEqual((2,2),(self.status().inputs,self.status().moves))
                self.reject_old_callbacks_without_mutation(old)

    def test_novel_source_recomputes_and_wrong_prefix_cannot_reuse_old_qualification(self):
        current,old,new=self.prepared_current(True)
        self.lib.qualification117_reset()
        self.now+=20_000_000
        identical=self.frame(current)
        self.assertEqual(1,self.observe(identical))
        self.assertGreater(self.lib.qualification117_count(1),0,'a new source must recompute normal evidence')
        self.now+=5_000_000
        self.lib.qualification117_reset()
        self.assertEqual(1,self.observe(identical))
        self.assertGreater(self.lib.qualification117_count(1),0,
            'identical bytes at a different capture ID still need independent current evidence')
        self.now+=5_000_000
        self.assertEqual(0,self.observe(current,prefix=self.prefix-1))
        self.lib.qualification117_reset()
        self.now=new.not_before_ns
        self.assertEqual(0,self.lib.ng2_controller_begin(self.engine,new.id,self.now,1,0,1),
            'a novel rejected source revokes qualification; an old same-pixel observation cannot authorize input')
        self.assertEqual((2,2),(self.status().inputs,self.status().moves))
        self.assertEqual(0,next(e for e in self.events()if e.command.id==new.id).begin_ns)
        self.assertEqual((0,0),(self.lib.qualification117_count(0),self.lib.qualification117_count(1)))
        self.reject_old_callbacks_without_mutation(old)

    def test_ready_owned_source_publication_tick_does_not_repeat_matchers(self):
        _,fixed,current,old=self.support_cut()
        self.cut_observe(fixed,start=10_700_083,end=22_107_292,commit=45_736_417)
        self.cut_observe(current,start=138_665_250,end=149_785_167,commit=175_623_458)
        # Same fixed50ms physical-HUD cadence as the independent future fixture.
        # Each new source computes evidence; its following tick must not repeat it.
        for offset in range(225_623_458,1_975_623_459,50_000_000):
            self.cut_observe(current,start=offset-18_000_000,end=offset-6_000_000,commit=offset)
            self.lib.qualification117_reset()
            ready,new=self.tick()
            self.assertEqual(0,self.status().reason)
            self.assertEqual((0,0),(self.lib.qualification117_count(0),self.lib.qualification117_count(1)),
                'publication must revalidate the exact current source without repeating pixel evidence')
            if ready:
                self.assertEqual(4,new.kind)
                break
        else:self.fail('fixed current proof/HUD cadence must produce one bounded replacement')
        self.assertEqual(self.saved_credit,self.credit())
        self.reject_old_callbacks_without_mutation(old)


for name in ('setUp','scene','frame','observe','observe_actual','tick','status','events','ack','fit',
    'next_move','publish_procedural_candidate','fresh_engine','recovery','recovery_samples',
    'all_public_bytes','reject_old_callbacks_without_mutation','motion_wait','credit','choice',
    'observed_vantage','observed_result','preparation_epoch','armed','motion','assert_waiting',
    'next_operation','start_clear_cut','start_gold_cut','cut_observe','reacquire_fixed_cadence','lose_ready'):
    setattr(NativeStationaryQualification117Tests,name,getattr(stationary.NativeClearProof117Tests,name))
NativeStationaryQualification117Tests.support_cut=support.NativeFixedSupport117Tests.support_cut

if __name__=='__main__':unittest.main()
