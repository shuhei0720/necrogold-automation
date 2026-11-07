"""TEST029: 扉前の実変位と、通過した入口へ戻らない商品接近。"""
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image, ImageChops
from necroprobe import shop_navigation as nav, shop_walk as walk, gold_scan
import test_shop_walk as old
from test_shop_navigation import scene, terrain, tile, shifted


def evidence(name, digest):
    folder = os.environ.get('NECRO_TEST028_FRAMES')
    if not folder:
        raise unittest.SkipTest('external TEST028 images not supplied')
    p = Path(folder) / name
    if hashlib.sha256(p.read_bytes()).hexdigest() != digest:
        raise AssertionError('TEST028 evidence hash mismatch')
    with Image.open(p) as im:
        return im.convert('RGB')


def actual_pair():
    return [nav.scan(evidence(n, h)) for n, h in (
        ('run-099.jpg', 'bb78c35d3a8dfc69e152bec01d2d59132cd2551536cf1f69a2294cc91f701d31'),
        ('run-103.jpg', 'db1568d085477923fdb34d663826ce98cbce0922ef9a526e42a80d76dd78faa7'))]


def corridor(direction, player=0, opened=True):
    dx, dy = nav.DIRECTIONS[direction]
    tiles = {((i-player)*dx, (i-player)*dy): 'floor' for i in range(-2, 6)}
    gate = ((1-player)*dx, (1-player)*dy)
    tiles[gate] = 'floor' if opened else 'door'
    for side in (-1, 1):
        tiles[(gate[0]-side*dy, gate[1]+side*dx)] = 'gold'
    return scene(tiles)


class DoorwayTests(unittest.TestCase):
    def test_actual_two_steps_continue_with_one_open_door_input(self):
        a, b = actual_pair()
        scores = sorted(nav._pillow_motion_scores(nav._motion_view(a.signature)[0], nav._motion_view(b.signature)[0]))
        self.assertGreater(scores[0][0], .45)  # This is the new fallback, not old fast path.
        self.assertEqual((18, 0), scores[0][1:])
        self.assertEqual('moved', nav.motion(a, b, 'left', 2))
        self.assertEqual('unexpected', nav.motion(a, b, 'right', 2))
        self.assertEqual('unexpected', nav.motion(a, b, 'left', 1))
        decision = nav.choose(b)
        self.assertEqual(('left', 'gate_single_probe', (-1, 0)),
                         (decision['direction'], decision['reason'], decision['target']))
        self.assertEqual(1, nav.burst_count(b, decision))

    def test_actual_fallback_needs_matching_gold_and_closed_gate(self):
        a, b = actual_pair()
        for fault in ('no_gold', 'one_gold', 'extra_gold', 'missing_gold', 'stationary_gold', 'no_door', 'open_door'):
            with self.subTest(fault=fault):
                x, y = deepcopy(a), deepcopy(b)
                if fault == 'no_gold': x.gold.clear(); y.gold.clear()
                if fault == 'one_gold': x.gold = {(-3,-1)}; y.gold = {(-1,-1)}
                if fault == 'extra_gold': y.gold.add((5,4))
                if fault == 'missing_gold': y.gold.pop()
                if fault == 'stationary_gold': y.gold = x.gold.copy()
                if fault == 'no_door': y.tiles.pop((-1,0))
                if fault == 'open_door': y.tiles[(-1,0)] = 'floor'
                self.assertEqual('unknown', nav.motion(x, y, 'left', 2))

    def test_moving_single_object_across_region_boundary_is_not_terrain(self):
        rng = random.Random(29029)
        values = [rng.randrange(-7, 8) for _ in range(40*30)]
        a, b = Image.new('L', (224,104), 100), Image.new('L', (224,104), 100)
        patch_a = Image.new('L',(40,30));patch_a.putdata([100+v for v in values])
        patch_b = Image.new('L',(40,30));patch_b.putdata([100+v*30//7 for v in values])
        a.paste(patch_a,(45,23));b.paste(patch_b,(63,23))
        s = [nav.Scene({}, set(), 'unknown', set(), im.tobytes()) for im in (a,b)]
        self.assertEqual('unknown', nav.motion(*s, 'left', 2))
        # Static shop landmarks cannot corroborate a translating foreground object.
        for obj in s:
            obj.gold = {(-3,-1),(-3,1)}
            obj.tiles = {(-3,-1):'gold',(-3,1):'gold',(-3,0):'door'}
        self.assertEqual('unknown', nav.motion(*s, 'left', 2))

    def test_passed_gate_is_not_revisited_all_four_directions(self):
        for direction, (dx,dy) in nav.DIRECTIONS.items():
            entrance = {'gate':(dx,dy), 'direction':direction}
            for player in (1,2,3):
                with self.subTest(direction=direction,player=player):
                    s = corridor(direction,player)
                    decision = nav.choose(s, (player*dx,player*dy), entrance=entrance)
                    self.assertEqual(direction, decision['direction'])
                    self.assertIn(nav.burst_count(s, decision, (player*dx,player*dy), entrance=entrance),(1,2))
                    target=decision['target']
                    self.assertGreater(target[0]*dx+target[1]*dy, 0)
            s = corridor(direction,1)
            s.tiles = {p:k for p,k in s.tiles.items() if p[0]*dx+p[1]*dy <= 0}
            self.assertIsNone(nav.choose(s,(dx,dy),entrance=entrance)['direction'])
            s=corridor(direction,1);s.protected.add((dx,dy))
            self.assertIsNone(nav.choose(s,(dx,dy),entrance=entrance)['direction'])
            s=corridor(direction,1);s.goods='visible'
            self.assertIsNone(nav.choose(s,(dx,dy),entrance=entrance)['direction'])

    def test_route_filter_retains_sideways_gate_boundaries_all_rotations(self):
        def rotate(point,n):
            x,y=point
            for _ in range(n):x,y=-y,x
            return x,y
        for rotation in range(4):
            tiles={(0,0):'floor',(0,1):'floor',(0,2):'floor',(0,3):'floor',(-1,2):'gold',(1,2):'gold'}
            s=scene({rotate(p,rotation):kind for p,kind in tiles.items()})
            inward=rotate((1,0),rotation)
            direction=next(name for name,delta in nav.DIRECTIONS.items() if delta==inward)
            entrance={'gate':rotate((-1,0),rotation),'direction':direction}
            decision=nav.choose(s,(0,0),entrance=entrance)
            self.assertEqual(rotate((0,1),rotation),decision['target'])
            self.assertEqual(1,nav.burst_count(s,decision,(0,0),entrance=entrance))

    def test_entry_memory_requires_visually_confirmed_open_gate_step(self):
        for direction,(dx,dy) in nav.DIRECTIONS.items():
            before,after=corridor(direction),corridor(direction,1)
            expected={'gate':(dx,dy),'direction':direction}
            self.assertEqual(expected,nav.entered_gate(before,after,direction,(0,0),1,'moved'))
            for outcome in ('door_opened','terrain_opened','blocked','partial','unknown','unexpected','tween'):
                self.assertIsNone(nav.entered_gate(before,after,direction,(0,0),1,outcome))
            self.assertIsNone(nav.entered_gate(before,after,direction,(0,0),2,'moved'))
            for source in (before,after):
                bad=deepcopy(source);bad.gold.clear();bad.tiles={p:k for p,k in bad.tiles.items() if k!='gold'}
                pair=(bad,after) if source is before else (before,bad)
                self.assertIsNone(nav.entered_gate(*pair,direction,(0,0),1,'moved'))
            closed=corridor(direction,opened=False)
            self.assertIsNone(nav.entered_gate(closed,after,direction,(0,0),1,'moved'))

    def test_driver_actual_movement_and_entry_context(self):
        with tempfile.TemporaryDirectory() as folder:
            d,clock=old.SyncDeadlineTests.build(self,folder)
            a,b=actual_pair()
            def observation(s):
                o=old.obs();o['_extra']['scene']=s;return o
            self.assertEqual('moved',d.movement(observation(a),observation(b),'left',2))
            self.assertIsNone(d.entrance)
            ground=terrain()
            for point in ((-1,-1),(-1,1)):tile(ground,point,(160,130,45))
            a=nav.scan(ground);b=nav.scan(shifted(ground,36,0))
            self.assertEqual('moved',d.movement(observation(a),observation(b),'left',1))
            self.assertEqual({'gate':(-1,0),'direction':'left'},d.entrance)
            d.state['position']=[-1,0]
            decision=d.choose(observation(b))
            self.assertEqual('left',decision['direction'])
            self.assertLess(decision['target'][0],0)

    def test_invalid_context_and_stale_outward_dispatch_are_rejected(self):
        for context in ({}, {'gate':(1,0),'direction':[]}, {'gate':(1,0),'direction':'side'},
                        {'gate':(True,0),'direction':'right'}, {'gate':(2,0),'direction':'right'}):
            with self.subTest(context=context):
                self.assertIsNone(nav.choose(corridor('right',1),(1,0),entrance=context)['direction'])
        with tempfile.TemporaryDirectory() as folder:
            d,clock=old.SyncDeadlineTests.build(self,folder)
            d.entrance={'gate':(-1,0),'direction':'left'};d.state['position']=[-1,0]
            d.last['_extra']['scene']=corridor('left',1)
            for count in (1,2):
                with self.assertRaises(walk.ProbeError) as caught:d.perform('right',d.last,{},count=count)
                self.assertEqual('method_not_allowed',caught.exception.code)
            self.assertEqual([],d.client.calls)
            self.assertEqual([],d.state['actions'])

    def test_open_enter_inside_unknown_then_goods_stops_all_four_directions(self):
        # Real scan/motion/planning; only transport, sync and eventual goods are simulated.
        for direction,(dx,dy) in nav.DIRECTIONS.items():
            with self.subTest(direction=direction):
                ground=terrain()
                for side in (-1,1):tile(ground,(dx-side*dy,dy+side*dx),(160,130,45))
                closed=ground.copy();tile(closed,(dx,dy),(65,44,22))
                frames=[closed,ground,shifted(ground,-36*dx,-36*dy),shifted(ground,-72*dx,-72*dy)]
                class ActualNavigation(old.Fake):
                    scene=walk.Driver.scene;goods=walk.Driver.goods;choose=walk.Driver.choose
                    movement=walk.Driver.movement;note_step=walk.Driver.note_step
                    track_observation=walk.Driver.track_observation
                    def __init__(self):
                        super().__init__([]);self.images_in=iter(frames);self.n=0
                        self.entrance=None;self.visits={(0,0):1};self.model=None;self.snapshots=[]
                    def observe(self):
                        self.n+=1;self.last=old.obs();self.last['_extra']['scene']=nav.scan(next(self.images_in))
                        return self.last
                    def synchronize(self,o):
                        if self.n==4:
                            # A fresh observation at this same position makes all goods visible.
                            o=deepcopy(o);o['_extra']['scene'].goods='visible';self.last=o
                        return o,{'period_ns':520_000_000}
                    def perform(self,action,o,model=None,count=1):
                        if action in walk.MOVE_POINTS:
                            self.snapshots.append((self.state['moves_confirmed'],self.state['door_changes'],deepcopy(self.entrance)))
                        return super().perform(action,o,model,count)
                d=ActualNavigation();walk.walk(d)
                self.assertEqual(['resume',direction,direction,direction,'pause'],d.sent)
                self.assertEqual([(0,0,None),(0,1,None)],d.snapshots[:2])
                self.assertEqual((1,1,{'gate':(dx,dy),'direction':direction}),d.snapshots[2])
                self.assertEqual(2,d.state['moves_confirmed']);self.assertEqual([2*dx,2*dy],d.state['position'])
                self.assertEqual(1,d.state['door_changes']);self.assertEqual(0,d.state['terrain_changes'])
                self.assertTrue(d.state['goods_visible']);self.assertTrue(d.state['paused'])

    def test_structural_fallback_confidence_and_competitor_boundaries(self):
        # Controlled matcher evidence isolates numerical gates from the real image regression.
        before=corridor('left',0,opened=False);after=corridor('left',1,opened=False)
        # corridor gate moves +1x when walking left; anchors are nonzero integer-tile shift.
        matched=Image.new('L',(224,104))
        matched.paste(255,(60,20,80,30));matched.paste(255,(139,40,159,50))
        candidates=[(.6,9,0),(.9,0,0),(1.,0,9)]
        def evaluate(support=400,bad=20,other_bad=80,region=matched):
            rows=[(support,bad,region,(0,0,224,104)),(400,other_bad,matched,(0,0,224,104)),(299,0,matched,(0,0,224,104))]
            with patch.object(nav,'_texture_match',side_effect=rows):
                return nav._structural_motion(before,after,candidates,None,None,None,None)
        self.assertTrue(evaluate())  # 95%, and exactly15percentage-point lead over static competitor.
        self.assertFalse(evaluate(bad=21))
        self.assertFalse(evaluate(other_bad=79))
        self.assertTrue(evaluate(support=300,bad=0,other_bad=100))
        self.assertFalse(evaluate(support=299,bad=0))
        only_top=Image.new('L',(224,104));only_top.paste(255,(60,20,100,30))
        self.assertFalse(evaluate(region=only_top))
        edge=only_top.copy();edge.paste(255,(139,40,149,50))
        self.assertTrue(evaluate(region=edge))
        edge.putpixel((139,40),0);self.assertFalse(evaluate(region=edge))
        # Even a weak intensity-ranked rival with sufficient ordinal support vetoes it.
        rows=[(400,20,matched,(0,0,224,104)),(400,100,matched,(0,0,224,104)),(300,0,matched,(0,0,224,104))]
        with patch.object(nav,'_texture_match',side_effect=rows):
            self.assertFalse(nav._structural_motion(before,after,candidates,None,None,None,None))

    def test_nonfinite_or_ambiguous_intensity_cannot_use_structural_fallback(self):
        a,b=actual_pair()
        from necroprobe import motion_stats
        for scores in ([(float('inf'),18,0),(float('inf'),0,0)],[(float('nan'),18,0),(1.,0,0)],
                       [(.5037,18,0),(.55,0,0)]):
            with patch.object(motion_stats,'scores',return_value=scores):
                self.assertEqual('unknown',nav.motion(a,b,'left',2))

if __name__=='__main__':unittest.main()
