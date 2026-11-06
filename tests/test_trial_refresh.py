"""TEST035: 実測相当の費用で、確認済み零移動の次試行を新画像から始める。

画像は合成HUD・地形であり端末の入力受付を証明しない。実物の取得・同期・
perform/walkを通し、比較結果と工程費用だけを独立した試験入力に置き換える。
"""
from collections import Counter
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
import hashlib
import os
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
from necroprobe import shop_walk as w, shop_navigation as nav
from necroprobe.input_timing import LEADS_NS, eligible
from necroprobe.protocol import RpcReply
from necroprobe.validation import ProbeError
from test_resume_once import GOOD
import test_shop_walk as old
import test_shop_navigation as oldnav


class TrialRefreshTests(unittest.TestCase):
    build = old.SyncDeadlineTests.build
    measured_runtime = old.SyncDeadlineTests.measured_runtime

    @contextmanager
    def runtime(self, observe_hook=None, sync_hook=None, rpc_unknown=False,
                motion='blocked', expire_leads=(), input_limit=None,
                trial_hook=None, direction='left', motion_ns=1_200_000_000):
        with tempfile.TemporaryDirectory() as folder, self.measured_runtime(folder) as values:
            d, now, captures, scenes, sent = values
            d.synthetic_capture_starts = captures
            d.state.update(lead_confirmed=False, lead_trials=[])
            d.last = dict(d.last, state='pause')
            full_counts = Counter()
            roles = {}
            history = []
            expired = set()
            call, observe, synchronize, checkpoint = d.client.call, d.observe, d.synchronize, d.checkpoint
            timing_result = d.timing_result

            def transport(method, params, timeout):
                if method == 'run_steps' and params['steps'][1]['method'] == 'tap':
                    now[0] += 600_000_000
                    return RpcReply(deepcopy(GOOD), {})
                reply = call(method, params, timeout)
                if method == 'run_steps':
                    now[0] += 440_000_000
                    if rpc_unknown:
                        return RpcReply({}, {})
                return reply

            def navigation(_image):
                now[0] += 330_000_000
                result = oldnav.ShopNavigationBurstTests.corridor(direction, 6)
                scenes.append(result)
                return result

            def compare(*_args, **_kwargs):
                now[0] += motion_ns(d) if callable(motion_ns) else motion_ns
                return motion(d, len(sent)) if callable(motion) else motion

            def persist():
                checkpoint()
                now[0] += 100_000_000
                # 故障注入も本物のperformの期限拒否を通す。予算を直接操作しない。
                if d.pending and d.state['actions']:
                    entry = d.state['actions'][-1]
                    lead = entry.get('dispatch_lead_ns')
                    if (entry['action'] in w.MOVE_POINTS and entry['issued_ns'] is None
                            and lead in expire_leads and lead not in expired):
                        expired.add(lead)
                        now[0] += 3_000_000_001

            def capture():
                frame = observe()
                if not d.beat_only:
                    count = len(sent)
                    full_counts[count] += 1
                    role = 'initial' if count == 0 else 'after' if full_counts[count] == 1 else 'refresh'
                    roles[id(frame)] = role
                    history.append((role, count, now[0], frame))
                    if observe_hook:
                        observe_hook(d, frame, role, count)
                return frame

            def sync(frame):
                result, model = synchronize(frame)
                if sync_hook and roles.get(id(result)) == 'refresh':
                    sync_hook(d, result, len(sent))
                return result, model

            def finish(reason, _frame):
                d.state['reason'] = reason
                d.state['end_ns'] = now[0]

            def trial(*args):
                result = timing_result(*args)
                if result == 'retry' and trial_hook:
                    trial_hook(d)
                return result

            with patch.object(d.client, 'call', side_effect=transport), \
                    patch.object(nav, 'scan', side_effect=navigation), \
                    patch.object(nav, 'motion', side_effect=compare), \
                    patch.object(d, 'checkpoint', side_effect=persist), \
                    patch.object(d, 'observe', side_effect=capture), \
                    patch.object(d, 'synchronize', side_effect=sync), \
                    patch.object(d, 'timing_result', side_effect=trial), \
                    patch.object(d, 'finish', side_effect=finish), \
                    patch.object(w, 'MAX_STEPS', input_limit or 16):
                d.synthetic_walk_started_ns = now[0]
                try:
                    w.walk(d)
                except ProbeError as exc:
                    d.state['reason'] = exc.code
                try:
                    yield d, now, sent, history, expired
                finally:
                    w.base.supervisor._cancel_requested = False

    def test_measured_costs_issue_all_seven_candidates_from_six_fresh_observations(self):
        with self.runtime() as (d, now, sent, history, _):
            self.assertEqual('timing_not_found', d.state['reason'])
            self.assertEqual(list(LEADS_NS), [a['lead_ns'] for a in d.state['lead_trials']])
            self.assertEqual(7, len(sent))
            self.assertEqual(6, sum(role == 'refresh' for role, *_ in history))
            self.assertEqual(0, d.state['moves_confirmed'])
            self.assertFalse(d.state['lead_confirmed'])
            self.assertEqual(d.synthetic_walk_started_ns, d.state['started_ns'])
            self.assertLess(now[0] - d.state['started_ns'], 45_000_000_000)
            issued = [a for a in d.state['actions'] if a['scheduled_inputs']]
            self.assertEqual(7, sum(a['scheduled_inputs'] for a in issued))
            self.assertTrue(all(a['outcome'] == 'acknowledged' for a in issued))

    def test_visible_goods_in_trial_refresh_hold_without_a_second_direction(self):
        def goods(_d, frame, role, _count):
            if role == 'refresh':
                frame['_extra']['scene'].goods = 'visible'
        with self.runtime(observe_hook=goods) as (d, _, sent, history, _):
            self.assertEqual('goods_visible', d.state['reason'])
            self.assertTrue(d.state['goods_visible'])
            self.assertEqual(1, len(sent))
            self.assertEqual(1, sum(role == 'refresh' for role, *_ in history))

    @staticmethod
    def invalidate(frame, fault):
        scene = frame['_extra']['scene']
        if fault == 'gold':
            scene.gold.add((4, 4))
        elif fault == 'route':
            frame['_extra']['scene'] = oldnav.ShopNavigationBurstTests.corridor('up', 6)
        elif fault == 'unknown':
            frame['state'] = 'unknown'
            frame['_extra']['scene'] = None
        elif fault == 'partial':
            scene.goods = 'partial'
        elif fault == 'protected':
            scene.protected.add((-1, 0))
        elif fault == 'dirt':
            scene.tiles[(-1, 0)] = 'dirt'

    def test_changed_refresh_is_rejected_before_sync_or_any_new_direction(self):
        for fault in ('gold', 'route', 'unknown', 'partial', 'protected', 'dirt'):
            with self.subTest(fault=fault):
                def change(_d, frame, role, _count):
                    if role == 'refresh':
                        self.invalidate(frame, fault)
                synced = []
                with self.runtime(observe_hook=change, sync_hook=lambda *_: synced.append(True)) as values:
                    d, _, sent, _, _ = values
                    self.assertEqual(1, len(sent))
                    self.assertEqual([], synced)
                    self.assertEqual(1, len(d.state['lead_trials']))

    def test_sync_cannot_replace_trial_route_with_new_gold_partial_or_protected_floor(self):
        for fault in ('gold', 'route', 'unknown', 'partial', 'protected', 'dirt'):
            with self.subTest(fault=fault):
                called = []
                def change(_d, frame, _count):
                    called.append(True)
                    self.invalidate(frame, fault)
                with self.runtime(sync_hook=change) as (d, _, sent, _, _):
                    self.assertEqual([True], called)
                    self.assertEqual(1, len(sent))
                    self.assertEqual(1, len(d.state['lead_trials']))

    def test_goods_found_during_sync_are_held_before_route_validation(self):
        def change(_d, frame, _count):
            frame['_extra']['scene'].goods = 'visible'
            frame['_extra']['scene'].gold.clear()
        with self.runtime(sync_hook=change) as (d, _, sent, _, _):
            self.assertEqual('goods_visible', d.state['reason'])
            self.assertTrue(d.state['goods_visible'])
            self.assertEqual(1, len(sent))

    def test_unknown_ack_or_unknown_motion_never_authorize_a_trial_refresh(self):
        for fault in ('ack', 'motion'):
            with self.subTest(fault=fault), self.runtime(
                    rpc_unknown=fault == 'ack', motion='unknown' if fault == 'motion' else 'blocked') as values:
                d, _, sent, history, _ = values
                self.assertEqual(1, len(sent))
                self.assertEqual([], d.state['lead_trials'])
                self.assertEqual(0, sum(role == 'refresh' for role, *_ in history))
                self.assertEqual(fault == 'ack', d.pending)

    def test_two_unsent_recoveries_are_global_across_lead_changes(self):
        with self.runtime(expire_leads=LEADS_NS[:3]) as (d, _, sent, _, expired):
            self.assertEqual(set(LEADS_NS[:3]), expired)
            self.assertEqual('dispatch_window_expired', d.state['reason'])
            self.assertEqual(2, len(sent))
            self.assertEqual(list(LEADS_NS[:2]), [v['lead_ns'] for v in d.state['lead_trials']])
            rejected = [a for a in d.state['actions'] if a['action'] in w.MOVE_POINTS and a['outcome'] == 'not_requested']
            self.assertEqual(3, len(rejected))
            self.assertTrue(all(a['issued_ns'] is None for a in rejected))
            self.assertFalse(d.pending)

    def test_input_limit_is_not_reset_by_trial_refreshes(self):
        with self.runtime(input_limit=3) as (d, _, sent, history, _):
            self.assertEqual('walk_limit', d.state['reason'])
            self.assertEqual(3, len(sent))
            self.assertEqual(3, sum(a['scheduled_inputs'] for a in d.state['actions']))
            self.assertLessEqual(sum(role == 'refresh' for role, *_ in history), 3)

    def test_cancel_or_expired_walk_during_refresh_never_reaches_sync_or_new_input(self):
        for fault in ('cancel', 'walk'):
            with self.subTest(fault=fault):
                def interrupt(d, _frame, role, _count):
                    if role != 'refresh':
                        return
                    if fault == 'cancel':
                        w.base.supervisor._cancel_requested = True
                    else:
                        d.sleeper(45)
                synced = []
                with self.runtime(observe_hook=interrupt, sync_hook=lambda *_: synced.append(True)) as values:
                    d, _, sent, _, _ = values
                    self.assertEqual(1, len(sent))
                    self.assertEqual([], synced)
                    self.assertEqual('cancelled' if fault == 'cancel' else 'walk_limit', d.state['reason'])

    def test_expiry_or_cancel_after_blocked_prevents_the_extra_capture_start(self):
        for fault in ('cancel', 'session', 'walk_exact', 'walk_after'):
            with self.subTest(fault=fault):
                def expire(d):
                    if fault == 'cancel':
                        w.base.supervisor._cancel_requested = True
                    elif fault == 'session':
                        d.stop_ns = d.clock()
                    else:
                        deadline = d.state['started_ns'] + 45_000_000_000
                        d.sleeper((deadline - d.clock() + (1 if fault == 'walk_after' else 0)) / 1e9)
                with self.runtime(trial_hook=expire) as (d, now, sent, history, _):
                    self.assertEqual(1, len(sent))
                    self.assertEqual(1, len(d.state['lead_trials']))
                    self.assertEqual(0, sum(role == 'refresh' for role, *_ in history))
                    self.assertEqual({'cancel': 'cancelled', 'session': 'session_deadline',
                                      'walk_exact': 'walk_limit', 'walk_after': 'walk_limit'}[fault],
                                     d.state['reason'])
                    if fault == 'walk_exact':
                        self.assertEqual(45_000_000_000, now[0] - d.state['started_ns'])

    def test_foreground_wait_crossing_walk_deadline_cannot_start_trial_screenshot(self):
        def near_deadline(d):
            before_guard = d.state['started_ns'] + 44_950_000_000
            d.sleeper((before_guard - d.clock()) / 1e9)
        with self.runtime(trial_hook=near_deadline) as (d, _, sent, history, _):
            deadline = d.state['started_ns'] + 45_000_000_000
            # 新しい取得の120msの前面照会が45秒をまたぐ。撮影RPCは開始不可。
            late = [start for start, _light in d.synthetic_capture_starts if start >= deadline]
            self.assertEqual([], late)
            self.assertEqual('walk_limit', d.state['reason'])
            self.assertEqual(1, len(sent))
            self.assertEqual(0, sum(role == 'refresh' for role, *_ in history))

    def test_lead_confirmed_after_one_refresh_resumes_sequences_and_preserves_sixteen_inputs(self):
        # 比較出力は合成で、経路制御の回帰だけ。成功後の100msは高速な比較の仮定。
        def outcomes(_d, sent):
            return 'blocked' if sent == 1 else 'moved'
        def cost(d):
            return 100_000_000 if d.state['lead_confirmed'] else 1_200_000_000
        with self.runtime(motion=outcomes, motion_ns=cost) as (d, _, sent, history, _):
            self.assertEqual('walk_limit', d.state['reason'])
            self.assertEqual(16, len(sent))
            self.assertEqual(16, sum(a['scheduled_inputs'] for a in d.state['actions']))
            self.assertEqual(['blocked', 'moved'], [v['motion'] for v in d.state['lead_trials']])
            self.assertEqual(75_000_000, d.state['dispatch_lead_ns'])
            self.assertTrue(d.state['lead_confirmed'])
            self.assertEqual(15, d.state['moves_confirmed'])
            self.assertIsNone(d.timing_anchor)
            self.assertTrue(any(a['planned_inputs'] > 1 for a in d.state['actions']))
            # 最初のblocked後以外の観測は、通常区間や未送信回復に属する。
            first_refresh = next(entry for entry in history if entry[0] == 'refresh')
            self.assertEqual(1, first_refresh[1])

    def test_finite_refresh_selection_works_in_all_four_directions(self):
        for direction in ('up', 'down', 'left', 'right'):
            with self.subTest(direction=direction), self.runtime(direction=direction) as values:
                d, _, sent, _, _ = values
                self.assertEqual('timing_not_found', d.state['reason'])
                self.assertEqual(7, len(sent))
                self.assertEqual([direction] * 7, [v['direction'] for v in d.state['lead_trials']])

    def test_changed_full_frame_inside_reacquisition_cannot_be_hidden_by_later_change_back(self):
        with tempfile.TemporaryDirectory() as folder, self.measured_runtime(folder) as values:
            d, now, captures, _, sent = values
            before, _ = d.synchronize(d.observe())
            original = oldnav.ShopNavigationBurstTests.corridor('left', 6)
            before['_extra']['scene'] = deepcopy(original)
            d.timing_anchor = (frozenset(original.gold), 'left')
            d.model = None  # 再取得の軽量HUD標本→full_handoffを実際に通す。
            returned = []
            track = d.track_beat

            def scan(_image):
                now[0] += 330_000_000
                scene = deepcopy(original)
                if not returned:
                    scene.gold.add((4, 4))
                returned.append(scene)
                return scene

            # 第1fullを拒否しなければtrack不成立→次の同じ地形で回復できる構成。
            # 途中の変化を一度見た時点で止める必要があり、最終画像だけの検査では不十分。
            def track_after_full(model):
                return None if len(returned) == 1 else track(model)

            with patch.object(nav, 'scan', side_effect=scan), \
                    patch.object(d, 'track_beat', side_effect=track_after_full):
                with self.assertRaises(ProbeError) as caught:
                    d.synchronize(before)
            self.assertEqual('timing_scene_changed', caught.exception.code)
            self.assertEqual(1, len(returned))
            self.assertEqual([], sent)
            self.assertTrue(any(light for _, light in captures))
            self.assertIsNone(d.model)
            self.assertFalse(d.beat_only)

    def test_test034_stationary_pair_and_floor_scope_are_preserved(self):
        root = os.environ.get('NECRO_TEST034_FRAMES')
        if not root:
            self.skipTest('external TEST034 frames not supplied')
        expected = [('run-099.jpg', '764b7b08213fb35285b505eeddfbb272535c9010289c0c6013724405ee1c39aa'),
                    ('run-102.jpg', 'aec873efdab68304405a538f10b238802025b8753dabada652bd53f136812c9c')]
        scenes = []
        for name, digest in expected:
            path = Path(root) / name
            self.assertEqual(digest, hashlib.sha256(path.read_bytes()).hexdigest())
            with Image.open(path) as image:
                self.assertEqual((896, 414), image.size)
                scenes.append(nav.scan(image.convert('RGB')))
        self.assertEqual('blocked', nav.motion(*scenes, 'up'))
        self.assertTrue(all(eligible(scene, 'up') for scene in scenes))
        self.assertEqual(scenes[0].gold, scenes[1].gold)


if __name__ == '__main__':
    unittest.main()
