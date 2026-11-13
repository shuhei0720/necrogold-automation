"""TEST097: sparse-view unit motion while the old singleton gold is preserved.

Procedural signatures define their own displacement. Plane-isolation tests are
primitive contracts; none are phone replay, future shop arrival or accuracy.
"""
import ctypes as C
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

from tests.test_native_controller import Scene
from tests.test_native_motion067 import Motion

CORE = Path(__file__).resolve().parents[1] / 'patches/loopctrl/ngg2'
W, H = 224, 104
DIRS = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}


def cell(x, y):
    return (y + 5) * 23 + x + 11


def translate_map(before, after, direction=3):
    dx, dy = DIRS[direction]
    after.tiles[:] = [0] * 230
    for y in range(-5, 5):
        for x in range(-11, 12):
            xx, yy = x - dx, y - dy
            if -11 <= xx <= 11 and -5 <= yy <= 4:
                after.tiles[cell(xx, yy)] = before.tiles[cell(x, y)]


def pair(direction=3, pixels=9):
    before, after = [Scene(abi_version=1, struct_size=C.sizeof(Scene), state=2,
                          gold_state=2) for _ in range(2)]
    dx, dy = DIRS[direction]
    before.tiles[:] = [4] * 230
    for x, y, kind in ((0, 0, 1), (dx, dy, 1), (-3, -3, 2), (-4, -1, 3), (2, 1, 3)):
        before.tiles[cell(x, y)] = kind
    translate_map(before, after, direction)
    rng = random.Random(97097)
    world = bytearray(W * H)
    for y in range(25, 85):
        for x in range(80, 130):
            world[y * W + x] = 96
    for y in range(36, 85):
        for x in range(90, 130):
            world[y * W + x] = rng.randrange(20, 221)
    points = [(x, y) for y in range(36, 79) for x in range(80, 90)]
    rng.shuffle(points)
    for x, y in points[:40]:
        world[y * W + x] = rng.randrange(160, 224) if rng.getrandbits(1) else rng.randrange(16, 40)
    moved = bytearray(W * H)
    for y in range(H):
        for x in range(W):
            xx, yy = x - pixels * dx, y - pixels * dy
            if 0 <= xx < W and 0 <= yy < H:
                moved[yy * W + xx] = world[y * W + x]
    before.signature[:] = world
    after.signature[:] = moved
    return [before, after]


SHIM = r'''
static void ns097_candidates(const NG2Scene*a,const NG2Scene*b,View v[2],Candidate raw[73]) {
    int n=1,amount,d;view(a->signature,&v[0]);view(b->signature,&v[1]);
    raw[0].sx=raw[0].sy=0;raw[0].score=intensity(&v[0],&v[1],0,0);
    for(amount=1;amount<=18;++amount)for(d=1;d<=4;++d){
        raw[n].sx=amount*ddx[d];raw[n].sy=amount*ddy[d];
        raw[n].score=intensity(&v[0],&v[1],raw[n].sx,raw[n].sy);++n;
    }
    qsort(raw,73,sizeof(*raw),ranked);
}
void ns097_stats(const NG2Scene*a,const NG2Scene*b,int d,double scores[4],int flags[12]) {
    View v[2];Candidate raw[73],phase[73];ClosedGateAxisCache*c=calloc(1,sizeof(*c));
    int n=1,amount,k,s,bad,regions[3];ns097_candidates(a,b,v,raw);
    scores[0]=raw[0].score;scores[1]=raw[1].score;
    texture_match(&v[0],&v[1],raw[0].sx,raw[0].sy,0,&s,&bad,regions);flags[0]=s;
    phase[0].sx=phase[0].sy=0;phase[0].score=sparse_gate_intensity(a,b,&v[0],&v[1],0,0,NULL,NULL);
    for(amount=1;amount<=18;++amount)for(k=1;k<=4;++k){
        phase[n].sx=amount*ddx[k];phase[n].sy=amount*ddy[k];
        phase[n].score=sparse_gate_intensity(a,b,&v[0],&v[1],phase[n].sx,phase[n].sy,NULL,NULL);++n;
    }
    qsort(phase,73,sizeof(*phase),ranked);scores[2]=phase[0].score;scores[3]=phase[1].score;
    sparse_gate_intensity(a,b,&v[0],&v[1],phase[0].sx,phase[0].sy,&s,regions);
    flags[1]=s;flags[2]=regions[0];flags[3]=regions[1];flags[4]=sparse_gate_phase_valid(phase,d,s,regions);
    closed_gate_axis_features(a,c->before,c->indices,&c->count);closed_gate_axis_features(b,c->after,NULL,NULL);
    closed_gate_axis_texture(c,raw[0].sx,raw[0].sy,&s,&bad,regions);
    flags[5]=s;flags[6]=bad;flags[7]=regions[0];flags[8]=regions[1];flags[9]=closed_gate_axis_strong(c,raw);
    flags[10]=unique_visible_terrain_translation(a,b,raw[0].sx,raw[0].sy);
    flags[11]=revealed_singleton_raw_domain(raw,d);free(c);
}
void ns097_proof(const NG2Scene*a,const NG2Scene*b,int d,int initial,int raw_mode,int plane_mode,NG2Motion*out) {
    out->kind=initial;out->dx=initial?7:0;out->dy=initial?-3:0;
#if TEST097_PRESENT
    View v[2];Candidate raw[73];NG2Scene aa=*a,bb=*b;int x,y;
    ns097_candidates(a,b,v,raw);
    if(raw_mode==1)raw[0].score=.450001;
    if(raw_mode==2)raw[1].score=raw[0].score+.079999;
    if(raw_mode==3)raw[1].score=INFINITY;
    if(raw_mode==4)raw[72].score=NAN;
    if(raw_mode==5)raw[72].score=-INFINITY;
    if(raw_mode==6)raw[72].score=INFINITY;
    if(raw_mode==7){raw[0].sx=9*ddx[d];raw[0].sy=9*ddy[d];}
    if(raw_mode==8)raw[0].score=-.1;
    /* Isolate each computed plane: the unchanged original raw candidate and
     * other plane are deliberately retained, not asserted as coherent images. */
    if(plane_mode==1)memset(v[1].normalized,0,N);
    if(plane_mode==2)for(y=0;y<65;++y)for(x=0;x<W;++x)v[0].normalized[y*W+x]=v[1].normalized[y*W+x]=0;
    if(plane_mode==3)memset(bb.signature,0,N);
    if(plane_mode==4)for(y=0;y<N;++y)bb.signature[y]=(unsigned char)(255-bb.signature[y]);
    if(plane_mode==5)for(y=0;y<54;++y)for(x=0;x<W;++x)aa.signature[y*W+x]=bb.signature[y*W+x]=0;
    preserved_singleton_sparse_motion(&aa,&bb,d,v,raw,out);
#else
    (void)a;(void)b;(void)d;(void)raw_mode;(void)plane_mode;
#endif
}
'''


class NativePreservedSparse097Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='test097-preserved-sparse-')
        cls.addClassCleanup(cls.temp.cleanup)
        source = Path(os.environ.get('NECRO_TEST097_BASELINE_NAVIGATION', CORE / 'NG2Navigation.c'))
        shim = Path(cls.temp.name) / 'proof.c'
        shim.write_text('#define TEST097_PRESENT ' + str(int('static void preserved_singleton_sparse_motion(' in source.read_text())) + '\n#include "' + str(source) + '"\n' + SHIM)
        cls.libraries = {}
        evidence = os.environ.get('NECRO_TEST097_COMPILER_EVIDENCE')
        receipts = []
        for profile, flags in (('unchanged_o0', ['-O0']), ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            library = Path(cls.temp.name) / (profile + '.so')
            command = ['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror', '-pedantic', '-I', str(CORE), '-fPIC', '-shared', str(shim), '-lm', '-o', str(library)]
            result = subprocess.run(command, capture_output=True)
            if result.returncode:
                raise RuntimeError(result.stdout.decode() + result.stderr.decode())
            lib = C.CDLL(str(library))
            ptr, ints, doubles = C.POINTER(Scene), C.POINTER(C.c_int), C.POINTER(C.c_double)
            lib.ng2_motion.argtypes = [ptr, ptr, C.c_int, C.POINTER(Motion)]
            lib.ns097_proof.argtypes = [ptr, ptr, C.c_int, C.c_int, C.c_int, C.c_int, C.POINTER(Motion)]
            lib.ns097_stats.argtypes = [ptr, ptr, C.c_int, doubles, ints]
            cls.libraries[profile] = lib
            receipts.append(dict(profile=profile, command=command, returncode=result.returncode))
            if evidence:
                target = Path(evidence) / profile;target.mkdir(parents=True, exist_ok=True)
                for name, raw in (('NG2Navigation.c', source.read_bytes()), ('NG2Core.h', (source.parent / 'NG2Core.h').read_bytes()), ('proof.c', shim.read_bytes()), ('fixture.py', Path(__file__).read_bytes())):
                    (target / name).write_bytes(raw)
                (target / 'compiler.stdout').write_bytes(result.stdout)
                (target / 'compiler.stderr').write_bytes(result.stderr)
        if evidence:
            (Path(evidence) / 'commands.json').write_text(json.dumps(receipts, indent=2) + '\n')

    def motion(self, lib, images, direction=3):
        out = Motion()
        self.assertEqual(1, lib.ng2_motion(C.byref(images[0]), C.byref(images[1]), direction, C.byref(out)))
        return out.kind, out.dx, out.dy

    def proof(self, lib, images, direction=3, initial=0, raw_mode=0, plane_mode=0):
        out = Motion()
        lib.ns097_proof(C.byref(images[0]), C.byref(images[1]), direction, initial, raw_mode, plane_mode, C.byref(out))
        return out.kind, out.dx, out.dy

    def test_public_sparse_known_one_cell_is_not_lost(self):
        images = pair()
        for profile, lib in self.libraries.items():
            with self.subTest(profile=profile):
                scores, flags = (C.c_double * 4)(), (C.c_int * 12)()
                lib.ns097_stats(C.byref(images[0]), C.byref(images[1]), 3, scores, flags)
                self.assertLess(flags[0], 300)
                self.assertEqual(1, flags[4]);self.assertEqual(1, flags[9]);self.assertEqual(1, flags[10]);self.assertEqual(1, flags[11])
                self.assertTrue(all(math.isfinite(v) for v in scores));self.assertLessEqual(scores[0], .45);self.assertGreaterEqual(scores[1]-scores[0], .08)
                self.assertEqual((1, 0, -1), self.motion(lib, images), 'an observed old singleton and independently supported sparse unit must not be lost')

    def test_four_directions_need_only_the_arrival_floor(self):
        for lib in self.libraries.values():
            for direction, (dx, dy) in DIRS.items():
                with self.subTest(direction=direction):
                    images = pair(direction)
                    self.assertEqual(4, images[1].tiles[cell(dx, dy)])
                    self.assertEqual((1, dx, dy), self.proof(lib, images, direction))
                    self.assertEqual((1, dx, dy), self.motion(lib, images, direction))

    def test_exact_old_gold_stones_and_unique_projection_are_required(self):
        for lib in self.libraries.values():
            for change in ('gold_count', 'gold_projection', 'missing_stone', 'new_stone_only', 'ambiguous_terrain'):
                images = pair();a,b = images
                if change=='gold_count':b.tiles[cell(4, 2)]=2
                if change=='gold_projection':b.tiles[cell(-3,-2)]=4;b.tiles[cell(-2,-2)]=2
                if change=='missing_stone':b.tiles[cell(-4,0)]=4
                if change=='new_stone_only':a.tiles[cell(2,1)]=4
                if change=='ambiguous_terrain':
                    for x,y in ((-4,-2),(2,0)):b.tiles[cell(x,y)]=3
                with self.subTest(change=change):self.assertEqual((0,0,0),self.proof(lib,images))

    def test_old_dirt_support_and_noncollinearity_are_required(self):
        points=((-6,-3),(-5,-3),(-4,-3),(-2,-3),(1,-3),(3,-3),(-6,2),(-5,2),(-4,2))
        for lib in self.libraries.values():
            for count in (8,9):
                images=pair();a,b=images
                for i in range(230):
                    if a.tiles[i]==4:a.tiles[i]=1
                for x,y in points[:count]:a.tiles[cell(x,y)]=4
                translate_map(a,b)
                with self.subTest(count=count):self.assertEqual((1,0,-1) if count==9 else (0,0,0),self.proof(lib,images))
            images=pair();a,b=images
            for i in range(230):
                if a.tiles[i] in (3,4):a.tiles[i]=1
            for x in (-4,2):a.tiles[cell(x,-2)]=3
            for x in (-8,-7,-6,-5,-3,-2,-1,0,1):a.tiles[cell(x,-2)]=4
            translate_map(a,b);self.assertEqual((0,0,0),self.proof(lib,images))

    def test_complete_witness_rois_and_observed_endpoints_are_required(self):
        for lib in self.libraries.values():
            for change in ('gold_hud','gold_projected_hud','stone_hud','stone_projected_hud','source_origin','source_next','arrival'):
                images=pair();a,b=images
                if change=='gold_hud':a.tiles[cell(-3,-3)]=4;a.tiles[cell(0,-5)]=2;translate_map(a,b)
                if change=='gold_projected_hud':a.tiles[cell(-3,-3)]=4;a.tiles[cell(0,2)]=2;translate_map(a,b)
                if change=='stone_hud':a.tiles[cell(-4,-1)]=4;a.tiles[cell(7,-4)]=3;translate_map(a,b)
                if change=='stone_projected_hud':a.tiles[cell(2,1)]=4;a.tiles[cell(0,2)]=3;translate_map(a,b)
                if change=='source_origin':a.tiles[cell(0,0)]=0
                if change=='source_next':a.tiles[cell(0,-1)]=4
                if change=='arrival':b.tiles[cell(0,0)]=0
                with self.subTest(change=change):self.assertEqual((0,0,0),self.proof(lib,images))

    def test_finite_rank_and_independent_sparse_axis_planes_are_required(self):
        for lib in self.libraries.values():
            for mode in (1,2,3,4,5,7,8):
                with self.subTest(raw_mode=mode):self.assertEqual((0,0,0),self.proof(lib,pair(),raw_mode=mode))
            self.assertEqual((1,0,-1),self.proof(lib,pair(),raw_mode=6))
            for mode in range(1,6):
                with self.subTest(plane_mode=mode):self.assertEqual((0,0,0),self.proof(lib,pair(),plane_mode=mode))

    def test_other_displacements_and_scene_scope_do_not_credit_a_unit(self):
        for lib in self.libraries.values():
            for pixels in (0,8,18,-9):
                with self.subTest(pixels=pixels):self.assertEqual((0,0,0),self.proof(lib,pair(pixels=pixels)))
            for change in ('abi','size','floor','goods','gold_state','item','door','protection'):
                images=pair();a,b=images
                if change=='abi':a.abi_version=0
                if change=='size':b.struct_size=0
                if change=='floor':b.state=0
                if change=='goods':b.goods=1
                if change=='gold_state':a.gold_state=1
                if change=='item':a.tiles[cell(4,2)]=6
                if change=='door':b.tiles[cell(4,2)]=5
                if change=='protection':b.protected_cells[cell(4,2)]=1
                with self.subTest(change=change):self.assertEqual((0,0,0),self.proof(lib,images))
            for direction in (0,5):self.assertEqual((0,0,0),self.proof(lib,pair(),direction=direction))

    def test_known_results_and_input_scenes_remain_unchanged(self):
        images=pair();old=[bytes(v) for v in images]
        for lib in self.libraries.values():
            for initial in range(1,7):self.assertEqual((initial,7,-3),self.proof(lib,images,initial=initial))
            self.assertEqual((1,0,-1),self.proof(lib,images))
        self.assertEqual(old,[bytes(v) for v in images])


if __name__ == '__main__':
    unittest.main()
