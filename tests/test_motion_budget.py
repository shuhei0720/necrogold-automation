"""TEST036: 経路不変と3秒予算の回帰。既存挙動Greenであり速度の実機証明ではない。"""
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from necroprobe import beat_sync, shop_navigation as nav, shop_walk as walk
import test_shop_walk as old
from test_continuous_walk import corridor


FRAME_HASHES = {
    'run-001.jpg': '495bcd4ea46d5eebd9b33f725da1365b14ea5bff299da2f893828d98186a76c4',
    'run-101.jpg': '51bf7ef7a79fedab7c88b82b645c416e515fec5dfcd9605c0827f2ac4017f07d',
    'run-102.jpg': 'b893e3a351c57f347d128189a13830bc90c9ffb4f172dd4db661e98cd620e18a',
    'run-103.jpg': '0a1c856c826de86d408a787eb89f444298b61980a70896ebb7c4f1c0955b1c6a',
    'run-104.jpg': '497db2abceaa1dc6e87cd8fa10171c639a91b47d10f21bf0860c9d322b2ba2e2',
    'run-105.jpg': '47f0fe7f7da0cf1102aaffb6bd271a627cf82b71efd6fbb5633a2d36e3e601bd',
    'run-099.jpg': '3205b1e1e6c3bed2d2afe87206a2afa9d602859cb20b4d74788a0278733a5be0',
    'run-106.jpg': 'dd94bdc95e4b4ff7647832007e37aca2670bc0ad85dcad32fb2cf0b72e446cc6',
}


def evidence_scene(name):
    folder = os.environ.get('NECRO_TEST035_FRAMES')
    if not folder:
        raise unittest.SkipTest('external TEST035 frames not supplied')
    path = Path(folder) / name
    if hashlib.sha256(path.read_bytes()).hexdigest() != FRAME_HASHES[name]:
        raise AssertionError('TEST035 evidence hash mismatch: ' + name)
    with Image.open(path) as image:
        return nav.scan(image.convert('RGB'))


def scene_observation(scene):
    observation = old.obs()
    observation['_extra']['scene'] = scene
    return observation


class MotionBudgetTests(unittest.TestCase):
    build = old.SyncDeadlineTests.build
    measured_runtime = old.SyncDeadlineTests.measured_runtime

    def test_actual_test035_routes_bursts_and_gate_pair_net_one_are_unchanged(self):
        # run001は保存済み同期画像。失われた第1入力前画像の代わりとはしない。
        expected = (
            ('run-001.jpg', 'left', 'observed_floor_vantage', (-4, -1), 2),
            ('run-101.jpg', 'left', 'observed_floor_vantage', (-3, -1), 1),
            ('run-102.jpg', 'up', 'observed_floor_vantage', (-2, -1), 1),
            ('run-103.jpg', 'left', 'approach_gate', (-2, 0), 2),
            ('run-104.jpg', 'left', 'approach_gate', (-1, 0), 1),
            ('run-105.jpg', 'left', 'gate_single_probe', (-1, 0), 1),
            ('run-099.jpg', 'left', 'gate_single_probe', (-1, 0), 1),
        )
        scenes = {}
        for name, direction, reason, target, burst in expected:
            with self.subTest(frame=name):
                scene = scenes[name] = evidence_scene(name)
                self.assertEqual('unknown', scene.goods)
                self.assertEqual(set(), scene.protected)
                decision = nav.choose(scene)
                self.assertEqual({'direction': direction, 'reason': reason, 'target': target}, decision)
                self.assertEqual(burst, nav.burst_count(scene, decision, limit=4))
        found = evidence_scene('run-106.jpg')
        self.assertEqual('visible', found.goods)
        self.assertEqual({'direction': None, 'reason': 'goods_visible', 'target': None}, nav.choose(found))
        before, after = scenes['run-099.jpg'], found
        self.assertTrue(nav.closed_gate_entry(before, 'left'))
        self.assertEqual('moved', nav.motion(before, after, 'left', expected_steps=1))
        self.assertEqual('partial', nav.motion(before, after, 'left', expected_steps=2))
        with tempfile.TemporaryDirectory() as folder:
            driver, _ = self.build(folder)
            first = scene_observation(scenes['run-001.jpg'])
            driver.state['lead_confirmed'] = False
            driver.state['lead_trials'] = []
            self.assertEqual(1, driver.burst_count(first, driver.choose(first), 16))
            driver.state['lead_confirmed'] = True
            gate = scene_observation(before)
            self.assertEqual(2, driver.burst_count(gate, driver.choose(gate), 16))
            self.assertEqual(0, driver.burst_count(gate, driver.choose(gate), 1))
            # 実行時はgoods-firstで変位加算前に終了。これは画像対のオフライン照合。
            self.assertEqual('gate_entered', driver.movement(gate, scene_observation(after),
                                                            'left', expected_steps=2))
            self.assertEqual({'gate': (-1, 0), 'direction': 'left'}, driver.entrance)
            self.assertEqual(0, driver.state['moves_confirmed'])

    def test_modeled_comparison_saving_preserves_pair_without_relaxing_three_seconds(self):
        # 500ms短縮は独立した仮定。iSH実測/次拍予測の正確な再生ではない。
        # 次拍だけを固定し、実Driverの前面確認・待機・期限・使い切りtokenを通す。
        self.assertEqual(3_000_000_000, beat_sync.FRESH_NS)
        baseline_dispatch_age = 2_520_967_000
        baseline_comparison_cost = 500_000_000
        preparation_to_dispatch = 450_000_000
        periods = []
        for comparison_cost, expected_count in ((baseline_comparison_cost, 1), (0, 2)):
            with self.subTest(comparison_cost_ns=comparison_cost), tempfile.TemporaryDirectory() as folder, \
                    self.measured_runtime(folder) as (driver, now, captures, _, sent):
                before, model = corridor(driver, now)
                source_ns = now[0] - (baseline_dispatch_age - baseline_comparison_cost
                                      - preparation_to_dispatch)
                before['_captured'] = source_ns
                model['last_sample_ns'] = source_ns
                self.assertTrue(beat_sync._model_valid(model, required_profile=beat_sync.ZONE1_1_PROFILE))
                periods.append(model['period_ns'])
                original_scene = driver.scene(before)
                original_lead = driver.state['dispatch_lead_ns']
                capture_count = len(captures)
                now[0] += comparison_cost
                target = now[0] + preparation_to_dispatch + original_lead
                with patch.object(beat_sync, 'next_target', return_value=target):
                    self.assertEqual(expected_count, driver.perform('left', before, model, count=2))
                actions = driver.state['actions']
                self.assertEqual(baseline_dispatch_age - baseline_comparison_cost + comparison_cost,
                                 actions[0]['issued_ns'] - source_ns)
                self.assertEqual('sequence_window_short' if expected_count == 1 else None,
                                 actions[0]['reason'])
                self.assertEqual([walk.move_batch('left')] * expected_count, sent)
                self.assertEqual(expected_count, sum(action['scheduled_inputs'] for action in actions))
                self.assertEqual([target + i * model['period_ns'] for i in range(expected_count)],
                                 [action['target_ns'] for action in actions])
                pair_end = actions[0]['issued_ns'] + original_lead + model['period_ns'] + 50_000_000
                self.assertEqual(expected_count == 2, pair_end <= source_ns + beat_sync.FRESH_NS)
                for action in actions:
                    self.assertEqual(original_lead, action['dispatch_lead_ns'])
                    self.assertEqual(original_lead, action['target_ns'] - action['issued_ns'])
                    self.assertLessEqual(action['issued_ns'] + original_lead + 50_000_000,
                                         source_ns + beat_sync.FRESH_NS)
                if expected_count == 2:
                    self.assertEqual(model['period_ns'], actions[1]['issued_ns'] - actions[0]['issued_ns'])
                self.assertEqual(150_000_000, driver.state['dispatch_lead_ns'])
                self.assertEqual(source_ns, before['_captured'])
                self.assertEqual(source_ns, model['last_sample_ns'])
                self.assertIs(original_scene, driver.scene(before))
                self.assertEqual(capture_count, len(captures))
                self.assertFalse(driver.pending)
                self.assertFalse(driver.state['input_pending'])
                self.assertFalse(driver.state['device_timing_verified'])
                self.assertIsNone(driver._followup_token)
        self.assertEqual(periods[0], periods[1])


if __name__ == '__main__':
    unittest.main()
