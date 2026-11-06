"""TEST032: 商品名に重なるpause記号と、商品が部分表示の開扉後の継続。"""
import base64
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zlib
from PIL import Image, ImageChops
from necroprobe import gold_scan as gold, shop_navigation as nav, shop_walk as walk
import test_shop_walk as old
from test_gold_scan import floor, fixture, FIXTURES
from test_shop_navigation import shop_image, shifted
from test_walk_doorway import corridor


def actual(name, digest):
    folder = os.environ.get('NECRO_TEST031_FRAMES')
    if not folder: raise unittest.SkipTest('external TEST031 frames not supplied')
    path = Path(folder) / name
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise AssertionError('TEST031 evidence hash mismatch')
    with Image.open(path) as im: return im.convert('RGB')


def opened_image():
    return actual('run-106.jpg', '53f98fe50b898dbcaa9a950b88c5bb07f53b107cabae2b19461f4b1e4d324a92')


def reference():
    return Image.frombytes('1', (36, 36), zlib.decompress(base64.b64decode(FIXTURES['icon'][1]))).convert('L')


def labeled_floor(mask=None, color=(128,128,128)):
    result = floor()
    crop = Image.new('RGB', (36,36))
    crop.paste(color, (0,0,36,36), reference() if mask is None else mask)
    # Short white item-name strokes span both bars and the intervening background.
    for y in (5,14,23): crop.paste((255,255,255), (0,y,36,y+3))
    result.paste(crop, FIXTURES['icon'][0][:2])
    return result


class ShopLabelTests(unittest.TestCase):
    def test_actual_opening_keeps_partial_and_selects_single_entry(self):
        images = [actual('run-105.jpg','c729388a692f5f70de079ed36ee3be974ed3226c3f280e47b90cb1043e9fd798'), opened_image()]
        with tempfile.TemporaryDirectory() as folder:
            d, now = old.SyncDeadlineTests.build(self, folder)
            observations=[]
            with patch.object(Image.Image,'resize',side_effect=AssertionError('resize')), patch.object(Image.Image,'rotate',side_effect=AssertionError('rotate')):
                for image in images:
                    obs=gold.analyze_image(image); obs['_extra']=d.analyze_frame(image,obs); observations.append(obs)
            self.assertEqual(['floor','floor'], [o['state'] for o in observations])
            self.assertEqual('partial', d.goods(observations[-1]))
            self.assertEqual('door_opened', d.movement(*observations,'up'))
            self.assertEqual(0,d.state['moves_confirmed']);self.assertIsNone(d.entrance)
            decision=d.choose(observations[-1]);self.assertEqual('up',decision['direction'])
            self.assertEqual('gate_single_probe',decision['reason'])
            self.assertEqual(1,d.burst_count(observations[-1],decision,16))

    def test_short_text_overlap_preserves_bars_and_all_state_guards(self):
        image=labeled_floor()
        self.assertFalse(gold._matches(image.convert('L'),'icon'))
        self.assertEqual('floor',gold.analyze_image(image)['state'])
        for fault in ('footer','zone_one','floor_one','death'):
            changed=image.copy()
            if fault=='death':fixture(changed,'death')
            else:changed.paste(0,gold._TEMPLATES[fault][0])
            self.assertEqual('unknown',gold.analyze_image(changed)['state'],fault)
        fixture(image,'continue');self.assertEqual('pause',gold.analyze_image(image)['state'])

    def test_text_alone_damaged_bars_and_persistent_clutter_are_rejected(self):
        ref=reference()
        for fault in ('no_bars','one_bar','short','split','shifted','solid','colored'):
            mask=ref.copy();color=(128,128,128)
            if fault=='no_bars':mask.paste(0,(0,0,36,36))
            elif fault=='one_bar':mask.paste(0,(18,0,36,36))
            elif fault=='short':mask.paste(0,(0,18,36,36))
            elif fault=='split':mask.paste(0,(0,18,36,22))
            elif fault=='shifted':mask=Image.new('L',(36,36));mask.paste(ref,(9,0))
            elif fault=='solid':mask.paste(255,(0,0,36,36))
            else:color=(255,40,40)
            self.assertEqual('unknown',gold.analyze_image(labeled_floor(mask,color))['state'],fault)

    def test_vertical_cleanup_cannot_fill_missing_pixels_or_wrap_edges(self):
        mask=Image.new('L',(36,36))
        mask.paste(255,(6,0,13,6));mask.paste(255,(6,30,13,36))
        # Two short pieces at opposite borders must not join by wraparound.
        self.assertIsNone(gold._vertical_icon(mask).getbbox())
        mask=reference();mask.paste(255,(0,14,36,17))
        cleaned=gold._vertical_icon(mask)
        self.assertIsNone(ImageChops.subtract(cleaned,mask).getbbox())
        self.assertEqual(255,cleaned.getpixel((8,20)))
        self.assertEqual(255,cleaned.getpixel((26,20)))
        self.assertGreaterEqual(cleaned.histogram()[255],.95*reference().histogram()[255])

    def test_one_two_or_occluded_products_never_count_as_all_three(self):
        for visible in (1,2,3):
            image=shop_image()
            for x in (268,304,340)[visible:]: image.paste(0,(x-15,160,x+16,220))
            self.assertEqual('visible' if visible==3 else 'partial',nav.scan(image).goods)
        image=shop_image();image.paste(0,(325,160,357,195))  # Third sprite hidden, price remains.
        self.assertEqual('partial',nav.scan(image).goods)
        image=shop_image();image.paste(0,(325,197,357,222))  # Third price hidden, sprite remains.
        self.assertEqual('partial',nav.scan(image).goods)

        self.assertEqual('partial',nav.scan(shifted(shop_image(),100,170)).goods)

    def test_partial_walk_continues_observed_floor_and_stops_for_full_or_unsafe(self):
        # Constructed scene sequence tests orchestration; not actual post-entry images.
        class Driver(old.Fake):
            def goods(self,o):return o['_extra']['scene'].goods
            def choose(self,o):return nav.choose(o['_extra']['scene'])
        scenes=[corridor('up') for _ in range(4)]
        for s in scenes:s.goods='partial'
        scenes[-1].goods='visible'
        def obs(s):
            o=old.obs();o['_extra']['scene']=s;return o
        d=Driver([obs(s) for s in scenes],['door_opened','moved'])
        walk.walk(d)
        self.assertEqual(['resume','up','up','up','pause'],d.sent)
        self.assertEqual(1,d.state['door_changes']);self.assertEqual(1,d.state['moves_confirmed'])
        self.assertTrue(d.state['goods_visible']);self.assertEqual('goods_visible',d.state['reason'])
        # An already visible set stops before any direction; partial cannot override protected cells.
        d=Driver([obs(scenes[-1])]);walk.walk(d);self.assertEqual(['resume','pause'],d.sent)
        scenes[0].protected.add((0,-1));d=Driver([obs(scenes[0])]);walk.walk(d)
        self.assertEqual(['resume','pause'],d.sent);self.assertEqual('goods_partial',d.state['reason'])

    def test_actual_open_screen_allows_one_final_pause_without_resend(self):
        with tempfile.TemporaryDirectory() as folder:
            d,now=old.SyncDeadlineTests.build(self,folder)
            frame=gold.analyze_image(opened_image());frame.update(_captured=now[0],_raw=b'x',_sha='a'*64);d.last=frame
            sent=[]
            def ack(action,obs,model=None,count=1):
                sent.append(action);d.state['actions'].append({'action':action,'outcome':'acknowledged'})
            with patch.object(d,'checkpoint'),patch.object(d,'save'),patch.object(d,'perform',side_effect=ack),patch.object(d,'observe',side_effect=walk.ProbeError('connection_error')) as observe:
                with self.assertRaises(walk.ProbeError):d.finish('movement_unconfirmed',frame)
                d.finish('movement_unconfirmed',frame)
            self.assertEqual(['pause'],sent);self.assertEqual(1,observe.call_count)
            self.assertFalse(d.state['paused'])

if __name__=='__main__':unittest.main()
