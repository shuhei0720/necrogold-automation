"""TEST-016の視覚同期候補。ホスト時計の一致を端末の同期成功としない。"""
import math
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw, ImageFilter

from necroprobe import beat_sync


def hud(remaining, right_shift=0):
    image = Image.new("RGB", (896, 414))
    draw = ImageDraw.Draw(image)
    for side in (-1, 1):
        for index in range(5):
            x = round(446 + side * (remaining + index) * 104)
            if side == 1:
                x += right_shift
            if 20 < x < 876 and not 418 < x < 474:
                draw.rectangle((x - 2, 354, x + 2, 385), fill=(30, 220, 175))
    return image


def observations(count=10, uniform=False, noise=False):
    base = 6_000_000_000_000
    increments = (610, 740, 590, 830, 670, 900, 620, 780, 690, 850, 640)
    offsets = [0]
    for index in range(count - 1):
        offsets.append(offsets[-1] + (900 if uniform else increments[index]) * 1_000_000)
    result = []
    for index, offset in enumerate(offsets):
        q = (0.23 - offset / 520_000_000) % 1
        if noise:
            q = (q + (0.004, -0.006, 0.002)[index % 3]) % 1
        result.append(beat_sync.make_sample(
            {"remaining": q, "spacing_px": 104.0, "center_px": 446.0},
            base + offset - 220_000_000, base + offset + 220_000_000))
    return result


def test022_samples():
    """TEST022 run54b1f314 の取得HTTP両端/HUD数値。画像・端末秘密を含まない。"""
    rows = [
        (132898709232000,132898929621000,.7625897465460014,104.25,445.25),
        (132899888198000,132900090544000,.4616435319302286,104.83333333333331,445.25),
        (132901177759000,132901393561000,.9800158124386286,104.25,445.),
        (132902264285000,132902485431000,.9320550288489993,104.25,445.5),
        (132903420917000,132903613584000,.7119047619047619,105.,445.25),
        (132904650625000,132904870980000,.36503241550656784,103.66666666666666,445.275),
        (132905727819000,132905926985000,.2846802451519779,103.5,445.25),
        (132906853136000,132907068229000,.11642319724680901,103.5,445.25),
        (132908211103000,132908437712000,.5105460202070369,105.,445.25),
        (132909388758000,132909602578000,.2940761304323943,103.5,445.5),
    ]
    return [beat_sync.make_sample({'remaining':q,'spacing_px':spacing,'center_px':center},start,end)
            for start,end,q,spacing,center in rows]


class MeasuredCadenceTests(unittest.TestCase):
    PROFILE = 'zone1-1-measured-v1'

    def test_022_alias_failure_and_four_live_sample_profile_acquisition(self):
        samples=test022_samples()
        self.assertIsNone(beat_sync.fit(samples[:8]))
        self.assertIsNone(beat_sync.fit(samples[:9]))
        self.assertIsNotNone(beat_sync.fit(samples))
        model=beat_sync.fit(samples[:4],profile=self.PROFILE)
        self.assertIsNotNone(model)
        self.assertEqual(4,model['sample_count'])
        self.assertAlmostEqual(520_659_934,model['period_ns'],delta=1)
        self.assertLess(model['residual_cycles'],.025)
        self.assertEqual(self.PROFILE,model['cadence_profile']['id'])
        self.assertFalse(model['device_timing_verified'])
        self.assertIsNotNone(beat_sync.next_target(model,samples[3]['http_end_ns']))
        # 動画のepochを転用せず、今回のHTTP時計と位相から再取得する。
        shifted=[]
        for sample in samples[:4]:
            offset=57_123_456_789
            shifted.append(beat_sync.make_sample(
                dict(sample,remaining=(sample['q']+.31)%1),
                sample['http_start_ns']+offset,sample['http_end_ns']+offset))
        updated=beat_sync.fit(shifted,profile=self.PROFILE)
        self.assertEqual(model['period_ns'],updated['period_ns'])
        phase_shift=(updated['epoch_ns']-model['epoch_ns']-offset)%model['period_ns']
        self.assertAlmostEqual(.31*model['period_ns'],phase_shift,delta=2)

    def test_profile_rejects_wrong_cadence_bad_samples_and_out_of_range_span(self):
        values=test022_samples()[:4]
        for period in (360_000_000,700_000_000,514_000_000,531_000_000):
            samples=[beat_sync.make_sample(dict(s,remaining=(.23-(s['midpoint_ns']-values[0]['midpoint_ns'])/period)%1),
                       s['http_start_ns'],s['http_end_ns']) for s in values]
            self.assertIsNone(beat_sync.fit(samples,profile=self.PROFILE))
        for samples in (values[:3],values[::-1],
                        [dict(s,q=.3,remaining=.3) for s in values],
                        [dict(s,midpoint_ns=True) for s in values],
                        values[:2]+[dict(values[2],q=(values[2]['q']+.3)%1,
                              remaining=(values[2]['q']+.3)%1)]+values[3:]):
            self.assertIsNone(beat_sync.fit(samples,profile=self.PROFILE))
        self.assertIsNone(beat_sync.fit(values,profile='unrecognized'))
        # 均等取得でglobal別枝が同等残差なら、既知範囲だけで都合よく選ばない。
        self.assertIsNone(beat_sync.fit(observations(4,uniform=True),profile=self.PROFILE))

    def test_profile_bounds_and_metadata_are_enforced_during_tracking_and_dispatch(self):
        samples=test022_samples();model=beat_sync.fit(samples[:4],profile=self.PROFILE)
        tracked=beat_sync.track(model,samples[:5]);self.assertIsNotNone(tracked)
        self.assertEqual(model['cadence_profile'],tracked['cadence_profile'])
        for period in (514_999_999,530_000_001):
            self.assertIsNone(beat_sync.next_target(dict(model,period_ns=period),model['last_sample_ns']))
        for metadata in ({},dict(model['cadence_profile'],period_min_ns=320_000_000),
                         dict(model['cadence_profile'],id='unknown')):
            self.assertIsNone(beat_sync.next_target(dict(model,cadence_profile=metadata),model['last_sample_ns']))
        for changes in ({'cadence_profile':None},{'sample_count':3},{'sample_count':13},{'mode':'unknown'},
                        {'first_sample_ns':model['last_sample_ns']},
                        {'first_sample_ns':model['last_sample_ns']-20_000_000_001}):
            self.assertIsNone(beat_sync.next_target(dict(model,**changes),model['last_sample_ns']))
        with patch.object(beat_sync,'_candidate',return_value={
                'frequency':1e9/531_000_000,'intercept':.2,'rms':.001,'maximum':.001}):
            self.assertIsNone(beat_sync.track(model,samples[:5]))

    def test_profile_period_bounds_use_model_nanosecond_precision(self):
        for period,accepted in ((514_999_999,False),(515_000_000,True),
                                (530_000_000,True),(530_000_001,False)):
            with self.subTest(period=period):
                samples=observations(5);origin=samples[0]['midpoint_ns']
                for sample in samples:
                    sample['q']=sample['remaining']=(.23-(sample['midpoint_ns']-origin)/period)%1
                model=beat_sync.fit(samples,profile=self.PROFILE)
                self.assertEqual(accepted,model is not None)
                if accepted:self.assertEqual(period,model['period_ns'])


class BeatSyncTests(unittest.TestCase):
    def test_05_scalar_only_pillow_and_vertical_coverage_boundary(self):
        # Pillow 9.5 ImageFilter.BoxBlur.__init__ begins with `radius < 0`.
        # A tuple fails before filtering on that supported iSH-era API.
        current = ImageFilter.BoxBlur
        def scalar_only(radius):
            if radius < 0:
                raise ValueError('radius must be >= 0')
            return current(radius)
        with patch.object(ImageFilter, 'BoxBlur', side_effect=scalar_only), \
             patch.object(Image.Image, 'resize', side_effect=AssertionError('resize forbidden')), \
             patch.object(Image.Image, 'rotate', side_effect=AssertionError('rotate forbidden')), \
             patch.object(Image.Image, 'transpose', side_effect=AssertionError('transpose forbidden')):
            for height in (17, 18, 37):
                image = Image.new('RGB', (896, 414))
                draw = ImageDraw.Draw(image)
                for side in (-1, 1):
                    for index in range(5):
                        x = round(446 + side * (.25 + index) * 104)
                        if 20 < x < 876 and not 418 < x < 474:
                            draw.rectangle((x-2,350,x+2,350+height-1),fill=(30,220,175))
                feature = beat_sync.extract(image)
                if height == 17:
                    self.assertIsNone(feature)
                else:
                    self.assertIsNotNone(feature)
                    self.assertAlmostEqual(.25, feature['remaining'], delta=.012)

    def test_01_hud_wrap_occlusion_and_rejection_without_reformatting(self):
        with patch.object(Image.Image, "resize", side_effect=AssertionError("resize forbidden")), \
             patch.object(Image.Image, "rotate", side_effect=AssertionError("rotate forbidden")), \
             patch.object(Image.Image, "transpose", side_effect=AssertionError("transpose forbidden")):
            for q in (0.01, 0.18, 0.55, 0.99):
                with self.subTest(q=q):
                    feature = beat_sync.extract(hud(q))
                    self.assertIsNotNone(feature)
                    delta = (feature["remaining"] - q + 0.5) % 1 - 0.5
                    self.assertLess(abs(delta), 0.012)
                    self.assertAlmostEqual(104, feature["spacing_px"], delta=1)
                    self.assertAlmostEqual(446, feature["center_px"], delta=1)
            for image in (Image.new("RGB", (414, 896)), Image.new("L", (896, 414)),
                          Image.new("RGB", (896, 414)), hud(0.25, right_shift=32)):
                self.assertIsNone(beat_sync.extract(image))
            left_only = hud(0.25)
            left_only.paste(0, (474, 350, 896, 388))
            self.assertIsNone(beat_sync.extract(left_only))
            self.assertIsNone(beat_sync.extract(None))

    def test_02_samples_preserve_http_bounds_and_reject_invalid_values(self):
        feature = {"remaining": 0.75, "spacing_px": 104, "center_px": 446}
        sample = beat_sync.make_sample(feature, 1_000_000_001, 1_450_000_002)
        self.assertEqual((1_000_000_001, 1_450_000_002),
                         (sample["http_start_ns"], sample["http_end_ns"]))
        self.assertEqual(1_225_000_001, sample["midpoint_ns"])
        self.assertEqual(225_000_000.5, sample["http_half_width_ns"])
        self.assertEqual(0.75, sample["q"])
        for start, end in ((2, 1), (1, 1), (-1, 2), (True, 2), (1, math.inf)):
            with self.assertRaises(ValueError):
                beat_sync.make_sample(feature, start, end)
        for q in (-0.1, 1.0, math.nan, math.inf, True):
            with self.assertRaises(ValueError):
                beat_sync.make_sample(dict(feature, remaining=q), 1, 2)

    def test_03_period_fit_wrap_noise_alias_and_sample_limits(self):
        for count in (8, 10, 12):
            with self.subTest(count=count):
                model = beat_sync.fit(observations(count, noise=True))
                self.assertIsNotNone(model)
                self.assertAlmostEqual(520_000_000, model["period_ns"], delta=1_000_000)
                self.assertLess(model["residual_cycles"], 0.012)
                self.assertFalse(model["device_timing_verified"])
                self.assertFalse(model["dispatch_timing_calibrated"])
                self.assertEqual("http_midpoint_unverified", model["clock_source"])
                self.assertEqual(220_000_000, model["http_half_width_max_ns"])
        self.assertIsNone(beat_sync.fit(observations(uniform=True)))
        self.assertIsNone(beat_sync.fit(observations(7)))
        self.assertIsNone(beat_sync.fit(observations() + observations()[:3]))
        repeated = observations()
        repeated[2] = dict(repeated[1])
        self.assertIsNone(beat_sync.fit(repeated))
        stale = observations()
        for sample in stale:
            sample.update(q=0.25, remaining=0.25)
        self.assertIsNone(beat_sync.fit(stale))
        corrupt = observations()
        corrupt[4] = dict(corrupt[4], q=math.nan)
        self.assertIsNone(beat_sync.fit(corrupt))
        shifted = observations()
        shifted[4].update(q=(shifted[4]["q"] + 0.35) % 1,
                          remaining=(shifted[4]["remaining"] + 0.35) % 1)
        self.assertIsNone(beat_sync.fit(shifted))

    def test_04_future_target_freshness_and_phase_check(self):
        samples = observations()
        model = beat_sync.fit(samples)
        now = samples[-1]["midpoint_ns"] + 230_000_000
        target = beat_sync.next_target(model, now)
        self.assertGreater(target, now + 150_000_000)
        self.assertLessEqual(target, now + 150_000_000 + model["period_ns"])
        self.assertAlmostEqual(0, ((target - model["epoch_ns"]) % model["period_ns"]), delta=1)
        self.assertIsNone(beat_sync.next_target(model, model["last_sample_ns"] + 3_000_000_001))
        self.assertIsNone(beat_sync.next_target(model, model["last_sample_ns"] - 1))
        self.assertIsNone(beat_sync.next_target(model, now, lead_ns=-1))
        self.assertIsNone(beat_sync.next_target(None, now))
        offset = 720_000_000
        current = dict(samples[-1])
        for key in ("http_start_ns", "http_end_ns", "midpoint_ns"):
            current[key] += offset
        current["q"] = current["remaining"] = (samples[-1]["q"] - offset / 520_000_000) % 1
        self.assertTrue(beat_sync.compatible(model, current))
        wrong = dict(current, q=(current["q"] + 0.3) % 1,
                     remaining=(current["remaining"] + 0.3) % 1)
        self.assertFalse(beat_sync.compatible(model, wrong))
        late = dict(current)
        for key in ("http_start_ns", "http_end_ns", "midpoint_ns"):
            late[key] += 4_000_000_000
        self.assertFalse(beat_sync.compatible(model, late))
        self.assertFalse(beat_sync.compatible(None, current))


def test020_sequences():
    """TEST020の2停止runのHTTP差分とHUD。端末受付時刻ではない。"""
    rows = [[(-77513500, 77513500, 0.6618703220855697, 104.25, 445.25),
      (2718448500, 2911907500, 0.28442226441658486, 103.5, 445.25),
      (3736211500, 3909803500, 0.2978087396549835, 104.58333333333331, 445.25),
      (4854130500, 5015080500, 0.17764460800896673, 104.375, 445.25),
      (5720471500, 5897709500, 0.5560386727719953, 103.5, 445.25),
      (6699621500, 6868767500, 0.6187048544596705, 104.25, 445.25),
      (7793052500, 7961608500, 0.5801282592930792, 104.0, 445.25),
      (8630455500, 8817803500, 0.9456435692608577, 104.25, 445.25),
      (9614451500, 9789054500, 0.060911270997635616, 104.25, 445.25)],
     [(-93816500, 93816500, 0.6570745220391305, 104.25, 445.25),
      (920586500, 1086046500, 0.7338127681287352, 104.25, 445.25),
      (2043802500, 2193837500, 0.5657051823700023, 104.0, 445.25),
      (2922935500, 3109836500, 0.8936848771868298, 104.25, 445.0),
      (3926343500, 4097901500, 0.9601276450976024, 104.5, 445.25),
      (5044904500, 5189852500, 0.8450839328681392, 104.25, 445.25),
      (5930838500, 6113886500, 0.1201595780688471, 104.375, 445.25),
      (6942165500, 7117636500, 0.20383711196718818, 104.25, 445.25),
      (8152335500, 8317677500, 0.8737011232176922, 104.25, 445.25),
      (9071682500, 9237305500, 0.11790586370197646, 104.25, 445.25)]]
    base = 20_000_000_000
    return [[beat_sync.make_sample({'remaining':q,'spacing_px':spacing,'center_px':center},base+start,base+end)
             for start,end,q,spacing,center in sequence] for sequence in rows]


class BeatTrackingTests(unittest.TestCase):
    def test_recorded_holdout_tracks_established_branch(self):
        for samples in test020_sequences():
            with self.subTest(count=len(samples)):
                old=beat_sync.fit(samples[:-1])
                self.assertIsNotNone(old)
                self.assertTrue(beat_sync.compatible(old,samples[-1]))
                self.assertIsNone(beat_sync.fit(samples))
                updated=beat_sync.track(old,samples)
                self.assertIsNotNone(updated)
                self.assertEqual('tracking',updated['mode'])
                self.assertLess(abs(updated['tracking_error_cycles']),.004)
                self.assertLess(updated['residual_cycles'],old['residual_cycles'])
                self.assertEqual(samples[-1]['midpoint_ns'],updated['last_sample_ns'])
                self.assertIsNotNone(beat_sync.next_target(updated,samples[-1]['http_end_ns']))
                self.assertFalse(updated['device_timing_verified'])
                self.assertFalse(updated['dispatch_timing_calibrated'])

    def test_tracking_neither_hardcodes_522ms_nor_uses_stale_phase(self):
        for period in (345_000_000,522_000_000,700_000_000):
            with self.subTest(period=period):
                samples=observations(9);origin=samples[0]['midpoint_ns']
                for v in samples:v['q']=v['remaining']=(.23-(v['midpoint_ns']-origin)/period)%1
                old=beat_sync.fit(samples);self.assertIsNotNone(old)
                sample=dict(samples[-1]);gap=4_000_000_000
                for key in ('http_start_ns','http_end_ns','midpoint_ns'):sample[key]+=gap
                sample['q']=sample['remaining']=(samples[-1]['q']-gap/period)%1
                self.assertIsNone(beat_sync.next_target(old,sample['http_end_ns']))
                tracked=beat_sync.track(old,samples+[sample]);self.assertIsNotNone(tracked)
                self.assertAlmostEqual(period,tracked['period_ns'],delta=2)
                self.assertIsNotNone(beat_sync.next_target(tracked,sample['http_end_ns']))
                self.assertIsNone(beat_sync.next_target(tracked,sample['midpoint_ns']+3_000_000_001))
                wrong=dict(sample,q=(sample['q']+.25)%1,remaining=(sample['remaining']+.25)%1)
                self.assertIsNone(beat_sync.track(old,samples+[wrong]))

    def test_tracking_bounds_and_branch_change_fail_closed(self):
        samples=observations(10,noise=True);old=beat_sync.fit(samples[:-1])
        self.assertIsNotNone(beat_sync.track(old,samples))
        for model,values in ((None,samples),(old,samples[-2:]),(old,samples[:-1]),
                             (old,samples[::-1]),(dict(old,max_residual_cycles=float('nan')),samples),
                             (dict(old,first_sample_ns=old['last_sample_ns']),samples)):
            with self.subTest(model=model,values=len(values)):
                self.assertIsNone(beat_sync.track(model,values))
        gap=old['last_sample_ns']-old['first_sample_ns']+1;latest=dict(samples[-2])
        for k in ('http_start_ns','http_end_ns','midpoint_ns'):latest[k]+=gap
        latest['q']=latest['remaining']=(samples[-2]['q']-gap/old['period_ns'])%1
        self.assertIsNone(beat_sync.track(old,samples[:-1]+[latest]))
        with patch.object(beat_sync,'_candidate',return_value={'frequency':2.9,'intercept':.2,'rms':.001,'maximum':.001}):
            self.assertIsNone(beat_sync.track(old,samples))

    def test_time_trim_keeps_continuity_without_requiring_eight_again(self):
        samples=observations(9);model=beat_sync.fit(samples)
        for _ in range(7):
            latest=dict(samples[-1])
            for key in ('http_start_ns','http_end_ns','midpoint_ns'):latest[key]+=4_000_000_000
            latest['q']=latest['remaining']=(samples[-1]['q']-4_000_000_000/520_000_000)%1
            samples=(samples+[latest])[-12:];model=beat_sync.track(model,samples)
            self.assertIsNotNone(model)
            self.assertLessEqual(model['last_sample_ns']-model['first_sample_ns'],20_000_000_000)
        self.assertLess(model['sample_count'],8)

    def test_tracking_window_budget_and_branch_boundaries(self):
        samples=observations(9);old=beat_sync.fit(samples)
        def sample_at(mid):
            q=((old['epoch_ns']-mid)%old['period_ns'])/old['period_ns']
            return beat_sync.make_sample({'remaining':q,'spacing_px':104.,'center_px':446.},
                                         mid-1,mid+1)
        last=old['last_sample_ns'];span=last-old['first_sample_ns']
        for offset,accepted in ((999_999_999,False),(1_000_000_000,True)):
            with self.subTest(two_second_window=offset):
                window=[sample_at(last-1_000_000_000),sample_at(last),sample_at(last+offset)]
                self.assertEqual(accepted,beat_sync.track(old,window) is not None)
        latest=sample_at(last+span);window=samples+[latest]
        limit=beat_sync.MAX_SINGLE_RESIDUAL_CYCLES/3
        for residual,accepted in ((limit,True),(math.nextafter(limit,math.inf),False)):
            with self.subTest(budget=residual):
                model=dict(old,max_residual_cycles=residual)
                self.assertEqual(accepted,beat_sync.track(model,window) is not None)
        self.assertIsNone(beat_sync.track(old,samples[:-1]+[sample_at(last+1_000_000_000)]))
        # 4sの予測spanで0.5周期ちょうどのbranch変更を拒否する。
        branch_model=dict(old,period_ns=500_000_000,first_sample_ns=last-4_000_000_000)
        values=[sample_at(last-1_000_000_000),sample_at(last),sample_at(last+1_000_000_000)]
        for value in values:
            value['q']=value['remaining']=((old['epoch_ns']-value['midpoint_ns'])%500_000_000)/500_000_000
        for frequency,accepted in ((2.124999,True),(2.125,False)):
            with patch.object(beat_sync,'_candidate',return_value={
                    'frequency':frequency,'intercept':.2,'rms':.001,'maximum':.001}):
                self.assertEqual(accepted,beat_sync.track(branch_model,values) is not None)
        ambiguous=observations(uniform=True)
        self.assertIsNone(beat_sync.fit(ambiguous))
        self.assertIsNone(beat_sync.track(beat_sync.fit(ambiguous),ambiguous))


if __name__ == "__main__":
    unittest.main()
