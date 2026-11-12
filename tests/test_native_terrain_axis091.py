"""TEST091: finite raw units need complete old terrain and independent axes.

The procedural surface has an independently defined displacement. These
fields are not phone pixels, Controller replies or evidence of shop arrival.
"""
import ctypes as C
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tests.test_native_controller import Scene
from tests.test_native_motion067 import Motion, procedural_pair
from tests.test_native_passage_motion082 import pair as base_pair, cell, DIRS

CORE = Path(__file__).resolve().parents[1] / 'patches/loopctrl/ngg2'


def pair(direction=3):
    scenes = base_pair(direction, points=45)
    dx, dy = DIRS[direction]
    for x, y in ((-4,-2),(-3,-2),(-2,-2),(2,-2),(3,-2),
                 (-4,2),(-3,2),(-2,2),(2,2)):
        scenes[0].tiles[cell(x,y)] = 4
        scenes[1].tiles[cell(x-dx,y-dy)] = 4
    # A narrow left surface and a wider right surface are both translated.
    # Dense edges retain the unit while blur admits nearby pixel aliases.
    for y in range(104):
        for x in range(224):
            if x >= 114 or (80 <= x < 102 and 25 <= y < 45): continue
            scenes[0].signature[y*224+x] = 0
            xx, yy = x-9*dx, y-9*dy
            if 0 <= xx < 224 and 0 <= yy < 104:
                scenes[1].signature[yy*224+xx] = 0
    return scenes


SHIM = r'''
static void test091_candidates(const NG2Scene*a,const NG2Scene*b,View v[2],Candidate c[73]){
    int n=1,amount,d;view(a->signature,v);view(b->signature,v+1);
    c[0].sx=c[0].sy=0;c[0].score=intensity(v,v+1,0,0);
    for(amount=1;amount<=18;++amount)for(d=1;d<=4;++d){
        c[n].sx=amount*ddx[d];c[n].sy=amount*ddy[d];
        c[n].score=intensity(v,v+1,c[n].sx,c[n].sy);++n;
    }
    qsort(c,73,sizeof(*c),ranked);
}
void test091_previous(const NG2Scene*a,const NG2Scene*b,int d,int out[51]){
    View v[2];Candidate c[73];NG2Motion m={0};int i=0;test091_candidates(a,b,v,c);
    #define SAVE091() do{out[3*i]=m.kind;out[3*i+1]=m.dx;out[3*i+2]=m.dy;++i;}while(0)
    evaluate_motion(a,b,d,v,c,&m);SAVE091();
    gate_detail_motion(a,b,d,v,c,&m);SAVE091();
    opening_detail_motion(a,b,d,v,c,&m);SAVE091();
    passage_detail_motion(a,b,d,v,c,&m);SAVE091();
    opening_gradient_motion(a,b,d,c,&m);SAVE091();
    static_floor_gradient_motion(a,b,d,c,&m);SAVE091();
    corner_blur_motion(a,b,d,v,c,&m);SAVE091();
    closed_gate_axis_motion(a,b,d,c,&m);SAVE091();
    revealed_gate_axis_motion(a,b,d,c,&m);SAVE091();
    sparse_gate_motion(a,b,d,v,c,&m);SAVE091();
    side_gate_motion(a,b,d,v,c,&m);SAVE091();
    terrain_blur_motion(a,b,d,v,c,&m);SAVE091();
    corner_gradient_blur_motion(a,b,d,v,c,&m);SAVE091();
    first_gold_terrain_blur_motion(a,b,d,v,c,&m);SAVE091();
    stationary_terrain_motion(a,b,d,v,c,&m);SAVE091();
    singleton_gold_terrain_blur_motion(a,b,d,v,c,&m);SAVE091();
    hud_occluded_terrain_blur_motion(a,b,d,v,c,&m);SAVE091();
    #undef SAVE091
}
void test091_stats(const NG2Scene*a,const NG2Scene*b,int d,double scores[2],int out[14]){
    View v[2];Candidate c[73];ClosedGateAxisCache*ax;int k,su,ba;
    test091_candidates(a,b,v,c);scores[0]=c[0].score;scores[1]=c[1].score-c[0].score;
    out[0]=c[0].sx;out[1]=c[0].sy;out[2]=1;
    for(k=0;k<73;++k)if(!isfinite(c[k].score))out[2]=0;
    world_blur_texture(a,b,v,c[0].sx,c[0].sy,out+3,out+4,out+5);out[7]=1;
    for(k=1;k<73;++k){world_blur_texture(a,b,v,c[k].sx,c[k].sy,&su,&ba,NULL);
        if(!texture_lead(out[3],out[4],su,ba))out[7]=0;}
    ax=(ClosedGateAxisCache*)calloc(1,sizeof(*ax));if(!ax)return;
    closed_gate_axis_features(a,ax->before,ax->indices,&ax->count);
    closed_gate_axis_features(b,ax->after,NULL,NULL);
    closed_gate_axis_texture(ax,c[0].sx,c[0].sy,out+8,out+9,out+10);out[12]=1;
    for(k=1;k<73;++k){closed_gate_axis_texture(ax,c[k].sx,c[k].sy,&su,&ba,NULL);
        if(!texture_lead(out[8],out[9],su,ba))out[12]=0;}
    free(ax);out[13]=d;
}
void test091_proof(const NG2Scene*a,const NG2Scene*b,int d,double score,double gap,
                   int sx,int sy,int other,NG2Motion*out){
    View v[2];Candidate c[73];int k;test091_candidates(a,b,v,c);
    for(k=0;k<73;++k)if(c[k].sx==sx&&c[k].sy==sy){Candidate z=c[0];c[0]=c[k];c[k]=z;break;}
    c[0].score=score;for(k=1;k<73;++k)c[k].score=score+gap;
    if(other==1)c[72].score=NAN;
    if(other==2)c[72].score=-INFINITY;
    if(other==3)c[72].score=INFINITY;
#if TEST091_PRESENT
    terrain_axis_unit_motion(a,b,d,v,c,out);
#else
    (void)d;(void)out;
#endif
}
int test091_geometry(const NG2Scene*a,const NG2Scene*b,int sx,int sy){
#if TEST091_PRESENT
    return unique_visible_terrain_translation(a,b,sx,sy);
#else
    (void)a;(void)b;(void)sx;(void)sy;return 0;
#endif
}
int test091_count(const NG2Scene*a,const NG2Scene*b){
#if TEST091_PRESENT
    int am,d,n=0;for(am=0;am<=2;++am)for(d=1;d<=(am?4:1);++d){
        n+=visible_terrain_translation(a,b,am*ddx[d],am*ddy[d]);}
    return n;
#else
    (void)a;(void)b;return 0;
#endif
}
void test091_component(const NG2Scene*a,const NG2Scene*b,int mode,int out[7]){
    NG2Scene aa=*a,bb=*b;View v[2];Candidate c[73];NG2Motion m={0};
    ClosedGateAxisCache*ax;int i,k,su,ba;
    test091_candidates(a,b,v,c);
    /* Isolate the computed feature boundary: raw candidates and the original
     * blur remain real while an independent axis plane is removed/aliased.
     * These negatives are not manufactured public-path acceptance fixtures. */
    if(mode==1){memset(v[0].blur,0,N);memset(v[1].blur,0,N);}
    if(mode==2){memset(aa.signature,0,N);memset(bb.signature,0,N);}
    if(mode==3)for(i=0;i<N;++i){int x=i%W,y=i/W;
        aa.signature[i]=bb.signature[i]=(unsigned char)(20+(37*x+53*(y%9))%211);}
    if(mode==4)for(i=0;i<N;++i)if(i/W<53){aa.signature[i]=bb.signature[i]=0;}
    ax=(ClosedGateAxisCache*)calloc(1,sizeof(*ax));if(!ax)return;
    closed_gate_axis_features(&aa,ax->before,ax->indices,&ax->count);
    closed_gate_axis_features(&bb,ax->after,NULL,NULL);
    closed_gate_axis_texture(ax,c[0].sx,c[0].sy,out,out+1,out+2);out[4]=1;
    for(k=1;k<73;++k){closed_gate_axis_texture(ax,c[k].sx,c[k].sy,&su,&ba,NULL);
        if(!texture_lead(out[0],out[1],su,ba))out[4]=0;}
    free(ax);
#if TEST091_PRESENT
    terrain_axis_unit_motion(&aa,&bb,NG2_UP,v,c,&m);
#endif
    out[5]=m.kind;out[6]=m.dx||m.dy;
}
'''


class NativeTerrainAxis091Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='test091-terrain-axis-')
        directory = Path(cls.temp.name)
        for p in CORE.glob('NG2*'):
            if p.suffix in ('.c','.h'): shutil.copyfile(p,directory/p.name)
        source = Path(os.environ.get('NECRO_TEST091_BASELINE_NAVIGATION', CORE/'NG2Navigation.c'))
        shutil.copyfile(source,directory/'NG2Navigation.c')
        hashes = {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(directory.glob('NG2*')) if p.suffix in ('.c','.h')}
        if len(hashes) != 8: raise AssertionError('eight native source identities required')
        identity = os.environ.get('NECRO_TEST091_UNIT_SOURCE_IDENTITY')
        if identity:
            Path(identity).write_text(json.dumps(dict(source_sha256=hashes,
                selected_navigation=str(source),test_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()),
                sort_keys=True,indent=2)+'\n')
        present = 'static void terrain_axis_unit_motion(' in source.read_text()
        shim = directory/'proof.c'
        shim.write_text('#define NECROGOLD_HOST_TEST 1\n'
            +f'#define TEST091_PRESENT {int(present)}\n#include "{directory / "NG2Navigation.c"}"\n'+SHIM)
        cls.libraries = {}
        external = os.environ.get('NECRO_TEST091_UNIT_LIBRARY')
        if external:
            cls.libraries['external'] = C.CDLL(external)
        else:
            for profile, flags in (('o0',['-O0']),('strict_o2',['-O2','-fno-fast-math','-ffp-contract=off'])):
                path = directory/(profile+'.so')
                subprocess.run(['cc','-std=c99',*flags,'-Wall','-Wextra','-Werror','-pedantic',
                    '-fPIC','-shared',str(shim),'-lm','-o',str(path)],check=True,capture_output=True)
                cls.libraries[profile]=C.CDLL(str(path))
        for lib in cls.libraries.values():
            ptr=C.POINTER(Scene);ints=C.POINTER(C.c_int)
            lib.ng2_motion.argtypes=[ptr,ptr,C.c_int,C.POINTER(Motion)]
            lib.test091_previous.argtypes=[ptr,ptr,C.c_int,ints]
            lib.test091_stats.argtypes=[ptr,ptr,C.c_int,C.POINTER(C.c_double),ints]
            lib.test091_proof.argtypes=[ptr,ptr,C.c_int,C.c_double,C.c_double,C.c_int,C.c_int,C.c_int,C.POINTER(Motion)]
            lib.test091_geometry.argtypes=[ptr,ptr,C.c_int,C.c_int]
            lib.test091_count.argtypes=[ptr,ptr]
            lib.test091_component.argtypes=[ptr,ptr,C.c_int,ints]

    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def motion(self,lib,scenes,direction=3):
        out=Motion(99,99,99)
        self.assertEqual(1,lib.ng2_motion(C.byref(scenes[0]),C.byref(scenes[1]),direction,C.byref(out)))
        return out.kind,out.dx,out.dy

    def proof(self,lib,scenes,direction=3,score=.6,gap=.2,shift=None,other=0,initial=0):
        dx,dy=DIRS[direction];sx,sy=shift if shift is not None else (-9*dx,-9*dy)
        out=Motion(initial,0,0)
        lib.test091_proof(C.byref(scenes[0]),C.byref(scenes[1]),direction,score,gap,sx,sy,other,C.byref(out))
        return out.kind,out.dx,out.dy

    def test_public_unit_requires_new_independent_axis_proof(self):
        for profile,lib in self.libraries.items():
            for direction in (3,4):
                with self.subTest(profile=profile,direction=direction):
                    scenes=pair(direction);dx,dy=DIRS[direction]
                    previous=(C.c_int*51)();scores=(C.c_double*2)();flags=(C.c_int*14)()
                    lib.test091_previous(C.byref(scenes[0]),C.byref(scenes[1]),direction,previous)
                    self.assertEqual([0]*51,list(previous),'all seventeen previous proofs stay independently UNKNOWN')
                    lib.test091_stats(C.byref(scenes[0]),C.byref(scenes[1]),direction,scores,flags)
                    self.assertGreater(scores[0],.45);self.assertGreaterEqual(scores[1],.08)
                    self.assertEqual((-9*dx,-9*dy),tuple(flags[:2]));self.assertEqual(1,flags[2])
                    self.assertGreaterEqual(flags[3],300);self.assertLessEqual(20*flags[4],flags[3])
                    self.assertGreaterEqual(min(flags[5:7]),100);self.assertEqual(0,flags[7])
                    self.assertGreaterEqual(flags[8],300);self.assertLessEqual(4*flags[9],flags[8])
                    self.assertGreaterEqual(min(flags[10:12]),100);self.assertEqual(1,flags[12])
                    self.assertEqual((1,dx,dy),self.motion(lib,scenes,direction),
                        'a uniquely retained observed unit needs its independent axis evidence')

    def test_complete_nonhud_old_terrain_and_unique_translation_are_required(self):
        for profile,lib in self.libraries.items():
            scenes=pair();self.assertEqual(1,lib.test091_count(C.byref(scenes[0]),C.byref(scenes[1])))
            self.assertEqual((1,0,-1),self.proof(lib,scenes))
            for point in ((-5,-2),(4,1)):
                for kind in (0,1,4):
                    scenes=pair();scenes[1].tiles[cell(point[0],point[1]+1)]=kind
                    self.assertEqual((0,0,0),self.proof(lib,scenes),'every old stone must survive without contradiction')
            scenes=pair();scenes[0].tiles[cell(4,1)]=1
            self.assertEqual((0,0,0),self.proof(lib,scenes),'one stone does not anchor a unit')
            scenes=pair();scenes[0].tiles[cell(-4,-2)]=1;scenes[1].tiles[cell(-4,-1)]=1
            self.assertEqual((0,0,0),self.proof(lib,scenes),'eight old dirt do not become nine')
            scenes=pair();scenes[0].tiles[cell(-9,-3)]=3;scenes[1].tiles[cell(-9,-2)]=3
            self.assertEqual((0,0,0),self.proof(lib,scenes),'a fixed HUD cannot supply a stone anchor')
            scenes=pair();scenes[0].tiles[cell(-4,-2)]=1;scenes[1].tiles[cell(-4,-1)]=1
            scenes[0].tiles[cell(-9,-3)]=4;scenes[1].tiles[cell(-9,-2)]=4
            self.assertEqual((0,0,0),self.proof(lib,scenes),'eight visible dirt plus one HUD do not become nine')
            scenes=pair()
            for scene in scenes:scene.tiles[:]=[1]*230
            for kind,points in ((3,((-5,0),(5,0))),
                                (4,tuple((x,0) for x in (-10,-9,-8,-7,-6,-4,-3,-2,2)))):
                for x,y in points:
                    scenes[0].tiles[cell(x,y)]=kind;scenes[1].tiles[cell(x,y+1)]=kind
            self.assertEqual(0,lib.test091_geometry(C.byref(scenes[0]),C.byref(scenes[1]),0,9))
            self.assertEqual((0,0,0),self.proof(lib,scenes),'collinear terrain is not independent')
            scenes=pair()
            for scene in scenes:scene.tiles[:]=[1]*230
            for kind,points in ((3,((-5,-2),(4,0))),
                                (4,((-5,-3),(-3,-3),(2,-3),(3,-3),(4,-3),(-5,2),(-4,2),(-3,2),(2,2)))):
                for x,y in points:
                    scenes[0].tiles[cell(x,y)]=kind
                    for tx,ty in ((0,1),(1,0)):
                        self.assertIn(scenes[1].tiles[cell(x+tx,y+ty)],(1,kind))
                        scenes[1].tiles[cell(x+tx,y+ty)]=kind
            self.assertEqual(2,lib.test091_count(C.byref(scenes[0]),C.byref(scenes[1])))
            self.assertEqual(0,lib.test091_geometry(C.byref(scenes[0]),C.byref(scenes[1]),0,9))
            self.assertEqual((0,0,0),self.proof(lib,scenes),'competing translations stay unknown')

    def test_blur_axis_ambiguity_and_single_region_cannot_supply_unit(self):
        for profile,lib in self.libraries.items():
            for mode in range(5):
                scenes=pair();flags=(C.c_int*7)()
                lib.test091_component(C.byref(scenes[0]),C.byref(scenes[1]),mode,flags)
                self.assertEqual((1,1) if mode==0 else (0,0),tuple(flags[5:7]))
                if mode==2:self.assertEqual(0,flags[0])
                if mode==3:
                    self.assertGreaterEqual(flags[0],300);self.assertLessEqual(4*flags[1],flags[0])
                    self.assertGreaterEqual(min(flags[2:4]),100);self.assertEqual(0,flags[4])
                if mode==4:self.assertLess(flags[2],100)

    def test_finite_unit_scope_and_original_known_results_are_preserved(self):
        for profile,lib in self.libraries.items():
            for score,gap,other,expected in ((.45,.2,0,0),(.450001,.2,0,1),(.6,.079999,0,0),
                    (.6,.2,0,1),(math.nan,.2,0,0),(math.inf,.2,0,0),(-math.inf,.2,0,0),
                    (.6,.2,1,0),(.6,.2,2,0),(.6,.2,3,0)):
                self.assertEqual((expected,0,-1 if expected else 0),self.proof(lib,pair(),score=score,gap=gap,other=other))
            for shift in ((0,0),(0,8),(0,18),(0,-9),(9,0)):
                self.assertEqual((0,0,0),self.proof(lib,pair(),shift=shift))
            for side in (0,1):
                for field,values in (('state',(0,1,3)),('gold_state',(0,2,3)),('goods',(1,2))):
                    for value in values:
                        scenes=pair();setattr(scenes[side],field,value)
                        self.assertEqual((0,0,0),self.proof(lib,scenes))
                for kind in (2,5,6):
                    scenes=pair();scenes[side].tiles[cell(7,-3)]=kind
                    self.assertEqual((0,0,0),self.proof(lib,scenes))
                scenes=pair();scenes[side].protected_cells[cell(8,4)]=1
                self.assertEqual((0,0,0),self.proof(lib,scenes))
            for side,point in ((0,(0,0)),(0,(0,-1)),(1,(0,0))):
                for kind in (0,3,4):
                    scenes=pair();scenes[side].tiles[cell(*point)]=kind
                    self.assertEqual((0,0,0),self.proof(lib,scenes))
            for initial in range(1,8):self.assertEqual((initial,0,0),self.proof(lib,pair(),initial=initial))
            for direction,(dx,dy) in DIRS.items():
                for pixels,expected in ((0,(2,0,0)),(8,(7,0,0)),(9,(1,dx,dy)),
                                        (18,(6,2*dx,2*dy)),(-9,(6,-dx,-dy))):
                    self.assertEqual(expected,self.motion(lib,procedural_pair(direction,pixels=pixels,overlay=False),direction))
            for direction in (1,2):
                dx,dy=DIRS[direction]
                self.assertEqual((1,dx,dy),self.motion(lib,pair(direction),direction))


if __name__ == '__main__': unittest.main()
