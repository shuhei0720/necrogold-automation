"""TEST037: 1秒の前面期限に既存10ms待機遅れを含める。実機受付の証明ではない。"""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from necroprobe import beat_sync, gold_scan, shop_navigation as nav, shop_walk as walk
from necroprobe.protocol import RpcReply
from necroprobe.validation import ProbeError
from test_resume_once import GOOD
import test_shop_walk as old


class ForegroundWindowTests(unittest.TestCase):
    build = old.SyncDeadlineTests.build
    measured_runtime = old.SyncDeadlineTests.measured_runtime

    @contextmanager
    def prepared(self):
        # 本物の取得・HUD fit/trackで得た画像年齢を維持する。最新時刻へ上書きしない。
        with tempfile.TemporaryDirectory() as folder, self.measured_runtime(folder) as values:
            driver, now, captures, _, sent = values
            before, model = driver.synchronize(driver.observe())
            front = []
            guard = driver.guard
            def observed_front():
                value = guard(); front.append(value); return value
            with patch.object(driver, 'guard', side_effect=observed_front):
                yield driver, now, before, model, front, captures, sent

    def test_test036_late_first_target_rejects_second_window_before_wait(self):
        with self.prepared() as (d, now, before, model, front, _, sent):
            original = beat_sync.next_target
            targets, waits = [], []
            def target(*args):
                if len(args) != 3:
                    return original(*args)
                second = front[-1] + 995_217_130 + args[2]
                result = second - model['period_ns'] if not targets else second
                targets.append(result)
                return result
            def wake(_seconds):
                index = len(waits)
                waits.append(d.state['actions'][-1]['target_ns'])
                now[0] = waits[-1] - d.state['dispatch_lead_ns'] + (11_171_897 if index == 0 else 9_384_870)
            with patch.object(beat_sync, 'next_target', side_effect=target), patch.object(d, 'sleeper', side_effect=wake):
                with self.assertRaises(ProbeError) as caught:
                    d.perform('left', before, model)
            self.assertEqual('dispatch_window_expired', caught.exception.code)
            self.assertEqual(2, len(targets))
            self.assertEqual([targets[0]], waits)
            action = d.state['actions'][-1]
            self.assertEqual(['late', 'expired'], [v['status'] for v in action['target_checks']])
            self.assertEqual('preflight', action['target_checks'][-1]['window']['stage'])
            self.assertEqual('not_requested', action['outcome'])
            self.assertIsNone(action['issued_ns']); self.assertIsNone(action['completed_ns'])
            self.assertEqual({}, action['rpc_timings']); self.assertEqual([], sent)
            self.assertFalse(d.pending); self.assertFalse(d.state['input_pending'])

    def test_990ms_boundary_reserves_ten_ms_without_changing_dispatch_tolerance(self):
        self.assertEqual(10_000_000, walk.DISPATCH_LATE_NS)
        for age, accepted in ((990_000_000, True), (990_000_001, False), (995_217_130, False)):
            with self.subTest(foreground_age=age), self.prepared() as (d, now, before, model, front, _, sent):
                original = beat_sync.next_target
                waits = []
                def target(*args):
                    return front[-1]+age+args[2] if len(args) == 3 else original(*args)
                def wake(_seconds):
                    waits.append(d.state['actions'][-1]['target_ns'])
                    now[0] = waits[-1]-d.state['dispatch_lead_ns']+10_000_000
                with patch.object(beat_sync, 'next_target', side_effect=target), patch.object(d, 'sleeper', side_effect=wake):
                    if accepted:
                        self.assertEqual(1, d.perform('left', before, model))
                    else:
                        with self.assertRaises(ProbeError) as caught:
                            d.perform('left', before, model)
                        self.assertEqual('dispatch_window_expired', caught.exception.code)
                self.assertEqual(int(accepted), len(waits)); self.assertEqual(int(accepted), len(sent))
                check = d.state['actions'][-1]['target_checks'][-1]
                self.assertEqual('dispatch' if accepted else 'preflight', check['window']['stage'])
                if accepted:
                    self.assertEqual(1_000_000_000, check['checked_ns']-front[-1])
                    self.assertEqual(10_000_000, check['checked_ns']-(check['target_ns']-150_000_000))
                else:
                    self.assertEqual('not_requested', d.state['actions'][-1]['outcome'])
                    self.assertEqual({}, d.state['actions'][-1]['rpc_timings'])

    @contextmanager
    def recovering_walk(self, third_failure=False, unknown_ack=False):
        # 実Driver.observe/synchronize/perform/walkを通す制御回帰。
        # 最初の未送信だけ時計を進めて既存2回枠の1回を消費させる。
        with tempfile.TemporaryDirectory() as folder, self.measured_runtime(folder) as values:
            d, now, captures, _, sent = values
            d.last = dict(d.last, state='pause')
            call, observe, guard, checkpoint = d.client.call, d.observe, d.guard, d.checkpoint
            original_target, original_sleep = beat_sync.next_target, d.sleeper
            front, targets, waits = [], [], []
            first_failure = []; trigger_entry = []; final_capture_count = []

            def transport(method, params, timeout):
                if method == 'run_steps' and params['steps'][1]['method'] == 'tap':
                    return RpcReply(deepcopy(GOOD), {})
                reply = call(method, params, timeout)
                if method == 'run_steps' and unknown_ack:
                    return RpcReply({}, {})
                return reply
            def capture():
                result = observe()
                if len(sent) >= 2 and not unknown_ack:
                    result['_extra']['scene'].goods = 'visible'
                return result
            def observed_front():
                value = guard(); front.append(value); return value
            def persist():
                checkpoint()
                if (d.pending and not first_failure and d.state['actions'][-1]['action'] in walk.MOVE_POINTS):
                    first_failure.append(True); now[0] += 3_000_000_001
            def target(*args):
                if len(args) != 3 or len(sent) != 1:
                    return original_target(*args)
                entry = d.state['actions'][-1]
                if not trigger_entry:
                    trigger_entry.append(entry)
                if entry is trigger_entry[0]:
                    second = front[-1]+995_217_130+args[2]
                    result = second-args[0]['period_ns'] if not targets else second
                    targets.append(result)
                    return result
                if third_failure:
                    return front[-1]+995_217_130+args[2]
                return original_target(*args)
            def wake(seconds):
                if trigger_entry and d.state['actions'][-1] is trigger_entry[0]:
                    waits.append(d.state['actions'][-1]['target_ns'])
                    now[0] = waits[-1]-d.state['dispatch_lead_ns']+(11_171_897 if len(waits) == 1 else 9_384_870)
                else:
                    original_sleep(seconds)
            def finish(reason, _frame):
                d.state['reason'] = reason
                final_capture_count.append(len(captures))
            with patch.object(d.client, 'call', side_effect=transport), patch.object(d, 'observe', side_effect=capture), \
                    patch.object(d, 'guard', side_effect=observed_front), patch.object(d, 'checkpoint', side_effect=persist), \
                    patch.object(d, 'burst_count', return_value=1), patch.object(nav, 'motion', return_value='moved'), \
                    patch.object(beat_sync, 'next_target', side_effect=target), patch.object(d, 'sleeper', side_effect=wake), \
                    patch.object(d, 'finish', side_effect=finish):
                try:
                    walk.walk(d)
                except ProbeError as exc:
                    d.state['reason'] = exc.code
                yield d, sent, captures, trigger_entry, waits

    def test_existing_last_refresh_recovers_but_a_third_unsent_window_cannot_reset_budget(self):
        for third_failure in (False, True):
            with self.subTest(third_failure=third_failure), self.recovering_walk(third_failure=third_failure) as values:
                d, sent, _, trigger, waits = values
                self.assertEqual('dispatch_window_expired' if third_failure else 'goods_visible', d.state['reason'])
                self.assertEqual(1 if third_failure else 2, len(sent))
                self.assertEqual(1, len(waits))
                self.assertEqual('preflight', trigger[0]['target_checks'][-1]['window']['stage'])
                rejected = [a for a in d.state['actions'] if a['action'] in walk.MOVE_POINTS and a['outcome'] == 'not_requested']
                self.assertEqual(3 if third_failure else 2, len(rejected))
                self.assertTrue(all(a['issued_ns'] is None and a['completed_ns'] is None and a['rpc_timings'] == {} for a in rejected))
                self.assertEqual(not third_failure, d.state['goods_visible'])
                self.assertFalse(d.pending); self.assertFalse(d.state['input_pending'])

    def test_unknown_ack_after_one_recovery_never_reaches_another_window(self):
        with self.recovering_walk(unknown_ack=True) as (d, sent, _, trigger, waits):
            self.assertEqual('batch_unknown', d.state['reason'])
            self.assertEqual(1, len(sent)); self.assertEqual([], trigger); self.assertEqual([], waits)
            self.assertTrue(d.pending); self.assertTrue(d.state['input_pending'])
            self.assertEqual(1, sum(a['action'] in walk.MOVE_POINTS and a['outcome']=='not_requested' for a in d.state['actions']))

    def test_actual_test036_two_up_steps_keep_floor_and_next_up_route(self):
        folder = os.environ.get('NECRO_TEST036_FRAMES')
        if not folder:
            self.skipTest('external TEST036 frames not supplied')
        scenes = []
        for name, digest in (
                ('run-099.jpg', 'de9f4b491be6eb2b151977863d25ad9afab3445bb0c42a58566cf62abad9a713'),
                ('run-103.jpg', '59dcfcaf24350339fb99e84113e3e3947e15aa7f1b485306040e0fcb1542a751')):
            path = Path(folder)/name
            self.assertEqual(digest, hashlib.sha256(path.read_bytes()).hexdigest())
            with Image.open(path) as image:
                self.assertEqual((896,414), image.size)
                rgb = image.convert('RGB')
                self.assertEqual('floor', gold_scan.analyze_image(rgb)['state'])
                scenes.append(nav.scan(rgb))
        self.assertEqual('moved', nav.motion(*scenes, 'up', expected_steps=2))
        self.assertEqual('unexpected', nav.motion(*scenes, 'up', expected_steps=1))
        self.assertEqual('unknown', scenes[-1].goods)
        self.assertEqual({'direction':'up','reason':'approach_gate','target':(0,-1)},nav.choose(scenes[-1]))
        self.assertEqual(1, nav.burst_count(scenes[-1], nav.choose(scenes[-1]), limit=4))
