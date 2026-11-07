"""TEST041: 準備と歩行の統合契約。ホスト検証は実機の速度証明ではない。"""
import builtins
import unittest
from unittest.mock import patch
from necroprobe import shop_walk as walk


class PureReportTests(unittest.TestCase):
    def test_cold_schema_and_beat_validation_do_not_import_pillow_or_native(self):
        import subprocess, sys, textwrap
        for operation in ('schema', 'beat'):
            code = textwrap.dedent("""
                import builtins, tempfile
                from pathlib import Path
                from necroprobe import shop_walk as walk
                original=builtins.__import__; loads=[]
                def counted(name, globals=None, locals=None, fromlist=(), level=0):
                    if name=='PIL' or any(x in ('navigation_stats','motion_stats') for x in (fromlist or ())):
                        loads.append((name,fromlist))
                    return original(name,globals,locals,fromlist,level)
                builtins.__import__=counted
                if OPERATION=='schema':
                    with tempfile.TemporaryDirectory() as folder:
                        r=walk.new_report(1,'e'*32);walk.write(folder,r)
                        walk.read_report(Path(folder)/'report.json',r['run_id'],r['start_ns'])
                else:
                    from necroprobe import beat_sync
                    assert not beat_sync._model_valid({})
                assert not loads, loads
            """).replace('OPERATION', repr(operation))
            result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True)
            with self.subTest(operation=operation):
                self.assertEqual(0,result.returncode,result.stderr)
    def test_report_factory_does_not_initialize_image_or_native_engines(self):
        original = builtins.__import__
        imports = []
        def recorded(name, globals=None, locals=None, fromlist=(), level=0):
            if name == 'PIL' or any(item in ('navigation_stats', 'motion_stats') for item in (fromlist or ())):
                imports.append((name, fromlist))
            return original(name, globals, locals, fromlist, level)
        with patch('builtins.__import__', side_effect=recorded):
            report = walk.new_report(1, 'e' * 32)
        self.assertEqual([], imports)
        self.assertIsNone(report['walk']['pillow_version'])
        self.assertIsNone(report['walk']['navigation_engine'])
        self.assertIsNone(report['walk']['motion_engine'])


from contextlib import contextmanager
from copy import deepcopy
import tempfile
from pathlib import Path
from necroprobe import shop_navigation as nav
from necroprobe.protocol import RpcReply
from necroprobe.validation import ProbeError
import test_shop_walk as old
from test_route_sequence import route_scene


class MixedDriverTests(unittest.TestCase):
    build = old.SyncDeadlineTests.build
    measured_runtime = old.SyncDeadlineTests.measured_runtime

    @contextmanager
    def prepared(self):
        with tempfile.TemporaryDirectory() as folder, self.measured_runtime(folder) as values:
            driver, now, captures, _, sent = values
            before, model = driver.synchronize(driver.observe())
            scene = route_scene()
            before['_extra']['scene'] = scene
            # Fresh synthetic clock isolates dispatch contracts; not a device-cost replay.
            before['_captured'] = now[0]
            model['last_sample_ns'] = now[0]
            decision = {'direction':'left', 'reason':'observed_floor_vantage', 'target':(-1,-1)}
            with patch.object(driver, 'choose', return_value=decision):
                yield driver, now, captures, sent, before, model, folder, decision

    def test_two_directions_use_adjacent_live_beats_and_persist_the_plan(self):
        with self.prepared() as (d, now, captures, sent, before, model, folder, decision):
            self.assertEqual(('left','up'), d.route_directions(before, decision, 16))
            count = d.perform('left', before, model, count=2, directions=('left','up'))
            self.assertEqual(2, count)
            self.assertEqual([walk.move_batch('left'), walk.move_batch('up')], sent)
            first, second = d.state['actions']
            self.assertEqual(model['period_ns'], second['target_ns']-first['target_ns'])
            self.assertEqual(model['period_ns'], second['issued_ns']-first['issued_ns'])
            self.assertEqual(['left','up'], first['planned_directions'])
            self.assertEqual([2,0], [first['planned_inputs'],second['planned_inputs']])
            self.assertFalse(d.pending)
            self.assertIsNone(d._followup_token)
            walk.read_report(Path(folder)/'report.json',d.outer['run_id'],d.outer['start_ns'])

    def test_partial_late_prefix_never_sends_or_retargets_second(self):
        with self.prepared() as (d, now, captures, sent, before, model, folder, decision):
            call=d.client.call
            def late(method,params,timeout):
                reply=call(method,params,timeout)
                if method=='run_steps':now[0]+=model['period_ns']+walk.DISPATCH_LATE_NS+1
                return reply
            with patch.object(d.client,'call',side_effect=late):
                count=d.perform('left',before,model,count=2,directions=('left','up'))
            self.assertEqual(1,count);self.assertEqual([walk.move_batch('left')],sent)
            self.assertEqual('not_requested',d.state['actions'][-1]['outcome'])
            self.assertFalse(d.pending);self.assertIsNone(d._followup_token)

    def test_source_mutation_cancel_and_unknown_ack_never_issue_more_inputs(self):
        for fault in ('scene','cancel','model_epoch','model_sample','unknown_first','unknown_second'):
            with self.subTest(fault=fault),self.prepared() as (d, now, captures, sent, before, model, folder, decision):
                call=d.client.call
                def faulty(method,params,timeout):
                    reply=call(method,params,timeout)
                    if method=='run_steps':
                        if fault=='scene':d.scene(before).protected.add((-1,-1))
                        elif fault=='cancel':walk.base.supervisor._cancel_requested=True
                        elif fault=='model_epoch' and len(sent)==1:model['epoch_ns']+=model['period_ns']//2
                        elif fault=='model_sample' and len(sent)==1:model['last_sample_ns']+=1000
                        elif fault.startswith('unknown') and len(sent)==(1 if fault=='unknown_first' else 2):return RpcReply({}, {})
                    return reply
                try:
                    with patch.object(d.client,'call',side_effect=faulty):
                        with self.assertRaises(ProbeError):d.perform('left',before,model,count=2,directions=('left','up'))
                    self.assertEqual(2 if fault=='unknown_second' else 1,len(sent))
                    if fault.startswith('unknown'):
                        self.assertTrue(d.pending)
                        calls=len(d.client.calls);d.finish('batch_unknown',None)
                        self.assertEqual(calls,len(d.client.calls))
                finally:walk.base.supervisor._cancel_requested=False

    def test_route_events_are_a_contiguous_non_overlapping_issued_prefix(self):
        from pathlib import Path
        with self.prepared() as (d, now, captures, sent, before, model, folder, decision):
            for index in (1,3):
                d.last=before;before['_captured']=now[0];model['last_sample_ns']=now[0]
                d.perform('left',before,model,count=2,directions=('left','up'))
                d.state['position']=[-(index+1)//2,-(index+1)//2]
                d.state['moves_confirmed']=index+1
                d.note_step(index,'left',before,before,'moved',dict(decision,directions=('left','up'),displacement=[-1,-1]),2)
            path=Path(folder)/'report.json'
            walk.read_report(path,d.outer['run_id'],d.outer['start_ns'])
            original=deepcopy(d.outer)
            for fault in ('duplicate','gap','overlap','missing_prefix'):
                r=deepcopy(original)
                if fault=='duplicate':
                    r['walk']['events'].append(deepcopy(r['walk']['events'][-1]))
                    r['walk']['position']=[-3,-3];r['walk']['moves_confirmed']=6
                elif fault=='gap':r['walk']['events'][0]['index']=3
                elif fault=='overlap':r['walk']['events'][1]['index']=1
                else:
                    r['walk']['events'].pop(0);r['walk']['position']=[-1,-1];r['walk']['moves_confirmed']=2
                walk.write(folder,r)
                with self.subTest(fault=fault),self.assertRaises((ValueError,ProbeError)):
                    walk.read_report(path,r['run_id'],r['start_ns'])

    def test_report_rejects_plan_prefix_and_observed_position_disagreement(self):
        with self.prepared() as (d, now, captures, sent, before, model, folder, decision):
            from pathlib import Path
            d.perform('left',before,model,count=2,directions=('left','up'))
            d.state['position']=[-1,-1];d.state['moves_confirmed']=2
            d.note_step(1,'left',before,before,'moved',dict(decision,directions=('left','up'),displacement=[-1,-1]),2)
            path=Path(folder)/'report.json'
            walk.read_report(path,d.outer['run_id'],d.outer['start_ns'])
            original=deepcopy(d.outer)
            for fault in ('sequence','delta','count','position','moves','actions','planned'):
                r=deepcopy(original)
                if fault=='sequence':r['walk']['events'][0]['directions']=['left','down']
                elif fault=='delta':r['walk']['events'][0]['displacement']=[-1,0]
                elif fault=='count':r['walk']['events'][0]['scheduled_inputs']=1
                elif fault=='position':r['walk']['position']=[0,0]
                elif fault=='moves':r['walk']['moves_confirmed']=1
                elif fault=='planned':r['walk']['actions'][0]['planned_directions']=['left','down']
                else:r['walk']['actions'][1]['action']='down'
                walk.write(folder,r)
                with self.subTest(fault=fault),self.assertRaises((ValueError,ProbeError)):
                    walk.read_report(path,r['run_id'],r['start_ns'])


class MixedWalkCreditTests(unittest.TestCase):
    def test_walk_credits_measured_vector_and_stops_on_partial_or_unknown(self):
        class RouteDriver(old.Fake):
            def __init__(self, outcome, delta):
                super().__init__([old.obs(), old.obs(), old.obs('visible')])
                self.outcome=outcome; self.delta=delta; self.notes=[]; self.state['lead_confirmed']=True
            def route_directions(self,*args): return ('left','up')
            def route_movement(self,*args): return {'motion':self.outcome,'delta':self.delta}
            def perform(self,action,frame,model=None,count=1,directions=None):
                return super().perform(action,frame,model,count)
            def note_step(self,*args): self.notes.append(args)
        for outcome,delta,position,moves in (
                ('moved',(-1,-1),[-1,-1],2),('partial',(-1,0),[-1,0],1),
                ('partial',(0,-1),[0,-1],1),('blocked',(0,0),[0,0],0),
                ('unknown',None,[0,0],0),('unexpected',(1,1),[0,0],0)):
            d=RouteDriver(outcome,delta); walk.walk(d)
            with self.subTest(outcome=outcome,delta=delta):
                self.assertEqual(position,d.state['position']); self.assertEqual(moves,d.state['moves_confirmed'])
                self.assertEqual(4 if outcome=='moved' else 3,len(d.sent))  # resume, one/two groups, pause
                self.assertEqual(['left','up'],list(d.notes[0][5]['directions']))
                self.assertEqual(list(delta) if delta is not None else None,d.notes[0][5]['displacement'])

    def test_trimmed_mixed_prefix_is_checked_as_one_original_direction(self):
        class One(old.Fake):
            def __init__(self):
                super().__init__([old.obs(),old.obs(),old.obs('visible')],['moved'])
                self.expected=[];self.notes=[];self.state['lead_confirmed']=True
            def route_directions(self,*args):return ('left','up')
            def perform(self,action,frame,model=None,count=1,directions=None):
                super().perform(action,frame,model,count);return 1
            def movement(self,*args,expected_steps=1):self.expected.append(expected_steps);return super().movement(*args,expected_steps=expected_steps)
            def route_movement(self,*args):raise AssertionError('unsent second direction')
            def note_step(self,*args):self.notes.append(args)
        d=One();walk.walk(d)
        self.assertEqual([1],d.expected);self.assertEqual([-1,0],d.state['position'])
        self.assertEqual(1,d.state['moves_confirmed']);self.assertEqual(('left',),d.notes[0][5]['directions'])


if __name__ == '__main__':
    unittest.main()
