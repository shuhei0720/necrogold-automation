"""TEST025: 実機では未検証の2拍入力と、追跡標本の再利用の契約。"""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from necroprobe import shop_walk as p, shop_navigation as nav, beat_sync
from necroprobe.validation import ProbeError
import test_shop_walk as old


class BurstTests(unittest.TestCase):
    build = old.SyncDeadlineTests.build
    measured_runtime = old.SyncDeadlineTests.measured_runtime

    def corridor(self, frame):
        scene = frame['_extra']['scene']
        scene.tiles = {(0, 0): 'floor', (-1, 0): 'floor', (-2, 0): 'floor', (-3, 0): 'gold'}
        scene.gold = {(-3, 0)}
        return frame

    def test_two_separate_touches_use_live_period_and_exact_allowlist(self):
        client = p.WalkClient(lambda *a: None);client.walking = True
        for period in (515_000_000, 521_234_567, 530_000_000):
            for direction, (x, y) in p.MOVE_POINTS.items():
                params = p.move_batch(direction, 2, period)
                paths = params['steps'][1]['params']['fingers']
                self.assertEqual([[{'x': x, 'y': y, 't': 0}, {'x': x, 'y': y, 't': .05}],
                                  [{'x': x, 'y': y, 't': period/1e9},
                                   {'x': x, 'y': y, 't': (period+50_000_000)/1e9}]], paths)
                client._validate('run_steps', params)
                for mutate in (lambda q: q['steps'][1]['params']['fingers'].append(paths[0]),
                               lambda q: q['steps'][1]['params']['fingers'][1][0].update(x=x+1),
                               lambda q: q['steps'][1]['params']['fingers'][1][0].update(t=float('nan')),
                               lambda q: q['steps'][1]['params']['fingers'][1][0].update(t=.4),
                               lambda q: q['steps'][1]['params']['fingers'][1][1].update(t=.99)):
                    invalid = deepcopy(params);mutate(invalid)
                    with self.assertRaises(ProbeError):client._validate('run_steps', invalid)
        for count, period in ((True, None), (0, None), (3, 520_000_000), (2, True),
                              (2, 514_999_999), (2, 530_000_001), (2, float('inf'))):
            with self.assertRaises(ProbeError):p.move_batch('left', count, period)

    def test_dispatch_pair_and_report_roundtrip(self):
        with tempfile.TemporaryDirectory() as folder, self.measured_runtime(folder) as (d, now, _, _, sent):
            before, model = d.synchronize(d.observe());self.corridor(before)
            count = d.perform('left', before, model, count=2)
            self.assertEqual(2, count)
            self.assertEqual(p.move_batch('left', 2, model['period_ns']), sent[-1])
            entry = d.state['actions'][-1]
            self.assertEqual((2, 2, model['period_ns']),
                             (entry['requested_inputs'], entry['scheduled_inputs'], entry['period_ns']))
            p.write(folder, d.outer)
            p.read_report(Path(folder)/'report.json', d.outer['run_id'], d.outer['start_ns'])
            for field, value in (('scheduled_inputs', 3), ('scheduled_inputs', True),
                                 ('requested_inputs', 1), ('period_ns', 530_000_001)):
                bad = deepcopy(d.outer);bad['walk']['actions'][-1][field] = value;p.write(folder, bad)
                with self.assertRaises(ValueError):p.read_report(Path(folder)/'report.json', d.outer['run_id'], d.outer['start_ns'])

    def test_actual_wake_final_horizon_downgrades_pair(self):
        for boundary in ('frame', 'phase', 'walk', 'session'):
            for slack in (-1, 0, 1):
                with self.subTest(boundary=boundary, slack=slack), tempfile.TemporaryDirectory() as folder, \
                     self.measured_runtime(folder) as (d, now, _, _, sent):
                    before, model = d.synchronize(d.observe());self.corridor(before)
                    start = now[0];target = start+400_000_000
                    issued = target-p.LEAD_NS+5_000_000
                    end = issued+p.LEAD_NS+model['period_ns']+50_000_000
                    if boundary == 'frame':before['_captured'] = end-3_000_000_000+slack
                    if boundary == 'phase':model['last_sample_ns'] = end-3_000_000_000+slack
                    if boundary == 'walk':d.state['started_ns'] = end-45_000_000_000+slack
                    if boundary == 'session':d.stop_ns = end+slack
                    sleep = d.sleeper
                    def late(seconds):
                        sleep(seconds)
                        if now[0] >= target-p.LEAD_NS:now[0] += 5_000_000
                    d.sleeper = late
                    with patch.object(beat_sync, 'next_target', return_value=target):
                        count = d.perform('left', before, model, count=2)
                    self.assertEqual(1 if slack < 0 else 2, count)
                    self.assertEqual(count, len(sent[-1]['steps'][1]['params']['fingers']))
                    self.assertEqual(count, d.state['actions'][-1]['scheduled_inputs'])

    def test_pair_cannot_bypass_route_or_input_limit(self):
        with tempfile.TemporaryDirectory() as folder, self.measured_runtime(folder) as (d, now, _, _, sent):
            before, model = d.synchronize(d.observe())
            with self.assertRaises(ProbeError):d.perform('left', before, model, count=2)
            self.assertEqual([], sent)
            self.corridor(before)
            d.state['actions'] = [dict(action='left', scheduled_inputs=2) for _ in range(7)]+[dict(action='left', scheduled_inputs=1)]
            self.assertEqual(1, d.perform('left', before, model, count=2))
            self.assertEqual(16, sum(a['scheduled_inputs'] for a in d.state['actions']))
            d.last = before
            with self.assertRaises(ProbeError):d.perform('left', before, model)
            self.assertEqual(1, len(sent))

    def test_early_tracking_reuses_fresh_frame_without_duplicate_sample(self):
        with tempfile.TemporaryDirectory() as folder, self.measured_runtime(folder) as (d, now, _, _, sent):
            before, model = d.synchronize(d.observe())
            d.perform('left', before, model)
            after = d.observe()
            with patch.object(nav, 'motion', return_value='moved'):
                d.movement(before, after, 'left')
            self.assertIs(after, d.tracked_frame)
            samples = deepcopy(d.samples);updated = d.model
            with patch.object(d, 'observe', side_effect=AssertionError('fresh frame recaptured')):
                frame, accepted = d.synchronize(after)
            self.assertIs(frame, after);self.assertIs(updated, accepted)
            self.assertEqual(samples, d.samples)

    def test_slow_motion_tracks_before_work_then_refreshes_stale_full(self):
        with tempfile.TemporaryDirectory() as folder, self.measured_runtime(folder) as (d, now, captures, _, sent):
            before, model = d.synchronize(d.observe());d.perform('left', before, model)
            after = d.observe();sample_mid = (after['_http_start_ns']+after['_http_end_ns'])//2
            def slow(*args, **kwargs):
                self.assertEqual(sample_mid, d.model['last_sample_ns'])
                now[0] += 1_400_000_000
                return 'moved'
            with patch.object(nav, 'motion', side_effect=slow):d.movement(before, after, 'left')
            old_count = len(captures);frame, accepted = d.synchronize(after)
            self.assertIsNot(frame, after);self.assertEqual(old_count+1, len(captures))
            self.assertFalse(captures[-1][1]);self.assertEqual('tracking', accepted['mode'])
            self.assertEqual(len(d.samples), len({s['midpoint_ns'] for s in d.samples}))

    def test_partial_pair_stops_and_total_inputs_count_pairs(self):
        class PairFake(old.Fake):
            def burst_count(self, frame, decision, remaining):return min(2, remaining)
            def perform(self, action, frame, model=None, count=1):
                super().perform(action, frame, model)
                return count
            def movement(self, before, after, direction, expected_steps=1):
                self.expected.append(expected_steps);return next(self.motions)
        for motions, total in ((['partial'], 1), (['moved']*8, 16)):
            d = PairFake([old.obs() for _ in range(10)], motions);d.expected = []
            p.walk(d)
            self.assertEqual(total, d.state['moves_confirmed'])
            self.assertEqual([2]*len(motions), d.expected)
            self.assertEqual(8 if total==16 else 1, d.sent.count('left'))
            self.assertEqual('walk_limit' if total==16 else 'movement_unconfirmed', d.state['reason'])

    def test_mixed_pairs_and_single_downgrade_do_not_consume_unsent_inputs(self):
        class Mixed(old.ExpiringFake):
            def burst_count(self, frame, decision, remaining):return min(2, remaining)
            def perform(self, action, frame, model=None, count=1):
                if action in p.MOVE_POINTS:
                    self.proposed.append(count)
                    count=1 if self.downgrade else count
                    self.downgrade=False
                result=super().perform(action, frame, model, count=count)
                if action in p.MOVE_POINTS:self.state['actions'][-1]['scheduled_inputs']=count
                return result
        d=Mixed([old.obs() for _ in range(20)], ['expired','expired']+['ok']*9)
        d.proposed=[];d.downgrade=True
        p.walk(d)
        self.assertEqual(16,d.state['moves_confirmed'])
        self.assertEqual(16,sum(a['scheduled_inputs'] for a in d.state['actions']))
        self.assertEqual(2,sum(a['outcome']=='not_requested' for a in d.state['actions']))
        # Two definitely-unsent retries consume no inputs; all completed pairs fit the cap.
        self.assertEqual(8,d.sent.count('left'))
        d=Mixed([old.obs() for _ in range(20)], ['ok']*10);d.proposed=[];d.downgrade=True
        p.walk(d)
        self.assertEqual(16,d.state['moves_confirmed']);self.assertEqual(1,d.proposed[-1])
        self.assertEqual([1]+[2]*7+[1],[a['scheduled_inputs'] for a in d.state['actions'] if a['action']=='left'])

    def test_pair_unknown_never_retries_and_opposite_route_cannot_send(self):
        from necroprobe.protocol import RpcReply
        with tempfile.TemporaryDirectory() as folder, self.measured_runtime(folder) as (d, now, _, _, sent):
            before,model=d.synchronize(d.observe());self.corridor(before)
            with self.assertRaises(ProbeError):d.perform('right',before,model,count=2)
            self.assertEqual([],sent)
            call=d.client.call
            def unknown(method,params,timeout):
                if method=='run_steps':return RpcReply({}, {})
                return call(method,params,timeout)
            with patch.object(d.client,'call',side_effect=unknown):
                with self.assertRaises(ProbeError):d.perform('left',before,model,count=2)
                d.finish('movement_unconfirmed',before)
            self.assertTrue(d.pending);self.assertEqual(1,len(d.state['actions']))
            self.assertEqual(2,d.state['actions'][0]['scheduled_inputs'])
            with self.assertRaises(ProbeError):d.perform('left',before,model,count=2)

    def test_failed_early_tracking_never_marks_frame_accepted(self):
        with tempfile.TemporaryDirectory() as folder, self.measured_runtime(folder) as (d, now, _, _, sent):
            before,model=d.synchronize(d.observe());d.perform('left',before,model)
            after=d.observe()
            with patch.object(d,'track_beat',return_value=None),patch.object(nav,'motion',return_value='moved'):
                d.movement(before,after,'left')
            self.assertIsNone(d.model);self.assertIsNone(d.tracked_frame)

    def test_final_validation_cost_is_in_lateness_and_next_target_selection(self):
        with tempfile.TemporaryDirectory() as folder, self.measured_runtime(folder) as (d, now, _, _, sent):
            before,model=d.synchronize(d.observe());self.corridor(before)
            first=now[0]+400_000_000;period=model['period_ns'];original=d.goods
            delayed=[False]
            def goods(frame):
                if not delayed[0] and now[0]>=first-p.LEAD_NS:
                    delayed[0]=True;now[0]+=20_000_000
                return original(frame)
            def target(m,current,lead=p.LEAD_NS):
                return first if current<first-p.LEAD_NS+1 else first+period
            with patch.object(d,'goods',side_effect=goods),patch.object(beat_sync,'next_target',side_effect=target):
                d.perform('left',before,model,count=2)
            entry=d.state['actions'][-1]
            self.assertEqual(['late','ready'],[c['status'] for c in entry['target_checks']])
            self.assertEqual(first-p.LEAD_NS+20_000_000,entry['target_checks'][0]['checked_ns'])
            self.assertEqual(first+period-p.LEAD_NS,entry['issued_ns']);self.assertEqual(1,len(sent))

    def test_pair_goods_wins_before_partial_and_tween_has_only_three_observations(self):
        class Pair(old.Fake):
            def burst_count(self,frame,decision,remaining):return min(2,remaining)
            def perform(self,action,frame,model=None,count=1):
                super().perform(action,frame,model);return count
        for goods in (True,False):
            frames=[old.obs(),old.obs(),old.obs(),old.obs('visible' if goods else 'unknown')]
            d=Pair(frames,['tween']*3);p.walk(d)
            self.assertEqual(['resume','left','pause'],d.sent)
            self.assertEqual('goods_visible' if goods else 'movement_unconfirmed',d.state['reason'])
            self.assertEqual(0,d.state['moves_confirmed'])


if __name__ == '__main__':unittest.main()
