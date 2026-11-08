"""NG-G2 C99 navigation and one-input motion, compared to the Python rules.

External images are calibration replays, not device acceptance measurements.
"""
import ctypes as C
from collections import defaultdict
from copy import deepcopy
from functools import wraps
import math
import hashlib
import json
import os
import random
from unittest.mock import patch

from PIL import Image, ImageChops, ImageStat
from necroprobe import shop_navigation as nav, motion_stats, native_scan, navigation_stats
from test_native_perception import required_fixtures, required_profile_fixtures
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'patches/loopctrl/ngg2'


class Scene(C.Structure):
    _fields_ = [('abi_version', C.c_uint32), ('struct_size', C.c_uint32),
                *[(k, C.c_int32) for k in ('state', 'restart_label', 'gold_state', 'gold_peak', 'goods')],
                ('tiles', C.c_uint8 * 230), ('protected_cells', C.c_uint8 * 230),
                ('signature', C.c_uint8 * 23296), ('fingerprint', C.c_uint8 * 48),
                ('beat_valid', C.c_int32), ('beat_remaining', C.c_double),
                ('beat_spacing', C.c_double), ('beat_center', C.c_double)]


class Entrance(C.Structure):
    _fields_ = [(k, C.c_int32) for k in ('valid', 'x', 'y', 'direction')]


class Decision(C.Structure):
    _fields_ = [(k, C.c_int32) for k in ('direction', 'reason', 'target_x', 'target_y', 'obstacle')]


class Motion(C.Structure):
    _fields_ = [(k, C.c_int32) for k in ('kind', 'dx', 'dy')]


KINDS = {'unknown': 0, 'floor': 1, 'gold': 2, 'stone': 3, 'dirt': 4, 'door': 5, 'item': 6}
DIRS = {None: 0, 'left': 1, 'right': 2, 'up': 3, 'down': 4}
REASONS = {name: k for k, name in enumerate((
    'no_observed_route', 'goods_visible', 'goods_adjacent_controls_unverified',
    'no_visible_gold_or_origin', 'entrance_unconfirmed', 'gate_single_probe',
    'dig_single_probe', 'approach_gate', 'observed_floor_vantage'))}
MOTIONS = {'unknown': 0, 'moved': 1, 'blocked': 2, 'door_opened': 3,
           'terrain_opened': 4, 'unexpected': 6, 'tween': 7}
CANDIDATES = [(0, 0)] + [(n * dx, n * dy) for n in range(1, 19)
                        for dx, dy in nav.DIRECTIONS.values()]


def canonical(scene):
    # The ABI holds the scan's finite grid, whose insertion order starts at origin.
    tiles = {p: scene.tiles[p] for p in [(0, 0)] + [(x, y) for y in range(-5, 5)
             for x in range(-11, 12) if (x, y) != (0, 0)] if p in scene.tiles}
    return nav.Scene(tiles, {p for p, k in tiles.items() if k == 'gold'}, scene.goods,
                     {p for p in scene.protected if -11 <= p[0] <= 11 and -5 <= p[1] <= 4},
                     scene.signature)


def as_native(scene):
    return native_scene(scene.tiles, scene.signature, scene.goods, scene.protected)


def random_signature(seed=43043):
    rng = random.Random(seed)
    return bytes(rng.randrange(20, 100) for _ in range(23296))


def translate(scene, dx, dy, sx=None, sy=None):
    source = Image.frombytes('L', (224, 104), scene.signature)
    changed = Image.new('L', source.size)
    changed.paste(source, (9*dx if sx is None else sx, 9*dy if sy is None else sy))
    return canonical(nav.Scene({(x+dx, y+dy): k for (x, y), k in scene.tiles.items()},
                     {(x+dx, y+dy) for x, y in scene.gold}, scene.goods,
                     {(x+dx, y+dy) for x, y in scene.protected}, changed.tobytes()))


def native_scene(tiles, signature=b'', goods='unknown', protected=()):
    out = Scene(abi_version=1, struct_size=C.sizeof(Scene), state=2,
                goods={'unknown': 0, 'partial': 1, 'visible': 2}[goods])
    for (x, y), kind in tiles.items():
        if -11 <= x <= 11 and -5 <= y <= 4:
            out.tiles[(y + 5) * 23 + x + 11] = KINDS[kind]
    for x, y in protected:
        if -11 <= x <= 11 and -5 <= y <= 4:
            out.protected_cells[(y + 5) * 23 + x + 11] = 1
    if signature:
        out.signature[:] = signature
    return out


def both_navigation_profiles(cls):
    """Execute the established independent expectations under both compilers."""
    def wrap(method):
        @wraps(method)
        def run(self):
            try:
                for name, library in self.libraries.items():
                    with self.subTest(profile=name):
                        self.lib = library
                        # Force Pillow instead of an installed native helper.
                        with patch.object(native_scan, '_native', None), \
                                patch.object(navigation_stats, '_native', None), \
                                patch.object(motion_stats, '_native', None):
                            method(self)
            finally:
                self.__dict__.pop('lib', None)
        return run
    for name, method in tuple(vars(cls).items()):
        if name.startswith('test_') and name != 'test_required_test049_navigation_strict_optimization_parity':
            setattr(cls, name, wrap(method))
    return cls


@both_navigation_profiles
class NativeNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        wrapper = Path(cls.temp.name) / 'wrapper.c'
        wrapper.write_text(r'''#include "NG2Navigation.c"
void ng2_test_view(const unsigned char *raw,unsigned char *out) {
    View v;int i;view(raw,&v);
    memcpy(out,v.normalized,N);
    for (i=0;i<N;++i) {out[N+i]=v.texture[i] ? 255 : 0;out[2*N+i]=v.positive[i] ? 255 : 0;}
}
void ng2_test_scores(const unsigned char *a,const unsigned char *b,double *out) {
    View views[2];int k=1,n,d;view(a,&views[0]);view(b,&views[1]);
    out[0]=intensity(&views[0],&views[1],0,0);
    for (n=1;n<=18;++n) for (d=1;d<=4;++d) out[k++]=intensity(&views[0],&views[1],n*ddx[d],n*ddy[d]);
}
void ng2_test_evaluate(const NG2Scene *a,const NG2Scene *b,int direction,const double *scores,NG2Motion *out) {
    View views[2];Candidate candidates[73];int k=1,n,d;
    view(a->signature,&views[0]);view(b->signature,&views[1]);memset(out,0,sizeof(*out));
    candidates[0].sx=0;candidates[0].sy=0;candidates[0].score=scores[0];
    for (n=1;n<=18;++n) for (d=1;d<=4;++d) {
        candidates[k].sx=n*ddx[d];candidates[k].sy=n*ddy[d];candidates[k].score=scores[k];++k;
    }
    evaluate_motion(a,b,direction,views,candidates,out);
}
int ng2_test_texture_strength(int support,int opposite,int percent) {return texture_strength(support,opposite,percent);}
int ng2_test_texture_lead(int support,int opposite,int count,int bad) {return texture_lead(support,opposite,count,bad);}
int ng2_test_strong(const unsigned char *texture,const unsigned char *positive,int expanded,int regions) {
    View views[2];Candidate candidates[73];int i,k=1,n,d;
    memset(views,0,sizeof(views));
    for (i=0;i<N;++i) {views[0].texture[i]=views[1].texture[i]=texture[i]!=0;views[1].positive[i]=positive[i]!=0;}
    candidates[0].sx=0;candidates[0].sy=0;candidates[0].score=0;
    for (n=1;n<=18;++n) for (d=1;d<=4;++d) {candidates[k].sx=n*ddx[d];candidates[k].sy=n*ddy[d];candidates[k].score=1;++k;}
    return strong_texture(&views[0],&views[1],candidates,expanded,regions);
}
''')
        perception = Path(cls.temp.name) / 'perception.o'
        subprocess.run(['cc', '-std=c99', '-O2', '-fno-fast-math', '-ffp-contract=off',
                        '-fPIC', '-c', str(CORE / 'NG2Perception.c'), '-o', str(perception)], check=True)
        cls.libraries = {}
        cls.compile_commands = {}
        for name, flags in (('unchanged_o0', ['-O0']),
                            ('strict_o2', ['-O2', '-fno-fast-math', '-ffp-contract=off'])):
            library = Path(cls.temp.name) / (name + '.so')
            command = ['cc', '-std=c99', *flags, '-Wall', '-Wextra', '-Werror', '-pedantic',
                       '-fPIC', '-shared', '-I' + str(CORE), str(wrapper), str(perception),
                       '-lm', '-o', str(library)]
            subprocess.run(command, check=True)
            cls.compile_commands[name] = command
            cls.libraries[name] = lib = C.CDLL(str(library))
            cls.configure_library(lib)
        cls.lib = cls.libraries['strict_o2']

    @staticmethod
    def configure_library(lib):
        lib.ng2_choose.argtypes = [C.POINTER(Scene), C.c_int32, C.c_int32,
                                      C.POINTER(C.c_uint16), C.c_size_t,
                                      C.POINTER(Entrance), C.POINTER(Decision)]
        lib.ng2_motion.argtypes = [C.POINTER(Scene), C.POINTER(Scene), C.c_int32, C.POINTER(Motion)]
        lib.ng2_entered_gate.argtypes = [C.POINTER(Scene), C.POINTER(Scene), C.c_int32,
                                           C.c_int32, C.c_int32, C.c_int32, C.POINTER(Entrance)]
        lib.ng2_test_view.argtypes = [C.c_char_p, C.c_void_p]
        lib.ng2_test_scores.argtypes = [C.c_char_p, C.c_char_p, C.POINTER(C.c_double)]
        lib.ng2_test_evaluate.argtypes = [C.POINTER(Scene), C.POINTER(Scene), C.c_int,
                                            C.POINTER(C.c_double), C.POINTER(Motion)]
        lib.ng2_test_strong.argtypes = [C.c_char_p, C.c_char_p, C.c_int, C.c_int]
        lib.ng2_test_texture_strength.argtypes = [C.c_int]*3
        lib.ng2_test_texture_lead.argtypes = [C.c_int]*4
        lib.ng2_analyze_rgba.argtypes = [C.c_void_p, C.c_size_t, C.c_size_t, C.POINTER(Scene)]

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_observed_gate_requires_up_single_probe(self):
        s = native_scene({(0, 0): 'floor', (0, -1): 'door', (-1, -1): 'gold', (1, -1): 'gold'})
        out = Decision()
        visits = (C.c_uint16 * 1089)()
        self.assertEqual(1, self.lib.ng2_choose(C.byref(s), 0, 0, visits, 1089, None, C.byref(out)))
        self.assertEqual(3, out.direction)
        self.assertEqual((0, -1), (out.target_x, out.target_y))

    def test_required_test045_subtile_motion_replay(self):
        """Known calibration images stay outside git and are mandatory locally."""
        root=Path(os.environ.get('NECRO_TEST046_FIXTURE_ROOT','/workspace/analysis-evidence'))
        manifest=json.loads((ROOT/'tests/test046-fixtures.json').read_text())
        self.assertEqual(('ngg2-test046-fixtures-v1',8), (manifest['schema'],manifest['count']))
        self.assertEqual(8,len(manifest['images']))
        self.assertEqual(8,len({entry['path'] for entry in manifest['images']}))
        images={}
        for entry in manifest['images']:
            path=root/entry['path']
            self.assertTrue(path.is_file(),f'missing required TEST046 fixture: {path}')
            self.assertEqual(entry['sha256'],hashlib.sha256(path.read_bytes()).hexdigest())
            images[path.name]=Image.open(path).convert('RGBA')
        native={};reference={}
        for capture_id in (13,16,17):
            image=images[f'capture-{capture_id:06d}.png'];raw=image.tobytes();out=Scene()
            self.assertEqual(0,self.lib.ng2_analyze_rgba(raw,len(raw),3584,C.byref(out)))
            native[capture_id]=out;reference[capture_id]=canonical(nav.scan(image.convert('RGB')))
            self.assertEqual(2,out.state)
            self.assertEqual(reference[capture_id].signature,bytes(out.signature))
            self.assertEqual(bytes(as_native(reference[capture_id]).tiles),bytes(out.tiles))
            self.assertEqual(bytes(as_native(reference[capture_id]).protected_cells),bytes(out.protected_cells))
            self.assertEqual(as_native(reference[capture_id]).goods,out.goods)
        # Independent original-pixel landmarks establish the one-pixel residual;
        # the sparse verifier itself intentionally retains UNKNOWN for 35px.
        for after,displacement in ((16,35),(17,36)):
            old=images['capture-000013.png'].convert('L');new=images[f'capture-{after:06d}.png'].convert('L')
            for box in ((503,9,534,37),(322,153,355,287),(360,143,394,282)):
                x0,y0,x1,y1=box
                errors=[(ImageStat.Stat(ImageChops.difference(old.crop(box),new.crop((x0,y0+sy,x1,y1+sy)))).mean[0],sy)
                        for sy in range(30,41)]
                self.assertEqual(displacement,min(errors)[1])
        for after,kind,score in ((16,0,.5591420100727641),(17,1,.13238347244935728)):
            before=native[13];changed=native[after];result=Motion()
            self.assertEqual(1,self.lib.ng2_motion(C.byref(before),C.byref(changed),3,C.byref(result)))
            self.assertEqual(kind,result.kind)
            self.assertEqual('unknown' if kind==0 else 'moved',nav.motion(reference[13],reference[after],'up'))
            native_scores=(C.c_double*73)()
            self.lib.ng2_test_scores(bytes(before.signature),bytes(changed.signature),native_scores)
            old=nav._motion_view(reference[13].signature)[0];new=nav._motion_view(reference[after].signature)[0]
            pillow=nav._pillow_motion_scores(old,new)
            for actual,(expected,_,_) in zip(native_scores,pillow):self.assertAlmostEqual(expected,actual,places=12)
            ranked=sorted((value,*point) for value,point in zip(native_scores,CANDIDATES))
            self.assertEqual((0,9),ranked[0][1:]);self.assertAlmostEqual(score,ranked[0][0],places=12)
            self.assertGreaterEqual(ranked[1][0]-ranked[0][0],.08)

    def choose(self, scene, position=(0, 0), visits=None, entrance=None):
        native = as_native(canonical(scene))
        values = (C.c_uint16 * 1089)()
        for (x, y), count in (visits or {}).items():
            if -16 <= x <= 16 and -16 <= y <= 16:
                values[(y+16)*33+x+16] = count
        context = None if entrance is None else Entrance(1, *entrance['gate'], DIRS[entrance['direction']])
        out = Decision()
        inputs = (bytes(native), bytes(values), None if context is None else bytes(context))
        status = self.lib.ng2_choose(C.byref(native), *position, values, 1089,
                                    None if context is None else C.byref(context), C.byref(out))
        self.assertEqual(inputs, (bytes(native), bytes(values), None if context is None else bytes(context)))
        return status, out

    def assert_choose(self, scene, position=(0, 0), visits=None, entrance=None):
        scene = canonical(scene)
        expected = nav.choose(scene, position, visits, entrance)
        status, out = self.choose(scene, position, visits, entrance)
        self.assertEqual(bool(expected['direction']), bool(status))
        self.assertEqual(DIRS[expected['direction']], out.direction)
        self.assertEqual(REASONS[expected['reason']], out.reason)
        self.assertEqual(expected['target'] or (0, 0), (out.target_x, out.target_y))
        if out.direction:
            self.assertEqual(KINDS.get(scene.tiles.get(nav.DIRECTIONS[expected['direction']]), 0), out.obstacle)
        return out

    def motion(self, before, after, direction, scores=None):
        a, b, out = as_native(canonical(before)), as_native(canonical(after)), Motion()
        inputs = bytes(a), bytes(b)
        if scores is None:
            self.assertEqual(1, self.lib.ng2_motion(C.byref(a), C.byref(b), DIRS[direction], C.byref(out)))
        else:
            values = (C.c_double * 73)(*scores)
            self.lib.ng2_test_evaluate(C.byref(a), C.byref(b), DIRS[direction], values, C.byref(out))
            self.assertEqual(tuple(scores), tuple(values))
        self.assertEqual(inputs, (bytes(a), bytes(b)))
        return out

    def assert_motion(self, before, after, direction, expected=None, scores=None):
        before, after = canonical(before), canonical(after)
        if scores is None:
            reference = nav.motion(before, after, direction)
        else:
            rows = [(value, *point) for value, point in zip(scores, CANDIDATES)]
            with patch.object(motion_stats, 'scores', return_value=rows):
                reference = nav.motion(before, after, direction)
        if expected is not None:
            self.assertEqual(expected, reference)
        result = self.motion(before, after, direction, scores)
        self.assertEqual(MOTIONS[reference], result.kind)
        if reference == 'moved':
            self.assertEqual(nav.DIRECTIONS[direction], (result.dx, result.dy))
        elif reference != 'unexpected':
            self.assertEqual((0, 0), (result.dx, result.dy))
        return result

    def test_weighted_gate_route_digs_only_toward_observed_gate(self):
        base = {(0,0): 'floor', (-1,0): 'dirt', (-2,0): 'floor', (-3,0): 'door',
                (-3,-1): 'gold', (-3,1): 'gold', (0,1): 'floor'}
        scene = canonical(nav.Scene(base, set(), 'unknown', set(), b''))
        self.assertEqual(6, self.assert_choose(scene).reason)
        scene.tiles.pop((-3,-1)); scene.gold.remove((-3,-1))
        # Without a known gate, fallback must never enter the dirt.
        self.assertEqual(4, self.assert_choose(scene).direction)
        scene.tiles.pop((0,1))
        self.assertEqual(0, self.assert_choose(scene).direction)

    def test_routes_all_orientations_and_world_visits(self):
        for direction, (dx, dy) in nav.DIRECTIONS.items():
            tx, ty = -dy, dx
            tiles = {(0,0): 'floor', (dx,dy): 'floor', (2*dx,2*dy): 'floor',
                     (3*dx,3*dy): 'door', (3*dx+tx,3*dy+ty): 'gold',
                     (3*dx-tx,3*dy-ty): 'gold', (tx,ty): 'floor', (2*tx,2*ty): 'floor'}
            scene = canonical(nav.Scene(tiles,set(),'unknown',set(),b''))
            with self.subTest(direction=direction):
                self.assertEqual(DIRS[direction], self.assert_choose(scene).direction)
                for pos in ((0,0),(-16,16),(16,-16)):
                    self.assert_choose(scene,pos,{(pos[0]+dx,pos[1]+dy): 65535})
                for goods in ('unknown','partial','visible'):
                    scene.goods=goods; self.assert_choose(scene)

    def test_planner_randomized_reference_ties_protection_and_entrance(self):
        rng=random.Random(43043)
        points=[(x,y) for y in range(-5,5) for x in range(-11,12)]
        for case in range(250):
            tiles={p:rng.choice(('floor','floor','floor','stone','dirt','door','unknown'))
                   for p in points if rng.random()<.7}
            tiles[(0,0)]='floor'
            for p in rng.sample(points, rng.randrange(1,8)): tiles[p]='gold'
            protected=set(rng.sample(points,rng.randrange(0,8)))
            scene=canonical(nav.Scene(tiles,set(),rng.choice(('unknown','partial','visible')),protected,b''))
            position=(rng.randrange(-16,17),rng.randrange(-16,17))
            visits={p:rng.randrange(0,10) for p in rng.sample([(x,y) for x in range(-16,17) for y in range(-16,17)],30)}
            entrance=None
            if case%3==0:
                direction=rng.choice(list(nav.DIRECTIONS));dx,dy=nav.DIRECTIONS[direction]
                entrance={'gate':(max(-16,min(16,position[0]-dx)),max(-16,min(16,position[1]-dy))), 'direction':direction}
            with self.subTest(case=case):self.assert_choose(scene,position,visits,entrance)

    def test_entrance_retains_gold_but_forbids_retreat(self):
        for direction,(dx,dy) in nav.DIRECTIONS.items():
            tx,ty=-dy,dx
            tiles={(0,0):'floor',(dx,dy):'floor',(-dx,-dy):'floor',(tx,ty):'floor',
                   (-dx+tx,-dy+ty):'gold',(-dx-tx,-dy-ty):'gold'}
            scene=canonical(nav.Scene(tiles,set(),'unknown',set(),b''))
            position=(2*dx,2*dy);context={'gate':(dx,dy),'direction':direction}
            with self.subTest(direction=direction):
                self.assert_choose(scene,position,entrance=context)
                scene.tiles.pop((dx,dy));scene.tiles.pop((tx,ty))
                self.assertEqual(0,self.assert_choose(scene,position,entrance=context).direction)
                bad={'gate':(3*dx,3*dy),'direction':direction}
                self.assertEqual(4,self.assert_choose(scene,position,entrance=bad).reason)

    def test_signature_normalization_and_all73_scores_exact_reference(self):
        rng=random.Random(43044)
        signatures=[bytes(23296),bytes([6])*23296,bytes([7])*23296,
                    bytes(rng.randrange(256) for _ in range(23296)),random_signature()]
        for raw in signatures:
            result=(C.c_ubyte*(3*23296))()
            self.lib.ng2_test_view(raw,result)
            normalized,texture,positive=nav._motion_view(raw,full_texture=True)
            self.assertEqual(normalized,bytes(result[:23296]))
            self.assertEqual(texture.tobytes(),bytes(result[23296:2*23296]))
            self.assertEqual(positive.tobytes(),bytes(result[2*23296:]))
        for before,after in ((signatures[0],signatures[0]),(signatures[3],signatures[4]),
                             (signatures[4],signatures[4])):
            result=(C.c_double*73)();self.lib.ng2_test_scores(before,after,result)
            a=nav._motion_view(before)[0];b=nav._motion_view(after)[0]
            expected=nav._pillow_motion_scores(a,b)
            for value,(score,_,_) in zip(result,expected):
                self.assertEqual(score,value)

    def test_public_one_step_zero_tween_two_opposite_and_unknown(self):
        base=canonical(nav.Scene({(0,0):'floor',(-3,-3):'gold'},set(),'unknown',set(),random_signature()))
        for direction,(dx,dy) in nav.DIRECTIONS.items():
            for amount in (0,1,8,9,10,18,-9):
                after=translate(base,-dx,-dy,sx=-dx*amount,sy=-dy*amount)
                with self.subTest(direction=direction,amount=amount):
                    expected='blocked' if amount==0 else ('tween' if amount in (1,8) else ('moved' if amount==9 else 'unexpected'))
                    self.assert_motion(base,after,direction,expected)
        base.signature=bytes([40])*23296
        self.assert_motion(base,base,'up','unknown')

    def test_opening_is_not_entry_and_dirt_requires_both_unprotected(self):
        raw=random_signature()
        for direction,(dx,dy) in nav.DIRECTIONS.items():
            tx,ty=-dy,dx
            before=canonical(nav.Scene({(0,0):'floor',(dx,dy):'door',
                           (dx+tx,dy+ty):'gold',(dx-tx,dy-ty):'gold'},set(),'unknown',set(),raw))
            after=deepcopy(before);after.tiles[(dx,dy)]='floor'
            self.assert_motion(before,after,direction,'door_opened')
            self.assert_entered(before,after,direction,(0,0),'door_opened',False)
            before.tiles[(dx,dy)]='dirt'
            self.assert_motion(before,after,direction,'terrain_opened')
            for scene in (before,after):
                scene.protected.add((dx,dy));self.assert_motion(before,after,direction,'blocked');scene.protected.clear()
            before.tiles[(dx,dy)]='floor'
            after=translate(before,-dx,-dy);after.tiles[(0,0)]='floor'
            self.assert_motion(before,after,direction,'moved')
            self.assert_entered(before,after,direction,(3,-3),'moved',True)
            for scene,point in ((before,(dx,dy)),(after,(0,0))):
                scene.protected.add(point);self.assert_entered(before,after,direction,(3,-3),'moved',False);scene.protected.clear()

    def assert_entered(self,before,after,direction,position,outcome,expected):
        a,b,out=as_native(canonical(before)),as_native(canonical(after)),Entrance()
        inputs=bytes(a),bytes(b)
        result=self.lib.ng2_entered_gate(C.byref(a),C.byref(b),DIRS[direction],*position,MOTIONS[outcome],C.byref(out))
        self.assertEqual(inputs,(bytes(a),bytes(b)))
        reference=nav.entered_gate(canonical(before),canonical(after),direction,position,1,outcome)
        self.assertEqual(expected,reference is not None)
        self.assertEqual(expected,bool(result));self.assertEqual(expected,bool(out.valid))
        if expected:
            self.assertEqual(reference['gate'],(out.x,out.y));self.assertEqual(DIRS[direction],out.direction)

    def test_structural_partial_gold_and_all_geometric_aliases(self):
        # Force only the coarse score; geometry and every real signed texture vote execute.
        for direction,(dx,dy) in nav.DIRECTIONS.items():
            before=canonical(nav.Scene({(0,0):'floor',(-2,2):'gold',(0,-1):'stone',(8,0):'stone'},set(),'unknown',set(),random_signature()))
            after=translate(before,-dx,-dy);after.tiles[(-6,-3)]='gold';after=canonical(after)
            scores=[.6 if p==(-9*dx,-9*dy) else .9 for p in CANDIDATES]
            self.assert_motion(before,after,direction,'moved',scores)
            for p in ((0,0),(-dx,-dy),(dx,dy),(2*dx,2*dy),(-2*dx,-2*dy)):
                if p==(-dx,-dy):continue
                alias=deepcopy(after)
                for (x,y),kind in before.tiles.items():alias.tiles[(x+p[0],y+p[1])]=kind
                self.assert_motion(before,canonical(alias),direction,'unknown',scores)
            for reverse in (False,True):
                bad=deepcopy(after);old=deepcopy(before)
                if reverse:old.tiles[(4,3)]='dirt';bad.tiles[(4-dx,3-dy)]='stone'
                else:old.tiles[(4,3)]='stone';bad.tiles[(4-dx,3-dy)]='dirt'
                self.assert_motion(old,bad,direction,'unknown',scores)

    def test_closed_gate_high_intensity_rescue_and_repeated_texture_rejection(self):
        before=canonical(nav.Scene({(0,0):'floor',(0,-2):'door',(-1,-2):'gold',(1,-2):'gold'},set(),'unknown',set(),random_signature()))
        after=translate(before,0,1)
        scores=[.6 if p==(0,9) else .9 for p in CANDIDATES]
        self.assert_motion(before,after,'up','moved',scores)
        for change in ('stationary_gold','missing_door','extra_gold','floor_gate'):
            a,b=deepcopy(before),deepcopy(after)
            if change=='stationary_gold':b.tiles=a.tiles.copy()
            if change=='missing_door':b.tiles.pop((0,-1))
            if change=='extra_gold':b.tiles[(6,2)]='gold'
            if change=='floor_gate':a.tiles[(0,-2)]='floor'
            self.assert_motion(a,b,'up','unknown',scores)
        rng=random.Random(43045);row=bytes(rng.randrange(20,100) for _ in range(224*9))
        before.signature=after.signature=(row*12)[:23296]
        self.assert_motion(before,after,'up','unknown',scores)

    def test_coarse_thresholds_and_texture_support_signed_regions_boundaries(self):
        before=canonical(nav.Scene({(0,0):'floor',(-3,-3):'gold'},set(),'unknown',set(),random_signature()))
        after=translate(before,0,1)
        for best,runner,expected in ((.45,.53,'moved'),(math.nextafter(.45,1),.6,'unknown'),
                                     (.2,.28,'moved'),(.2,math.nextafter(.28,0),'unknown'),
                                     (math.inf,math.inf,'unknown')):
            scores=[best if p==(0,9) else runner for p in CANDIDATES]
            self.assert_motion(before,after,'up',expected,scores)
        rng=random.Random(43046)
        top=rng.sample([(x,y) for y in range(20,36) for x in range(40,179)],150)
        left=rng.sample([(x,y) for y in range(36,79) for x in range(40,90)],201)
        for a,b,bad,regions,expected in ((150,150,15,1,True),(150,149,0,1,False),
                                        (150,150,16,1,False),(99,201,0,1,False),
                                        (99,201,0,0,True)):
            points=top[:a]+left[:b];texture=bytearray(23296);positive=bytearray(23296)
            for x,y in points:texture[y*224+x]=255
            for x,y in points[:bad]:positive[y*224+x]=255
            self.assertEqual(expected,bool(self.lib.ng2_test_strong(bytes(texture),bytes(positive),0,regions)))

    def test_narrow_corridor_real_texture_and_actor_exclusions(self):
        rng=random.Random(43047)
        raw=Image.new('L',(224,104),40)
        for y in range(20,79):
            for x in range(90,110):raw.putpixel((x,y),rng.randrange(20,90))
        before=canonical(nav.Scene({(0,0):'floor',(0,-1):'floor',(-1,-1):'gold',(1,-1):'gold'},
                                   set(),'unknown',set(),raw.tobytes()))
        after=translate(before,0,1);after.tiles[(0,0)]='floor'
        a=nav._motion_view(before.signature);b=nav._motion_view(after.signature)
        self.assertLess(nav._texture_match(a[1],b[1],a[2],b[2],0,9)[0],300)
        self.assert_motion(before,after,'up','moved')
        for fault in ('missing_gate','missing_gold','stationary_landmarks','floor_to_door','repeat'):
            old,new=deepcopy(before),deepcopy(after)
            if fault=='missing_gate':new.tiles.pop((0,0))
            if fault=='missing_gold':new.tiles.pop((-1,0))
            if fault=='stationary_landmarks':new.tiles=old.tiles.copy()
            if fault=='floor_to_door':new.tiles[(0,0)]='door'
            if fault=='repeat':
                for p,k in old.tiles.items():new.tiles[p]=k
            self.assert_motion(old,new,'up','unknown')
        actor=Image.new('L',(224,104),40)
        for box in ((104,44,121,60),):
            block=Image.frombytes('L',(box[2]-box[0],box[3]-box[1]),
                    bytes(rng.randrange(20,100) for _ in range((box[2]-box[0])*(box[3]-box[1]))))
            actor.paste(block,box[:2])
        before.signature=actor.tobytes();after=translate(before,0,1)
        self.assert_motion(before,after,'up','unknown')

    def test_large_moving_object_cannot_outvote_stationary_terrain(self):
        before=canonical(nav.Scene({(0,0):'floor',(-2,2):'gold',(0,-1):'stone',(8,0):'stone'},
                                   set(),'unknown',set(),random_signature()))
        after=translate(before,0,-1);after.tiles[(-6,-3)]='gold'
        rng=random.Random(43048)
        stationary=Image.new('L',(224,104),40)
        def texture(box):
            w,h=box[2]-box[0],box[3]-box[1]
            return Image.frombytes('L',(w,h),bytes(rng.randrange(20,100) for _ in range(w*h)))
        for box in ((44,68,85,76),(140,55,178,63)):stationary.paste(texture(box),box[:2])
        initial,changed=stationary.copy(),stationary.copy()
        for box in ((44,29,178,35),(44,50,85,58)):
            block=texture(box);initial.paste(block,box[:2]);changed.paste(block,(box[0],box[1]-9))
        before.signature,after.signature=initial.tobytes(),changed.tobytes()
        scores=[.6 if p==(0,-9) else .9 for p in CANDIDATES]
        self.assert_motion(before,after,'down','unknown',scores)

    def test_signed_texture_thresholds_exact75_95_and15point_lead(self):
        for support,bad,percent,expected in ((299,0,75,False),(300,75,75,True),
                                            (300,76,75,False),(300,15,95,True),(300,16,95,False)):
            self.assertEqual(expected,bool(self.lib.ng2_test_texture_strength(support,bad,percent)))
        # Winner95%, competitors80% and80.25%: exactly15pp passes, below fails.
        for count,bad,expected in ((400,80,True),(400,79,False),(299,0,True),(300,0,False)):
            self.assertEqual(expected,bool(self.lib.ng2_test_texture_lead(400,20,count,bad)))

    def test_invalid_arguments_zero_outputs_and_do_not_authorize_input(self):
        good=native_scene({(0,0):'floor',(0,-1):'gold'})
        visits=(C.c_uint16*1089)()
        for mutate in (lambda s:setattr(s,'abi_version',0),lambda s:setattr(s,'struct_size',0),
                       lambda s:setattr(s,'state',0),lambda s:setattr(s,'goods',3),
                       lambda s:s.tiles.__setitem__(0,7),lambda s:s.protected_cells.__setitem__(0,2)):
            s=Scene.from_buffer_copy(good);mutate(s)
            out=Decision(99,99,99,99,99)
            self.assertEqual(0,self.lib.ng2_choose(C.byref(s),0,0,visits,1089,None,C.byref(out)))
            self.assertEqual(bytes(Decision()),bytes(out))
            motion=Motion(99,99,99)
            self.assertEqual(0,self.lib.ng2_motion(C.byref(s),C.byref(good),3,C.byref(motion)))
            self.assertEqual(bytes(Motion()),bytes(motion))
        for pos,count,pointer in (((17,0),1089,visits),((0,-17),1089,visits),((0,0),1088,visits),((0,0),1089,None)):
            out=Decision(99,99,99,99,99)
            self.assertEqual(0,self.lib.ng2_choose(C.byref(good),*pos,pointer,count,None,C.byref(out)))
            self.assertEqual(bytes(Decision()),bytes(out))
        for direction in (0,5,-1,2**31-1):
            out=Motion(99,99,99)
            self.assertEqual(0,self.lib.ng2_motion(C.byref(good),C.byref(good),direction,C.byref(out)))
            self.assertEqual(bytes(Motion()),bytes(out))
        self.assertEqual(0,self.lib.ng2_choose(None,0,0,visits,1089,None,None))
        self.assertEqual(0,self.lib.ng2_motion(None,None,3,None))

    def test_actual037_single_partial_gold_step_retains_stone_evidence(self):
        digests=('76cb87a61ba9667e8bd11457f024889299a58d739139a1500a7dc6ee55068a0f',
                 '95071b5d4a42b8c48fcf42f23a4095245da1bd9cd2e1b04d125adc332742d7aa')
        paths={hashlib.sha256(p.read_bytes()).hexdigest():p for p in required_fixtures()}
        scenes=[]
        for digest in digests:
            with Image.open(paths[digest]) as image:scenes.append(canonical(nav.scan(image.convert('RGB'))))
        self.assertEqual([1,2],[len(s.gold) for s in scenes])
        self.assert_motion(*scenes,'down','moved')
        self.assert_motion(*scenes,'up','unexpected')
        self.assertEqual(1,self.assert_choose(scenes[-1]).direction)

    def test_required034_to042_route_motion_and_all73_score_parity(self):
        groups=defaultdict(list);count=0
        for path in required_fixtures():
            with Image.open(path) as image:scene=canonical(nav.scan(image.convert('RGB')))
            with self.subTest(frame=str(path)):
                self.assert_choose(scene)
                if len(scene.signature)==23296:
                    self.assert_motion(scene,scene,'up')
            if path.name.startswith('run-'):groups[path.parent].append((path.name,scene))
            count+=1
        self.assertGreaterEqual(count,66)
        pairs=0
        for folder,frames in groups.items():
            ordered=sorted(frames)
            for (aname,before),(bname,after) in zip(ordered,ordered[1:]):
                with self.subTest(run=folder.name,before=aname,after=bname):
                    for direction in nav.DIRECTIONS:self.assert_motion(before,after,direction)
                    scores=(C.c_double*73)();self.lib.ng2_test_scores(before.signature,after.signature,scores)
                    old=nav._motion_view(before.signature)[0];new=nav._motion_view(after.signature)[0]
                    for value,(expected,_,_) in zip(scores,nav._pillow_motion_scores(old,new)):
                        self.assertEqual(expected,value)
                pairs+=1
        self.assertGreaterEqual(pairs,25)

    def test_required_test049_navigation_strict_optimization_parity(self):
        """141 known image paths and all 15 TEST049 FLOOR pairs; no speed extrapolation."""
        from test_native_perception import NativePerceptionTests, NativeScene
        manifest = json.loads((ROOT / 'tests/test050-fixtures.json').read_text())
        self.assertEqual(('ngg2-test050-fixtures-v1', 11), (manifest['schema'], manifest['count']))
        self.assertEqual('84c30bff8567b893184a67fd18f67ab71adee4f298b3ab7d82f7166c4f19c39a',
                         manifest['source_zip_sha256'])
        self.assertEqual('a1e266be56ee9bc0c69e2bac5a8439133d78cf65db39f4ea7b6936794ef34683',
                         manifest['source_report_sha256'])
        self.assertEqual([6, 33, 34, 36, 45, 46], manifest['floor_capture_ids'])
        ids = manifest['floor_capture_ids']
        self.assertEqual([[a, b] for k, a in enumerate(ids) for b in ids[k+1:]], manifest['floor_pairs'])
        self.assertEqual(list(nav.DIRECTIONS), manifest['directions'])
        baseline = self.compile_commands['unchanged_o0']
        self.assertIn('-O0', baseline)
        self.assertFalse(any(flag in baseline for flag in ('-O2', '-fno-fast-math', '-ffp-contract=off')))
        for flag in ('-O2', '-fno-fast-math', '-ffp-contract=off'):
            self.assertIn(flag, self.compile_commands['strict_o2'])

        counts = defaultdict(int)
        def public(name, arguments, output_type, inputs):
            snapshots = [bytes(value) for value in inputs]
            results = []
            for index, library in enumerate(self.libraries.values()):
                output = output_type()
                C.memset(C.byref(output), 0xa5 if index == 0 else 0x5a, C.sizeof(output))
                result = getattr(library, name)(*arguments, C.byref(output))
                self.assertEqual(snapshots, [bytes(value) for value in inputs], name + ' mutated its input')
                results.append((result, bytes(output)))
            self.assertEqual(results[0], results[1], name + ' return/full output bytes changed')
            counts[name] += 1
            return results[0][0], output_type.from_buffer_copy(results[0][1])

        views = {}
        def view(scene):
            raw = bytes(scene.signature)
            outputs = []
            for library in self.libraries.values():
                output = (C.c_ubyte * (3 * 23296))()
                library.ng2_test_view(raw, output)
                self.assertEqual(raw, bytes(scene.signature))
                outputs.append(bytes(output))
            self.assertEqual(outputs[0], outputs[1], 'entire normalized/texture/positive views changed')
            normalized, texture, positive = nav._motion_view(raw, full_texture=True)
            self.assertEqual(normalized + texture.tobytes() + positive.tobytes(), outputs[0])
            counts['views'] += 1
            return normalized

        def pair(a, b, old_reference, new_reference):
            inputs = bytes(a), bytes(b)
            old_raw, new_raw = bytes(a.signature), bytes(b.signature)
            scores = []
            for library in self.libraries.values():
                output = (C.c_double * 73)()
                library.ng2_test_scores(old_raw, new_raw, output)
                self.assertEqual(inputs, (bytes(a), bytes(b)))
                self.assertEqual((old_raw, new_raw), (bytes(a.signature), bytes(b.signature)),
                                 'score probe mutated its signature inputs')
                scores.append(bytes(output))
            self.assertEqual(scores[0], scores[1], 'all 73 double score bytes changed')
            values = (C.c_double * 73).from_buffer_copy(scores[0])
            expected_scores = nav._pillow_motion_scores(views[old_raw], views[new_raw])
            for actual, (expected, _, _) in zip(values, expected_scores):
                self.assertAlmostEqual(expected, actual, places=12)
            counts['scores'] += 1
            for direction in nav.DIRECTIONS:
                result, motion = public('ng2_motion', (C.byref(a), C.byref(b), DIRS[direction]),
                                        Motion, (a, b))
                valid = a.state == b.state == 2
                self.assertEqual(int(valid), result)
                if valid:
                    # Pillow scores are independently computed above and reused
                    # without mutating their candidate order between directions.
                    with patch.object(motion_stats, 'scores', side_effect=lambda *_: list(expected_scores)):
                        expected = nav.motion(old_reference, new_reference, direction)
                    self.assertEqual(MOTIONS[expected], motion.kind)
                    if expected == 'moved':
                        self.assertEqual(nav.DIRECTIONS[direction], (motion.dx, motion.dy))
                    elif expected != 'unexpected':
                        self.assertEqual((0, 0), (motion.dx, motion.dy))
                else:
                    self.assertEqual(bytes(Motion()), bytes(motion))
                for outcome in range(8):
                    entered, entrance = public('ng2_entered_gate',
                        (C.byref(a), C.byref(b), DIRS[direction], 0, 0, outcome), Entrance, (a, b))
                    expected = (nav.entered_gate(old_reference, new_reference, direction,
                                                (0, 0), 1, 'moved' if outcome == 1 else 'unknown')
                                if valid else None)
                    self.assertEqual(expected is not None, bool(entered))
                    expected_bytes = (bytes(Entrance(1, *expected['gate'], DIRS[expected['direction']]))
                                      if expected else bytes(Entrance()))
                    self.assertEqual(expected_bytes, bytes(entrance))

        NativePerceptionTests.setUpClass()
        try:
            perception = NativePerceptionTests()
            old_path = Path(self.temp.name) / 'perception-unchanged-o0.so'
            subprocess.run(['cc', '-std=c99', '-O0', '-fPIC', '-shared',
                            str(CORE / 'NG2Perception.c'), '-lm', '-o', str(old_path)], check=True)
            old = C.CDLL(str(old_path))
            old.ng2_analyze_rgba.argtypes = [C.c_void_p, C.c_size_t, C.c_size_t, C.POINTER(NativeScene)]
            new_floors = {}
            with patch.object(native_scan, '_native', None), patch.object(navigation_stats, '_native', None), \
                    patch.object(motion_stats, '_native', None):
                for filename, entry, path in required_profile_fixtures():
                    with self.subTest(manifest=filename, path=entry['path']):
                        with Image.open(path) as source:
                            image = source.convert('RGB')
                        self.assertEqual((896, 414), image.size)
                        analyzed = perception.assert_reference(image)
                        scene = Scene.from_buffer_copy(bytes(analyzed))
                        reference = canonical(nav.scan(image)) if scene.state == 2 else None
                        raw = bytes(scene.signature)
                        views[raw] = view(scene)
                        if filename in ('test050-fixtures.json', 'test052-fixtures.json', 'test053-fixtures.json', 'test054-fixtures.json'):
                            expected_keys = {'path', 'sha256', 'bytes', 'capture_id', 'state', 'goods', 'stable'}
                            if filename == 'test054-fixtures.json':
                                expected_keys.add('completed_prefix')
                                self.assertIs(type(entry['completed_prefix']), int)
                                self.assertGreaterEqual(entry['completed_prefix'], 0)
                            self.assertEqual(expected_keys, set(entry))
                            for key in ('bytes', 'capture_id', 'state', 'goods'):
                                self.assertIs(type(entry[key]), int)
                            self.assertIs(type(entry['stable']), bool)
                            self.assertEqual(entry['bytes'], path.stat().st_size)
                            self.assertEqual((entry['state'], entry['goods']), (scene.state, scene.goods))
                            rgba = image.convert('RGBA').tobytes()
                            unchanged = NativeScene()
                            self.assertEqual(0, old.ng2_analyze_rgba(rgba, len(rgba), 3584, C.byref(unchanged)))
                            self.assertEqual(bytes(unchanged), bytes(analyzed), 'new Perception full Scene parity')
                            counts['new_perception'] += 1
                            if scene.state == 2 and filename == 'test050-fixtures.json':
                                new_floors[entry['capture_id']] = scene, reference
                        for position in ((0, 0), (-1, 0)):
                            for visited in (False, True):
                                visits = (C.c_uint16 * 1089)()
                                visits[(position[1]+16)*33+position[0]+16] = int(visited)
                                result, decision = public('ng2_choose',
                                    (C.byref(scene), *position, visits, 1089, None), Decision, (scene, visits))
                                if reference is None:
                                    self.assertEqual((0, bytes(Decision())), (result, bytes(decision)))
                                else:
                                    expected = nav.choose(reference, position, {position: int(visited)})
                                    self.assertEqual(bool(expected['direction']), bool(result))
                                    self.assertEqual(DIRS[expected['direction']], decision.direction)
                                    self.assertEqual(REASONS[expected['reason']], decision.reason)
                                    self.assertEqual(expected['target'] or (0, 0), (decision.target_x, decision.target_y))
                                    obstacle = KINDS.get(reference.tiles.get(nav.DIRECTIONS[expected['direction']]), 0) if expected['direction'] else 0
                                    self.assertEqual(obstacle, decision.obstacle)
                        pair(scene, scene, reference, reference)
                        counts['images'] += 1
                for before_id, after_id in manifest['floor_pairs']:
                    with self.subTest(before=before_id, after=after_id):
                        a, before = new_floors[before_id]
                        b, after = new_floors[after_id]
                        pair(a, b, before, after)
        finally:
            NativePerceptionTests.tearDownClass()
        self.assertEqual({'images': 141, 'new_perception': 54, 'views': 141, 'scores': 156,
                          'ng2_choose': 564, 'ng2_motion': 624, 'ng2_entered_gate': 4992}, dict(counts))


    def test_required_test051_target_drift_and_strict_parity(self):
        """Known raw replay under both profiles; no new classifier thresholds."""
        from test_native_perception import NativePerceptionTests
        manifest = json.loads((ROOT/'tests/test052-fixtures.json').read_text())
        self.assertEqual(('ngg2-test052-fixtures-v1', 9), (manifest['schema'], manifest['count']))
        self.assertEqual('8227fa10433a458bd5f945cbf7bb953f6d2fe76ab8a2daa07181b1890dcf020c', manifest['source_zip_sha256'])
        self.assertEqual('7ced44081507e544e997e545510b6a2ce849236d40271ba89cbcb63e79af079a', manifest['source_report_sha256'])
        NativePerceptionTests.setUpClass()
        try:
            perception = NativePerceptionTests()
            scenes, references = {}, {}
            for filename, entry, path in required_profile_fixtures():
                if filename != 'test052-fixtures.json':
                    continue
                with Image.open(path) as source:
                    image = source.convert('RGB')
                analyzed = perception.assert_reference(image)
                self.assertEqual((entry['state'], entry['goods']), (analyzed.state, analyzed.goods))
                self.assertEqual(entry['bytes'], path.stat().st_size)
                scenes[entry['capture_id']] = Scene.from_buffer_copy(bytes(analyzed))
                references[entry['capture_id']] = nav.scan(image)
            self.assertEqual(9, len(scenes))
            visits = (C.c_uint16*1089)()
            for x in (0, -1, -2):
                visits[16*33+x+16] = 1
            decisions = {}
            for capture, expected in ((77, (3,8,-2,-1,1)), (78, (3,8,-2,-1,1)), (79, (3,8,0,-2,1))):
                scene = scenes[capture]
                decision = Decision()
                self.assertEqual(1, self.lib.ng2_choose(C.byref(scene), -2, 0, visits, 1089, None, C.byref(decision)))
                decisions[capture] = decision
                self.assertEqual(expected, tuple(getattr(decision, field) for field, _ in Decision._fields_))
                reference = nav.choose(references[capture], (-2,0), {(x,0):1 for x in (0,-1,-2)})
                self.assertEqual(('up', 'observed_floor_vantage', expected[2:4]),
                                 (reference['direction'], reference['reason'], reference['target']))
            self.assertEqual(bytes(scenes[78].protected_cells), bytes(scenes[79].protected_cells))
            self.assertEqual([i for i,k in enumerate(scenes[78].tiles) if k == 2],
                             [i for i,k in enumerate(scenes[79].tiles) if k == 2])
            for a,b in manifest['motion_pairs']:
                before, after = scenes[a], scenes[b]
                old = nav._motion_view(bytes(before.signature))[0]
                new = nav._motion_view(bytes(after.signature))[0]
                expected_scores = nav._pillow_motion_scores(old, new)
                actual = (C.c_double*73)()
                self.lib.ng2_test_scores(bytes(before.signature), bytes(after.signature), actual)
                for value, (expected, _, _) in zip(actual, expected_scores):
                    self.assertAlmostEqual(expected, value, places=12)
                for direction in nav.DIRECTIONS:
                    motion = Motion()
                    self.assertEqual(1, self.lib.ng2_motion(C.byref(before), C.byref(after), DIRS[direction], C.byref(motion)))
                    with patch.object(motion_stats, 'scores', side_effect=lambda *_: list(expected_scores)):
                        expected = nav.motion(references[a], references[b], direction)
                    self.assertEqual(MOTIONS[expected], motion.kind)
                if (a,b) == (78,79):
                    motion = Motion()
                    self.assertEqual(1, self.lib.ng2_motion(C.byref(before), C.byref(after), 3, C.byref(motion)))
                    self.assertEqual((2,0,0), (motion.kind, motion.dx, motion.dy))
        finally:
            NativePerceptionTests.tearDownClass()


    def test_required_test052_startup_flickers_and_strict_parity(self):
        """Received stationary images; original phase/controller clock is not reconstructed."""
        from test_native_perception import NativePerceptionTests
        manifest = json.loads((ROOT/'tests/test053-fixtures.json').read_text())
        self.assertEqual(('ngg2-test053-fixtures-v1', 17), (manifest['schema'], manifest['count']))
        self.assertEqual('237952c07a388101cbf73ee204991891c45f91f6030fbb399405eb19a3924650',
                         manifest['source_zip_sha256'])
        self.assertEqual(12, len({entry['sha256'] for entry in manifest['images']}))
        first = 'c934567d1600449e8ede6529b3c78150'
        second = '388744e136a944669dd0cae1c2f86a9b'
        scenes, references = {}, {}
        NativePerceptionTests.setUpClass()
        try:
            perception = NativePerceptionTests()
            with patch.object(native_scan, '_native', None), patch.object(navigation_stats, '_native', None), \
                    patch.object(motion_stats, '_native', None):
                for filename, entry, path in required_profile_fixtures():
                    if filename != 'test053-fixtures.json':
                        continue
                    run = path.parent.parent.name.removeprefix('native-')
                    with Image.open(path) as source:
                        image = source.convert('RGB')
                    analyzed = perception.assert_reference(image)
                    self.assertEqual((entry['state'], entry['goods']), (analyzed.state, analyzed.goods))
                    self.assertEqual(entry['bytes'], path.stat().st_size)
                    scenes[run, entry['capture_id']] = Scene.from_buffer_copy(bytes(analyzed))
                    if analyzed.state == 2:
                        references[run, entry['capture_id']] = nav.scan(image)
                self.assertEqual(17, len(scenes))
                visits = (C.c_uint16*1089)();visits[16*33+16] = 1
                expected = {(first, capture): (1,8,-4,-1,1) for capture in (8,34,35,36,37)}
                expected.update({(second,8):(1,8,-4,1,1), (second,38):(1,8,-3,1,1)})
                for key, fields in expected.items():
                    scene = scenes[key]
                    self.assertEqual(0, sum(scene.protected_cells))
                    choices = []
                    for library in self.libraries.values():
                        result = Decision()
                        self.assertEqual(1, library.ng2_choose(C.byref(scene),0,0,visits,1089,None,C.byref(result)))
                        choices.append(bytes(result))
                        self.assertEqual(fields, tuple(getattr(result, field) for field,_ in Decision._fields_))
                    self.assertEqual(choices[0], choices[1])
                    reference = nav.choose(references[key], (0,0), {(0,0):1})
                    self.assertEqual(('left','observed_floor_vantage',fields[2:4]),
                                     (reference['direction'],reference['reason'],reference['target']))
                for run, pairs in manifest['motion_pairs_by_run'].items():
                    for a,b in pairs:
                        before, after = scenes[run,a], scenes[run,b]
                        self.assertEqual(bytes(before.protected_cells),bytes(after.protected_cells))
                        self.assertEqual([i for i,k in enumerate(before.tiles) if k == 2],
                                         [i for i,k in enumerate(after.tiles) if k == 2])
                        scores = []
                        expected_scores = nav._pillow_motion_scores(nav._motion_view(bytes(before.signature))[0],
                                                                   nav._motion_view(bytes(after.signature))[0])
                        for library in self.libraries.values():
                            values = (C.c_double*73)()
                            library.ng2_test_scores(bytes(before.signature),bytes(after.signature),values)
                            scores.append(bytes(values))
                            for value,(score,_,_) in zip(values,expected_scores):
                                self.assertAlmostEqual(score,value,places=12)
                            motion = Motion()
                            self.assertEqual(1,library.ng2_motion(C.byref(before),C.byref(after),1,C.byref(motion)))
                            self.assertEqual((2,0,0),(motion.kind,motion.dx,motion.dy))
                        self.assertEqual(scores[0],scores[1])
                        self.assertEqual('blocked',nav.motion(references[run,a],references[run,b],'left'))
                for a,b,x,y,old,new in ((35,36,3,-1,4,3),(36,37,3,-1,3,4)):
                    index=(y+5)*23+x+11
                    self.assertEqual((old,new),(scenes[first,a].tiles[index],scenes[first,b].tiles[index]))
                    self.assertEqual(1,sum(u!=v for u,v in zip(scenes[first,a].tiles,scenes[first,b].tiles)))
        finally:
            NativePerceptionTests.tearDownClass()


    def test_required_test053_reference_motion_and_strict_parity(self):
        """Known references to the same logical move; no threshold or future-frame inference."""
        from test_native_perception import NativePerceptionTests
        manifest=json.loads((ROOT/'tests/test054-fixtures.json').read_text())
        self.assertEqual(('ngg2-test054-fixtures-v1',17),(manifest['schema'],manifest['count']))
        self.assertEqual('ba851972e0d5b69e44fe6286913117f8c8156e4fd33a92ca449c0fdc89d2cfc2',manifest['source_zip_sha256'])
        scenes,references,entries={},{},{}
        NativePerceptionTests.setUpClass()
        try:
            perception=NativePerceptionTests()
            with patch.object(native_scan,'_native',None), patch.object(navigation_stats,'_native',None), \
                    patch.object(motion_stats,'_native',None):
                for filename,entry,path in required_profile_fixtures():
                    if filename!='test054-fixtures.json':continue
                    self.assertEqual(entry['bytes'],path.stat().st_size)
                    with Image.open(path) as raw:image=raw.convert('RGB')
                    analyzed=perception.assert_reference(image)
                    self.assertEqual((entry['state'],entry['goods']),(analyzed.state,analyzed.goods))
                    cid=entry['capture_id'];scenes[cid]=Scene.from_buffer_copy(bytes(analyzed));entries[cid]=entry
                    if analyzed.state==2:references[cid]=nav.scan(image)
                self.assertEqual(17,len(scenes))
                for a,b in manifest['motion_pairs']:
                    before,after=scenes[a],scenes[b]
                    expected_scores=nav._pillow_motion_scores(nav._motion_view(bytes(before.signature))[0],
                                                            nav._motion_view(bytes(after.signature))[0])
                    outputs=[]
                    for library in self.libraries.values():
                        scores=(C.c_double*73)();library.ng2_test_scores(bytes(before.signature),bytes(after.signature),scores)
                        outputs.append(bytes(scores))
                        for actual,(expected,_,_) in zip(scores,expected_scores):self.assertAlmostEqual(expected,actual,places=12)
                        for direction in nav.DIRECTIONS:
                            result=Motion();self.assertEqual(1,library.ng2_motion(C.byref(before),C.byref(after),DIRS[direction],C.byref(result)))
                            expected=manifest['expected_motion_by_pair'][f'{a},{b}'][direction]
                            self.assertEqual(MOTIONS[expected],result.kind)
                            with patch.object(motion_stats,'scores',side_effect=lambda *_:list(expected_scores)):
                                self.assertEqual(expected,nav.motion(references[a],references[b],direction))
                    self.assertEqual(outputs[0],outputs[1])
                visits=(C.c_uint16*1089)()
                for x,y in ((0,0),(-1,0),(-1,-1),(-1,-2)):visits[(y+16)*33+x+16]=1
                for cid in (99,101):
                    self.assertEqual(8,entries[cid]['completed_prefix']);self.assertTrue(entries[cid]['stable'])
                    self.assertEqual(0,sum(scenes[cid].protected_cells))
                    for library in self.libraries.values():
                        choice=Decision();self.assertEqual(1,library.ng2_choose(C.byref(scenes[cid]),-1,-2,visits,1089,None,C.byref(choice)))
                        self.assertEqual((3,7,0,-2,1),tuple(getattr(choice,k) for k,_ in Decision._fields_))
                self.assertEqual(bytes(scenes[99].protected_cells),bytes(scenes[101].protected_cells))
                self.assertEqual([i for i,t in enumerate(scenes[99].tiles) if t==2],
                                 [i for i,t in enumerate(scenes[101].tiles) if t==2])
                for cid in (110,111):
                    self.assertEqual(10,entries[cid]['completed_prefix']);self.assertTrue(entries[cid]['stable'])
                    for library in self.libraries.values():
                        primary,fallback=Motion(),Motion()
                        self.assertEqual(1,library.ng2_motion(C.byref(scenes[101]),C.byref(scenes[cid]),3,C.byref(primary)))
                        self.assertEqual(1,library.ng2_motion(C.byref(scenes[99]),C.byref(scenes[cid]),3,C.byref(fallback)))
                        self.assertEqual((0,0,0),(primary.kind,primary.dx,primary.dy))
                        self.assertEqual((1,0,-1),(fallback.kind,fallback.dx,fallback.dy))
                for a,b,offset in ((99,111,1),(101,111,1)):
                    before,after=scenes[a],scenes[b]
                    gold={(i%23-11,i//23-5) for i,t in enumerate(before.tiles) if t==2}
                    aftergold={(i%23-11,i//23-5) for i,t in enumerate(after.tiles) if t==2}
                    self.assertEqual({(x,y+offset) for x,y in gold},aftergold)
                    self.assertEqual((5,5),(before.tiles[2*23+11],after.tiles[3*23+11]))
        finally:NativePerceptionTests.tearDownClass()


if __name__ == '__main__':
    unittest.main()
