"""TEST028: 鉄扉背景でもゲーム状態を保ち、同点経路の横行き過ぎを減らす。"""
import base64
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
import zlib
from PIL import Image,ImageDraw
from necroprobe import gold_scan as gold,shop_navigation as nav
from test_gold_scan import floor,fixture,FIXTURES
from test_shop_navigation import scene
import test_shop_walk as old

class ApproachTests(unittest.TestCase):
    build=old.SyncDeadlineTests.build
    def frame(self,name,sha):
        folder=os.environ.get('NECRO_TEST027_FRAMES')
        if not folder:self.skipTest('external TEST027 evidence not supplied')
        p=Path(folder)/name;self.assertEqual(sha,hashlib.sha256(p.read_bytes()).hexdigest())
        with Image.open(p) as im:return im.convert('RGB')
    def test_actual_right_step_survives_state_scene_motion_pipeline(self):
        frames=[self.frame(n,h) for n,h in (
            ('run-101.jpg','a811a5b6b84036b4673cfa3efc09ebc2c9ad025b9894dc95e287f82500e05cae'),
            ('run-103.jpg','1c85b13520fc35ded09f008c519da1c032ec45e060338b7e8d7d054c7fd22f07'))]
        with tempfile.TemporaryDirectory() as folder:
            d,now=self.build(folder);observations=[]
            for im in frames:
                o=gold.analyze_image(im);o['_extra']=d.analyze_frame(im,o);o['_captured']=now[0]
                observations.append(o)
            self.assertEqual(['floor','floor'],[o['state'] for o in observations])
            self.assertTrue(all(d.scene(o) is not None for o in observations))
            self.assertEqual('moved',d.movement(*observations,'right'))
            self.assertEqual('up',d.choose(observations[-1])['direction'])
            self.assertEqual(2,d.burst_count(observations[-1],d.choose(observations[-1]),16))
    def test_actual_first_route_aligns_with_observed_corridor(self):
        im=self.frame('run-001.jpg','ee6bf7da75b6d95f68f0087ccf7a7979841646fb3933067d6cc76ec928601921')
        s=nav.scan(im);d=nav.choose(s)
        self.assertEqual((-1,-3),d['target']);self.assertEqual('left',d['direction']);self.assertEqual(1,nav.burst_count(s,d))
    def test_neutral_background_needs_both_bars_and_all_floor_gates(self):
        box,compressed=FIXTURES['icon'];mask=Image.frombytes('1',(36,36),zlib.decompress(base64.b64decode(compressed)))
        im=floor();crop=Image.new('RGB',(36,36),(70,70,70));crop.paste((150,150,150),(0,0,36,36),mask);im.paste(crop,box[:2])
        self.assertEqual('floor',gold.analyze_image(im)['state'])
        for fault in ('missing_left','missing_right','no_bars','bright_rectangle','wrong_columns','footer','zone','floor','death','coloured_bars'):
            with self.subTest(fault=fault):
                bad=im.copy();draw=ImageDraw.Draw(bad)
                if fault=='missing_left':draw.rectangle((429,6,446,41),fill=(70,70,70))
                if fault=='missing_right':draw.rectangle((447,6,464,41),fill=(70,70,70))
                if fault=='no_bars':bad.paste((70,70,70),box)
                if fault=='bright_rectangle':bad.paste((150,150,150),box)
                if fault=='wrong_columns':
                    bad.paste((70,70,70),box);draw.rectangle((429,6,432,41),fill=(180,180,180));draw.rectangle((461,6,464,41),fill=(180,180,180))
                if fault in ('footer','zone','floor'):
                    bad.paste(0,{'footer':(752,396,856,414),'zone':(791,399,804,414),'floor':(842,399,855,414)}[fault])
                if fault=='death':fixture(bad,'death')
                if fault=='coloured_bars':
                    c=Image.new('RGB',(36,36),(70,70,70));c.paste((210,170,30),(0,0,36,36),mask);bad.paste(c,box[:2])
                self.assertEqual('unknown',gold.analyze_image(bad)['state'])
        fixture(im,'continue');self.assertEqual('pause',gold.analyze_image(im)['state'])
    def base_tiles(self):
        tiles={(x,y):'floor' for x in (0,-1,-2) for y in (0,-1,-2,-3)}
        del tiles[(-2,-3)];tiles[(-2,-5)]='gold';return tiles
    def test_equal_score_prefers_axis_progress_all_rotations(self):
        def rotate(p,n):
            for _ in range(n):p=(-p[1],p[0])
            return p
        for rotation in range(4):
            with self.subTest(rotation=rotation):
                s=scene({rotate(p,rotation):kind for p,kind in self.base_tiles().items()})
                self.assertEqual(rotate((-1,-3),rotation),nav.choose(s)['target'])
    def test_diagonal_prefers_vertical_and_nearest_gold_tie_is_deterministic(self):
        tiles={(x,y):'floor' for x in (0,-1,-2,-3) for y in (0,-1,-2,-3) if x>=-1 or y>=-1}
        tiles[(-4,-4)]='gold'
        self.assertEqual((-1,-3),nav.choose(scene(tiles))['target'])
        tiles=self.base_tiles();tiles[(5,-2)]='gold'
        self.assertEqual((-1,-3),nav.choose(scene(tiles))['target'])

    def test_primary_score_visits_and_observed_floor_still_control(self):
        s=scene(self.base_tiles());s.tiles[(-2,-3)]='floor'
        self.assertEqual((-2,-3),nav.choose(s)['target'])
        s=scene(self.base_tiles());self.assertEqual((-2,-2),nav.choose(s,visits={(-1,-3):1})['target'])
        for blocked in ('unknown','stone','dirt','item'):
            s=scene(self.base_tiles());s.tiles[(-1,-3)]=blocked
            self.assertNotEqual((-1,-3),nav.choose(s)['target'])
        s=scene(self.base_tiles());s.protected.add((-1,-3));self.assertNotEqual((-1,-3),nav.choose(s)['target'])
        s=scene(self.base_tiles(),goods='visible');self.assertIsNone(nav.choose(s)['direction'])

if __name__=='__main__':unittest.main()
