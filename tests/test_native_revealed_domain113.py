"""TEST113: a past unit reveals a side gate with raw domain-2 contrast.

The translated grayscale field and terrain are procedural. Image-plane
metrics must independently qualify the expected physical unit before the
public Motion assertion. Received phone frames remain calibration outside Git.
"""
import ctypes as C
import math
from pathlib import Path
import random
import subprocess
import tempfile
import unittest

from tests.test_native_controller import Scene
from tests.test_native_motion067 import Motion
from tests.test_native_revealed_motion108 import pair as terrain_pair, DIRS, cell

CORE = Path(__file__).resolve().parents[1] / 'patches/loopctrl/ngg2'
W, H = 224, 104


def pair(direction=3, contrast=3, right=143, top=36, extra_dirt=True):
    """One physical unit, with an affine contrast change after translation.

    TEST108 supplies old-known terrain, with three translated dirt cells at
    the left edge of the room. TEST096's fixed block-phase texture is reused
    at lower amplitude. A flat upper/right area leaves the ordinary plane
    with only one spatial support region; the wider plane has two bands.
    """
    before, after = terrain_pair(direction)
    dx, dy = DIRS[direction]
    for x, y in (((-3, 0), (-3, 1), (-3, 2)) if extra_dirt else ()):
        if before.tiles[cell(x, y)] == 0:
            before.tiles[cell(x, y)] = 4
            if after.tiles[cell(x - dx, y - dy)] == 0:
                after.tiles[cell(x - dx, y - dy)] = 4
    rng = random.Random(113096)
    phases = {(x, y): (rng.randrange(4), rng.randrange(4))
              for y in range((H + 7) // 8) for x in range((W + 7) // 8)}
    world = bytearray(W * H)
    for y in range(H):
        for x in range(W):
            px, py = phases[x // 8, y // 8]
            sign = 1 if ((x + px) // 2 + (y + py) // 2) % 2 else -1
            value = 128 + 16 * sign + rng.randrange(-2, 3)
            world[y * W + x] = value if y >= top and x < right else 128
    moved = bytearray([128] * (W * H))
    for y in range(H):
        for x in range(W):
            qx, qy = x - 9 * dx, y - 9 * dy
            if 0 <= qx < W and 0 <= qy < H:
                moved[qy * W + qx] = 128 + contrast * (world[y * W + x] - 128)
    before.signature[:] = world
    after.signature[:] = moved
    return before, after


SHIM = r'''
int test113_domain_proof(const NG2Scene *a,const NG2Scene *b,int direction,NG2Motion *out) {
    View *v=calloc(2,sizeof(*v));Candidate raw[73];int n=1,amount,d;
    if(!v)return 0;
    view(a->signature,v);view(b->signature,v+1);
    raw[0].sx=raw[0].sy=0;raw[0].score=intensity(v,v+1,0,0);
    for(amount=1;amount<=18;++amount)for(d=1;d<=4;++d){
        raw[n].sx=amount*ddx[d];raw[n].sy=amount*ddy[d];
        raw[n].score=intensity(v,v+1,raw[n].sx,raw[n].sy);++n;
    }
    qsort(raw,73,sizeof(*raw),ranked);
    revealed_domain2_dependency_motion(a,b,direction,v,raw,out);
    free(v);return 1;
}
int test113_domain_stats(const NG2Scene *a,const NG2Scene *b,int direction,
                         double scores[4],int metrics[23]) {
    View *v=calloc(2,sizeof(*v));Candidate raw[73];
    ClosedGateAxisCache *cache;unsigned char included[N];
    int i,n=1,amount,d,support,bad,regions[2];
    if(!v)return 0;
    view(a->signature,v);view(b->signature,v+1);
    raw[0].sx=raw[0].sy=0;raw[0].score=intensity(v,v+1,0,0);
    for(amount=1;amount<=18;++amount)for(d=1;d<=4;++d){
        raw[n].sx=amount*ddx[d];raw[n].sy=amount*ddy[d];
        raw[n].score=intensity(v,v+1,raw[n].sx,raw[n].sy);++n;
    }
    qsort(raw,73,sizeof(*raw),ranked);
    scores[0]=raw[0].score;scores[1]=raw[1].score-raw[0].score;
    metrics[0]=revealed_singleton_raw_domain(raw,direction);
    metrics[1]=raw[0].sx;metrics[2]=raw[0].sy;
    metrics[3]=unique_revealed_singleton_translation(a,b,direction,raw[0].sx,raw[0].sy);
    metrics[4]=unique_visible_terrain_translation(a,b,raw[0].sx,raw[0].sy);
    world_blur_texture(a,b,v,raw[0].sx,raw[0].sy,metrics+5,metrics+6,metrics+7);
    revealed_world_mask(included);
    revealed_dependency_texture(v,included,raw[0].sx,raw[0].sy,&support,&bad,regions);
    metrics[9]=support;metrics[10]=bad;metrics[11]=regions[0];metrics[12]=regions[1];
    metrics[13]=INT_MAX;metrics[14]=metrics[15]=0;scores[2]=INFINITY;
    for(i=1;i<73;++i){
        int count,opposite;
        revealed_dependency_texture(v,included,raw[i].sx,raw[i].sy,&count,&opposite,NULL);
        if(count<metrics[13])metrics[13]=count;
        if(count<300)++metrics[14];
        else{
            double lead=100.0*((double)opposite/count-(double)bad/support);
            if(lead<scores[2])scores[2]=lead;
            if(!texture_lead(support,bad,count,opposite))++metrics[15];
        }
    }
    cache=calloc(1,sizeof(*cache));if(!cache){free(v);return 0;}
    closed_gate_axis_features(a,cache->before,cache->indices,&cache->count);
    closed_gate_axis_features(b,cache->after,NULL,NULL);
    closed_gate_axis_texture(cache,raw[0].sx,raw[0].sy,&support,&bad,regions);
    metrics[16]=support;metrics[17]=bad;metrics[18]=regions[0];metrics[19]=regions[1];
    metrics[20]=metrics[21]=0;scores[3]=INFINITY;
    for(i=1;i<73;++i){
        int count,opposite;
        closed_gate_axis_texture(cache,raw[i].sx,raw[i].sy,&count,&opposite,NULL);
        if(count<300)++metrics[20];
        else{
            double lead=100.0*((double)opposite/count-(double)bad/support);
            if(lead<scores[3])scores[3]=lead;
            if(!texture_lead(support,bad,count,opposite))++metrics[21];
        }
    }
    metrics[22]=0;for(i=0;i<73;++i)metrics[22]+=isfinite(raw[i].score)!=0;
    free(cache);free(v);return 1;
}
'''


class RevealedDomain113Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        root = Path(cls.directory.name)
        source = root / 'fixture.c'
        source.write_text('#include "NG2Navigation.c"\n' + SHIM)
        binary = root / 'fixture.so'
        subprocess.run(['cc', '-shared', '-fPIC', '-std=c11', '-O2', '-Wall', '-Wextra',
                        '-Werror', '-I', str(CORE), str(source), '-lm', '-o', str(binary)],
                       check=True, capture_output=True, text=True)
        cls.native = C.CDLL(str(binary))
        cls.native.ng2_motion.argtypes = [C.POINTER(Scene), C.POINTER(Scene), C.c_int,
                                         C.POINTER(Motion)]
        cls.native.ng2_motion.restype = C.c_int
        cls.native.test113_domain_proof.argtypes = cls.native.ng2_motion.argtypes
        cls.native.test113_domain_proof.restype = C.c_int
        cls.native.test113_domain_stats.argtypes = [C.POINTER(Scene), C.POINTER(Scene),
                                                   C.c_int, C.POINTER(C.c_double),
                                                   C.POINTER(C.c_int)]
        cls.native.test113_domain_stats.restype = C.c_int

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def stats(self, before, after, direction):
        scores, metrics = (C.c_double * 4)(), (C.c_int * 23)()
        self.assertEqual(1, self.native.test113_domain_stats(
            C.byref(before), C.byref(after), direction, scores, metrics))
        return tuple(scores), tuple(metrics)

    def motion(self, before, after, direction):
        result = Motion()
        self.assertEqual(1, self.native.ng2_motion(C.byref(before), C.byref(after),
                                                 direction, C.byref(result)))
        return result.kind, result.dx, result.dy

    def proof(self, before, after, direction, result=None):
        result = result if result is not None else Motion()
        self.assertEqual(1, self.native.test113_domain_proof(
            C.byref(before), C.byref(after), direction, C.byref(result)))
        return result.kind, result.dx, result.dy

    def qualify(self, before, after, direction):
        scores, m = self.stats(before, after, direction)
        dx, dy = DIRS[direction]
        self.assertEqual((2, -9 * dx, -9 * dy, 1, 1), m[:5])
        self.assertGreater(scores[0], .45)
        self.assertGreaterEqual(scores[1], .08)
        self.assertEqual(73, m[22], 'all raw candidates require observed finite scores')
        self.assertLess(m[5], 300, 'this fixture must exercise the narrow-plane gap')
        self.assertGreaterEqual(m[9], 300)
        self.assertLessEqual(20 * m[10], m[9])
        self.assertTrue(min(m[11:13]) >= 100)
        self.assertGreaterEqual(m[13], 300, 'every wider alternative is positive support')
        self.assertEqual((0, 0), m[14:16])
        self.assertGreaterEqual(scores[2], 15)
        self.assertGreaterEqual(m[16], 300)
        self.assertLessEqual(20 * m[17], m[16])
        self.assertTrue(min(m[18:20]) >= 100)
        self.assertEqual(0, m[21])
        return scores, m

    def test_complete_domain2_dependency_and_known_axis_prove_one_past_unit(self):
        for direction, (dx, dy) in DIRS.items():
            with self.subTest(direction=direction):
                before, after = pair(direction)
                original = bytes(before), bytes(after)
                self.qualify(before, after, direction)
                self.assertEqual((1, dx, dy), self.motion(before, after, direction))
                self.assertEqual(original, (bytes(before), bytes(after)))

    def test_one_unavailable_wider_alternative_rejects_despite_two_strong_winners(self):
        before, after = pair(3, right=101, top=37)
        scores, m = self.stats(before, after, 3)
        self.assertEqual((2, 0, 9, 1, 1), m[:5])
        self.assertGreaterEqual(scores[1], .08)
        self.assertEqual(73, m[22])
        self.assertGreaterEqual(m[9], 300)
        self.assertLessEqual(20 * m[10], m[9])
        self.assertTrue(min(m[11:13]) >= 100)
        self.assertLess(m[13], 300)
        self.assertGreater(m[14], 0)
        self.assertGreaterEqual(m[16], 300)
        self.assertLessEqual(20 * m[17], m[16])
        self.assertTrue(min(m[18:20]) >= 100)
        self.assertEqual(0, m[21])
        self.assertEqual(72, m[20], 'all unavailable axis comparisons are neutral')
        self.assertTrue(math.isinf(scores[3]), 'no positive axis margin was observed')
        self.assertEqual((0, 0, 0), self.proof(before, after, 3))
        self.assertEqual((0, 0, 0), self.motion(before, after, 3))

    def test_each_signed_plane_requires_its_own_95_percent_agreement(self):
        for plane, box in (('wider', (43, 59, 36, 79)), ('axis', (80, 90, 54, 72))):
            with self.subTest(plane=plane):
                before, after = pair(3)
                signature = bytearray(after.signature)
                rng = random.Random(113099)
                left, right, top, bottom = box
                for y in range(top, bottom):
                    for x in range(left, right):
                        signature[(y + 9) * W + x] = rng.randrange(74, 183)
                after.signature[:] = signature
                scores, m = self.stats(before, after, 3)
                self.assertEqual((2, 0, 9, 1, 1), m[:5])
                self.assertEqual(73, m[22])
                self.assertGreaterEqual(m[13], 300)
                self.assertEqual((0, 0), m[14:16])
                self.assertGreaterEqual(scores[2], 15)
                self.assertTrue(min(m[11:13]) >= 100 and min(m[18:20]) >= 100)
                self.assertTrue(m[9] >= 300 and m[16] >= 300)
                if plane == 'wider':
                    self.assertGreater(20 * m[10], m[9])
                    self.assertLessEqual(20 * m[17], m[16])
                else:
                    self.assertLessEqual(20 * m[10], m[9])
                    self.assertGreater(20 * m[17], m[16])
                self.assertEqual((0, 0, 0), self.proof(before, after, 3))

    def test_positive_competing_known_axis_needs_its_own_15_point_lead(self):
        before, after = pair(3)
        world = bytearray(before.signature)
        rng = random.Random(113105)
        for y in range(36, 80):
            for x in range(80, 115):
                sign = 1 if (x // 2 + y // 2) % 2 else -1
                world[y * W + x] = 128 + 16 * sign + rng.randrange(-2, 3)
        moved = bytearray([128] * (W * H))
        for y in range(H - 9):
            for x in range(W):
                moved[(y + 9) * W + x] = 128 + 3 * (world[y * W + x] - 128)
        before.signature[:], after.signature[:] = world, moved
        scores, m = self.stats(before, after, 3)
        self.assertEqual((2, 0, 9, 1, 1), m[:5])
        self.assertEqual(73, m[22])
        self.assertGreaterEqual(m[13], 300)
        self.assertEqual((0, 0), m[14:16])
        self.assertGreaterEqual(scores[2], 15)
        self.assertTrue(m[9] >= 300 and m[16] >= 300)
        self.assertTrue(min(m[11:13]) >= 100 and min(m[18:20]) >= 100)
        self.assertLessEqual(20 * m[10], m[9])
        self.assertLessEqual(20 * m[17], m[16])
        self.assertGreater(m[21], 0)
        self.assertLess(scores[3], 15)
        self.assertEqual((0, 0, 0), self.proof(before, after, 3))
        self.assertEqual((0, 0, 0), self.motion(before, after, 3))

    def test_dependency_plane_cannot_replace_missing_known_axis_support(self):
        before, after = pair(3, extra_dirt=False)
        scores, m = self.stats(before, after, 3)
        self.assertEqual((2, 0, 9, 1, 1), m[:5])
        self.assertGreaterEqual(m[13], 300)
        self.assertEqual((0, 0), m[14:16])
        self.assertGreaterEqual(scores[2], 15)
        self.assertGreaterEqual(m[9], 300)
        self.assertLessEqual(20 * m[10], m[9])
        self.assertTrue(min(m[11:13]) >= 100)
        self.assertLess(m[16], 300)
        self.assertEqual((0, 0, 0), self.proof(before, after, 3))

    def test_known_axis_needs_both_bands_despite_strong_total_and_margins(self):
        before, after = pair(3)
        for i, kind in enumerate(before.tiles):
            x, y = i % 23 - 11, i // 23 - 5
            if kind == 4 and y >= 0:
                before.tiles[i] = 0
                if y < 4:
                    after.tiles[cell(x, y + 1)] = 0
        for y in (-2, -1):
            for x in range(-6, 0):
                if before.tiles[cell(x, y)] == 0:
                    before.tiles[cell(x, y)] = 4
                    if after.tiles[cell(x, y + 1)] == 0:
                        after.tiles[cell(x, y + 1)] = 4
        scores, m = self.stats(before, after, 3)
        self.assertEqual((2, 0, 9, 1, 1), m[:5])
        self.assertEqual(73, m[22])
        self.assertGreaterEqual(m[13], 300)
        self.assertEqual((0, 0), m[14:16])
        self.assertGreaterEqual(scores[2], 15)
        self.assertTrue(min(m[11:13]) >= 100)
        self.assertTrue(m[9] >= 300 and m[16] >= 300)
        self.assertLessEqual(20 * m[10], m[9])
        self.assertLessEqual(20 * m[17], m[16])
        self.assertGreaterEqual(m[18], 100)
        self.assertLess(m[19], 100)
        self.assertEqual(0, m[21])
        self.assertGreaterEqual(scores[3], 15)
        self.assertEqual((0, 0, 0), self.proof(before, after, 3))

    def test_scene_authority_and_complete_old_witnesses_are_required(self):
        for fault in ('source_state', 'observed_state', 'one_stone', 'lost_stone',
                      'few_dirt', 'lost_gold', 'no_new_gate', 'old_door', 'protected',
                      'item', 'source_goods', 'observed_goods', 'source_clear',
                      'observed_clear', 'source_origin', 'source_next', 'observed_origin'):
            with self.subTest(fault=fault):
                before, after = pair(3)
                if fault.endswith('state'):
                    (before if fault == 'source_state' else after).state = 1
                elif fault in ('one_stone', 'lost_stone'):
                    index = next(i for i, kind in enumerate(before.tiles) if kind == 3)
                    x, y = index % 23 - 11, index // 23 - 5
                    after.tiles[cell(x, y + 1)] = 0 if fault == 'lost_stone' else 4
                    if fault == 'one_stone':
                        before.tiles[index] = 4
                elif fault == 'few_dirt':
                    count = 0
                    for i, kind in enumerate(before.tiles):
                        if kind == 4:
                            count += 1
                            if count > 8:
                                before.tiles[i] = 0
                                x, y = i % 23 - 11, i // 23 - 5
                                if y < 4:
                                    after.tiles[cell(x, y + 1)] = 0
                elif fault == 'lost_gold':
                    index = next(i for i, kind in enumerate(before.tiles) if kind == 2)
                    x, y = index % 23 - 11, index // 23 - 5
                    after.tiles[cell(x, y + 1)] = 0
                elif fault == 'no_new_gate':
                    after.tiles[next(i for i, kind in enumerate(after.tiles) if kind == 5)] = 0
                elif fault == 'old_door':
                    before.tiles[cell(4, 1)] = 5
                elif fault == 'protected':
                    after.protected_cells[cell(4, 1)] = 1
                elif fault == 'item':
                    after.tiles[cell(4, 1)] = 6
                elif fault.endswith('goods'):
                    (before if fault == 'source_goods' else after).goods = 1
                elif fault.endswith('clear'):
                    (before if fault == 'source_clear' else after).gold_state = 1
                elif fault == 'source_origin':
                    before.tiles[cell(0, 0)] = 4
                elif fault == 'source_next':
                    before.tiles[cell(0, -1)] = 0
                else:
                    after.tiles[cell(0, 0)] = 0
                original = bytes(before), bytes(after)
                self.assertEqual((0, 0, 0), self.proof(before, after, 3))
                self.assertEqual(original, (bytes(before), bytes(after)))

    def test_raw_wrong_direction_nonunit_and_old_known_results_are_not_overridden(self):
        before, after = pair(3)
        for direction in (0, 1, 2, 4, 5):
            with self.subTest(direction=direction):
                self.assertEqual((0, 0, 0), self.proof(before, after, direction))
        for kind in (1, 2, 3, 4, 5, 6):
            with self.subTest(known_kind=kind):
                result = Motion(kind=kind, dx=7, dy=-6)
                original = bytes(result)
                self.proof(before, after, 3, result)
                self.assertEqual(original, bytes(result))
        self.assertEqual((0, 0, 0), self.proof(before, before, 3))
        for pixels in (0, 8, 18):
            with self.subTest(signature_shift=pixels):
                moved = bytearray([128] * (W * H))
                for y in range(H - pixels):
                    for x in range(W):
                        moved[(y + pixels) * W + x] = 128 + 3 * (before.signature[y * W + x] - 128)
                after.signature[:] = moved
                self.assertEqual((0, 0, 0), self.proof(before, after, 3))

    def test_raw_domain1_stays_with_its_existing_qualification(self):
        before, after = terrain_pair(3)
        scores, m = self.stats(before, after, 3)
        self.assertEqual(1, m[0])
        self.assertEqual((0, 0, 0), self.proof(before, after, 3))
        self.assertEqual((1, 0, -1), self.motion(before, after, 3))


if __name__ == '__main__':
    unittest.main()
