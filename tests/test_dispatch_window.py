"""期限拒否を基準時刻から再計算する。端末の受付時刻とは区別する。"""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
import json
from unittest.mock import patch

from necroprobe import shop_walk as walk, beat_sync
from necroprobe.validation import ProbeError
import test_shop_walk as old
import test_shop_navigation as oldnav


class DispatchWindowTests(unittest.TestCase):
    measured_runtime = old.SyncDeadlineTests.measured_runtime
    build = old.SyncDeadlineTests.build

    def test_post_wait_budget_rejection_records_actual_wake_before_stopping(self):
        for fault in ('walk', 'session', 'cancel'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as folder, self.measured_runtime(folder) as (d, now, _, _, sent):
                before, model=d.synchronize(d.observe())
                def wake(_seconds):
                    now[0]=d.state['started_ns']+45_000_000_000
                    if fault=='session':d.stop_ns=now[0]
                    if fault=='cancel':walk.base.supervisor._cancel_requested=True
                try:
                    with patch.object(d,'sleeper',side_effect=wake):
                        with self.assertRaises(ProbeError):d.perform('left',before,model)
                    check=d.state['actions'][-1]['target_checks'][-1]
                    self.assertEqual('dispatch',check['window']['stage'])
                    self.assertEqual(now[0],check['checked_ns'])
                    self.assertEqual([],sent)
                finally:walk.base.supervisor._cancel_requested=False

    def test_sent_single_records_actual_source_phase_and_foreground(self):
        with tempfile.TemporaryDirectory() as folder, self.measured_runtime(folder) as (d, now, _, _, sent):
            before, model = d.synchronize(d.observe())
            fronts = []
            guard = d.guard
            def foreground():
                value = guard(); fronts.append(value); return value
            with patch.object(d, 'guard', side_effect=foreground):
                d.perform('left', before, model)
            action = d.state['actions'][-1]
            check = action['target_checks'][-1]
            self.assertEqual('ready', check['status'])
            self.assertEqual(dict(stage='dispatch', frame_ns=before['_captured'],
                                  phase_ns=model['last_sample_ns'], foreground_ns=fronts[-1],
                                  required_end_ns=check['checked_ns']+150_000_000+50_000_000), check['window'])
            self.assertEqual(1, len(sent))
            walk.write(folder, d.outer)
            saved = walk.read_report(Path(folder)/'report.json', d.outer['run_id'], d.outer['start_ns'])
            self.assertEqual(check, saved['walk']['actions'][-1]['target_checks'][-1])

    def test_unsent_preflight_and_first_end_have_distinct_stages(self):
        for stage in ('preflight', 'dispatch'):
            with self.subTest(stage=stage), tempfile.TemporaryDirectory() as folder, self.measured_runtime(folder) as (d, now, _, _, sent):
                before, model = d.synchronize(d.observe())
                target = now[0]+400_000_000
                until = target-150_000_000
                # 最初は待機時点の期限、次は先行+50msを含めた末尾だけが期限超過。
                before['_captured'] = until-3_000_000_000+(1 if stage=='dispatch' else -1)
                with patch.object(beat_sync, 'next_target', return_value=target):
                    with self.assertRaises(ProbeError):
                        d.perform('left', before, model)
                action = d.state['actions'][-1]; check = action['target_checks'][-1]
                self.assertEqual(stage, check['window']['stage'])
                self.assertGreater(check['window']['required_end_ns']-check['window']['frame_ns'], 3_000_000_000)
                self.assertEqual('not_requested', action['outcome'])
                self.assertEqual([], sent)

    def test_followup_records_same_source_and_fixed_next_beat(self):
        with tempfile.TemporaryDirectory() as folder, self.measured_runtime(folder) as (d, now, _, _, sent):
            before, model = d.synchronize(d.observe())
            before['_captured']=now[0]; model['last_sample_ns']=now[0]
            before['_extra']['scene']=oldnav.ShopNavigationBurstTests.corridor('left',6)
            self.assertEqual(2, d.perform('left', before, model, count=2))
            first, second = d.state['actions']
            check = second['target_checks'][-1]
            self.assertEqual('followup', check['window']['stage'])
            self.assertEqual(before['_captured'], check['window']['frame_ns'])
            self.assertEqual(model['last_sample_ns'], check['window']['phase_ns'])
            self.assertEqual(model['period_ns'], second['target_ns']-first['target_ns'])
            self.assertEqual(2, len(sent))

    def test_window_schema_is_bounded_and_old_three_key_checks_remain_readable(self):
        with tempfile.TemporaryDirectory() as folder, self.measured_runtime(folder) as (d, now, _, _, _):
            before, model = d.synchronize(d.observe()); d.perform('left', before, model)
            original = deepcopy(d.outer)
            check = original['walk']['actions'][-1]['target_checks'][0]
            self.assertIn('window', check)
            faults = [dict(check['window'], stage='arbitrary'), dict(check['window'], frame_ns=True),
                      dict(check['window'], phase_ns=-1), dict(check['window'], foreground_ns=2**63),
                      dict(check['window'], required_end_ns='0'), dict(check['window'], secret='raw'), [], None]
            for fault in faults:
                bad=deepcopy(original); bad['walk']['actions'][-1]['target_checks'][0]['window']=fault
                walk.write(folder,bad)
                with self.assertRaises((ValueError, ProbeError)):
                    walk.read_report(Path(folder)/'report.json',d.outer['run_id'],d.outer['start_ns'])
            old_check=deepcopy(original); del old_check['walk']['actions'][-1]['target_checks'][0]['window']
            walk.write(folder,old_check)
            walk.read_report(Path(folder)/'report.json',d.outer['run_id'],d.outer['start_ns'])

    def test_maximum_action_and_check_counts_fit_existing_report_limit(self):
        with tempfile.TemporaryDirectory() as folder, self.measured_runtime(folder) as (d, now, _, _, _):
            before, model = d.synchronize(d.observe()); d.perform('left', before, model)
            report=deepcopy(d.outer); template=report['walk']['actions'][0]
            template['outcome']='not_requested'; template['scheduled_inputs']=0
            template['issued_ns']=template['completed_ns']=None
            template['target_checks']=[deepcopy(template['target_checks'][0]) for _ in range(walk.MAX_TARGET_ATTEMPTS)]
            report['walk']['actions']=[deepcopy(template) for _ in range(walk.MAX_ACTIONS)]
            report['walk']['models']=[deepcopy(model) for _ in range(walk.MAX_STEPS+1)]
            report['walk']['samples']=[deepcopy(d.samples[-1]) for _ in range(12)]
            self.assertLessEqual(len(json.dumps(report,ensure_ascii=False,indent=2).encode()),131072)
            walk.write(folder,report)
            walk.read_report(Path(folder)/'report.json',d.outer['run_id'],d.outer['start_ns'])
