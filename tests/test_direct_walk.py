"""TEST041: 候補floorから直接歩行へ渡す。ホスト画像/模擬RPCの結合試験。"""
import base64
from contextlib import contextmanager, nullcontext
from copy import deepcopy
import hashlib
import io
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw
from necroprobe import beat_sync, gold_scan, native_scan, shop_navigation as nav, shop_walk as walk
from necroprobe.protocol import RpcReply
from necroprobe.validation import ProbeError
from test_beat_sync import hud
from test_gold_scan import floor, fixture
from test_restart_loop import A, LiveStub
from test_source_geometry import geometry_payload
from test_state_only import actual_image, runtime_image
import test_shop_walk as old


def candidate_image():
    image = floor()
    ImageDraw.Draw(image).rectangle((323, 118, 357, 152), fill=(210, 170, 30))
    with hud(.23) as bars:
        image.paste(bars.crop((0, 350, 896, 386)), (0, 350))
    return image


def reply_image(image, now):
    output = io.BytesIO(); image.save(output, 'JPEG', quality=95)
    _, payload = geometry_payload(walk.base.resume.CAPTURE_PARAMS,
                                  size=(896, 414), source_scale=2)
    payload.update(data=base64.b64encode(output.getvalue()).decode(), source_orientation=2)
    start = now[0]; now[0] += 100_000_000
    return RpcReply(payload, {'http_start_ns': start, 'http_end_ns': now[0]})


@contextmanager
def pause_after_input(test, driver, now):
    """The simulated device changes to a real classified menu after one pause RPC."""
    paused = Image.new('RGB', (896, 414))
    fixture(paused, 'continue'); fixture(paused, 'restart')
    call = driver.client.call
    holding = []
    def rpc(method, params, timeout):
        if method == 'run_steps':
            test.assertEqual(walk.base.batch('pause'), params)
            holding.append(True)
        if method == 'screenshot' and holding:
            driver.client.calls.append(method)
            return reply_image(paused, now)
        return call(method, params, timeout)
    try:
        with patch.object(driver.client, 'call', side_effect=rpc):
            yield holding
    finally:
        paused.close()


class DirectWalkTests(unittest.TestCase):
    build = old.SyncDeadlineTests.build
    @contextmanager
    def candidate(self):
        with candidate_image() as image, tempfile.TemporaryDirectory() as folder:
            driver, now = runtime_image(self, folder, image)
            driver.outer['phase'] = 'search'
            driver.state.update(started_ns=None, lead_confirmed=False, lead_trials=[])
            yield driver, now, folder, image

    def test_search_candidate_enriches_same_capture_and_collect_hands_it_without_pause(self):
        with self.candidate() as (driver, now, folder, image), \
                patch.object(nav, 'scan', wraps=nav.scan) as scene_scan, \
                patch.object(beat_sync, 'extract', wraps=beat_sync.extract) as beat:
            result = walk.base.collect(driver, candidate_handoff=driver.accept_candidate)
            hand = driver.handoff_frame
            self.assertIs(hand, driver.last)
            self.assertEqual('candidate', hand['gold'])
            self.assertEqual('floor', hand['state'])
            self.assertTrue(driver.scene(hand).gold)
            self.assertIsNotNone(hand['_extra']['beat'])
            self.assertEqual(1, scene_scan.call_count)
            self.assertEqual(1, beat.call_count)
            self.assertEqual(['device_info', 'screenshot'], driver.client.calls)
            self.assertIs(result, driver.report)
            self.assertTrue(result['candidate']); self.assertFalse(result['paused'])
            self.assertEqual([], result['actions'])
            self.assertIn('found.jpg', driver.images)
            self.assertIsNone(driver.model); self.assertEqual([], driver.samples)
            saved = walk.read_report(Path(folder) / 'report.json',
                                     driver.outer['run_id'], driver.outer['start_ns'])
            self.assertTrue(saved['search']['candidate']); self.assertFalse(saved['search']['paused'])

    def test_clear_black_and_pause_search_frames_never_authorize_direct_entry(self):
        paused = Image.new('RGB', (896, 414)); fixture(paused, 'continue')
        images = [floor(), Image.new('RGB', (896, 414)), paused]
        try:
            for image, state in zip(images, ('floor', 'unknown', 'pause')):
                with self.subTest(state=state), tempfile.TemporaryDirectory() as folder:
                    driver, _ = runtime_image(self, folder, image)
                    driver.outer['phase'] = 'search'; driver.state['started_ns'] = None
                    observed = driver.observe()
                    self.assertEqual(state, observed['state'])
                    self.assertIsNone(driver.scene(observed))
                    self.assertFalse(driver.accept_candidate(observed))
                    self.assertIsNone(driver.handoff_frame)
                    self.assertEqual([], driver.state['actions'])
                    self.assertNotIn('run_steps', driver.client.calls)
        finally:
            for image in images: image.close()

    def test_accept_rechecks_identity_age_scene_hud_phase_and_both_pending_flags(self):
        for fault in ('changed_last', 'stale', 'future', 'phase', 'pending', 'state_pending',
                      'missing_scene', 'missing_beat', 'no_gold', 'analysis_failed', 'wrong_state'):
            with self.subTest(fault=fault), self.candidate() as (driver, now, folder, _):
                observed = driver.observe(); self.assertIsNotNone(driver.scene(observed))
                if fault == 'changed_last': driver.last = deepcopy(observed)
                elif fault == 'stale': observed['_captured'] = now[0] - 3_000_000_001
                elif fault == 'future': observed['_captured'] = now[0] + 1
                elif fault == 'phase': driver.outer['phase'] = 'walk'
                elif fault == 'pending': driver.pending = True
                elif fault == 'state_pending': driver.state['input_pending'] = True
                elif fault == 'missing_scene': observed['_extra']['scene'] = None
                elif fault == 'missing_beat': observed['_extra']['beat'] = None
                elif fault == 'no_gold': driver.scene(observed).gold.clear()
                elif fault == 'analysis_failed': driver.analysis_failed = True
                else: observed['state'] = 'unknown'
                before = list(driver.client.calls)
                self.assertFalse(driver.accept_candidate(observed))
                self.assertIsNone(driver.handoff_frame)
                self.assertEqual(before, driver.client.calls)
                self.assertEqual([], driver.state['actions'])

    def test_accept_cancel_and_session_deadline_never_store_handoff_or_issue_input(self):
        for fault in ('cancel', 'deadline'):
            with self.subTest(fault=fault), self.candidate() as (driver, now, folder, _):
                observed = driver.observe(); before = list(driver.client.calls)
                if fault == 'cancel': walk.base.supervisor._cancel_requested = True
                else: driver.stop_ns = now[0]
                try:
                    with self.assertRaises(ProbeError) as caught:
                        driver.accept_candidate(observed)
                finally:
                    walk.base.supervisor._cancel_requested = False
                self.assertEqual('cancelled' if fault == 'cancel' else 'session_deadline',
                                 caught.exception.code)
                self.assertIsNone(driver.handoff_frame)
                self.assertEqual(before, driver.client.calls)

    def test_candidate_analysis_failure_is_latched_then_paused_without_resume(self):
        for stage in ('navigation', 'beat'):
            with self.subTest(stage=stage), self.candidate() as (driver, now, folder, _), \
                    pause_after_input(self, driver, now):
                target = nav if stage == 'navigation' else beat_sync
                name = 'scan' if stage == 'navigation' else 'extract'
                with patch.object(target, name, side_effect=ValueError('injected analysis failure')):
                    result = walk.base.collect(driver, candidate_handoff=driver.accept_candidate)
                self.assertTrue(driver.analysis_failed)
                self.assertTrue(result['candidate']); self.assertTrue(result['paused'])
                self.assertIsNone(driver.handoff_frame)
                self.assertEqual(['pause'], [a['action'] for a in result['actions']])
                self.assertEqual([], driver.state['actions'])
                self.assertIn('found.jpg', driver.images)
                self.assertEqual('pause', driver.last['state'])

    def test_visible_goods_survive_beat_failure_and_hold_before_synchronization(self):
        with self.candidate() as (driver, now, folder, image):
            scene = nav.scan(image); scene.goods = 'visible'
            with patch.object(nav, 'scan', return_value=scene), \
                    patch.object(beat_sync, 'extract', side_effect=ValueError('injected beat failure')):
                walk.base.collect(driver, candidate_handoff=driver.accept_candidate)
            hand = driver.handoff_frame
            self.assertIsNotNone(hand); self.assertTrue(driver.analysis_failed)
            self.assertIsNone(hand['_extra']['beat'])
            driver.outer['phase'] = 'walk'
            with pause_after_input(self, driver, now), \
                    patch.object(driver, 'synchronize', side_effect=AssertionError('goods must hold first')):
                walk.walk(driver, initial=hand)
            self.assertTrue(driver.state['goods_visible']); self.assertTrue(driver.state['paused'])
            self.assertEqual('goods_visible', driver.state['reason'])
            self.assertEqual(['pause'], [a['action'] for a in driver.state['actions']])
            self.assertEqual([], driver.report['actions'])
            self.assertIsNone(driver.handoff_frame)

    def test_direct_entry_consumes_handoff_once_and_waits_for_real_synchronization(self):
        with self.candidate() as (driver, now, folder, _):
            observed = driver.observe(); self.assertTrue(driver.accept_candidate(observed))
            driver.outer['phase'] = 'walk'; before = list(driver.client.calls)
            with patch.object(driver, 'synchronize', side_effect=ProbeError('beat_unconfirmed')) as sync, \
                    patch.object(driver, 'observe', side_effect=AssertionError('initial frame must be reused')):
                with self.assertRaises(ProbeError) as caught:
                    walk.walk(driver, initial=observed)
            self.assertEqual('beat_unconfirmed', caught.exception.code)
            sync.assert_called_once_with(observed)
            self.assertIsNone(driver.handoff_frame)
            self.assertEqual(before, driver.client.calls)
            self.assertEqual([], driver.state['actions'])
            with self.assertRaises(ProbeError) as replay:
                walk.walk(driver, initial=observed)
            self.assertEqual('host_observation_expired', replay.exception.code)
            self.assertEqual([], driver.state['actions'])

    def test_source_change_or_expiry_after_callback_blocks_walk_before_synchronization(self):
        for fault in ('identity', 'stale', 'pending', 'state_pending', 'missing_scene'):
            with self.subTest(fault=fault), self.candidate() as (driver, now, folder, _):
                observed = driver.observe(); self.assertTrue(driver.accept_candidate(observed))
                driver.outer['phase'] = 'walk'
                if fault == 'identity': driver.last = deepcopy(observed)
                elif fault == 'stale': now[0] += 3_000_000_001
                elif fault == 'pending': driver.pending = True
                elif fault == 'state_pending': driver.state['input_pending'] = True
                else: observed['_extra']['scene'] = None
                before = list(driver.client.calls)
                with patch.object(driver, 'synchronize', side_effect=AssertionError('invalid handoff sync')):
                    with self.assertRaises(ProbeError): walk.walk(driver, initial=observed)
                self.assertEqual(before, driver.client.calls)
                self.assertEqual([], driver.state['actions'])

    def test_foreground_change_after_callback_prevents_first_direction(self):
        with self.candidate() as (driver, now, folder, _):
            observed = driver.observe(); self.assertTrue(driver.accept_candidate(observed))
            driver.outer['phase'] = 'walk'
            driver.client.system = {'foreground_app': 'other', 'screen_locked': False}
            with self.assertRaises(ProbeError) as caught:
                walk.walk(driver, initial=observed)
            self.assertEqual('foreground_not_verified', caught.exception.code)
            self.assertEqual([], driver.state['actions'])
            self.assertNotIn('run_steps', driver.client.calls)
            self.assertEqual(1, driver.client.calls.count('screenshot'))

    def test_candidate_hud_is_first_live_sample_with_original_four_point_two_second_fit(self):
        with tempfile.TemporaryDirectory() as folder, \
                old.SyncDeadlineTests.measured_runtime(self, folder) as values:
            driver, now, captures, scenes, sent = values
            driver.outer['phase'] = 'search'; driver.state['started_ns'] = None
            def classify(_image):
                now[0] += 125_000_000
                observed = deepcopy(A)
                if driver.outer['phase'] == 'search': observed.update(gold='candidate', gold_peak=168)
                return observed
            with patch.object(driver, 'classify_frame', side_effect=classify):
                candidate = driver.observe(); self.assertTrue(driver.accept_candidate(candidate))
                driver.outer['phase'] = 'walk'
                original = driver.synchronize; accepted = []
                def synchronize(frame):
                    result = original(frame); accepted.append(result)
                    raise ProbeError('beat_unconfirmed')  # Stop before any route/input in this test.
                with patch.object(driver, 'synchronize', side_effect=synchronize):
                    with self.assertRaises(ProbeError): walk.walk(driver, initial=candidate)
            self.assertEqual(1, len(accepted))
            final_frame, model = accepted[0]
            self.assertGreaterEqual(model['sample_count'], 4)
            self.assertGreaterEqual(model['last_sample_ns'] - model['first_sample_ns'], 2_000_000_000)
            self.assertTrue(any(s['http_start_ns'] == candidate['_http_start_ns'] for s in driver.samples))
            self.assertIsNot(final_frame, candidate)
            self.assertIsNotNone(driver.scene(final_frame))
            self.assertEqual(2,sum(light for _, light in captures))
            self.assertEqual(4,len(captures))
            self.assertEqual(4,model['sample_count'])
            self.assertEqual([], sent); self.assertEqual([], driver.state['actions'])

    def test_actual_goods_candidate_with_beat_failure_is_directly_held(self):
        image, _ = actual_image(self, '039', 0)
        with image, tempfile.TemporaryDirectory() as folder:
            driver, now = runtime_image(self, folder, image)
            driver.outer['phase'] = 'search'; driver.state['started_ns'] = None
            with patch.object(beat_sync, 'extract', side_effect=ValueError('injected beat failure')):
                walk.base.collect(driver, candidate_handoff=driver.accept_candidate)
            hand = driver.handoff_frame
            self.assertIsNotNone(hand); self.assertTrue(driver.analysis_failed)
            self.assertEqual('visible', driver.goods(hand))
            driver.outer['phase'] = 'walk'
            with pause_after_input(self, driver, now): walk.walk(driver, initial=hand)
            self.assertTrue(driver.state['goods_visible']); self.assertTrue(driver.state['paused'])
            self.assertEqual(['pause'], [a['action'] for a in driver.state['actions']])


class DirectWorkerTests(unittest.TestCase):
    def test_worker_selects_direct_floor_and_never_resumes_rejected_analysis_failure(self):
        for mode in ('direct', 'goods_beat_failure', 'held_failure', 'source_changed',
                     'missing_beat', 'missing_scene'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as folder:
                start = time.monotonic_ns(); run_id = 'e' * 32
                args = walk.parser().parse_args(['--worker', '--output', folder,
                    '--checkpoint-dir', folder, '--run-id', run_id, '--start-ns', str(start),
                    '--stop-ns', str(start + 20_000_000_000), '--worker-mode', 'exec'])
                walk.write(folder, walk.new_report(start, run_id))
                client = LiveStub(); real_call = client.call
                def rpc(method, params, timeout):
                    if method == 'launch_app': client.calls.append(method); return RpcReply({}, {})
                    return real_call(method, params, timeout)
                client.call = rpc
                def search(driver, max_restarts, candidate_handoff):
                    self.assertEqual(walk.MAX_RESTARTS, max_restarts)
                    with candidate_image() as image:
                        observed = gold_scan.analyze_image(image)
                        scene = nav.scan(image); beat = beat_sync.extract(image)
                        if mode == 'goods_beat_failure': scene.goods = 'visible'; beat = None
                        if mode == 'missing_beat': beat = None
                        if mode == 'missing_scene': scene = None
                        raw = io.BytesIO(); image.save(raw, 'JPEG', quality=95)
                    stamp = driver.clock()
                    observed.update(_captured=stamp, _seen_ns=stamp, _raw=raw.getvalue(),
                        _sha=hashlib.sha256(raw.getvalue()).hexdigest(),
                        _http_start_ns=stamp, _http_end_ns=stamp,
                        _extra={'scene': scene, 'beat': beat})
                    driver.last = observed
                    driver.report.update(candidate=True, reason='gold_candidate', paused=False)
                    if mode in ('held_failure', 'goods_beat_failure'):
                        driver.analysis_failed = True
                        driver.record_failure('beat_extract', ValueError('injected beat failure'))
                    if mode in ('held_failure', 'missing_beat', 'missing_scene'):
                        if mode == 'held_failure': observed['_extra']['beat'] = None
                        self.assertFalse(candidate_handoff(observed))
                        driver.report['paused'] = True
                        driver.last = dict(observed, state='pause')
                    else:
                        self.assertTrue(candidate_handoff(observed))
                        if mode == 'source_changed': driver.last = dict(observed, state='unknown')
                received = []
                actual_walk = walk.walk
                def direct(driver, initial=None):
                    if mode in ('missing_beat', 'missing_scene'):
                        # The current bug actually enters the old resume path.
                        # Run the public walk entry so a real Driver resume is visible.
                        return actual_walk(driver, initial=initial)
                    self.assertIsNotNone(initial)
                    self.assertIs(initial, driver.last)
                    self.assertIs(initial, driver.handoff_frame)
                    self.assertEqual('walk', driver.outer['phase'])
                    self.assertFalse(driver.report['paused'])
                    received.append(initial)
                    driver.handoff_frame = None
                    driver.state.update(started_ns=driver.clock(), reason='goods_visible',
                                        goods_visible=True, paused=True)
                with patch.object(walk, '_MODULE_STARTED_NS', start), \
                        patch.object(walk.base, 'device_lock', return_value=nullcontext()), \
                        patch.object(walk.base, 'load_pairing', return_value=(b'key', 'token')), \
                        patch.object(walk.base, 'Crypto', return_value=type('Crypto', (), {'engine': 'python'})()), \
                        patch.object(walk.base, 'OwnedRpcTimer', return_value=nullcontext()), \
                        patch.object(walk, 'WalkClient', return_value=client), \
                        patch.object(walk.base, 'collect', side_effect=search), \
                        patch.object(walk, 'walk', side_effect=direct):
                    self.assertEqual(0, walk.worker(args))
                result = walk.read_report(Path(folder) / 'report.json', run_id, start)
                self.assertTrue(result['search']['candidate'])
                self.assertEqual([], [a['action'] for a in result['walk']['actions']],
                                 'rejected candidate must never resume')
                self.assertEqual(['launch_app'], client.calls)
                self.assertEqual(int(mode in ('direct', 'goods_beat_failure')), len(received))
                if mode in ('direct', 'goods_beat_failure'):
                    self.assertEqual('completed', result['status'])
                    self.assertEqual('goods_visible', result['reason'])
                    self.assertFalse(result['search']['paused'])
                    self.assertTrue(result['walk']['paused'])
                else:
                    self.assertEqual('stopped', result['status'])
                    if mode == 'held_failure':
                        self.assertEqual('walk_analysis_failed', result['reason'])
                        self.assertTrue(result['search']['paused'])
                    elif mode == 'source_changed':
                        self.assertEqual('navigation_unknown', result['reason'])
                    self.assertIsNone(result['walk']['started_ns'])


if __name__ == '__main__':
    unittest.main()
