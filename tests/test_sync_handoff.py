"""TEST042: 最後の同期標本をfull取得し、同じ画像で歩行へ渡す。"""
from contextlib import contextmanager
from copy import deepcopy
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from necroprobe import beat_sync, shop_walk as walk
from necroprobe.validation import ProbeError
import test_shop_walk as old


class SyncHandoffTests(unittest.TestCase):
    build = old.SyncDeadlineTests.build
    measured_runtime = old.SyncDeadlineTests.measured_runtime

    @contextmanager
    def stream(self, gap_ns=740_000_000):
        """実fitに渡す周期標本。capture/解析時間は模擬し、実機速度にはしない。"""
        with tempfile.TemporaryDirectory() as folder:
            d,now=self.build(folder);base=1_000_000_000_000
            now[0]=base+40_000_000;d.state['started_ns']=now[0];d.stop_ns=base+100_000_000_000
            captures=[]
            def frame(index,light):
                mid=base+index*gap_ns
                return dict(old.obs(),_captured=mid-40_000_000,_seen_ns=mid+40_000_000,
                    _http_start_ns=mid-40_000_000,_http_end_ns=mid+40_000_000,
                    _extra={'scene':None if light else SimpleNamespace(goods='unknown'),
                            'beat':{'remaining':(.23-index*gap_ns/520_000_000)%1,
                                    'spacing_px':104.,'center_px':446.}})
            initial=frame(0,False);d.last=initial
            def observe():
                captures.append(d.beat_only)
                current=frame(len(captures),d.beat_only)
                self.assertGreaterEqual(current['_http_start_ns'],now[0])
                now[0]=current['_seen_ns'];d.last=current
                return current
            with patch.object(d,'observe',side_effect=observe):
                yield d,now,captures,initial,observe

    def test_public_sync_fits_fourth_full_frame_without_a_fifth_capture(self):
        with tempfile.TemporaryDirectory() as folder, self.measured_runtime(folder) as (d, now, captures, scenes, sent):
            first = d.observe()
            frame, model = d.synchronize(first)
            self.assertEqual(4, len(captures))
            self.assertEqual([False, True, True, False], [light for _, light in captures])
            self.assertEqual(4, model['sample_count'])
            self.assertGreaterEqual(model['last_sample_ns']-model['first_sample_ns'], 2_000_000_000)
            self.assertIs(frame, d.last)
            self.assertIs(frame['_extra']['scene'], scenes[-1])
            self.assertIsNotNone(frame['_extra']['beat'])
            self.assertEqual(frame['_http_start_ns'] + (frame['_http_end_ns']-frame['_http_start_ns'])//2,
                             model['last_sample_ns'])
            self.assertFalse(d.beat_only)
            self.assertIsNone(d.sync_deadline)
            self.assertEqual([], sent)

    def test_four_points_still_need_two_seconds_of_live_span(self):
        with self.stream(gap_ns=600_000_000) as (d,now,captures,first,_):
            attempts=[];fit=d.fit_beat
            def fitting():
                model=fit();attempts.append((len(d.samples),model is not None))
                return model
            with patch.object(d,'fit_beat',side_effect=fitting):frame,model=d.synchronize(first)
            self.assertEqual([(4,False),(5,True)],attempts)
            self.assertEqual([True,True,False,False],captures)
            self.assertEqual(5,model['sample_count'])
            self.assertGreaterEqual(model['last_sample_ns']-model['first_sample_ns'],2_000_000_000)
            self.assertIs(frame,d.last)

    def test_missing_scene_or_latest_hud_uses_a_new_full_frame(self):
        for fault in ('scene','hud','binding'):
            with self.subTest(fault=fault),self.stream() as (d,now,captures,first,observe):
                invalid=[];fit=d.fit_beat
                def captured():
                    frame=observe()
                    if len(captures)==3:
                        invalid.append(frame)
                        if fault=='scene':frame['_extra']['scene']=None
                        if fault=='hud':frame['_extra']['beat']=None
                    return frame
                def fitted():
                    model=fit()
                    if model is not None and len(captures)==3 and fault=='binding':
                        invalid.append(d.last);d.last['_http_start_ns']+=1
                    return model
                with patch.object(d,'observe',side_effect=captured),patch.object(d,'fit_beat',side_effect=fitted):
                    frame,model=d.synchronize(first)
                self.assertTrue(invalid);self.assertTrue(all(frame is not item for item in invalid))
                self.assertFalse(captures[-1]);self.assertGreaterEqual(len(captures),4)
                self.assertIsNotNone(d.scene(frame));self.assertIsNotNone(model)
                self.assertEqual([],d.state['actions'])

    def test_stale_or_replaced_full_frame_cannot_be_accepted(self):
        for fault in ('age','identity'):
            with self.subTest(fault=fault),self.stream() as (d,now,captures,first,observe):
                def captured():
                    frame=observe()
                    if len(captures)==3:
                        if fault=='age':now[0]=frame['_captured']+beat_sync.FRESH_NS+1
                        else:d.last=deepcopy(frame)
                    return frame
                with patch.object(d,'observe',side_effect=captured),self.assertRaises(ProbeError) as caught:
                    d.synchronize(first)
                self.assertEqual('navigation_unknown',caught.exception.code)
                self.assertEqual(3,len(captures));self.assertIsNone(d.model)
                self.assertEqual([],d.state['models']);self.assertEqual([],d.state['actions'])
                self.assertFalse(d.beat_only);self.assertIsNone(d.sync_deadline)

    def test_goods_on_fourth_full_frame_win_before_fit_even_without_hud(self):
        with self.stream() as (d,now,captures,first,observe):
            def captured():
                frame=observe()
                if len(captures)==3:
                    frame['_extra']['scene'].goods='visible';frame['_extra']['beat']=None
                return frame
            with patch.object(d,'observe',side_effect=captured), \
                 patch.object(d,'fit_beat',side_effect=AssertionError('goods must win')):
                frame,model=d.synchronize(first)
            self.assertEqual('visible',d.goods(frame));self.assertIsNone(model)
            self.assertEqual(3,len(captures));self.assertEqual([],d.state['actions'])

    def test_all_new_light_and_full_captures_share_twelve_start_limit(self):
        with self.stream(gap_ns=300_000_000) as (d,now,captures,first,_):
            with patch.object(d,'fit_beat',return_value=None),self.assertRaises(ProbeError) as caught:
                d.synchronize(first)
            self.assertEqual('beat_unconfirmed',caught.exception.code)
            self.assertEqual(12,len(captures));self.assertEqual([True,True]+[False]*10,captures)
            self.assertIsNone(d.model);self.assertEqual([],d.state['actions'])

    def test_failed_full_handoffs_are_also_included_in_twelve_start_limit(self):
        with self.stream() as (d,now,captures,first,_):
            fit=d.fit_beat;handoffs=[]
            def fitted():
                model=fit()
                if model is not None:
                    # 明示的な軽量/不完全画像には従来のfull handoffが必要。
                    d.last['_extra']['scene']=None
                return model
            def tracking(model):handoffs.append(len(captures));return None
            with patch.object(d,'fit_beat',side_effect=fitted),patch.object(d,'track_beat',side_effect=tracking), \
                 self.assertRaises(ProbeError) as caught:
                d.synchronize(first)
            self.assertEqual('beat_unconfirmed',caught.exception.code)
            self.assertEqual(12,len(captures));self.assertGreaterEqual(len(handoffs),2)
            self.assertFalse(d.beat_only);self.assertIsNone(d.sync_deadline);self.assertIsNone(d.model)
            self.assertEqual([],d.state['actions'])

    def test_existing_model_tracking_handoff_consumes_the_same_capture_budget(self):
        from test_beat_sync import observations
        with self.stream(gap_ns=300_000_000) as (d,now,captures,first,_):
            samples=observations(8)
            offset=(first['_http_start_ns']+first['_http_end_ns'])//2-samples[-1]['midpoint_ns']
            for sample in samples:
                for key in ('http_start_ns','http_end_ns','midpoint_ns'):sample[key]+=offset
            d.model=beat_sync.fit(samples,profile=beat_sync.ZONE1_1_PROFILE)
            self.assertIsNotNone(d.model)
            self.assertIsNotNone(beat_sync.next_target(d.model,now[0]))
            d.samples=samples;d.state['samples']=samples
            first['_extra']['scene']=None
            with patch.object(d,'fit_beat',return_value=None),patch.object(d,'track_beat',return_value=None), \
                 self.assertRaises(ProbeError) as caught:
                d.synchronize(first)
            self.assertEqual('beat_unconfirmed',caught.exception.code)
            self.assertEqual(12,len(captures));self.assertFalse(captures[0])
            self.assertTrue(any(captures[1:]));self.assertTrue(any(not light for light in captures[1:]))

    def test_candidate_capture_deadline_or_cancel_prevents_model_acceptance(self):
        for fault in ('deadline','cancel'):
            with self.subTest(fault=fault),self.stream() as (d,now,captures,first,observe):
                def captured():
                    frame=observe()
                    if len(captures)==3:
                        if fault=='deadline':now[0]=d.sync_deadline
                        else:walk.base.supervisor._cancel_requested=True
                    return frame
                try:
                    with patch.object(d,'observe',side_effect=captured),self.assertRaises(ProbeError) as caught:
                        d.synchronize(first)
                    self.assertEqual('beat_sync_timeout' if fault=='deadline' else 'cancelled',caught.exception.code)
                    self.assertEqual(3,len(captures));self.assertIsNone(d.model)
                    self.assertEqual([],d.state['models']);self.assertEqual([],d.state['actions'])
                    self.assertFalse(d.beat_only);self.assertIsNone(d.sync_deadline)
                finally:walk.base.supervisor._cancel_requested=False

    def test_pause_and_unknown_frames_cannot_supply_a_model(self):
        for state in ('pause','unknown'):
            with self.subTest(state=state),self.stream(gap_ns=300_000_000) as (d,now,captures,first,observe):
                def captured():
                    frame=observe();frame['state']=state;frame['_extra']=None
                    return frame
                with patch.object(d,'observe',side_effect=captured), \
                     patch.object(d,'fit_beat',side_effect=AssertionError('invalid frames supplied a fit')), \
                     self.assertRaises(ProbeError) as caught:
                    d.synchronize(first)
                self.assertEqual('beat_unconfirmed',caught.exception.code)
                self.assertEqual(12,len(captures));self.assertIsNone(d.model)
                self.assertEqual([],d.state['actions'])


if __name__ == '__main__':
    unittest.main()
