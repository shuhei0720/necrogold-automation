"""TEST042: 同じ観測の安全計画を使い切りで渡し、再探索を省く。"""
from copy import deepcopy
from contextlib import contextmanager
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from necroprobe import shop_walk as walk, shop_navigation as nav, route_sequence
from necroprobe.validation import ProbeError
import test_shop_walk as old
import test_shop_navigation as oldnav


class RoutePreparationTests(unittest.TestCase):
    build = old.SyncDeadlineTests.build
    measured_runtime = old.SyncDeadlineTests.measured_runtime

    def test_public_driver_plans_straight_once_and_sends_same_three_live_beats(self):
        with tempfile.TemporaryDirectory() as folder, self.measured_runtime(folder) as (d,now,_,_,sent):
            before,model=d.synchronize(d.observe())
            before['_extra']['scene']=oldnav.ShopNavigationBurstTests.corridor('left',6)
            before['_captured']=now[0];model['last_sample_ns']=now[0]
            with patch.object(nav,'choose',wraps=nav.choose) as choose, \
                 patch.object(nav,'burst_count',wraps=nav.burst_count) as burst, \
                 patch.object(route_sequence,'mixed_pair',wraps=route_sequence.mixed_pair) as mixed:
                decision=d.choose(before)
                directions=d.route_directions(before,decision,3)
                count=d.perform(decision['direction'],before,model,count=len(directions))
                self.assertEqual(3,count)
                self.assertEqual([walk.move_batch('left')]*3,sent)
                self.assertEqual((1,1,0),(choose.call_count,burst.call_count,mixed.call_count))
            a,b,c=d.state['actions']
            self.assertEqual(model['period_ns'],b['target_ns']-a['target_ns'])
            self.assertEqual(model['period_ns'],c['target_ns']-b['target_ns'])
            walk.read_report(Path(folder)/'report.json',d.outer['run_id'],d.outer['start_ns'])


class RouteProofBoundaryTests(unittest.TestCase):
    build = old.SyncDeadlineTests.build
    measured_runtime = old.SyncDeadlineTests.measured_runtime

    @contextmanager
    def ready(self, scene=None, count=4, confirmed=True):
        with tempfile.TemporaryDirectory() as folder, self.measured_runtime(folder) as values:
            d, now, _, _, sent = values
            before, model = d.synchronize(d.observe())
            before['_extra']['scene'] = (oldnav.ShopNavigationBurstTests.corridor('left', 6)
                                        if scene is None else scene)
            # Fresh synthetic clock isolates authorization, not device costs.
            before['_captured'] = now[0]
            model['last_sample_ns'] = now[0]
            d.state['lead_confirmed'] = confirmed
            if not confirmed:
                d.state['lead_trials'] = []
            yield d, now, sent, before, model, folder, count

    @staticmethod
    def alter(fault, d, before, model, decision=None):
        scene = d.scene(before)
        if fault == 'tiles': scene.tiles[(-1, 0)] = 'stone'
        elif fault == 'gold': scene.gold.clear()
        elif fault == 'protected': scene.protected.add((-1, 0))
        elif fault == 'goods': scene.goods = 'partial'
        elif fault == 'signature': scene.signature += b'changed'
        elif fault == 'position': d.state['position'][0] += 1
        elif fault == 'visits': d.visits[(0, 0)] += 1
        elif fault == 'entrance': d.entrance = {'gate': (-1, 0), 'direction': 'left'}
        elif fault == 'model_epoch': model['epoch_ns'] += 1
        elif fault == 'model_sample': model['last_sample_ns'] -= 1
        elif fault == 'model_profile': model['cadence_profile']['id'] += '-changed'
        elif fault == 'model_object': d.model = deepcopy(model)
        elif fault == 'lead': d.state['dispatch_lead_ns'] = walk.LEADS_NS[1]
        elif fault == 'confirmed': d.state['lead_confirmed'] = False
        elif fault == 'trials':
            d.state['lead_trials'].append({'lead_ns': walk.LEAD_NS, 'direction': 'left', 'motion': 'blocked'})
        elif fault == 'actual_count':
            action = deepcopy(d.state['actions'][-1]) if d.state['actions'] else {'action': 'left'}
            action.update(outcome='acknowledged', scheduled_inputs=1)
            d.state['actions'].append(action)
        elif fault == 'frame_time': before['_captured'] -= 1
        elif fault == 'frame_hash': before['_sha'] = 'f' * 64
        elif fault == 'decision': decision['target'] = (-2, 0)
        else: raise AssertionError(fault)

    def test_decision_copies_and_equivalent_plans_use_full_dispatch_validation(self):
        for source in ('copy', 'equivalent', 'copy_other_observation'):
            with self.subTest(source=source), self.ready() as (d, now, sent, before, model, _, count):
                with patch.object(nav, 'choose', wraps=nav.choose) as choose, \
                     patch.object(nav, 'burst_count', wraps=nav.burst_count) as burst:
                    if source == 'equivalent':
                        decision = {'direction': 'left', 'reason': 'approach_gate', 'target': (-5, 0)}
                    else:
                        decision = deepcopy(d.choose(before))
                    if source == 'copy_other_observation':
                        before = deepcopy(before)
                        d.last = before
                    directions = d.route_directions(before, decision, count)
                    previous = choose.call_count, burst.call_count
                    self.assertEqual(4, d.perform('left', before, model, count=len(directions)))
                    self.assertEqual((previous[0] + 1, previous[1] + 1),
                                     (choose.call_count, burst.call_count))
                self.assertEqual([walk.move_batch('left')] * 4, sent)

    def test_foreign_driver_decision_cannot_bypass_its_dispatch_planner(self):
        with self.ready() as (d, now, sent, before, model, folder, count):
            decision = d.choose(before)
            other, _ = self.build(folder)
            other.clock = d.clock
            other.sleeper = d.sleeper
            other.spin_wait = d.spin_wait
            other.client = d.client
            other.last = before
            other.model = model
            with patch.object(nav, 'choose', wraps=nav.choose) as choose, \
                 patch.object(nav, 'burst_count', wraps=nav.burst_count) as burst:
                directions = other.route_directions(before, decision, count)
                self.assertEqual(4, other.perform('left', before, model, count=len(directions)))
                self.assertEqual((1, 2), (choose.call_count, burst.call_count))
            self.assertEqual(4, len(sent))

    def test_original_decision_cannot_be_minted_for_another_observation(self):
        with self.ready() as (d, now, sent, before, model, _, count):
            decision = d.choose(before)
            different = deepcopy(before)
            d.last = different
            with self.assertRaises(ProbeError):
                d.route_directions(different, decision, count)
            self.assertEqual([], sent)

    def test_changed_choice_context_is_refused_before_mint_or_dispatch(self):
        faults = ('tiles', 'gold', 'protected', 'goods', 'signature', 'position', 'visits',
                  'entrance', 'model_epoch', 'model_sample', 'model_profile', 'model_object',
                  'lead', 'confirmed', 'trials', 'actual_count', 'frame_time', 'frame_hash', 'decision')
        for stage in ('before_mint', 'before_dispatch'):
            for fault in faults:
                with self.subTest(stage=stage, fault=fault), self.ready() as (d, now, sent, before, model, _, count):
                    decision = d.choose(before)
                    directions = None
                    if stage == 'before_dispatch':
                        directions = d.route_directions(before, decision, count)
                    self.alter(fault, d, before, model, decision)
                    with self.assertRaises(ProbeError):
                        if stage == 'before_mint':
                            d.route_directions(before, decision, count)
                        else:
                            d.perform('left', before, model, count=len(directions))
                    self.assertEqual([], sent)

    def test_guard_pending_checkpoint_and_wait_mutations_never_send(self):
        faults = ('tiles', 'position', 'visits', 'entrance', 'model_epoch', 'model_sample',
                  'model_profile', 'lead', 'trials', 'actual_count')
        for stage in ('guard', 'pending_checkpoint', 'wait'):
            for fault in faults:
                with self.subTest(stage=stage, fault=fault), self.ready() as (d, now, sent, before, model, _, count):
                    decision = d.choose(before)
                    directions = d.route_directions(before, decision, count)
                    method = {'guard': 'guard', 'pending_checkpoint': 'checkpoint', 'wait': 'sleeper'}[stage]
                    original = getattr(d, method)
                    changed = []
                    def mutate(*args, **kwargs):
                        result = original(*args, **kwargs)
                        if not changed:
                            changed.append(True)
                            self.alter(fault, d, before, model, decision)
                        return result
                    with patch.object(d, method, side_effect=mutate):
                        with self.assertRaises(ProbeError):
                            d.perform('left', before, model, count=len(directions))
                    self.assertEqual([True], changed)
                    self.assertEqual([], sent)

    def test_each_ack_prefix_rechecks_scene_route_and_model_before_more_input(self):
        faults = ('tiles', 'position', 'visits', 'entrance', 'model_epoch', 'model_sample',
                  'model_profile', 'lead', 'trials', 'actual_count')
        for prefix in (1, 2, 3):
            for fault in faults:
                with self.subTest(prefix=prefix, fault=fault), self.ready() as (d, now, sent, before, model, _, count):
                    decision = d.choose(before)
                    directions = d.route_directions(before, decision, count)
                    original = d.client.call
                    def mutate(method, params, timeout):
                        reply = original(method, params, timeout)
                        if method == 'run_steps' and len(sent) == prefix:
                            self.alter(fault, d, before, model, decision)
                        return reply
                    with patch.object(d.client, 'call', side_effect=mutate):
                        with self.assertRaises(ProbeError):
                            d.perform('left', before, model, count=len(directions))
                    self.assertEqual([walk.move_batch('left')] * prefix, sent)

    def test_plan_is_consumed_on_guard_failure_and_cannot_reuse_after_dispatch(self):
        with self.ready() as (d, now, sent, before, model, _, count):
            decision = d.choose(before)
            directions = d.route_directions(before, decision, count)
            with patch.object(d, 'guard', side_effect=ProbeError('foreground_not_verified')):
                with self.assertRaises(ProbeError):
                    d.perform('left', before, model, count=len(directions))
            self.assertEqual([], sent)
            with patch.object(nav, 'choose', wraps=nav.choose) as choose, \
                 patch.object(nav, 'burst_count', wraps=nav.burst_count) as burst:
                self.assertEqual(4, d.perform('left', before, model, count=len(directions)))
                self.assertEqual((1, 1), (choose.call_count, burst.call_count))
            with self.assertRaises(ProbeError):
                d.perform('left', before, model, count=len(directions))
            self.assertEqual(4, len(sent))

    def test_partial_goods_gate_and_first_lead_limits_are_preserved(self):
        for case, scene, confirmed, expected in (
                ('partial', oldnav.ShopNavigationBurstTests.corridor('left', 6, goods='partial'), True, 1),
                ('closed_gate', oldnav.ShopNavigationBurstTests.corridor('left', 1), True, 2),
                ('first_lead', None, False, 1)):
            with self.subTest(case=case), self.ready(scene, confirmed=confirmed) as (d, now, sent, before, model, _, count):
                decision = d.choose(before)
                directions = d.route_directions(before, decision, count)
                self.assertEqual(expected, len(directions))
                self.assertEqual(expected, d.perform('left', before, model, count=len(directions)))
                self.assertEqual([walk.move_batch('left')] * expected, sent)

    def test_authentic_corner_proof_keeps_both_actual_directions_and_no_replan(self):
        scene = nav.Scene({(0, 0): 'floor', (-1, 0): 'floor', (0, -1): 'floor',
                           (-1, -1): 'floor', (-2, -1): 'gold', (2, 2): 'stone', (3, 0): 'stone'},
                          {(-2, -1)}, 'unknown', set(), bytes(224*104))
        with self.ready(scene) as (d, now, sent, before, model, folder, count):
            with patch.object(nav, 'choose', wraps=nav.choose) as choose, \
                 patch.object(nav, 'burst_count', wraps=nav.burst_count) as burst, \
                 patch.object(route_sequence, 'mixed_pair', wraps=route_sequence.mixed_pair) as mixed:
                decision = d.choose(before)
                directions = d.route_directions(before, decision, count)
                self.assertEqual(('left', 'up'), directions)
                self.assertEqual(2, d.perform('left', before, model, count=2, directions=directions))
                self.assertEqual((1, 1, 1), (choose.call_count, burst.call_count, mixed.call_count))
            self.assertEqual([walk.move_batch('left'), walk.move_batch('up')], sent)
            walk.read_report(Path(folder)/'report.json', d.outer['run_id'], d.outer['start_ns'])


if __name__ == '__main__':
    unittest.main()
