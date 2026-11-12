"""TEST086: one past unit that preserves an already visible single gold cell.

Deterministic pixel fields define their own displacement. They are not phone
captures, a replay of private Controller state, or shop-arrival acceptance.
"""
import ctypes as C
from copy import deepcopy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tests import test_native_controller as controller
from tests.test_native_controller import Scene
from tests.test_native_motion067 import Motion, procedural_pair
from tests.test_native_blocked067 import Entrance
from tests.test_native_passage_motion082 import pair as base_pair, cell, DIRS
from tests.test_native_first_gold083 import SHIM as FIRST_GOLD_SHIM

CORE = Path(__file__).resolve().parents[1] / 'patches/loopctrl/ngg2'


def pair(direction=3, pixels=9, gold=(-3, -3)):
    scenes = base_pair(direction, pixels=pixels)
    dx, dy = DIRS[direction]
    for x, y in ((-4, -2), (-3, -2), (-2, -2), (2, -2), (3, -2),
                 (-4, 2), (-3, 2), (-2, 2), (2, 2)):
        scenes[0].tiles[cell(x, y)] = 4
        scenes[1].tiles[cell(x - dx, y - dy)] = 4
    scenes[0].tiles[cell(*gold)] = 2
    scenes[1].tiles[cell(gold[0] - dx, gold[1] - dy)] = 2
    scenes[0].gold_state = scenes[1].gold_state = 2
    return scenes


# Reuse the established candidate, phase/blur measurement, raw-boundary and
# computed-plane primitives. Their helper call alone selects this new proof.
REUSED_SHIM = FIRST_GOLD_SHIM.replace('first_gold_terrain_blur_motion',
                                    'singleton_gold_terrain_blur_motion')
SHIM = r'''
void test086_previous(const NG2Scene*a,const NG2Scene*b,int d,int out[45]) {
    View v[2];Candidate c[73];NG2Motion m;
    test083_previous(a,b,d,out);test083_candidates(a,b,v,c);
    m.kind=out[36];m.dx=out[37];m.dy=out[38];
    first_gold_terrain_blur_motion(a,b,d,v,c,&m);
    out[39]=m.kind;out[40]=m.dx;out[41]=m.dy;
    stationary_terrain_motion(a,b,d,v,c,&m);
    out[42]=m.kind;out[43]=m.dx;out[44]=m.dy;
}
void test086_stats(const NG2Scene*a,const NG2Scene*b,int d,double scores[6],int flags[24]) {
    View v[2];Candidate c[73];ClosedGateAxisCache*ax;
    int i,su,ba,first=-1,second=-1,dx=ddx[d],dy=ddy[d];
    memset(flags,0,24*sizeof(*flags));test083_stats(a,b,scores,flags);
    test083_candidates(a,b,v,c);flags[8]=independent_phase(v,c);flags[9]=1;
    for(i=0;i<73;++i)if(!isfinite(c[i].score))flags[9]=0;
    for(i=0;i<CELLS;++i)if(a->tiles[i]==NG2_TILE_STONE){
        ++flags[10];flags[11]+=tile(b,px(i)-dx,py(i)-dy)==NG2_TILE_STONE;
        if(first<0)first=i;else if(second<0)second=i;
    }
    for(i=0;i<CELLS;++i)if(a->tiles[i]==NG2_TILE_DIRT&&tile(b,px(i)-dx,py(i)-dy)==NG2_TILE_DIRT){
        ++flags[12];if(first>=0&&second>=0&&(px(second)-px(first))*(py(i)-py(first))
            !=(py(second)-py(first))*(px(i)-px(first)))++flags[13];
    }
    ax=(ClosedGateAxisCache*)calloc(1,sizeof(*ax));
    if(ax){
        closed_gate_axis_features(a,ax->before,ax->indices,&ax->count);
        closed_gate_axis_features(b,ax->after,NULL,NULL);
        closed_gate_axis_texture(ax,c[0].sx,c[0].sy,flags+14,flags+15,flags+16);flags[18]=1;
        for(i=1;i<73;++i){closed_gate_axis_texture(ax,c[i].sx,c[i].sy,&su,&ba,NULL);
            if(!texture_lead(flags[14],flags[15],su,ba))flags[18]=0;}
        free(ax);
    }
    flags[19]=gold_count(a);flags[20]=gold_count(b);
    flags[21]=tile(a,0,0);flags[22]=tile(a,dx,dy);flags[23]=tile(b,0,0);
}
int test086_axis_components(const NG2Scene*a,const NG2Scene*b,int mode,int flags[6]) {
    NG2Scene aa=*a,bb=*b;View v[2];Candidate c[73];NG2Motion m={0};
    ClosedGateAxisCache*ax;int x,y,i,su,ba;
    test083_candidates(a,b,v,c);
    /* Explicitly isolate the raw signed-axis plane. Frozen raw phases and
     * world blur still come from the coherent original pair, not these copies. */
    if(mode==1)memset(bb.signature,0,N);
    if(mode==2)for(i=0;i<N;++i)bb.signature[i]=(unsigned char)(255-bb.signature[i]);
    if(mode==3)for(y=0;y<54;++y)for(x=0;x<W;++x)aa.signature[y*W+x]=bb.signature[y*W+x]=0;
    if(mode==4){
        memset(bb.signature,0,N);
        for(y=0;y<H;++y)for(x=0;x<W;++x){
            int phase=y%16;unsigned char value=(unsigned char)(20+24*(phase<8?phase:16-phase));
            aa.signature[y*W+x]=value;if(y+9<H)bb.signature[(y+9)*W+x]=value;
        }
    }
    ax=(ClosedGateAxisCache*)calloc(1,sizeof(*ax));memset(flags,0,6*sizeof(*flags));
    if(ax){
        closed_gate_axis_features(&aa,ax->before,ax->indices,&ax->count);
        closed_gate_axis_features(&bb,ax->after,NULL,NULL);
        closed_gate_axis_texture(ax,c[0].sx,c[0].sy,flags,flags+1,flags+2);flags[4]=1;
        for(i=1;i<73;++i){closed_gate_axis_texture(ax,c[i].sx,c[i].sy,&su,&ba,NULL);
            if(!texture_lead(flags[0],flags[1],su,ba))flags[4]=0;}
        free(ax);
    }
    flags[5]=independent_phase(v,c);
#if TEST083_PRESENT
    singleton_gold_terrain_blur_motion(&aa,&bb,NG2_UP,v,c,&m);
#endif
    return m.kind;
}
int test086_numeric(int support,int bad,int upper,int count,int opposite) {
    return texture_strength(support,bad,75)&&upper>=100&&support-upper>=100
        &&texture_lead(support,bad,count,opposite);
}
int test086_dependencies(const NG2Scene*a,const NG2Scene*b,int x,int y,int sx,int sy) {
    return world_kernel_known(a,b,x,y,sx,sy);
}
'''


class NativeSingleGold086Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='test086-single-gold-')
        directory = Path(cls.temp.name)
        for path in CORE.glob('NG2*'):
            if path.suffix in ('.c', '.h'):
                shutil.copyfile(path, directory / path.name)
        selected = Path(os.environ.get('NECRO_TEST086_BASELINE_NAVIGATION',
                                       CORE / 'NG2Navigation.c'))
        shutil.copyfile(selected, directory / 'NG2Navigation.c')
        cls.source_directory = directory
        hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(directory.glob('NG2*')) if p.suffix in ('.c', '.h')}
        if len(hashes) != 8:
            raise AssertionError('exactly eight C/H source identities are required')
        identity = os.environ.get('NECRO_TEST086_SOURCE_IDENTITY')
        if identity:
            Path(identity).write_text(json.dumps({'source_sha256': hashes,
                'selected_navigation': str(selected), 'python_sha256': {
                    p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (
                        Path(__file__), Path(controller.__file__),
                        CORE.parents[2] / 'tests/test_native_first_gold083.py')}},
                sort_keys=True, indent=2)+'\n')
        present = 'static void singleton_gold_terrain_blur_motion(' in selected.read_text()
        shim = directory / 'proof.c'
        shim.write_text(f'#define TEST083_PRESENT {int(present)}\n'
            '#define NECROGOLD_HOST_TEST 1\n'
            f'#include "{directory / "NG2Navigation.c"}"\n'
            '#if defined(NECROGOLD_HOST_TEST)\n' + REUSED_SHIM + SHIM + '\n#endif\n')
        cls.libraries = {}
        for profile, flags in (('o0', ['-O0']), ('strict_o2',
                ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            output = directory / (profile + '.so')
            subprocess.run(['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror',
                '-pedantic', '-fPIC', '-shared', str(shim), '-lm', '-o', str(output)],
                check=True, capture_output=True)
            lib = C.CDLL(str(output)); ptr = C.POINTER(Scene); ints = C.POINTER(C.c_int)
            lib.ng2_motion.argtypes = [ptr, ptr, C.c_int, C.POINTER(Motion)]
            lib.ng2_entered_gate.argtypes = [ptr, ptr, C.c_int, C.c_int, C.c_int,
                                              C.c_int, C.POINTER(Entrance)]
            lib.test086_previous.argtypes = [ptr, ptr, C.c_int, ints]
            lib.test086_stats.argtypes = [ptr, ptr, C.c_int, C.POINTER(C.c_double), ints]
            lib.test083_proof.argtypes = [ptr, ptr, C.c_int, C.c_double, C.c_double,
                                            C.c_int, C.c_int, C.c_int, C.POINTER(Motion)]
            lib.test083_components.argtypes = [ptr, ptr, C.c_int, ints]
            lib.test083_geometry.argtypes = [ptr, ptr, C.c_int, C.c_int]
            lib.test083_numeric.argtypes = [C.c_int] * 5
            lib.test086_axis_components.argtypes = [ptr, ptr, C.c_int, ints]
            lib.test086_numeric.argtypes = [C.c_int] * 5
            lib.test086_dependencies.argtypes = [ptr, ptr] + [C.c_int] * 4
            cls.libraries[profile] = lib

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def motion(self, lib, scenes, direction=3):
        out = Motion(99, 99, 99)
        self.assertEqual(1, lib.ng2_motion(C.byref(scenes[0]), C.byref(scenes[1]),
                                         direction, C.byref(out)))
        return out.kind, out.dx, out.dy

    def proof(self, lib, scenes, direction=3, score=.6, gap=.2, shift=None,
              other=0, initial=0):
        dx, dy = DIRS[direction]
        sx, sy = shift if shift is not None else (-9 * dx, -9 * dy)
        out = Motion(initial, 0, 0)
        lib.test083_proof(C.byref(scenes[0]), C.byref(scenes[1]), direction,
                         score, gap, sx, sy, other, C.byref(out))
        return out.kind, out.dx, out.dy

    def preconditions(self, lib, scenes, direction=3):
        scores, flags, previous = (C.c_double * 6)(), (C.c_int * 24)(), (C.c_int * 45)()
        lib.test086_previous(C.byref(scenes[0]), C.byref(scenes[1]), direction, previous)
        lib.test086_stats(C.byref(scenes[0]), C.byref(scenes[1]), direction, scores, flags)
        dx, dy = DIRS[direction]
        self.assertEqual([0] * 45, list(previous))
        self.assertGreater(scores[0], .45); self.assertGreaterEqual(scores[1], .08)
        self.assertEqual((-9 * dx, -9 * dy), tuple(flags[:2]))
        self.assertEqual((1, 1, 1), (flags[2], flags[8], flags[9]))
        self.assertGreaterEqual(flags[3], 300); self.assertLessEqual(20 * flags[4], flags[3])
        self.assertGreaterEqual(min(flags[5:7]), 100); self.assertEqual(1, flags[7])
        self.assertGreaterEqual(flags[10], 2); self.assertEqual(flags[10], flags[11])
        self.assertGreaterEqual(flags[12], 9); self.assertGreater(flags[13], 0)
        self.assertGreaterEqual(flags[14], 300); self.assertLessEqual(4 * flags[15], flags[14])
        self.assertGreaterEqual(min(flags[16:18]), 100); self.assertEqual(1, flags[18])
        self.assertEqual((1, 1, 1, 1, 1), tuple(flags[19:24]))
        return scores, flags

    def test_public_four_directions_retained_single_gold_unit_requires_independent_old15_unknown_proof(self):
        for profile, lib in self.libraries.items():
            for direction, (dx, dy) in DIRS.items():
                for gold in ((-3, -3), (3, 2)):
                    with self.subTest(profile=profile, direction=direction, gold=gold):
                        scenes = pair(direction, gold=gold)
                        self.preconditions(lib, scenes, direction)
                        self.assertEqual((1, dx, dy), self.motion(lib, scenes, direction))
                        entry = Entrance()
                        self.assertEqual(0, lib.ng2_entered_gate(C.byref(scenes[0]),
                            C.byref(scenes[1]), direction, 0, 0, 1, C.byref(entry)))
                        self.assertEqual((0, 0, 0, 0), tuple(getattr(entry, k)
                            for k in ('valid', 'x', 'y', 'direction')))

    def test_scope_gold_projection_endpoints_global_materials_and_known_results_remain_separate(self):
        for profile, lib in self.libraries.items():
            for which in (0, 1):
                for field, values in (('state', (0, 1, 3)), ('gold_state', (0, 1, 3)),
                                      ('goods', (1, 2))):
                    for value in values:
                        scenes = pair(); setattr(scenes[which], field, value)
                        with self.subTest(profile=profile, which=which, field=field, value=value):
                            self.assertEqual((0, 0, 0), self.proof(lib, scenes))
                for kind in (5, 6):
                    scenes = pair(); scenes[which].tiles[cell(8, 1)] = kind
                    self.assertEqual((0, 0, 0), self.proof(lib, scenes))
                scenes = pair(); scenes[which].protected_cells[cell(8, 1)] = 1
                self.assertEqual((0, 0, 0), self.proof(lib, scenes))
                for point in ((0, 0), (0, -1)):
                    scenes = pair(); scenes[which].tiles[cell(*point)] = 0
                    self.assertEqual((0, 0, 0), self.proof(lib, scenes))
                for mode in ('none', 'second', 'wrong_projection'):
                    scenes = pair(); gold = (-3, -3 + which)
                    if mode != 'second': scenes[which].tiles[cell(*gold)] = 1
                    if mode != 'none': scenes[which].tiles[cell(7, 1)] = 2
                    self.assertEqual((0, 0, 0), self.proof(lib, scenes))
            for known in range(1, 8):
                self.assertEqual((known, 0, 0), self.proof(lib, pair(), initial=known))
            out = Motion(99, 99, 99)
            for d in (0, 5):
                scenes = pair()
                self.assertEqual(0, lib.ng2_motion(C.byref(scenes[0]), C.byref(scenes[1]), d, C.byref(out)))
                self.assertEqual((0, 0, 0), (out.kind, out.dx, out.dy))

    def test_complete_old_stones_dirt_support_noncollinearity_and_unique_nine_are_required(self):
        for profile, lib in self.libraries.items():
            for point in ((-5, -2), (4, 1)):
                for kind in (0, 1, 4):
                    scenes = pair(); scenes[1].tiles[cell(point[0], point[1] + 1)] = kind
                    self.assertEqual(0, lib.test083_geometry(C.byref(scenes[0]), C.byref(scenes[1]), 0, 9))
                    self.assertEqual((0, 0, 0), self.proof(lib, scenes))
            scenes = pair(); scenes[0].tiles[cell(4, 1)] = 1
            self.assertEqual((0, 0, 0), self.proof(lib, scenes))
            scenes = pair()
            old_dirt = [i for i, kind in enumerate(scenes[0].tiles) if kind == 4]
            self.assertEqual(9, len(old_dirt))
            scenes[1].tiles[old_dirt[0] + 23] = 1
            self.assertEqual(1, lib.test083_geometry(C.byref(scenes[0]), C.byref(scenes[1]), 0, 9))
            self.assertEqual((0, 0, 0), self.proof(lib, scenes))
            # Two old stones and nine old dirt on one horizontal line cannot
            # supply a two-dimensional material anchor, despite many points.
            scenes = pair()
            for scene in scenes: scene.tiles[:] = [1] * 230
            for x, kind in ((-6, 3), (6, 3), *[(x, 4) for x in range(-4, 5)]):
                scenes[0].tiles[cell(x, 2)] = kind; scenes[1].tiles[cell(x, 3)] = kind
            scenes[0].tiles[cell(-3, -3)] = scenes[1].tiles[cell(-3, -2)] = 2
            self.assertEqual(0, lib.test083_geometry(C.byref(scenes[0]), C.byref(scenes[1]), 0, 9))
            self.assertEqual((0, 0, 0), self.proof(lib, scenes))
            scenes = pair(gold=(6, -3))
            # Preserve the original noncollinear shape at both zero and +1.
            for i, kind in enumerate(scenes[0].tiles):
                if kind in (3, 4): scenes[1].tiles[i] = kind
            self.assertEqual(0, lib.test083_geometry(C.byref(scenes[0]), C.byref(scenes[1]), 0, 9))
            self.assertEqual((0, 0, 0), self.proof(lib, scenes))

    def test_raw_all73_phase_unit_and_both_strong_planes_keep_their_original_boundaries(self):
        for profile, lib in self.libraries.items():
            scenes = pair()
            for score, gap, other, expected in ((.45, .2, 0, 0), (.450001, .2, 0, 1),
                    (.6, .079999, 0, 0), (.6, .2, 0, 1), (math.nan, .2, 0, 0),
                    (math.inf, .2, 0, 0), (-math.inf, .2, 0, 0),
                    (.6, math.inf, 0, 0), (.6, .2, 1, 0), (.6, .2, 2, 0), (.6, .2, 3, 0)):
                with self.subTest(profile=profile, raw=(score, gap, other)):
                    self.assertEqual(expected, self.proof(lib, scenes, score=score, gap=gap, other=other)[0])
            for direction, (dx, dy) in DIRS.items():
                for shift in ((0, 0), (-8 * dx, -8 * dy), (9 * dx, 9 * dy), (-18 * dx, -18 * dy)):
                    self.assertEqual((0, 0, 0), self.proof(lib, pair(direction), direction, shift=shift))
                for pixels, expected in ((0, (2, 0, 0)), (8, (7, 0, 0)), (9, (1, dx, dy)),
                                         (18, (6, 2 * dx, 2 * dy)), (-9, (6, -dx, -dy))):
                    self.assertEqual(expected, self.motion(lib,
                        procedural_pair(direction, pixels=pixels, overlay=False), direction))
            for mode in range(6):
                flags = (C.c_int * 9)()
                with self.subTest(profile=profile, component=mode):
                    # This isolated mode preserves the original independent
                    # phase rule: a finite unit can beat an unavailable band
                    # competitor. The coherent public raw73 must be all finite.
                    self.assertEqual(1 if mode in (0, 2) else 0,
                        lib.test083_components(C.byref(scenes[0]), C.byref(scenes[1]), mode, flags))
                self.assertEqual(1, flags[8])
                if mode == 1: self.assertEqual(0, flags[5])
                if mode == 2: self.assertEqual((1, 0, 1), tuple(flags[5:8]))
                if mode == 3: self.assertLess(flags[0], 300)
                if mode == 4: self.assertGreater(20 * flags[1], flags[0])
                if mode == 5:
                    self.assertGreaterEqual(flags[0], 300); self.assertLessEqual(20 * flags[1], flags[0])
                    self.assertGreaterEqual(min(flags[2:4]), 100); self.assertEqual(0, flags[4])
            for values, expected in (((300, 15, 100, 300, 60), 1), ((299, 0, 100, 300, 60), 0),
                    ((300, 16, 100, 300, 60), 0), ((300, 15, 99, 300, 60), 0),
                    ((300, 15, 201, 300, 60), 0), ((300, 15, 100, 300, 59), 0)):
                self.assertEqual(expected, lib.test083_numeric(*values))

    def test_axis_independence_all73_competition_and_blur_dependency_closure_are_required(self):
        for profile, lib in self.libraries.items():
            scenes = pair()
            for mode in range(5):
                flags = (C.c_int * 6)()
                self.assertEqual(1 if mode == 0 else 0,
                    lib.test086_axis_components(C.byref(scenes[0]), C.byref(scenes[1]), mode, flags))
                self.assertEqual(1, flags[5])
                if mode == 1: self.assertLess(flags[0], 300)
                if mode == 2: self.assertGreater(4 * flags[1], flags[0])
                if mode == 3: self.assertLess(flags[2], 100)
                if mode == 4:
                    self.assertGreaterEqual(flags[0], 300); self.assertLessEqual(4 * flags[1], flags[0])
                    self.assertGreaterEqual(min(flags[2:4]), 100); self.assertEqual(0, flags[4])
            for values, expected in (((300, 75, 100, 300, 120), 1), ((299, 0, 100, 300, 120), 0),
                    ((300, 76, 100, 300, 120), 0), ((300, 75, 99, 300, 120), 0),
                    ((300, 75, 201, 300, 120), 0), ((300, 75, 100, 300, 119), 0)):
                self.assertEqual(expected, lib.test086_numeric(*values))
            self.assertEqual(1, lib.test086_dependencies(C.byref(scenes[0]), C.byref(scenes[1]), 75, 28, 0, 9))
            # An outer radius-two derivative dependency must be known even
            # though the center and its radius-one neighborhood remain FLOOR.
            self.assertEqual(1, scenes[1].tiles[cell(-4, -2)])
            scenes[1].tiles[cell(-4, -1)] = 0
            self.assertEqual(1, scenes[1].tiles[cell(-4, -2)])
            self.assertEqual(0, lib.test086_dependencies(C.byref(scenes[0]), C.byref(scenes[1]), 75, 28, 0, 9))

    def test_public_controller_credits_only_one_qualified_post_ack_unit_and_goods_has_priority(self):
        directory = self.source_directory
        objects = []
        for name in ('NG2Controller', 'NG2Perception', 'NG2Beat'):
            obj = directory / (name + '.o')
            subprocess.run(['cc', '-std=c99', '-O2', '-fno-fast-math', '-ffp-contract=off',
                '-Wall', '-Wextra', '-Werror', '-pedantic', '-fPIC', '-c',
                str(directory / (name + '.c')), '-o', str(obj)], check=True, capture_output=True)
            objects.append(str(obj))
        output = directory / 'controller.so'
        subprocess.run(['cc', '-shared', *objects, str(directory / 'strict_o2.so'),
                        '-lm', '-o', str(output)], check=True, capture_output=True)
        lib = C.CDLL(str(output))
        lib.ng2_controller_create.argtypes = [C.c_uint64]; lib.ng2_controller_create.restype = C.c_void_p
        lib.ng2_controller_destroy.argtypes = [C.c_void_p]
        lib.ng2_controller_observe.argtypes = [C.c_void_p, C.POINTER(Scene)] + [C.c_uint64] * 4 + [C.c_int]
        lib.ng2_controller_tick.argtypes = [C.c_void_p, C.c_uint64] + [C.c_int] * 3 + [C.POINTER(controller.Command)]
        lib.ng2_controller_begin.argtypes = [C.c_void_p, C.c_uint64, C.c_uint64] + [C.c_int] * 3
        lib.ng2_controller_complete.argtypes = [C.c_void_p, C.c_uint64, C.c_uint64, C.c_int]
        lib.ng2_controller_status.argtypes = [C.c_void_p, C.POINTER(controller.Status)]
        lib.ng2_controller_events.argtypes = [C.c_void_p, C.POINTER(controller.Event), C.c_size_t]
        lib.ng2_controller_events.restype = C.c_size_t
        lib.ng2_controller_motion_wait.argtypes = [C.c_void_p, C.POINTER(controller.MotionWait)]
        names = {v: k for k, v in controller.KINDS.items()}
        scenes = pair(gold=(0, -3))
        terrains = [controller.nav.Scene({(i % 23 - 11, i // 23 - 5): names[kind]
                    for i, kind in enumerate(s.tiles) if kind},
                    {(i % 23 - 11, i // 23 - 5) for i, kind in enumerate(s.tiles) if kind == 2},
                    'unknown', set(), bytes(s.signature)) for s in scenes]
        for goods in (False, True):
            fixture = controller.NativeControllerTests('runTest'); fixture.lib = lib; fixture.setUp()
            self.addCleanup(fixture.doCleanups)
            fixture.fit(terrains[0]); command = fixture.next_move(); self.assertEqual(3, command.direction)
            ticket = bytes(command); fixture.ack(command); wait = fixture.motion_wait()
            deadline = wait.deadline_ns; event = fixture.events()[-1]
            earliest = max(event.end_ns, command.target_ns + 80_000_000)
            self.assertEqual((1, 0), (fixture.status().inputs, fixture.status().moves))
            fixture.now = earliest
            frame = fixture.scene(2, 2, terrains[1], beat=True)
            fixture.observe(frame, start=earliest - 1, end=earliest)
            self.assertEqual(0, fixture.status().moves); self.assertEqual(0, fixture.motion_wait().attempts)
            fixture.now = earliest + 20_000_002
            frame = fixture.scene(2, 2, terrains[1], beat=True)
            frame.beat_remaining = ((5 * controller.SECOND - (earliest + 10_000_002)) % controller.PERIOD) / controller.PERIOD
            if goods: frame.goods = 2
            self.assertLess(fixture.now, deadline)
            self.assertEqual(1, fixture.observe(frame, start=earliest + 2, end=fixture.now))
            self.assertEqual(ticket, bytes(fixture.events()[0].command))
            self.assertEqual(deadline, fixture.motion_wait().deadline_ns)
            if goods:
                self.assertEqual((1, 0, 1), (fixture.status().inputs, fixture.status().moves, fixture.status().goods))
                ready, pause = fixture.tick(); self.assertEqual((1, 2), (ready, pause.kind))
            else:
                self.assertEqual((1, 1, 0, 0, 0, -1), (fixture.status().inputs, fixture.status().moves,
                    fixture.status().door_changes, fixture.status().terrain_changes, fixture.status().x, fixture.status().y))
                credited = fixture.events()[-1]
                self.assertEqual((command.id, 2, 1, 0, -1),
                    (credited.command.id, credited.outcome, credited.motion, credited.dx, credited.dy))
                self.assertEqual((0, 1), (fixture.motion_wait().active, fixture.motion_wait().attempts))
                number = fixture.number; fixture.now += 1
                self.assertEqual(0, fixture.observe(frame, number=number, start=earliest + 2, end=earliest + 20_000_002))
                self.assertEqual((1, 1), (fixture.status().inputs, fixture.status().moves))
                following = fixture.next_move(terrains[1])
                self.assertNotEqual(command.id, following.id)
                self.assertEqual(command.ordinal + 1, following.ordinal)
                self.assertEqual(10_000_000, following.deadline_ns - following.not_before_ns)
                self.assertEqual(ticket, bytes(fixture.events()[0].command))


if __name__ == '__main__':
    unittest.main()
