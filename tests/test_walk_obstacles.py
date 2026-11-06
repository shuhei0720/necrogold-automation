"""TEST027: 観測した扉・茶壁の開通と、移動数を混同しない。"""
from copy import deepcopy
import hashlib
import io
from contextlib import redirect_stdout
import os
from pathlib import Path
import unittest
from PIL import Image
from necroprobe import shop_navigation as nav, shop_walk as walk
from test_shop_navigation import terrain, tile, scene, shifted
from test_shop_walk import Fake, obs


class ObstacleTests(unittest.TestCase):
    def test_actual_test026_door_points_up_not_away(self):
        folder=os.environ.get('NECRO_TEST026_FRAMES')
        if not folder:self.skipTest('external TEST026 frames not supplied')
        p=Path(folder)/'run-105.jpg'
        self.assertEqual('8bf1c73ee667a736a60ec2975376f8984c1dcd4b665eba8a200a0bf8ddd80a10',hashlib.sha256(p.read_bytes()).hexdigest())
        with Image.open(p) as im:s=nav.scan(im.convert('RGB'))
        self.assertEqual('door',s.tiles.get((0,-1)))
        d=nav.choose(s);self.assertEqual('up',d['direction']);self.assertEqual('gate_single_probe',d['reason'])
        self.assertEqual(1,nav.burst_count(s,d))

    def test_dark_red_door_needs_texture_and_observed_gold_both_sides(self):
        for textured,gold,color,expected in ((True,True,(63,19,0),'door'),(False,True,(63,19,0),None),
                (True,False,(63,19,0),None),(True,True,(0,0,0),None),(True,True,(190,10,0),None)):
            with self.subTest(textured=textured,gold=gold,color=color):
                im=terrain()
                if gold:
                    tile(im,(-1,-1),(199,164,63));tile(im,(1,-1),(199,164,63))
                cell=Image.new('RGB',(25,25));cell.putdata([tuple(max(0,c+(3 if n%2 else -3)) for c in color) if textured else color for n in range(625)])
                im.paste(cell,(436,159))
                self.assertEqual(expected,nav.scan(im).tiles.get((0,-1)))

    def corridor(self,kind='dirt'):
        return scene({(0,0):'floor',(0,-1):kind,(0,-2):'floor',(0,-3):'door',(-1,-3):'gold',(1,-3):'gold'})

    def test_only_observed_dirt_on_route_to_gate_is_diggable(self):
        s=self.corridor();d=nav.choose(s)
        self.assertEqual('up',d['direction']);self.assertEqual('dig_single_probe',d['reason']);self.assertEqual(1,nav.burst_count(s,d))
        for blocked in ('stone','gold','item','unknown',None):
            s=self.corridor(blocked)
            self.assertIsNone(nav.choose(s)['direction'])
        for p in ((0,-1),(0,0)):
            s=self.corridor();s.protected.add(p);self.assertIsNone(nav.choose(s)['direction'])
        s=self.corridor();s.tiles.pop((0,-3));self.assertIsNone(nav.choose(s)['direction'])
        s=self.corridor();s.goods='visible';self.assertIsNone(nav.choose(s)['direction'])

    def test_weighted_route_prefers_open_floor_and_next_scan_enters_opened_cell(self):
        s=self.corridor();s.tiles[(0,-1)]='floor'
        d=nav.choose(s);self.assertEqual('up',d['direction']);self.assertEqual('approach_gate',d['reason'])
        s=self.corridor();s.tiles.update({(-1,0):'floor',(-1,-1):'floor',(-1,-2):'floor'})
        self.assertEqual('up',nav.choose(s)['direction']) # dig+move+step=3, detour=4

    def test_pair_uses_weighted_route_prefix_then_single_at_dirt(self):
        s=scene({(0,0):'floor',(0,-1):'floor',(0,-2):'floor',(0,-3):'dirt',
                 (0,-4):'floor',(0,-5):'door',(-1,-5):'gold',(1,-5):'gold'})
        d=nav.choose(s);self.assertEqual('up',d['direction']);self.assertEqual(2,nav.burst_count(s,d))
        s=self.corridor();self.assertEqual(1,nav.burst_count(s,nav.choose(s)))

    def test_real_scan_open_and_step_replans_without_crediting_dig_as_movement(self):
        clean=terrain()
        for pt in ((-3,-1),(-3,1)):tile(clean,pt,(199,164,63))
        tile(clean,(-3,0),(65,44,22))
        closed=clean.copy();tile(closed,(-1,0),(65,44,22))
        frames=[closed,clean,shifted(clean,36,0),clean]
        class Scanned(Fake):
            def __init__(self):
                super().__init__([]);self.source=iter(frames);self.n=0;self.observed=[];self.pre=[]
            def observe(self):
                im=next(self.source);self.n+=1
                self.last=obs();self.last['_extra']['scene']=nav.scan(im)
                if self.n==4:self.last['_extra']['scene'].goods='visible'
                self.observed.append(self.last);return self.last
            def goods(self,o):return o['_extra']['scene'].goods
            def choose(self,o):return nav.choose(o['_extra']['scene'],tuple(self.state['position']))
            def movement(self,a,b,d,expected_steps=1):return nav.motion(a['_extra']['scene'],b['_extra']['scene'],d,expected_steps)
            def perform(self,a,o,model=None,count=1):
                if a in walk.MOVE_POINTS:self.pre.append((o,self.state['moves_confirmed'],self.state['terrain_changes']))
                return super().perform(a,o,model,count)
        d=Scanned();output=io.StringIO()
        with redirect_stdout(output):walk.walk(d)
        self.assertIn('予定1入力',output.getvalue());self.assertIn('dig_single_probe',output.getvalue())
        self.assertEqual([(0,0),(0,1),(1,1)],[(m,t) for _,m,t in d.pre])
        self.assertIs(d.pre[1][0],d.observed[1]);self.assertIsNot(d.pre[0][0],d.pre[1][0])
        self.assertEqual(1,d.state['moves_confirmed']);self.assertEqual([-1,0],d.state['position'])
        self.assertTrue(d.state['goods_visible']);self.assertTrue(d.state['paused'])

    def test_zero_displacement_requires_input_cell_change_not_ack_or_other_cell(self):
        clean=terrain();closed=clean.copy();tile(closed,(1,0),(65,44,22))
        a,b=nav.scan(closed),nav.scan(clean)
        self.assertEqual('dirt',a.tiles[(1,0)])
        self.assertEqual('terrain_opened',nav.motion(a,b,'right'))
        self.assertEqual('blocked',nav.motion(a,a,'right'))
        self.assertEqual('blocked',nav.motion(a,b,'left'))
        self.assertEqual('blocked',nav.motion(a,b,'right',expected_steps=2))
        for kind in ('gold','stone',None):
            c=deepcopy(a);c.tiles[(1,0)]=kind
            self.assertEqual('blocked',nav.motion(c,b,'right'))
        c=deepcopy(b);c.protected.add((1,0))
        self.assertEqual('blocked',nav.motion(a,c,'right'))

    def test_walk_open_then_move_counts_input_but_not_displacement(self):
        d=Fake([obs(),obs(),obs(),obs('visible')],['terrain_opened','moved'])
        walk.walk(d)
        self.assertEqual(1,d.state['terrain_changes']);self.assertEqual(1,d.state['moves_confirmed'])
        self.assertEqual(0,d.state['door_changes']);self.assertTrue(d.state['goods_visible']);self.assertTrue(d.state['paused'])
        self.assertEqual(['resume','left','left','left','pause'],d.sent)

if __name__=='__main__':unittest.main()
