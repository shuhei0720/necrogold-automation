"""TEST030: 白いゾーン/フロア文字を、重なる赤いハートと分けて判定。"""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image,ImageChops
from necroprobe import gold_scan as gold,shop_walk as walk
import test_shop_walk as old
from test_gold_scan import floor,fixture,FIXTURES

COLORS=((255,70,70),(60,255,60),(90,90,255))
FOOTER=(752,396,856,414)
ZONE=(791,399,804,414)
FLOOR=(842,399,855,414)


def tinted(image,color,background=False):
    result=image.copy();mask=image.crop(FOOTER).convert('L').point([0]*90+[255]*166)
    if background:mask=ImageChops.invert(mask)
    crop=image.crop(FOOTER);crop.paste(color,(0,0,crop.width,crop.height),mask);result.paste(crop,FOOTER[:2])
    return result


def actual(name,digest):
    folder=os.environ.get('NECRO_TEST029_FRAMES')
    if not folder:raise unittest.SkipTest('external TEST029 frames not supplied')
    p=Path(folder)/name
    if hashlib.sha256(p.read_bytes()).hexdigest()!=digest:raise AssertionError('TEST029 evidence hash mismatch')
    with Image.open(p) as im:return im.convert('RGB')


class FooterStateTests(unittest.TestCase):
    def test_actual_state_scene_movement_and_next_door_input(self):
        images=[actual(name,sha) for name,sha in (
            ('run-099.jpg','a392c769f8919cd134f0884e6d9b7e0f132d45923a5179face477f4bf74d1a2c'),
            ('run-104.jpg','bd96403e42533bcefad5819dc711794ab5ef0700117b4ef4d9f48c716bf2d114'))]
        self.assertFalse(gold._matches(images[1].convert('L'),'zone_one'))
        with tempfile.TemporaryDirectory() as folder:
            d,now=old.SyncDeadlineTests.build(self,folder);frames=[]
            with patch.object(Image.Image,'resize',side_effect=AssertionError('resize')),patch.object(Image.Image,'rotate',side_effect=AssertionError('rotate')):
                for image in images:
                    frame=gold.analyze_image(image);frame['_extra']=d.analyze_frame(image,frame);frame['_captured']=now[0];frames.append(frame)
                self.assertEqual(['floor','floor'],[f['state'] for f in frames])
                self.assertTrue(all(d.scene(f) is not None for f in frames))
                self.assertEqual('moved',d.movement(*frames,'up'))
                decision=d.choose(frames[-1]);self.assertEqual('up',decision['direction']);self.assertEqual('gate_single_probe',decision['reason'])
                self.assertEqual(2,d.burst_count(frames[-1],decision,16))  # TEST033: open + enter

    def test_bright_colored_background_does_not_erase_white_footer(self):
        for color in COLORS:
            image=tinted(floor(),color,background=True)
            self.assertGreaterEqual(Image.new('RGB',(1,1),color).convert('L').getpixel((0,0)),90)
            self.assertFalse(gold._matches(image.convert('L'),'zone_one'))
            self.assertEqual('floor',gold.analyze_image(image)['state'])

    def test_colored_fake_glyphs_never_authorize_floor(self):
        for color in COLORS:
            image=tinted(floor(),color)
            self.assertTrue(gold._matches(image.convert('L'),'zone_one'))
            self.assertTrue(gold._matches(image.convert('L'),'floor_one'))
            self.assertEqual('unknown',gold.analyze_image(image)['state'])

    def test_missing_wrong_or_obscured_digits_stay_unknown(self):
        for box in (ZONE,FLOOR,FOOTER):
            for color in ((0,0,0),*COLORS,(160,160,160)):
                image=tinted(floor(),COLORS[0],background=True);image.paste(color,box)
                self.assertEqual('unknown',gold.analyze_image(image)['state'])
            # The wrong neutral symbol keeps approximately the same occupied area.
            image=tinted(floor(),COLORS[0],background=True)
            glyph=floor().crop(box);image.paste(glyph.transpose(Image.ROTATE_180),box[:2])
            self.assertEqual('unknown',gold.analyze_image(image)['state'])

    def test_other_state_gates_and_full_union_are_unchanged(self):
        base=tinted(floor(),COLORS[0],background=True)
        for fault in ('icon','death','neutral_background'):
            image=base.copy()
            if fault=='icon':image.paste(0,FIXTURES['icon'][0])
            elif fault=='death':fixture(image,'death')
            else:image=tinted(floor(),(160,160,160),background=True)
            self.assertEqual('unknown',gold.analyze_image(image)['state'])
        fixture(base,'continue');self.assertEqual('pause',gold.analyze_image(base)['state'])
        self.assertEqual('unknown',gold.analyze_image(Image.new('RGB',(414,896)))['state'])
        for color in ((89,89,89),(90,90,90),(200,100,100),(202,100,100)):
            image=tinted(floor(),color)
            self.assertEqual('floor' if color in ((90,90,90),(200,100,100)) else 'unknown',gold.analyze_image(image)['state'])

    def test_final_pause_uses_actual_footer_and_never_retries(self):
        image=actual('run-104.jpg','bd96403e42533bcefad5819dc711794ab5ef0700117b4ef4d9f48c716bf2d114')
        for valid in (True,False):
            with tempfile.TemporaryDirectory() as folder:
                d,now=old.SyncDeadlineTests.build(self,folder)
                im=image.copy()
                if not valid:im.paste(0,ZONE)
                frame=gold.analyze_image(im);frame.update(_captured=now[0],_raw=b'x',_sha='a'*64);d.last=frame
                pause=Image.new('RGB',gold.SIZE);fixture(pause,'continue');paused=gold.analyze_image(pause);paused.update(_captured=now[0],_raw=b'p',_sha='b'*64)
                sent=[]
                def perform(action,obs,model=None,count=1):
                    sent.append(action);d.state['actions'].append({'action':action})
                with patch.object(d,'checkpoint'),patch.object(d,'save'),patch.object(d,'perform',side_effect=perform),patch.object(d,'observe',return_value=paused) as observe:
                    d.finish('movement_unconfirmed',frame);d.finish('movement_unconfirmed',frame)
                self.assertEqual(['pause'] if valid else [],sent)
                self.assertEqual(1 if valid else 0,observe.call_count)
                self.assertEqual(valid,d.state['paused'])

    def test_pause_ack_then_capture_failure_is_not_retried(self):
        image=actual('run-104.jpg','bd96403e42533bcefad5819dc711794ab5ef0700117b4ef4d9f48c716bf2d114')
        with tempfile.TemporaryDirectory() as folder:
            d,now=old.SyncDeadlineTests.build(self,folder)
            frame=gold.analyze_image(image);frame.update(_captured=now[0],_raw=b'x',_sha='a'*64);d.last=frame
            sent=[]
            def ack(action,obs,model=None,count=1):
                sent.append(action);d.state['actions'].append({'action':action,'outcome':'acknowledged'})
            with patch.object(d,'checkpoint'),patch.object(d,'save'),patch.object(d,'perform',side_effect=ack),patch.object(d,'observe',side_effect=walk.ProbeError('connection_error')) as observe:
                with self.assertRaises(walk.ProbeError):d.finish('movement_unconfirmed',frame)
                d.finish('movement_unconfirmed',frame)
            self.assertEqual(['pause'],sent);self.assertEqual(1,observe.call_count)
            self.assertFalse(d.state['paused'])  # ACK alone is not observed pause success.

if __name__=='__main__':unittest.main()
