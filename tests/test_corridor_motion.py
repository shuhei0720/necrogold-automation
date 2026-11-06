"""TEST031: 狭い入口の地形を使い、支持点の最低数を下げずに歩行を確認。"""
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import random
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image,ImageChops
from necroprobe import shop_navigation as nav,shop_walk as walk,gold_scan as gold
import test_shop_walk as old


def frames():
    folder=os.environ.get('NECRO_TEST030_FRAMES')
    if not folder:raise unittest.SkipTest('external TEST030 frames not supplied')
    result=[]
    for name,digest in (
        ('run-104.jpg','c5c7f8f4c0df111b2181840b34ef1ce11360141a00a57c99c3126f1a5f315bf2'),
        ('run-105.jpg','40f70fa5cce6b34adc2e9870eba63edb52107da7671d9470e9516e797b1d5866')):
        p=Path(folder)/name
        if hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise AssertionError('TEST030 evidence hash mismatch')
        with Image.open(p) as im:result.append(im.convert('RGB'))
    return result


def old_support(a,b,sx,sy):
    _,at,ap=nav._motion_view(a.signature);_,bt,bp=nav._motion_view(b.signature)
    return nav._texture_match(at,bt,ap,bp,sx,sy)[0]


def observation(scene):
    result=old.obs();result['_extra']['scene']=scene;return result


class CorridorTests(unittest.TestCase):
    def test_actual_last_step_then_one_gate_probe_through_driver(self):
        with tempfile.TemporaryDirectory() as folder:
            d,now=old.SyncDeadlineTests.build(self,folder);observations=[]
            for im in frames():
                o=gold.analyze_image(im);o['_extra']=d.analyze_frame(im,o);observations.append(o)
            a,b=[d.scene(o) for o in observations]
            self.assertEqual(228,old_support(a,b,0,9))
            self.assertEqual('moved',d.movement(*observations,'up'))
            self.assertIsNone(d.entrance)
            decision=d.choose(observations[-1]);self.assertEqual('up',decision['direction'])
            self.assertEqual('gate_single_probe',decision['reason']);self.assertEqual(1,d.burst_count(observations[-1],decision,16))
            self.assertEqual('partial',nav.motion(a,b,'up',2))
            self.assertEqual('unexpected',nav.motion(a,b,'down'))

    def test_sparse_stationary_frame_opening_and_entry_have_distinct_results(self):
        # Simulate scan outputs after opening/entry; these are not observed device opening images.
        closed=nav.scan(frames()[1]);self.assertEqual(273,old_support(closed,closed,0,0))
        self.assertEqual('blocked',nav.motion(closed,closed,'up'))
        opened=deepcopy(closed);opened.tiles[(0,-1)]='floor'
        # Newly revealed gold is permitted only when it does not add a competing alignment.
        opened.gold.add((5,-3));opened.tiles[(5,-3)]='gold'
        self.assertEqual('door_opened',nav.motion(closed,opened,'up'))
        self.assertEqual('blocked',nav.motion(closed,opened,'down'))
        # Entry uses constructed narrow-corridor pixels, not a claimed device frame.
        # The actual closed-door image shifted wholesale has insufficient coarse contrast.
        raw=Image.new('L',(224,104),40);rng=random.Random(31033)
        for y in range(20,79):
            for x in range(90,110):raw.putpixel((x,y),rng.randrange(20,90))
        entry_before=deepcopy(opened);entry_before.signature=raw.tobytes()
        entered=deepcopy(entry_before)
        entered.tiles={(x,y+1):kind for (x,y),kind in opened.tiles.items()};entered.tiles[(0,0)]='floor'
        entered.gold={(x,y+1) for x,y in opened.gold}
        shifted=Image.new('L',raw.size);shifted.paste(raw,(0,9));entered.signature=shifted.tobytes()
        self.assertLess(old_support(entry_before,entered,0,9),300)
        with tempfile.TemporaryDirectory() as folder:
            d,now=old.SyncDeadlineTests.build(self,folder)
            self.assertEqual('door_opened',d.movement(observation(closed),observation(opened),'up'))
            self.assertIsNone(d.entrance);self.assertEqual([0,0],d.state['position'])
            self.assertEqual('moved',d.movement(observation(entry_before),observation(entered),'up'))
            self.assertEqual({'gate':(0,-1),'direction':'up'},d.entrance)
            self.assertEqual([0,0],d.state['position'])  # Position credit belongs to walk, once.
            self.assertEqual('blocked',nav.motion(opened,opened,'up'))
        d=old.Fake([old.obs(),old.obs(),old.obs(),old.obs('visible')],['door_opened','moved'])
        walk.walk(d);self.assertEqual(1,d.state['door_changes']);self.assertEqual(1,d.state['moves_confirmed'])

    def test_correspondence_must_be_unique_and_image_direction_independent(self):
        a,b=[nav.scan(im) for im in frames()]
        for fault in ('missing_gold','missing_gate','stationary_landmarks','duplicate_alignment','floor_to_door'):
            x,y=deepcopy(a),deepcopy(b)
            if fault=='missing_gold':y.gold.pop()
            if fault=='missing_gate':y.tiles.pop((0,-1))
            if fault=='stationary_landmarks':y.gold=x.gold.copy();y.tiles=x.tiles.copy()
            if fault=='duplicate_alignment':
                for p in x.gold:y.gold.add(p);y.tiles[p]='gold'
                y.tiles[(0,-2)]='door'
            if fault=='floor_to_door':x.tiles[(0,-2)]='floor'
            self.assertEqual('unknown',nav.motion(x,y,'up'),fault)
        # Metadata alone cannot make a stationary frame count as movement.
        y=deepcopy(b);y.signature=a.signature
        self.assertNotIn(nav.motion(a,y,'up'),('moved','partial'))

    def test_actor_and_instruction_changes_do_not_supply_expanded_votes(self):
        rng=random.Random(31031);base=Image.frombytes('L',(224,104),bytes(rng.randrange(20,90) for _ in range(224*104)))
        changed=base.copy()
        for box in ((104,44,121,60),(116,39,153,79)):
            changed.paste(255,box)
        views=[nav._motion_view(im.tobytes(),full_texture=True) for im in (base,changed)]
        self.assertEqual(nav._texture_mask(views[0][1],True).tobytes(),nav._texture_mask(views[1][1],True).tobytes())
        valid=nav._texture_mask(Image.new('L',(224,104),255),True)
        self.assertEqual(ImageChops.darker(views[0][2],valid).tobytes(),ImageChops.darker(views[1][2],valid).tobytes())
        actor_only=Image.new('L',(224,104),40)
        for box in ((104,44,121,60),(116,39,153,79)):
            patch_image=Image.new('L',(box[2]-box[0],box[3]-box[1]));patch_image.putdata([rng.randrange(0,256) for _ in range(patch_image.width*patch_image.height)])
            actor_only.paste(patch_image,box[:2])
        _,texture,_=nav._motion_view(actor_only.tobytes(),full_texture=True)
        self.assertEqual(0,nav._texture_mask(texture,True).histogram()[255])

    def test_expanded_evidence_minimum_and_all_candidate_competition(self):
        a,b=[nav.scan(im) for im in frames()]
        candidates=[(.2,0,9),(.9,0,0),(1.,9,0)]
        dummy=Image.new('L',(224,104));row=lambda support,bad:(support,bad,dummy,(0,0,224,104))
        def evaluate(support=400,bad=20,competitor_bad=80,far_count=299,far_bad=0):
            with patch.object(nav,'_texture_match',side_effect=[row(support,bad),row(400,competitor_bad),row(far_count,far_bad)]):
                return nav._corridor_motion(a,b,candidates,dummy,dummy,dummy,dummy)
        self.assertTrue(evaluate())
        self.assertFalse(evaluate(support=299,bad=0))
        self.assertTrue(evaluate(support=300,bad=0,competitor_bad=100))
        self.assertFalse(evaluate(bad=21));self.assertFalse(evaluate(competitor_bad=79))
        self.assertFalse(evaluate(far_count=300,far_bad=0))

    def test_original_coarse_thresholds_gate_additional_confirmation(self):
        from necroprobe import motion_stats
        a,b=[nav.scan(im) for im in frames()]
        for best,runner,allowed in ((.45,.53,True),(.450001,.6,False),(.2,.279999,False),(float('inf'),float('inf'),False)):
            scores=[(best,0,9),(runner,0,0)]
            with patch.object(motion_stats,'scores',return_value=scores),patch.object(nav,'_structural_motion',return_value=False),patch.object(nav,'_corridor_motion',return_value=True) as extra:
                self.assertEqual('moved' if allowed else 'unknown',nav.motion(a,b,'up'))
                self.assertEqual(int(allowed),extra.call_count)

    def test_periodic_texture_ties_cannot_pass_unique_geometry(self):
        a,b=[nav.scan(im) for im in frames()]
        # Actual repeated texture, with deliberately favorable independent coarse ranking.
        rng=random.Random(31032);row=bytes(rng.randrange(20,90) for _ in range(224*9))
        repeated=(row*12)[:224*104];a.signature=b.signature=repeated
        scores=[(.2,0,9),(.9,0,0)]+[(.9,dx*k,dy*k) for k in range(1,19) for dx,dy in nav.DIRECTIONS.values() if (dx*k,dy*k)!=(0,9)]
        from necroprobe import motion_stats
        # Force old low-support branch; expanded actual textures match at zero and nine.
        original=nav._texture_mask
        def mask(texture,expanded=False):return original(texture,True) if expanded else Image.new('L',(224,104))
        with patch.object(motion_stats,'scores',return_value=scores),patch.object(nav,'_texture_mask',side_effect=mask):
            self.assertEqual('unknown',nav.motion(a,b,'up'))

if __name__=='__main__':unittest.main()
