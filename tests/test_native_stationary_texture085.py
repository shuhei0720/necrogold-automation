"""TEST085: independent zero-only proof for an observed clear-floor passage.

Procedural fields describe a fixed background under photometric noise, never
phone pixels, unseen device frames, an ACK, movement or input authority.
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
from tests.test_native_motion067 import Motion, procedural_pair
from tests.test_native_blocked067 import Entrance

CORE = Path(__file__).resolve().parents[1] / 'patches/loopctrl/ngg2'
W, H = 224, 104
DIRS = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}


def cell(x, y):
    return (y + 5) * 23 + x + 11


def stationary_pair(points=17, noise=17, after_gain=True):
    rng = random.Random(85085)
    world = bytearray(rng.randrange(14, 35) for _ in range(W * H))
    # A fixed sparse surface is observed twice. New independent high-frequency
    # noise defeats the legacy normalized strength; integer blur retains the
    # same spatial surface. The expected zero comes from this construction.
    for lower, upper in ((23, 34), (68, 80)):
        for _ in range(points):
            x, y = rng.randrange(44, 174), rng.randrange(lower, upper)
            world[y * W + x] = rng.randrange(160, 200)
    pair = [Scene(abi_version=1, struct_size=C.sizeof(Scene), state=2,
                  gold_state=1) for _ in range(2)]
    for scene in pair:
        scene.tiles[:] = [1] * 230
        for x, y in ((-5, -2), (4, 1)):
            scene.tiles[cell(x, y)] = 3
        for x, y in ((-5, -3), (-4, -3), (-3, -3), (2, -3), (3, -3), (4, -3),
                     (-5, 3), (-4, 3), (-3, 3), (2, 3), (3, 3), (4, 3)):
            scene.tiles[cell(x, y)] = 4
    pair[0].signature[:] = world
    rng = random.Random(85086)
    pair[1].signature[:] = bytes(min(255, max(0,
        (value * 5 // 4 + 4 if after_gain else value) + rng.randrange(-noise, noise + 1)))
        for value in world)
    return pair


def shifted_signature(scene, sx, sy):
    pixels = bytearray(W * H)
    for y in range(H):
        for x in range(W):
            xx, yy = x + sx, y + sy
            if 0 <= xx < W and 0 <= yy < H:
                pixels[yy * W + xx] = scene.signature[y * W + x]
    scene.signature[:] = pixels


SHIM = r'''
#if defined(NECROGOLD_HOST_TEST)
static int test085_stationary_mask(int x,int y){int ox,oy;for(oy=-1;oy<=1;++oy)for(ox=-1;ox<=1;++ox)if(!mask(x+ox,y+oy,0))return 0;return 1;}
static double test085_stationary_blur(const View *a,const View *b,int sx,int sy) {
    uint32_t count=0,sa=0,sb=0,qa=0,qb=0,total=0;
    int x,y;double contrast,ma,mb,gain;unsigned char lut[256];
    /* Preserve intensity()'s score arithmetic and limits. Only its spatial
     * support is restricted to an independent, dependency-safe raw band. */
    for (y=20;y<85;++y) for (x=40;x<179;++x) {
        unsigned int av,bv;
        if (!test085_stationary_mask(x,y) || !test085_stationary_mask(x+sx,y+sy)) continue;
        av=a->blur[y*W+x];bv=b->blur[(y+sy)*W+x+sx];
        if (av<=6 || bv<=6) continue;
        ++count;sa+=av;sb+=bv;qa+=av*av;qb+=bv*bv;
    }
    if (count<300) return INFINITY;
    contrast=(sqrt(((double)qa-(double)sa*sa/count)/count)+sqrt(((double)qb-(double)sb*sb/count)/count))/2;
    ma=(double)sa/count;mb=(double)sb/count;
    if (contrast<2.5 || ma<6 || mb<6) return INFINITY;
    gain=ma/mb;if (gain<.65) gain=.65;else if (gain>1.55) gain=1.55;
    for (x=0;x<256;++x) { volatile double product=(double)x*gain;lut[x]=even_round(product); }
    for (y=20;y<85;++y) for (x=40;x<179;++x) {
        int av,bv;
        if (!test085_stationary_mask(x,y) || !test085_stationary_mask(x+sx,y+sy)) continue;
        av=a->blur[y*W+x];bv=b->blur[(y+sy)*W+x+sx];
        if (av>6 && bv>6) total+=(uint32_t)abs(av-(int)lut[bv]);
    }
    return (double)total/count/contrast;
}
static void test085_stationary_candidates(const NG2Scene*a,const NG2Scene*b,View v[2],Candidate c[73]){
    int n=1,amount,d;view(a->signature,v);view(b->signature,v+1);
    c[0].sx=c[0].sy=0;c[0].score=intensity(v,v+1,0,0);
    for(amount=1;amount<=18;++amount)for(d=1;d<=4;++d){
        c[n].sx=amount*ddx[d];c[n].sy=amount*ddy[d];
        c[n].score=intensity(v,v+1,c[n].sx,c[n].sy);++n;
    }
    qsort(c,73,sizeof(*c),ranked);
}
void test085_stationary_stats(const NG2Scene*a,const NG2Scene*b,double scores[4],int flags[19]){
    View v[2];Candidate c[73];ClosedGateAxisCache*axis;int i,k,su,ba,first=-1,second=-1;
    memset(flags,0,19*sizeof(*flags));test085_stationary_candidates(a,b,v,c);
    scores[0]=c[0].score;scores[1]=c[1].score-c[0].score;
    flags[0]=c[0].sx;flags[1]=c[0].sy;flags[2]=1;
    for(i=0;i<73;++i)if(!isfinite(c[i].score))flags[2]=0;
    scores[2]=test085_stationary_blur(v,v+1,0,0);scores[3]=INFINITY;
    flags[3]=flags[4]=isfinite(scores[2]);
    for(i=1;i<73;++i){double z=test085_stationary_blur(v,v+1,c[i].sx,c[i].sy);
        if(!isfinite(z))flags[3]=0;
        if(!(z>scores[2]))flags[4]=0;
        if(z<scores[3])scores[3]=z;
    }
    world_blur_texture(a,b,v,0,0,flags+5,flags+6,flags+7);
    axis=(ClosedGateAxisCache*)calloc(1,sizeof(*axis));
    if(axis){
        closed_gate_axis_features(a,axis->before,axis->indices,&axis->count);
        closed_gate_axis_features(b,axis->after,NULL,NULL);
        closed_gate_axis_texture(axis,0,0,flags+9,flags+10,flags+11);flags[13]=1;
        for(i=1;i<73;++i){closed_gate_axis_texture(axis,c[i].sx,c[i].sy,&su,&ba,NULL);
            if(!texture_lead(flags[9],flags[10],su,ba))flags[13]=0;
        }
        free(axis);
    }
    flags[14]=unique_terrain_translation(a,b,0,0);
    for(i=0;i<CELLS;++i)if(a->tiles[i]==NG2_TILE_STONE){++flags[15];if(first<0)first=i;else if(second<0)second=i;}
    for(k=0;k<CELLS;++k)if(a->tiles[k]==NG2_TILE_DIRT&&b->tiles[k]==NG2_TILE_DIRT){
        ++flags[16];if(first>=0&&second>=0&&(px(second)-px(first))*(py(k)-py(first))!=(py(second)-py(first))*(px(k)-px(first)))++flags[17];
    }
    flags[18]=1;
    for(i=20;i<85;++i)for(k=40;k<179;++k)if(test085_stationary_mask(k,i)){
        int x,y;for(y=-1;y<=1;++y)for(x=-1;x<=1;++x)if(!mask(k+x,i+y,0))flags[18]=0;
    }
}
void test085_original_stages(const NG2Scene*a,const NG2Scene*b,int d,int out[42]){
    View v[2];Candidate c[73];NG2Motion m={0};int i=0;test085_stationary_candidates(a,b,v,c);
    #define TEST085_SAVE() do{out[i++]=m.kind;out[i++]=m.dx;out[i++]=m.dy;}while(0)
    evaluate_motion(a,b,d,v,c,&m);TEST085_SAVE();
    gate_detail_motion(a,b,d,v,c,&m);TEST085_SAVE();
    opening_detail_motion(a,b,d,v,c,&m);TEST085_SAVE();
    passage_detail_motion(a,b,d,v,c,&m);TEST085_SAVE();
    opening_gradient_motion(a,b,d,c,&m);TEST085_SAVE();
    static_floor_gradient_motion(a,b,d,c,&m);TEST085_SAVE();
    corner_blur_motion(a,b,d,v,c,&m);TEST085_SAVE();
    closed_gate_axis_motion(a,b,d,c,&m);TEST085_SAVE();
    revealed_gate_axis_motion(a,b,d,c,&m);TEST085_SAVE();
    sparse_gate_motion(a,b,d,v,c,&m);TEST085_SAVE();
    side_gate_motion(a,b,d,v,c,&m);TEST085_SAVE();
    terrain_blur_motion(a,b,d,v,c,&m);TEST085_SAVE();
    corner_gradient_blur_motion(a,b,d,v,c,&m);TEST085_SAVE();
    first_gold_terrain_blur_motion(a,b,d,v,c,&m);TEST085_SAVE();
    #undef TEST085_SAVE
}
void test085_stationary_numeric(int support,int bad,int upper,int lower,int count,int opposite,int out[3]){
    out[0]=texture_strength(support,bad,95)&&upper>=100&&lower>=100;
    out[1]=texture_strength(support,bad,75)&&upper>=100&&lower>=100;
    out[2]=texture_lead(support,bad,count,opposite);
}
#endif
'''


class NativeStationaryTexture085Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='test085-stationary-')
        cls.snapshot = Path(cls.temp.name) / 'source'
        cls.snapshot.mkdir()
        cls.source_sha256 = {}
        for name in ('NG2Beat.c', 'NG2CaptureBridge.h', 'NG2Controller.c', 'NG2Controller.h',
                     'NG2Core.h', 'NG2Navigation.c', 'NG2Perception.c', 'NG2Templates.h'):
            path = (Path(os.environ['NECRO_TEST085_STATIONARY_BASELINE_NAVIGATION'])
                    if name == 'NG2Navigation.c' and 'NECRO_TEST085_STATIONARY_BASELINE_NAVIGATION' in os.environ
                    else CORE / name)
            raw = path.read_bytes()
            (cls.snapshot / name).write_bytes(raw)
            cls.source_sha256[name] = hashlib.sha256(raw).hexdigest()
        wrapper = Path(cls.temp.name) / 'stationary.c'
        wrapper.write_text('#include "source/NG2Navigation.c"\n' + SHIM)
        cls.libraries = {}
        cls.compile_results = []
        for label, flags in (('o0', ['-O0']),
                             ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            path = Path(cls.temp.name) / (label + '.so')
            command = ['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror', '-pedantic',
                       '-DNECROGOLD_HOST_TEST=1', '-fPIC', '-shared', str(wrapper), '-lm', '-o', str(path)]
            result = subprocess.run(command, capture_output=True, text=True)
            cls.compile_results.append({'profile': label, 'command': command,
                'exit_code': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr})
            if result.returncode:
                raise RuntimeError(result.stderr)
            lib = C.CDLL(str(path))
            ptr = C.POINTER(Scene)
            lib.ng2_motion.argtypes = [ptr, ptr, C.c_int32, C.POINTER(Motion)]
            lib.ng2_entered_gate.argtypes = [ptr, ptr, C.c_int32, C.c_int32, C.c_int32,
                                           C.c_int32, C.POINTER(Entrance)]
            lib.test085_stationary_stats.argtypes = [ptr, ptr, C.POINTER(C.c_double), C.POINTER(C.c_int)]
            lib.test085_original_stages.argtypes = [ptr, ptr, C.c_int, C.POINTER(C.c_int)]
            lib.test085_stationary_numeric.argtypes = [C.c_int] * 6 + [C.POINTER(C.c_int)]
            cls.libraries[label] = lib
        if 'NECRO_TEST085_STATIONARY_EVIDENCE' in os.environ:
            evidence = Path(os.environ['NECRO_TEST085_STATIONARY_EVIDENCE'])
            evidence.mkdir(parents=True, exist_ok=True)
            (evidence / 'source-identity.json').write_text(json.dumps(cls.source_sha256, indent=2) + '\n')
            (evidence / 'compile.json').write_text(json.dumps(cls.compile_results, indent=2) + '\n')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def motion(self, lib, pair, direction=3):
        out = Motion(99, 99, 99)
        self.assertEqual(1, lib.ng2_motion(C.byref(pair[0]), C.byref(pair[1]), direction, C.byref(out)))
        return out.kind, out.dx, out.dy

    def stats(self, lib, pair):
        values, flags = (C.c_double * 4)(), (C.c_int * 19)()
        lib.test085_stationary_stats(C.byref(pair[0]), C.byref(pair[1]), values, flags)
        return list(values), list(flags)

    def assert_independent_zero_preconditions(self, lib, pair, direction=3):
        previous = (C.c_int * 42)()
        lib.test085_original_stages(C.byref(pair[0]), C.byref(pair[1]), direction, previous)
        self.assertEqual([0] * 42, list(previous), 'all fourteen legacy stages are unresolved')
        values, flags = self.stats(lib, pair)
        self.assertEqual([0, 0, 1, 1, 1], flags[:5])
        self.assertTrue(all(math.isfinite(v) for v in values))
        self.assertGreater(values[0], .45)
        self.assertGreaterEqual(values[1], .08)
        self.assertLessEqual(values[2], .45)
        self.assertGreater(values[3], values[2], 'blur is strictly best at zero; no .08 gap is claimed')
        for at, required in ((5, 95), (9, 75)):
            support, bad, upper, lower = flags[at:at + 4]
            self.assertGreaterEqual(support, 300)
            self.assertLessEqual((20 if required == 95 else 4) * bad, support)
            self.assertGreaterEqual(min(upper, lower), 100)
        self.assertEqual(1, flags[13], 'all original axis competitors obey the existing texture_lead')
        self.assertEqual(1, flags[14], 'old observed terrain has one zero translation')
        self.assertGreaterEqual(flags[15], 2)
        self.assertGreaterEqual(flags[16], 9)
        self.assertGreater(flags[17], 0)
        self.assertEqual(1, flags[18], 'every blur dependency remains inside the old mask')

    def test_public_clear_floor_zero_requires_independent_stationary_evidence(self):
        for label, lib in self.libraries.items():
            for direction in DIRS:
                pair = stationary_pair()
                with self.subTest(profile=label, direction=direction):
                    self.assert_independent_zero_preconditions(lib, pair, direction)
                    frozen = tuple(bytes(s) for s in pair)
                    self.assertEqual((2, 0, 0), self.motion(lib, pair, direction))
                    self.assertEqual(frozen, tuple(bytes(s) for s in pair))
                    entrance = Entrance()
                    self.assertEqual(0, lib.ng2_entered_gate(C.byref(pair[0]), C.byref(pair[1]),
                        direction, 0, 0, 2, C.byref(entrance)))
                    self.assertEqual(0, entrance.valid, 'stationary evidence never grants entry')

    def test_observed_terrain_goods_gold_door_and_protection_guards(self):
        cases = []
        for side in (0, 1):
            for field, values in (('state', (0, 1, 3)), ('gold_state', (0, 2, 3)), ('goods', (1, 2))):
                for value in values:
                    pair = stationary_pair(); setattr(pair[side], field, value)
                    cases.append((f'{field}:{side}:{value}', pair))
            for kind in (2, 5, 6):
                pair = stationary_pair(); pair[side].tiles[cell(8, 4)] = kind
                cases.append((f'forbidden-material:{side}:{kind}', pair))
            pair = stationary_pair(); pair[side].protected_cells[cell(8, 4)] = 1
            cases.append((f'protection:{side}', pair))
            for point in ((0, 0), (0, -1)):
                pair = stationary_pair(); pair[side].tiles[cell(*point)] = 0
                cases.append((f'unknown-step:{side}:{point}', pair))
        for label in ('old-stone-disappears', 'one-old-stone', 'eight-dirt', 'local-change'):
            pair = stationary_pair()
            if label == 'old-stone-disappears': pair[1].tiles[cell(-5, -2)] = 0
            elif label == 'one-old-stone':
                for scene in pair: scene.tiles[cell(-5, -2)] = 1
            elif label == 'eight-dirt':
                for scene in pair:
                    for point in ((-5, -3), (-4, -3), (-3, -3), (2, -3)):
                        scene.tiles[cell(*point)] = 1
            else: pair[1].tiles[cell(1, 0)] = 4
            cases.append((label, pair))
        for profile, lib in self.libraries.items():
            for label, pair in cases:
                with self.subTest(profile=profile, case=label):
                    if pair[0].state != 2 or pair[1].state != 2:
                        out = Motion(99, 99, 99)
                        self.assertEqual(0, lib.ng2_motion(C.byref(pair[0]), C.byref(pair[1]), 3, C.byref(out)))
                        self.assertEqual((0, 0, 0), (out.kind, out.dx, out.dy))
                    else:
                        self.assertNotEqual((2, 0, 0), self.motion(lib, pair))
            for direction in (0, 5):
                out = Motion(99, 99, 99); pair = stationary_pair()
                self.assertEqual(0, lib.ng2_motion(C.byref(pair[0]), C.byref(pair[1]), direction, C.byref(out)))
            pair = stationary_pair(); pair[0].abi_version = 9
            self.assertEqual(0, lib.ng2_motion(C.byref(pair[0]), C.byref(pair[1]), 3, C.byref(Motion())))
            self.assertEqual(0, lib.ng2_motion(None, C.byref(pair[1]), 3, C.byref(Motion())))

    def test_phase_alias_noise_and_blur_dependency_counterexamples_stay_unknown(self):
        cases = [('blur-weak', stationary_pair(noise=21))]
        pair = stationary_pair(); rng = random.Random(85087)
        pair[1].signature[:] = bytes(rng.randrange(20, 100) for _ in range(W * H))
        cases.append(('unrelated-flat-rng', pair))
        for shift in (1, 8, 9, -9):
            pair = stationary_pair(); shifted_signature(pair[1], shift, 0)
            cases.append((f'phase-shift:{shift}', pair))
        for name in ('flat', 'periodic-alias', 'black', 'upper-band-only', 'lower-band-only'):
            pair = stationary_pair()
            for scene in pair:
                if name == 'flat': scene.signature[:] = bytes([48]) * (W * H)
                elif name == 'black': scene.signature[:] = bytes(W * H)
                elif name == 'periodic-alias':
                    scene.signature[:] = bytes(30 + 80 * (x % 8 < 4) for y in range(H) for x in range(W))
                else:
                    raw = bytearray(scene.signature)
                    for y in range(H):
                        if (name == 'upper-band-only' and y >= 50) or (name == 'lower-band-only' and y <= 53):
                            raw[y * W:(y + 1) * W] = bytes([48]) * W
                    scene.signature[:] = raw
            cases.append((name, pair))
        for profile, lib in self.libraries.items():
            for label, pair in cases:
                with self.subTest(profile=profile, case=label):
                    # Existing paths may classify genuine independent zero or a
                    # displacement; none of these cases may be added as zero.
                    stages = (C.c_int * 42)()
                    lib.test085_original_stages(C.byref(pair[0]), C.byref(pair[1]), 3, stages)
                    old = tuple(stages[-3:])
                    actual = self.motion(lib, pair)
                    self.assertTrue(actual != (2, 0, 0) or old == (2, 0, 0))
            values, flags = self.stats(lib, stationary_pair(noise=21))
            self.assertGreater(values[2], .45, 'real procedural blur-weak field misses strength')
            self.assertEqual(1, flags[2])
            pair = stationary_pair()
            reference, _ = self.stats(lib, pair)
            raw = bytearray(pair[1].signature)
            raw[36 * W + 90] = 255  # excluded raw pixel adjacent to the old mask edge
            pair[1].signature[:] = raw
            changed, closure = self.stats(lib, pair)
            self.assertEqual(reference[2:], changed[2:],
                             'the entire blur kernel must remain outside excluded pixels')
            self.assertEqual(1, closure[18])

    def test_original_numeric_support_agreement_bands_and_competition_boundaries(self):
        for profile, lib in self.libraries.items():
            for support, bad, upper, lower, count, opposite, expected in (
                (300, 15, 100, 200, 300, 60, (1, 1, 1)),
                (299, 14, 100, 199, 300, 60, (0, 0, 1)),
                (300, 16, 100, 200, 300, 61, (0, 1, 1)),
                (300, 15, 99, 201, 300, 60, (0, 0, 1)),
                (300, 15, 201, 99, 300, 60, (0, 0, 1)),
                (300, 75, 100, 200, 300, 120, (0, 1, 1)),
                (300, 76, 100, 200, 300, 121, (0, 0, 1)),
                (300, 15, 100, 200, 300, 59, (1, 1, 0)),
                (300, 15, 100, 200, 299, 0, (1, 1, 1)),
            ):
                with self.subTest(profile=profile, support=support, bad=bad,
                                  upper=upper, lower=lower, count=count, opposite=opposite):
                    out = (C.c_int * 3)()
                    lib.test085_stationary_numeric(support, bad, upper, lower, count, opposite, out)
                    self.assertEqual(expected, tuple(out))

    def test_old_unit_tween_reverse_and_opening_outputs_are_never_overwritten(self):
        for profile, lib in self.libraries.items():
            for direction in DIRS:
                for pixels in (8, 9):
                    pair = procedural_pair(direction, pixels=pixels)
                    with self.subTest(profile=profile, direction=direction, pixels=pixels):
                        stages = (C.c_int * 42)()
                        lib.test085_original_stages(C.byref(pair[0]), C.byref(pair[1]), direction, stages)
                        expected = tuple(stages[-3:])
                        self.assertNotEqual((2, 0, 0), expected)
                        self.assertEqual(expected, self.motion(lib, pair, direction))
                pair = procedural_pair(direction, pixels=9)
                reverse = {1: 2, 2: 1, 3: 4, 4: 3}[direction]
                stages = (C.c_int * 42)()
                lib.test085_original_stages(C.byref(pair[0]), C.byref(pair[1]), reverse, stages)
                self.assertEqual(tuple(stages[-3:]), self.motion(lib, pair, reverse))
                for obstacle, expected_kind in ((5, 3), (4, 4)):
                    before, _ = procedural_pair(direction, amount=0, overlay=False)
                    before.tiles[:] = [1] * 230
                    dx, dy = DIRS[direction]
                    before.tiles[cell(dx, dy)] = obstacle
                    if obstacle == 5:
                        before.tiles[cell(dx + dy, dy - dx)] = 2
                        before.tiles[cell(dx - dy, dy + dx)] = 2
                    after = Scene.from_buffer_copy(bytes(before))
                    after.tiles[cell(dx, dy)] = 1
                    self.assertEqual((expected_kind, 0, 0), self.motion(lib, [before, after], direction))

    def test_public_controller_observe_proof_reaches_ready_before_original_w(self):
        from tests import test_native_controller as controller
        from tests import test_native_passage072 as passage
        from tests import test_native_passage_unsent076 as unsent

        # This local harness runs no inherited test methods. Every action below
        # uses public observe/tick/begin/complete/status/event/recovery APIs.
        class Harness(unsent.NativePassageUnsent076Tests):
            """Public helper bindings; inherited test methods are never loaded."""

        previous = unsent.CORE
        try:
            unsent.CORE = self.snapshot
            Harness.setUpClass()
        finally:
            unsent.CORE = previous
        try:
            Harness.lib.ng2_motion.argtypes = [C.POINTER(Scene), C.POINTER(Scene),
                                              C.c_int, C.POINTER(Motion)]
            for first_at_w in (False, True):
                with self.subTest(first_at_original_w=first_at_w):
                    h = Harness(methodName='runTest')
                    h.setUp()
                    try:
                        terrain = passage.passage_room(mouth=(0, -3))
                        # Entirely procedural observed terrain: the starting
                        # upper mouth remains the single route. Extra observed
                        # background is never an unobserved device tile.
                        tiles = {(x, y): 'floor' for y in range(-5, 5) for x in range(-11, 12)}
                        tiles.update(terrain.tiles)
                        tiles[(-3, -2)], tiles[(3, 1)] = 'stone', 'stone'
                        terrain.tiles = tiles
                        self.assertFalse(terrain.gold)
                        h.fit_clear(terrain)
                        for count in range(2):
                            move = h.next_move(terrain)
                            self.assertEqual((4, 3), (move.kind, move.direction))
                            terrain = h.moved(terrain, move)
                            self.assertEqual((count + 1, count + 1),
                                             (h.status().inputs, h.status().moves))
                        verified_ns = h.now
                        # Explicit later current-prefix synthetic observation,
                        # before reserving a ticket, supplies the new anchor.
                        # No private before/pose/lead or pending ticket is set.
                        terrain.signature = bytes(stationary_pair()[0].signature)
                        h.now += 1_000_000
                        h.observe(terrain)
                        old = h.next_move(terrain)
                        self.assertEqual((4, 3, 2, 2),
                            (old.kind, old.direction, h.status().inputs, h.status().moves))
                        anchor = h.scene(terrain)
                        stable = deepcopy(terrain)
                        rng = random.Random(85086)
                        stable.signature = bytes(min(255, max(0, value * 5 // 4 + 4
                            + rng.randrange(-17, 18))) for value in terrain.signature)
                        stable_frame = h.scene(stable)
                        self.assert_independent_zero_preconditions(
                            self.libraries['strict_o2'], [anchor, stable_frame], old.direction)
                        self.assertEqual((2, 0, 0), self.motion(Harness.lib,
                            [anchor, stable_frame], old.direction))
                        trigger = deepcopy(terrain)
                        rng = random.Random(85087)
                        trigger.signature = bytes(rng.randrange(20, 100) for _ in range(W * H))
                        trigger_frame = h.scene(trigger)
                        self.assertEqual((0, 0, 0), self.motion(Harness.lib,
                            [anchor, trigger_frame], old.direction))
                        self.assertEqual((2, 0, 0), self.motion(Harness.lib,
                            [trigger_frame, trigger_frame], old.direction))
                        period = h.status().beat_period_ns
                        parent = min(old.source_start_ns + 3_000_000_000,
                            old.phase_sample_ns + 3_000_000_000,
                            verified_ns + 12_000_000_000,
                            h.status().walk_started_ns + 45_000_000_000,
                            h.status().started_ns + 180_000_000_000)
                        h.now = old.deadline_ns - 30_000_000
                        trigger_commit = h.now
                        wait_end = min(parent, trigger_commit + 2 * period)
                        self.assertEqual(1, h.observe(trigger))
                        self.assertEqual((0, 0, 4, 0, 0), (h.status().reason,
                            h.status().terminal, h.status().phase,
                            h.status().input_state, h.status().current_command_id))
                        event = next(e for e in h.events() if e.command.id == old.id)
                        self.assertEqual((3, 17, 0, 0),
                            (event.outcome, event.reason, event.begin_ns, event.motion))
                        old_event = bytes(event)
                        self.assertEqual(bytes(old), bytes(event.command))
                        self.assertEqual((2, 2), (h.status().inputs, h.status().moves))
                        self.assertEqual(0, h.motion_wait().active)
                        if first_at_w:
                            h.now = wait_end
                            h.observe(stable)
                            self.assertEqual((8, 0, 0), (h.status().reason, h.status().terminal, h.status().paused),
                                'expiry requests holding cleanup; it does not fabricate terminal PAUSE')
                            ready, cleanup = h.tick()
                            self.assertEqual((1, 2), (ready, cleanup.kind))
                            h.ack(cleanup)
                            self.assertEqual((8, 0, 0),
                                (h.status().reason, h.status().terminal, h.status().paused))
                            h.now += 1_000_000
                            pause = controller.NativeControllerTests.scene(h, state=1)
                            self.assertEqual(1, h.observe(pause))
                            self.assertEqual((8, 1, 1),
                                (h.status().reason, h.status().terminal, h.status().paused))
                        else:
                            h.now = trigger_commit + 100_000_000
                            self.assertLess(h.now, wait_end)
                            h.observe(stable)
                            self.assertEqual(0, h.status().reason)
                            # READY has no private getter here. Crossing W with
                            # a public observation without BEAT proves it left
                            # OBSERVE; the immutable parent still applies.
                            h.now = wait_end
                            h.observe(stable)
                            self.assertEqual((0, 0), (h.status().reason, h.status().terminal))
                            new = h.next_recovery(stable)
                            self.assertGreater(new.id, old.id)
                            self.assertGreater(new.target_ns, old.target_ns)
                            self.assertGreaterEqual(new.not_before_ns - h.now, 50_000_000)
                            self.assertLessEqual(h.recovery().schedule_deadline_ns, parent)
                            self.assertLessEqual(h.motion_wait().deadline_ns, parent)
                            self.assertEqual((2, 2), (h.status().inputs, h.status().moves))
                        self.assertEqual(old_event, bytes(next(
                            e for e in h.events() if e.command.id == old.id)))
                        self.assertEqual(0, Harness.lib.ng2_controller_begin(
                            h.engine, old.id, old.not_before_ns, 1, 0, 1))
                        self.assertEqual(0, Harness.lib.ng2_controller_complete(
                            h.engine, old.id, h.now, 1))
                        self.assertEqual((2, 2), (h.status().inputs, h.status().moves))
                    finally:
                        h.doCleanups()
        finally:
            Harness.tearDownClass()
