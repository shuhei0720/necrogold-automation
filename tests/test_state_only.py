"""TEST040: 歩行の安全状態分類を保ち、開幕検索だけを省く。ホスト再生試験。"""
import base64
from copy import deepcopy
import hashlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw
from necroprobe import gold_scan as gold, native_scan, shop_navigation as nav, shop_walk as walk
from necroprobe.protocol import RpcReply
import test_shop_walk as old
from test_gold_scan import floor, fixture
from test_restart_loop import LiveStub
from test_source_geometry import geometry_payload


def runtime_image(test, folder, image):
    driver, now = old.SyncDeadlineTests.build(test, folder)
    encoded = io.BytesIO(); image.save(encoded, 'JPEG', quality=95)
    _, payload = geometry_payload(walk.base.resume.CAPTURE_PARAMS,
                                  size=(896, 414), source_scale=2)
    payload.update(data=base64.b64encode(encoded.getvalue()).decode(), source_orientation=2)
    class Images(LiveStub):
        def call(self, method, params, timeout):
            if method == 'screenshot':
                self.calls.append(method)
                start = now[0]; now[0] += 100_000_000
                return RpcReply(deepcopy(payload), {'http_start_ns':start, 'http_end_ns':now[0]})
            return super().call(method, params, timeout)
    driver.client = Images()
    return driver, now


class StateOnlyTests(unittest.TestCase):
    def test_walk_observe_skips_opening_gold_scan_but_keeps_full_scene(self):
        with floor() as image, tempfile.TemporaryDirectory() as folder:
            driver, _ = runtime_image(self, folder, image)
            with patch.object(native_scan, 'scan', wraps=native_scan.scan) as opening_scan:
                observed = driver.observe()
            self.assertEqual('floor', observed['state'])
            self.assertIsNotNone(driver.scene(observed))
            self.assertEqual(0, opening_scan.call_count)
            self.assertEqual(('unknown',0,[]), (observed['gold'],observed['gold_peak'],observed['fingerprint']))

    def test_state_only_rejects_non_bool_flags_without_scanning(self):
        # Optional mode is a boolean contract, never truthiness of arbitrary input.
        with floor() as image:
            for value in (None, 0, 1, 'false', [], {}):
                with self.subTest(value=value), patch.object(native_scan, 'scan', side_effect=AssertionError('scan')):
                    result = gold.analyze_image(image, scan_gold=value)
                self.assertEqual('unknown', result['state'])

    def test_full_default_keeps_opening_gold_and_fingerprint_boundaries(self):
        with floor() as image:
            for peak, expected in ((0,'clear'),(99,'clear'),(100,'unknown'),(134,'unknown'),(135,'candidate'),(255,'candidate')):
                with self.subTest(peak=peak), patch.object(native_scan, 'scan', return_value=(peak,list(range(48)))) as scan:
                    result = gold.analyze_image(image)
                self.assertEqual(('floor',expected,peak,list(range(48))),
                                 (result['state'],result['gold'],result['gold_peak'],result['fingerprint']))
                self.assertEqual(1,scan.call_count)
                with patch.object(native_scan, 'scan', return_value=(peak,list(range(48)))):
                    self.assertEqual(result,gold.analyze_image(image,scan_gold=True))

    def test_state_only_uses_no_opening_native_or_pillow_fallback(self):
        with floor() as image, patch.object(native_scan,'scan',side_effect=AssertionError('native opening scan')), \
             patch.object(gold,'_gold_peak',side_effect=AssertionError('gold mask')), \
             patch.object(gold,'_fingerprint',side_effect=AssertionError('opening fingerprint')):
            result=gold.analyze_image(image,scan_gold=False)
        self.assertEqual({'state':'floor','gold':'unknown','gold_peak':0,
                          'fingerprint':[],'restart_label':False},result)

    def test_all_safety_state_checks_match_default(self):
        images=[floor()]
        for name in ('icon','footer'):
            image=floor();image.paste(0,gold._TEMPLATE_DATA[name][0]);images.append(image)
        for name in ('zone_one','floor_one'):
            image=floor();image.paste(0,gold._TEMPLATE_DATA[name][0]);images.append(image)
        dead=floor();fixture(dead,'death');images.append(dead)
        paused=Image.new('RGB',(896,414));fixture(paused,'continue');fixture(paused,'restart');images.append(paused)
        paused_without_restart=Image.new('RGB',(896,414));fixture(paused_without_restart,'continue');images.append(paused_without_restart)
        images.extend((Image.new('RGB',(896,414)),Image.new('RGB',(896,414),'white'),
                       Image.new('RGB',(414,896)),Image.new('RGB',(1792,828))))
        try:
            for index,image in enumerate(images):
                with self.subTest(index=index):
                    full=gold.analyze_image(image);light=gold.analyze_image(image,scan_gold=False)
                    self.assertEqual((full['state'],full['restart_label']),
                                     (light['state'],light['restart_label']))
                    self.assertEqual(('unknown',0,[]),(light['gold'],light['gold_peak'],light['fingerprint']))
            self.assertEqual(['floor']+['unknown']*5+['pause','pause']+['unknown']*4,
                             [gold.analyze_image(image,scan_gold=False)['state'] for image in images])
        finally:
            for image in images:image.close()

    def test_mode_conversion_and_original_pixels_are_preserved_without_reformatting(self):
        with floor() as original:
            for mode in ('RGB','L','RGBA','P'):
                with self.subTest(mode=mode),original.convert(mode) as image:
                    before=image.tobytes();full=gold.analyze_image(image)
                    with patch.object(Image.Image,'resize',side_effect=AssertionError('resize')), \
                         patch.object(Image.Image,'rotate',side_effect=AssertionError('rotate')), \
                         patch.object(Image.Image,'transpose',side_effect=AssertionError('transpose')):
                        light=gold.analyze_image(image,scan_gold=False)
                    self.assertEqual(full['state'],light['state'])
                    self.assertEqual(before,image.tobytes());self.assertEqual(mode,image.mode)
            for invalid in (None,object(),b'not an image'):
                self.assertEqual('unknown',gold.analyze_image(invalid,scan_gold=False)['state'])

    def test_search_phase_and_standalone_driver_keep_full_opening_analysis(self):
        with floor() as image,tempfile.TemporaryDirectory() as folder:
            driver,now=runtime_image(self,folder,image);driver.outer['phase']='search'
            with patch.object(native_scan,'scan',wraps=native_scan.scan) as scan:
                result=driver.observe()
            self.assertEqual(1,scan.call_count);self.assertEqual(48,len(result['fingerprint']))
            self.assertEqual('clear',result['gold']);self.assertIsNone(driver.scene(result))
            standalone=walk.base.RuntimeDriver(driver.client,walk.base.new_report(now[0],'a'*32),
                                               folder,now[0]+100_000_000_000,clock=lambda:now[0])
            with patch.object(native_scan,'scan',wraps=native_scan.scan) as scan:
                full=standalone.observe()
            self.assertEqual(1,scan.call_count);self.assertEqual(48,len(full['fingerprint']))
            self.assertEqual('clear',full['gold'])

    def test_walk_metadata_does_not_claim_native_opening_classification(self):
        with floor() as image,tempfile.TemporaryDirectory() as folder:
            driver,_=runtime_image(self,folder,image)
            with patch.object(native_scan,'ENGINE','native_i386'), \
                 patch.object(native_scan,'scan',side_effect=AssertionError('unused native scan')):
                result=driver.observe()
            self.assertEqual('floor',result['state']);self.assertEqual('pillow',driver.report['analysis_engine'])

    def test_light_beat_observation_cannot_authorize_route_or_motion(self):
        from necroprobe.validation import ProbeError
        from test_beat_sync import hud
        with floor() as image,tempfile.TemporaryDirectory() as folder:
            with hud(.23) as bars:
                image.paste(bars.crop((0,350,896,386)),(0,350))
            driver,_=runtime_image(self,folder,image)
            full=driver.observe();driver.beat_only=True
            with patch.object(nav,'scan',side_effect=AssertionError('beat-only navigation')), \
                 patch.object(native_scan,'scan',side_effect=AssertionError('opening scan')):
                light=driver.observe()
            self.assertIsNone(driver.scene(light));self.assertIsNotNone(light['_extra']['beat'])
            self.assertEqual('unknown',driver.goods(light));self.assertIsNone(driver.choose(light)['direction'])
            self.assertEqual('unknown',driver.movement(full,light,'left'))
            with self.assertRaises(ProbeError) as caught:driver.perform('left',light,{'period_ns':520_000_000})
            self.assertEqual('navigation_unknown',caught.exception.code)
            self.assertEqual([],driver.state['actions']);self.assertFalse(driver.pending)
            self.assertNotIn('run_steps',driver.client.calls)

    def test_finishing_keeps_safe_state_but_skips_expensive_navigation(self):
        paused=Image.new('RGB',(896,414));fixture(paused,'continue');fixture(paused,'restart')
        try:
            with tempfile.TemporaryDirectory() as folder:
                driver,_=runtime_image(self,folder,paused);driver.finishing=True
                with patch.object(nav,'scan',side_effect=AssertionError('finishing navigation')), \
                     patch.object(native_scan,'scan',side_effect=AssertionError('opening scan')):
                    result=driver.observe()
                self.assertEqual('pause',result['state']);self.assertTrue(result['restart_label'])
                self.assertIsNone(driver.scene(result));self.assertFalse(driver.pending)
        finally:paused.close()


ACTUAL={
 '035':(('found.jpg','dd94bdc95e4b4ff7647832007e37aca2670bc0ad85dcad32fb2cf0b72e446cc6','floor'),
        ('stopped.jpg','bff223e428cbab1b474d5aa164d68a0d4518e69dbb98854ea6aa348320f10519','pause')),
 '036':(('run-103.jpg','59dcfcaf24350339fb99e84113e3e3947e15aa7f1b485306040e0fcb1542a751','floor'),
        ('stopped.jpg','4f9c49522b2fc6897d93210e3bdfecdf3202f87a86911e50496e25cd21757bc8','pause')),
 '037':(('run-107.jpg','95071b5d4a42b8c48fcf42f23a4095245da1bd9cd2e1b04d125adc332742d7aa','floor'),
        ('stopped.jpg','bff223e428cbab1b474d5aa164d68a0d4518e69dbb98854ea6aa348320f10519','pause')),
 '038':(('found.jpg','b6d575f244554ba001e537b70f5ac49378f9d1373ad130330d96a0b0e21e2e83','floor'),
        ('stopped.jpg','d98fb8f5dd40b55143fe628257dd7e9970399b6b8ce615f853811464a26aa6d0','pause')),
 '039':(('found.jpg','deeccfd18f30e00bba6a644f3965170998d2973c1295d84f838207c6e774e6ac','floor'),
        ('stopped.jpg','4f9c49522b2fc6897d93210e3bdfecdf3202f87a86911e50496e25cd21757bc8','pause')),
}


def actual_image(test,number,index):
    folder=os.environ.get('NECRO_TEST'+number+'_FRAMES')
    if not folder:test.skipTest('external TEST'+number+' frames not supplied')
    name,digest,state=ACTUAL[number][index];path=Path(folder)/name
    test.assertEqual(digest,hashlib.sha256(path.read_bytes()).hexdigest())
    with Image.open(path) as source:return source.convert('RGB'),state


class ActualStateOnlyTests(unittest.TestCase):
    def check_pair(self,number):
        for index in range(2):
            image,expected=actual_image(self,number,index)
            with image:
                full=gold.analyze_image(image)
                with patch.object(native_scan,'scan',side_effect=AssertionError('opening scan')), \
                     patch.object(gold,'_gold_peak',side_effect=AssertionError('fallback peak')), \
                     patch.object(gold,'_fingerprint',side_effect=AssertionError('fingerprint')):
                    light=gold.analyze_image(image,scan_gold=False)
                self.assertEqual(expected,light['state']);self.assertEqual(full['state'],light['state'])
                self.assertEqual(full['restart_label'],light['restart_label'])
                self.assertEqual(('unknown',0,[]),(light['gold'],light['gold_peak'],light['fingerprint']))
    def test_actual_035(self):self.check_pair('035')
    def test_actual_036(self):self.check_pair('036')
    def test_actual_037(self):self.check_pair('037')
    def test_actual_038(self):self.check_pair('038')
    def test_actual_039(self):self.check_pair('039')

    def test_actual_goods_latch_survives_state_only_and_beat_failure(self):
        from necroprobe import beat_sync
        from necroprobe.validation import ProbeError
        image,_=actual_image(self,'039',0)
        with image,tempfile.TemporaryDirectory() as folder:
            driver,_=runtime_image(self,folder,image)
            with patch.object(native_scan,'scan',side_effect=AssertionError('opening scan')):
                result=driver.observe()
            self.assertEqual('floor',result['state']);self.assertEqual('visible',driver.goods(result))
            self.assertTrue(driver.state['goods_visible']);self.assertIn('found.jpg',driver.images)
            self.assertEqual([],driver.state['actions']);self.assertFalse(driver.pending)
            failed,_=runtime_image(self,folder,image)
            with patch.object(beat_sync,'extract',side_effect=ValueError('beat fixture failure')), \
                 patch.object(native_scan,'scan',side_effect=AssertionError('opening scan')):
                with self.assertRaises(ProbeError) as caught:failed.observe()
            self.assertEqual('walk_analysis_failed',caught.exception.code)
            self.assertTrue(failed.state['goods_visible']);self.assertIn('found.jpg',failed.images)
            self.assertFalse(failed.pending);self.assertEqual([],failed.state['actions'])


if __name__=='__main__':unittest.main()
