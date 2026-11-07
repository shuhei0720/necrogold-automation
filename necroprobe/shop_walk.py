"""TEST-042: 経路準備・拍同期・送信待機の重複を減らす限定版。

HTTP中点と150ms先行は未校正の推定。予定拍での実受付を保証しない。
"""
import time
_MODULE_STARTED_NS=time.monotonic_ns()

from copy import deepcopy
from datetime import datetime, timezone
import json
import math
import re
from pathlib import Path
import shutil
import signal
import sys
import tempfile
import uuid

from . import VERSION, restart_loop as base
from .validation import ProbeError, json_object
from .input_timing import LEADS_NS,OBSERVE_DELAY_NS,eligible as timing_eligible
from .dispatch_wait import wait_until

REVISION='shop-walk-v27'
STARTUP_KEYS=('parent_module_started_ns','parent_report_ready_ns','worker_module_started_ns',
    'worker_entered_ns','worker_validated_ns','pairing_ready_ns','crypto_ready_ns',
    'driver_ready_ns','launch_ready_ns','first_observe_ns','first_capture_ns','first_seen_ns')
MOVE_POINTS={'up':(290,838),'down':(124,838),'left':(207,49),'right':(207,838)}
DIRECTIONS={'up':(0,-1),'down':(0,1),'left':(-1,0),'right':(1,0)}
MAX_STEPS=16
MAX_SEQUENCE=4
MAX_REFRESHES=2
MAX_ACTIONS=2*MAX_STEPS+MAX_REFRESHES+2
WALK_SECONDS=45
SYNC_SECONDS=12
MAX_RESTARTS=12
LEAD_NS=150_000_000
# 予定送信時刻からのホスト待機遅れ上限。ゲームの入力受付幅/精度保証ではない。
DISPATCH_LATE_NS=10_000_000
MAX_TARGET_ATTEMPTS=2
PAUSE_FRAME_NS=2_000_000_000  # 通常の停止準備へ1秒を残す。最終3秒チェックは維持。
RPC_TIMING_FIELDS=('request_start_ns','http_start_ns','http_end_ns','response_end_ns')
REASONS={'goods_visible','goods_partial','no_safe_path','movement_unconfirmed','unexpected_movement',
         'beat_unconfirmed','beat_sync_timeout','walk_limit','gold_not_found','approach','navigation_unknown',
         'walk_analysis_failed','dispatch_window_expired','sequence_window_short','timing_not_found','timing_scene_changed'}
FAILURE_KINDS={'TypeError','ValueError','AttributeError','IndexError','KeyError','OverflowError','MemoryError','RuntimeError','other'}
VERSION_PATTERN=r'[0-9][0-9A-Za-z.+_-]{0,31}'


def code(reason):return reason if reason in REASONS else base.code(reason)


def move_batch(direction,count=1,period_ns=None):
    if (direction not in MOVE_POINTS or type(count) is not int or count!=1
            or period_ns is not None):raise ProbeError('method_not_allowed')
    x,y=MOVE_POINTS[direction]
    fingers=[[{'x':x,'y':y,'t':0},{'x':x,'y':y,'t':.05}]]
    return {'steps':[{'method':'wait_for','params':{'foreground':base.GAME,'timeout':.5}},
        {'method':'gesture','params':{'fingers':fingers}}],
        'observe':'none'}


class WalkClient(base.RestartClient):
    walking=False
    def _validate(self,method,params):
        if method=='run_steps':
            if self.walking and any(base.resume.exact(params,move_batch(d)) for d in MOVE_POINTS):return
            if self.walking and base.resume.exact(params,base.batch('restart')):raise ProbeError('method_not_allowed')
        return super()._validate(method,params)


def gesture_evidence(result):
    if type(result) is not dict:return 'unknown'
    result=deepcopy(result)
    steps=result.get('steps')
    if type(steps) is list and len(steps)==2 and type(steps[1]) is dict:
        if steps[1].get('method')!='gesture':return 'unknown'
        steps[1]['method']='tap'
    return base.resume.batch_evidence(result)[0]


def new_walk():
    return {'started_ns':None,'end_ns':None,'reason':None,'goods_visible':False,'paused':False,
        'device_timing_verified':False,'dispatch_timing_calibrated':False,'dispatch_lead_ns':LEAD_NS,
        'lead_confirmed':False,'lead_trials':[],
        'position':[0,0],'moves_confirmed':0,'door_changes':0,'terrain_changes':0,'actions':[],'events':[],
        'samples':[],'models':[],'input_pending':False,
        'navigation_ms':[],'beat_extract_ms':[],'motion_ms':[],'beat_fit_ms':[],
        'failure':None,'pillow_version':None,'navigation_engine':None,'motion_engine':None}


def new_report(start,run_id):
    return {'version':VERSION,'test_id':'TEST-042','revision':REVISION,'run_id':run_id,
        'start_ns':start,'end_ns':None,'phase':'search','status':'running','reason':None,
        'control_reason':None,'control_end_ns':None,'worker_returncode':None,'worker_exit_confirmed':None,
        'search':base.new_report(start,run_id),'walk':new_walk(),
        'startup':dict.fromkeys(STARTUP_KEYS),'worker_mode':None}


def write(folder,report,name='report.json'):
    base.atomic_write(Path(folder)/name,json.dumps(report,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode())


def read_report(path,run_id,start):
    with Path(path).open('rb') as source:r=json_object(source.read(131073),131072)
    req=base.supervisor.require
    req(type(r) is dict and set(r)==set(new_report(start,run_id)))
    for k,v in [('version',VERSION),('test_id','TEST-042'),('revision',REVISION),('run_id',run_id),('start_ns',start)]:
        req(type(r[k]) is type(v) and r[k]==v)
    req(r['phase'] in ('search','walk','done'))
    req(r['status'] in ('running','completed','stopped'))
    req(r['worker_mode'] is None or type(r['worker_mode']) is str and r['worker_mode'] in ('fork','exec'))
    startup=r['startup'];req(type(startup) is dict and set(startup)==set(STARTUP_KEYS))
    stamps=[]
    for key in STARTUP_KEYS:
        value=startup[key]
        req(value is None or type(value) is int and 0<=value<2**63)
        if value is not None:
            req(key=='parent_module_started_ns' or start<=value)
            stamps.append(value)
    req(stamps==sorted(stamps))
    req(startup['parent_module_started_ns'] is None or startup['parent_module_started_ns']<=start)
    req(startup['parent_report_ready_ns'] is None or start<=startup['parent_report_ready_ns'])
    req(r['end_ns'] is None or type(r['end_ns']) is int and all(v<=r['end_ns'] for v in stamps))
    for key in ('reason','control_reason'):req(r[key] is None or type(r[key]) is str and code(r[key])==r[key])
    for key in ('end_ns','control_end_ns'):req(r[key] is None or type(r[key]) is int and start<=r[key]<2**63)
    req(r['worker_exit_confirmed'] is None or type(r['worker_exit_confirmed']) is bool)
    req(r['worker_returncode'] is None or type(r['worker_returncode']) is int and -255<=r['worker_returncode']<=255)
    base.validate_report(r['search'],run_id,start)
    w=r['walk'];req(type(w) is dict and set(w)==set(new_walk()))
    for engine in ('navigation_engine','motion_engine'):
        req(w[engine] is None or type(w[engine]) is str and w[engine] in (('native_i386','pillow','native_i386+pillow') if engine=='motion_engine' else ('native_i386','pillow')))
    req(w['pillow_version'] is None or type(w['pillow_version']) is str and re.fullmatch(VERSION_PATTERN,w['pillow_version']) is not None)
    failure=w['failure']
    req(failure is None or type(failure) is dict and set(failure)=={'stage','kind'}
        and type(failure['stage']) is str and type(failure['kind']) is str
        and failure['stage'] in ('navigation','beat_extract','control') and failure['kind'] in FAILURE_KINDS)
    for key in ('goods_visible','paused','input_pending','lead_confirmed'):req(type(w[key]) is bool)
    req(w['device_timing_verified'] is False and w['dispatch_timing_calibrated'] is False and type(w['dispatch_lead_ns']) is int and w['dispatch_lead_ns'] in LEADS_NS)
    trials=w['lead_trials'];req(type(trials) is list and len(trials)<=len(LEADS_NS))
    for i,trial in enumerate(trials):
        req(type(trial) is dict and set(trial)=={'lead_ns','direction','motion'})
        req(type(trial['lead_ns']) is int and trial['lead_ns']==LEADS_NS[i])
        req(type(trial['direction']) is str and trial['direction'] in MOVE_POINTS)
        req(type(trial['motion']) is str and trial['motion'] in ('moved','blocked'))
        req(trial['motion']=='blocked' or i==len(trials)-1)
    if trials:
        req(w['lead_confirmed']==(trials[-1]['motion']=='moved'))
        wanted=len(trials)-1 if w['lead_confirmed'] else min(len(trials),len(LEADS_NS)-1)
        req(w['dispatch_lead_ns']==LEADS_NS[wanted])
    else:
        req(w['lead_confirmed'] is False and w['dispatch_lead_ns']==LEADS_NS[0])
    req(w['reason'] is None or type(w['reason']) is str and code(w['reason'])==w['reason'])
    for key in ('started_ns','end_ns'):req(w[key] is None or type(w[key]) is int and start<=w[key]<2**63)
    req(type(w['position']) is list and len(w['position'])==2 and all(type(v) is int and -16<=v<=16 for v in w['position']))
    for key in ('moves_confirmed','door_changes','terrain_changes'):req(type(w[key]) is int and 0<=w[key]<=MAX_STEPS)
    for key,limit in [('actions',MAX_ACTIONS),('events',MAX_STEPS),('samples',12),('models',MAX_STEPS+1)]:
        req(type(w[key]) is list and len(w[key])<=limit and all(type(v) is dict for v in w[key]))
    if w['samples'] or w['models']:
        from . import beat_sync
        req(all(beat_sync._sample_valid(sample) for sample in w['samples']))
        req(all(beat_sync._model_valid(model,required_profile=beat_sync.ZONE1_1_PROFILE) for model in w['models']))
    for a in w['actions']:
        action_keys={'action','outcome','reason','requested_ns','issued_ns','completed_ns','target_ns','rpc_timings','target_checks',
                    'requested_inputs','scheduled_inputs','period_ns','planned_inputs','dispatch_lead_ns'}
        req(set(a) in (action_keys,action_keys|{'planned_directions'}))
        timings=a['rpc_timings']
        req(type(timings) is dict and set(timings)<=set(RPC_TIMING_FIELDS))
        req(all(type(value) is int and start<=value<2**63 for value in timings.values()))
        req(a['action'] in (*MOVE_POINTS,'resume','pause'))
        req(type(a['requested_inputs']) is int and type(a['scheduled_inputs']) is int)
        req(0<=a['scheduled_inputs']<=a['requested_inputs']<=1)
        req(a['requested_inputs']==1 if a['action'] in MOVE_POINTS else a['requested_inputs']==0)
        req(a['period_ns'] is None)
        req(type(a['dispatch_lead_ns']) is int and a['dispatch_lead_ns'] in LEADS_NS
            if a['action'] in MOVE_POINTS else a['dispatch_lead_ns'] is None)
        req(type(a['planned_inputs']) is int and 0<=a['planned_inputs']<=MAX_SEQUENCE)
        req(a['action'] in MOVE_POINTS or a['planned_inputs']==0)
        if 'planned_directions' in a:
            seq=a['planned_directions']
            req(type(seq) is list and len(seq)==2 and all(type(d) is str and d in MOVE_POINTS for d in seq))
            req(a['action']==seq[0] and a['planned_inputs']==2
                and sum(x*y for x,y in zip(DIRECTIONS[seq[0]],DIRECTIONS[seq[1]]))==0)
        checks=a['target_checks']
        req(type(checks) is list and len(checks)<=MAX_TARGET_ATTEMPTS)
        req(a['action'] in MOVE_POINTS or not checks)
        for check in checks:
            req(type(check) is dict and set(check) in ({'target_ns','checked_ns','status'},
                                                     {'target_ns','checked_ns','status','window'}))
            req(all(type(check[key]) is int and start<=check[key]<2**63 for key in ('target_ns','checked_ns')))
            req(type(check['status']) is str and check['status'] in ('ready','late','expired'))
            if 'window' in check:
                window=check['window']
                req(type(window) is dict and set(window)=={'stage','frame_ns','phase_ns','foreground_ns','required_end_ns'})
                req(type(window['stage']) is str and window['stage'] in ('preflight','dispatch','followup'))
                req(all(type(window[key]) is int and 0<=window[key]<2**63
                        for key in ('frame_ns','phase_ns','foreground_ns','required_end_ns')))
        req(a['outcome'] in ('not_requested','unknown','not_sent','acknowledged'))
        req(a['reason'] is None or type(a['reason']) is str and code(a['reason'])==a['reason'])
        for k in ('requested_ns','issued_ns','completed_ns','target_ns'):
            req(a[k] is None or type(a[k]) is int and start<=a[k]<2**63)
    req(sum(a['scheduled_inputs'] for a in w['actions'])<=MAX_STEPS)
    for i,a in enumerate(w['actions'][:-1]):
        if 'planned_directions' not in a:continue
        following=w['actions'][i+1]
        if following['action'] in DIRECTIONS and following['planned_inputs']==0:
            req(a['outcome']=='acknowledged' and a['scheduled_inputs']==1
                and following['action']==a['planned_directions'][1])
    if any('directions' in e or 'displacement' in e for e in w['events']):
        issued=[a for a in w['actions'] if a['scheduled_inputs']==1]
        position=[0,0];moves=0;next_index=1
        event_keys={'index','direction','motion','before_sha256','after_sha256','image','target','goods','scheduled_inputs'}
        for e in w['events']:
            routed='directions' in e or 'displacement' in e
            req(set(e)==(event_keys|{'directions','displacement'} if routed else event_keys))
            req(type(e['index']) is int and 1<=e['index']<=MAX_STEPS)
            req(type(e['scheduled_inputs']) is int and 1<=e['scheduled_inputs']<=MAX_SEQUENCE)
            req(type(e['direction']) is str and e['direction'] in DIRECTIONS)
            delta=None;count=e['scheduled_inputs']
            req(e['index']==next_index and next_index-1+count<=len(issued))
            completed=issued[next_index-1:next_index-1+count]
            req(all(a['outcome']=='acknowledged' for a in completed))
            if not routed:req([a['action'] for a in completed]==[e['direction']]*count)
            next_index+=count
            if routed:
                seq=e['directions'];delta=e['displacement']
                req(type(seq) is list and 1<=len(seq)<=2 and len(seq)==count
                    and all(type(d) is str and d in DIRECTIONS for d in seq) and seq[0]==e['direction'])
                req(len(seq)==1 or sum(x*y for x,y in zip(DIRECTIONS[seq[0]],DIRECTIONS[seq[1]]))==0)
                start_index=e['index']-1
                req([a['action'] for a in issued[start_index:start_index+count]]==seq)
                req('planned_directions' in issued[start_index]
                    and seq==issued[start_index]['planned_directions'][:count])
                req(delta is None or type(delta) is list and len(delta)==2
                    and all(type(v) is int and -2<=v<=2 for v in delta))
                expected=[sum(DIRECTIONS[d][axis] for d in seq) for axis in (0,1)]
                if e['motion']=='moved':req(delta==expected)
                elif e['motion']=='partial':req(len(seq)==2 and delta in [list(DIRECTIONS[d]) for d in seq])
                elif e['motion'] in ('blocked','door_opened','terrain_opened'):req(delta==[0,0])
                else:req(e['motion'] in ('unknown','unexpected','tween','goods_visible'))
            if e['motion'] in ('moved','partial','gate_entered'):
                if not routed:
                    credited=count if e['motion']=='moved' else 1
                    delta=[v*credited for v in DIRECTIONS[e['direction']]]
                req(delta is not None)
                position=[p+v for p,v in zip(position,delta)];moves+=sum(abs(v) for v in delta)
        req(w['position']==position and w['moves_confirmed']==moves)
    for key in ('navigation_ms','beat_extract_ms','motion_ms','beat_fit_ms'):
        req(type(w[key]) is list and len(w[key])<=240)
        req(all(type(v) in (float,int) and math.isfinite(v) and 0<=v<=180_000 for v in w[key]))
    return r


class Driver(base.RuntimeDriver):
    def __init__(self,client,outer,folder,stop_ns,control,clock=time.monotonic_ns):
        # 初回importの準備費用を撮影済み画像の鮮度へ持ち込まない。
        # TEST022初回fullの遅延原因がimportだけだったとは未確定。
        from . import beat_sync,shop_navigation,navigation_stats,motion_stats,route_sequence
        from PIL import __version__ as pillow_version
        self.outer=outer;self.state=outer['walk'];self.model=None;self.samples=[];self.visits={(0,0):1}
        self.state.update(pillow_version=pillow_version if isinstance(pillow_version,str) and re.fullmatch(VERSION_PATTERN,pillow_version) else None,
                          navigation_engine=navigation_stats.ENGINE,motion_engine=motion_stats.ENGINE)
        self.analysis_failed=False;self.finishing=False;self.finish_refresh_attempted=False;self.sync_deadline=None
        self.beat_only=False;self.tracked_frame=None;self._followup_token=None;self.entrance=None
        self.timing_anchor=None;self.handoff_frame=None;self.handoff_rejected=False
        self.spin_wait=None
        self._route_choice=None;self._prepared_route=None
        super().__init__(client,outer['search'],folder,stop_ns,clock,control,self.analyze_frame)
    def budget(self):
        if base.supervisor._cancel_requested:raise ProbeError('cancelled')
        remaining=super().budget()
        # observeの前面照会中にも時間は進む。screenshot直前のbudgetで再検査する。
        # 終了後のポーズ確認は歩行継続とは別なので、session期限内で従来どおり許可する。
        if (not self.finishing and self.outer['phase']=='walk' and self.state['started_ns'] is not None
                and self.clock()-self.state['started_ns']>=WALK_SECONDS*1_000_000_000):
            raise ProbeError('walk_limit')
        # observe内の前面確認が長引いても、期限後のscreenshotを開始しない。
        if self.sync_deadline is not None and self.clock()>=self.sync_deadline:
            self.model=None
            raise ProbeError('beat_sync_timeout')
        return remaining
    def record_failure(self,stage,exc):
        if self.state['failure'] is None:
            kind=type(exc).__name__
            self.state['failure']={'stage':stage,'kind':kind if kind in FAILURE_KINDS else 'other'}
    def analyze_frame(self,image,obs):
        candidate=(self.outer['phase']=='search' and obs['state']=='floor' and obs.get('gold')=='candidate')
        if ((self.outer['phase']!='walk' and not candidate) or obs['state']!='floor'
                or self.analysis_failed or self.finishing):return None
        from . import beat_sync,shop_navigation,navigation_stats
        stage='navigation';scene=None
        try:
            if candidate or not self.beat_only:
                begin=self.clock()
                try:scene=shop_navigation.scan(image)
                finally:
                    self.state['navigation_ms'].append((self.clock()-begin)/1e6)
                    self.state['navigation_engine']=navigation_stats.ENGINE
            stage='beat_extract';begin=self.clock()
            try:beat=beat_sync.extract(image)
            finally:self.state['beat_extract_ms'].append((self.clock()-begin)/1e6)
            return {'scene':scene,'beat':beat}
        except ProbeError:raise
        except Exception as exc:
            self.record_failure(stage,exc);self.analysis_failed=True
            # 基本の画像検証・分類・時刻・原画像はsuper.observeに保存させる。
            # beatだけ失敗した場合も、既に得られた商品可視は失わない。
            return {'scene':scene,'beat':None} if scene is not None else None
    def checkpoint(self):
        before=self.clock();write(self.control_dir,self.outer)
        if len(self.report['checkpoint_ms'])<512:self.report['checkpoint_ms'].append((self.clock()-before)/1e6)
    def classify_frame(self,image):
        from .gold_scan import analyze_image
        return analyze_image(image,scan_gold=False) if self.outer['phase']=='walk' else analyze_image(image)
    def capture_started(self,started):
        if self.outer['startup']['first_capture_ns'] is None:
            self.outer['startup']['first_capture_ns']=started
    def observe(self):
        if self.outer['startup']['first_observe_ns'] is None:
            self.outer['startup']['first_observe_ns']=self.clock()
        observed=super().observe()
        if self.outer['startup']['first_seen_ns'] is None:
            self.outer['startup']['first_seen_ns']=observed['_seen_ns']
        if self.outer['phase']=='walk':self.report['analysis_engine']='pillow'
        if self.outer['phase']=='walk' and self.goods(observed)=='visible' and not self.state['goods_visible']:
            self.state['goods_visible']=True
            self.save('found.jpg',observed)
            self.checkpoint()
        if self.analysis_failed and not self.finishing and self.outer['phase']=='walk':raise ProbeError('walk_analysis_failed')
        return observed
    def accept_candidate(self,obs):
        """検索がlatchした候補を一度だけ歩行へ渡す。拒否時は検索側が保持する。"""
        self.budget()
        def reject():
            self.handoff_rejected=True;self.handoff_frame=None
            return False
        if (self.outer['phase']!='search' or obs is not self.last or obs.get('state')!='floor'
                or obs.get('gold')!='candidate' or self.pending or self.state['input_pending']
                or not 0<=self.clock()-obs['_captured']<=3_000_000_000):return reject()
        scene=self.scene(obs);extra=obs.get('_extra') or {}
        if scene is None:return reject()
        if scene.goods!='visible' and (self.analysis_failed or not scene.gold or extra.get('beat') is None):return reject()
        self.handoff_frame=obs
        return True
    def scene(self,obs):
        extra=obs.get('_extra')
        return extra.get('scene') if extra else None
    def goods(self,obs):
        scene=self.scene(obs)
        return scene.goods if scene is not None else 'unknown'
    def choose(self,obs):
        from .shop_navigation import choose
        scene=self.scene(obs)
        self._route_choice=None;self._prepared_route=None
        if scene is None:return {'direction':None,'reason':'navigation_unknown','target':None}
        context=self.route_context(obs)
        decision=choose(scene,tuple(self.state['position']),self.visits,entrance=self.entrance)
        if context is not None:self._route_choice=(decision,deepcopy(decision),context)
        return decision
    def route_context(self,obs):
        from .shop_navigation import Scene
        scene=self.scene(obs)
        if not isinstance(scene,Scene):return None
        return {'obs':obs,'scene':scene,
            'scene_state':(scene.tiles.copy(),scene.gold.copy(),scene.protected.copy(),scene.goods,scene.signature),
            'frame':tuple(obs.get(k) for k in ('state','_captured','_sha','_http_start_ns','_http_end_ns','_seen_ns')),
            'position':tuple(self.state['position']),'visits':self.visits.copy(),'entrance':deepcopy(self.entrance),
            'lead':self.state['dispatch_lead_ns'],'confirmed':self.state['lead_confirmed'],
            'trials':deepcopy(self.state['lead_trials']),'model':self.model,'model_state':deepcopy(self.model),
            'issued':sum(a['scheduled_inputs'] for a in self.state['actions'])}
    def route_context_matches(self,context,obs,model,ordinal=0):
        return (context['obs'] is obs and self.scene(obs) is context['scene']
            and self.route_scene_matches(context['scene'],context['scene_state'])
            and tuple(obs.get(k) for k in ('state','_captured','_sha','_http_start_ns','_http_end_ns','_seen_ns'))==context['frame']
            and tuple(self.state['position'])==context['position'] and self.visits==context['visits']
            and self.entrance==context['entrance'] and self.state['dispatch_lead_ns']==context['lead']
            and self.state['lead_confirmed']==context['confirmed'] and self.state['lead_trials']==context['trials']
            and self.model is context['model'] and model is context['model'] and model==context['model_state']
            and sum(a['scheduled_inputs'] for a in self.state['actions'])==context['issued']+ordinal)
    def burst_count(self,obs,decision,remaining):
        from .shop_navigation import burst_count,closed_gate,closed_gate_entry,DIRECTIONS
        direction=decision.get('direction') if isinstance(decision,dict) else None
        if not self.timing_route_allowed(obs,direction):return 0
        if not self.state['lead_confirmed'] and timing_eligible(self.scene(obs),direction):return min(1,remaining)
        if (isinstance(direction,str) and direction in DIRECTIONS and decision.get('reason')=='gate_single_probe'
                and decision.get('target')==DIRECTIONS[direction]
                and closed_gate(self.scene(obs),direction)):
            return 2 if remaining>=2 and closed_gate_entry(self.scene(obs),direction) else 0
        return min(remaining,burst_count(self.scene(obs),decision,tuple(self.state['position']),entrance=self.entrance,limit=MAX_SEQUENCE))
    def route_directions(self,obs,decision,remaining):
        selected=self._route_choice;self._route_choice=None;self._prepared_route=None
        authentic=selected is not None and selected[0] is decision
        if authentic and (decision!=selected[1] or obs is not self.last
                or not self.route_context_matches(selected[2],obs,self.model)):
            raise ProbeError('navigation_unknown')
        count=self.burst_count(obs,decision,remaining)
        result=(decision['direction'],)*count if count else ()
        if count==1 and remaining>=2 and self.state['lead_confirmed']:
            from .route_sequence import mixed_pair
            pair=mixed_pair(self.scene(obs),decision,tuple(self.state['position']),self.entrance)
            if pair:result=pair
        if authentic and result:
            if not self.route_context_matches(selected[2],obs,self.model):raise ProbeError('navigation_unknown')
            self._prepared_route={'context':selected[2],'directions':result,'decision':selected[0],
                                  'decision_state':selected[1]}
        return result
    def timing_route_allowed(self,obs,direction):
        trials=self.state['lead_trials']
        return (self.state['lead_confirmed'] or not trials or
                trials[-1]['motion']=='blocked' and direction==trials[-1]['direction']
                and timing_eligible(self.scene(obs),direction))
    def check_timing_scene(self,obs):
        """blocked試行後の基準は、未送信回復と同期をまたいでも保持する。"""
        if self.timing_anchor is None or self.goods(obs)=='visible':return
        gold,direction=self.timing_anchor
        scene=self.scene(obs)
        if (obs is not self.last or obs.get('state')!='floor' or not timing_eligible(scene,direction)
                or frozenset(scene.gold)!=gold or self.choose(obs).get('direction')!=direction):
            raise ProbeError('timing_scene_changed')
    def timing_result(self,before,after,direction,outcome,count):
        state=self.state;trials=state['lead_trials']
        if (state['lead_confirmed'] or self.pending or state['input_pending'] or count!=1
                or outcome not in ('moved','blocked') or not timing_eligible(self.scene(before),direction)
                or after is not self.last or after.get('state')!='floor' or not state['actions']):return None
        entry=state['actions'][-1];captured=after.get('_http_start_ns');now=self.clock()
        if (entry.get('action')!=direction or entry.get('outcome')!='acknowledged'
                or entry.get('scheduled_inputs')!=1 or type(entry.get('target_ns')) is not int
                or type(entry.get('completed_ns')) is not int or type(captured) is not int
                or not max(entry['target_ns']+OBSERVE_DELAY_NS,entry['completed_ns'])<=captured<=now
                or now-captured>3_000_000_000 or entry.get('dispatch_lead_ns')!=state['dispatch_lead_ns']
                or len(trials)>=len(LEADS_NS) or state['dispatch_lead_ns']!=LEADS_NS[len(trials)]):return None
        if outcome=='blocked' and (not timing_eligible(self.scene(after),direction)
                or self.scene(before).gold!=self.scene(after).gold or self.choose(after).get('direction')!=direction):return None
        trials.append({'lead_ns':state['dispatch_lead_ns'],'direction':direction,'motion':outcome})
        if outcome=='moved':
            state['lead_confirmed']=True
            print('拍入力: 先行%dmsで実際の1歩を確認。以降の連続入力に使用します。'%(state['dispatch_lead_ns']//1_000_000),flush=True)
            return None
        if len(trials)==len(LEADS_NS):return 'exhausted'
        state['dispatch_lead_ns']=LEADS_NS[len(trials)]
        print('拍入力: 移動0を画像で確認。次は先行%dmsで1歩を試します。'%(state['dispatch_lead_ns']//1_000_000),flush=True)
        return 'retry'
    def track_observation(self,after):
        # 変位照合の前に今回のHUDを追跡。重い処理後に古くなっても標本は失わない。
        if self.model is not None and after is self.last and after is not self.tracked_frame:
            sample=self.add_sample(after)
            updated=self.track_beat(self.model) if sample is not None else None
            self.model=updated;self.tracked_frame=after if updated is not None else None
            if updated is not None:self.remember_model(updated)
    def movement(self,before,after,direction,expected_steps=1):
        from .shop_navigation import motion,entered_gate,closed_gate_entry
        from . import motion_stats
        a,b=self.scene(before),self.scene(after)
        if a is None or b is None:return 'unknown'
        self.track_observation(after)
        before_ns=self.clock()
        try:
            gate_sequence=expected_steps==2 and closed_gate_entry(a,direction)
            result=motion(a,b,direction,expected_steps=1 if gate_sequence else expected_steps)
            if gate_sequence and result=='moved':
                context=entered_gate(a,b,direction,tuple(self.state['position']),2,result,door_sequence=True)
                if context is None:return 'unknown'
                if self.entrance is None:self.entrance=context
                return 'gate_entered'
            if self.entrance is None:
                self.entrance=entered_gate(a,b,direction,tuple(self.state['position']),expected_steps,result)
            return result
        finally:
            self.state['motion_ms'].append((self.clock()-before_ns)/1e6)
            self.state['motion_engine']='native_i386+pillow' if expected_steps>2 and motion_stats.ENGINE=='native_i386' else motion_stats.ENGINE
    def route_movement(self,before,after,directions):
        from .route_sequence import motion
        from . import motion_stats
        a,b=self.scene(before),self.scene(after)
        if a is None or b is None:return {'motion':'unknown','delta':None}
        self.track_observation(after);begin=self.clock()
        try:return motion(a,b,directions)
        finally:
            self.state['motion_ms'].append((self.clock()-begin)/1e6)
            self.state['motion_engine']='native_i386+pillow' if motion_stats.ENGINE=='native_i386' else 'pillow'
    def fit_beat(self):
        from .beat_sync import fit,ZONE1_1_PROFILE
        # gold_scanのfloor分類はfooter/zone_one/floor_one確認済みの1-1だけ。
        before=self.clock()
        result=fit(self.samples,profile=ZONE1_1_PROFILE) if self.last and self.last['state']=='floor' else None
        self.state['beat_fit_ms'].append((self.clock()-before)/1e6);return result
    def track_beat(self,model):
        from .beat_sync import track
        before=self.clock();result=track(model,self.samples)
        self.state['beat_fit_ms'].append((self.clock()-before)/1e6);return result
    def remember_model(self,model):
        self.state['models']=(self.state['models']+[model])[-(MAX_STEPS+1):]
    def add_sample(self,obs):
        from .beat_sync import make_sample
        extra=obs.get('_extra')
        if not extra or extra.get('beat') is None:return None
        sample=make_sample(extra['beat'],obs['_http_start_ns'],obs['_http_end_ns'])
        self.samples=(self.samples+[sample])[-12:];self.state['samples']=self.samples
        return sample
    def synchronize(self,obs):
        self.sync_deadline=self.clock()+SYNC_SECONDS*1_000_000_000
        try:return self._synchronize(obs,self.sync_deadline)
        except BaseException:
            self.model=None
            raise
        finally:self.beat_only=False;self.sync_deadline=None
    def _synchronize(self,obs,deadline):
        from . import beat_sync
        captures=0
        def check_deadline():
            self.budget()
            now=self.clock()
            if now>=deadline:
                self.model=None
                raise ProbeError('beat_sync_timeout')
            if now-self.state['started_ns']>=WALK_SECONDS*1_000_000_000:raise ProbeError('walk_limit')
        def capture():
            nonlocal captures
            check_deadline()
            # 渡された初期画像を除く全新規取得。full handoffも同じ枠で数える。
            if captures>=12:raise ProbeError('beat_unconfirmed')
            captures+=1
            frame=self.observe();check_deadline()
            return frame
        def latest_full(frame):
            return (frame is self.last and frame['state']=='floor' and self.scene(frame) is not None
                    and 0<=self.clock()-frame['_captured']<=beat_sync.FRESH_NS)
        def accept(frame,model):
            check_deadline()
            if not latest_full(frame):raise ProbeError('navigation_unknown')
            self.check_timing_scene(frame)
            if beat_sync.next_target(model,self.clock()) is None:raise ProbeError('beat_unconfirmed')
            self.remember_model(model)
            # 採用モデルは入力前のpending checkpointでまとめて永続化する。
            self.model=model
            self.tracked_frame=frame
            print('拍同期: 周期%.3f秒（実測1-1範囲内の条件付き推定）'%(model['period_ns']/1e9),flush=True)
            return frame,model
        def full_handoff(model):
            # 軽量標本は移動の基準にしない。地形とHUDを同じ新規画像で確認する。
            self.beat_only=False
            fresh=capture()
            if self.goods(fresh)=='visible':return fresh,None
            self.check_timing_scene(fresh)
            if not latest_full(fresh):raise ProbeError('navigation_unknown')
            latest=self.add_sample(fresh)
            updated=self.track_beat(model) if latest is not None else None
            check_deadline()
            return fresh,updated
        print('拍同期: 開始（最大%d秒）'%SYNC_SECONDS,flush=True)
        check_deadline()
        if self.goods(obs)=='visible':return obs,None
        self.check_timing_scene(obs)
        if self.model is not None:
            if obs is self.tracked_frame and latest_full(obs):return accept(obs,self.model)
            # 地形/位相が古くても周期の根拠は直ちに捨てず、full画像1回で追跡を試す。
            if not latest_full(obs):
                obs,updated=full_handoff(self.model)
                sample=self.samples[-1] if self.samples and self.samples[-1]['http_start_ns']==obs.get('_http_start_ns') else None
            else:
                sample=self.add_sample(obs)
                updated=self.track_beat(self.model) if sample is not None else None
                check_deadline()
            if self.goods(obs)=='visible':return obs,None
            if updated is not None:return accept(obs,updated)
            print('拍追跡: 条件不成立、同一期限内で初期取得へ戻る',flush=True)
        else:
            captured=obs.get('_captured')
            sample=self.add_sample(obs) if type(captured) is int and 0<=self.clock()-captured<=beat_sync.FRESH_NS else None
        # 追跡不成立時も同じ12秒枠内で初期取得する。旧window/周期は再利用しない。
        self.model=None
        self.samples=[] if sample is None else [sample]
        self.state['samples']=self.samples
        self.beat_only=True
        for i in range(13):
            check_deadline()
            print('拍標本: %d/4（取得%d/12）'%(len(self.samples),captures),flush=True)
            if len(self.samples)>=4:
                model=self.fit_beat();check_deadline()
                if model:
                    latest=self.samples[-1]
                    extra=obs.get('_extra') or {}
                    # fitに使った最新HUDと完全Sceneが同じ画像なら再撮影しない。
                    # 軽量画像や別画像の標本を、地形入力の根拠へ昇格させない。
                    if (self.scene(obs) is not None and extra.get('beat') is not None
                            and latest['http_start_ns']==obs.get('_http_start_ns')
                            and latest['http_end_ns']==obs.get('_http_end_ns')
                            and model['last_sample_ns']==latest['midpoint_ns']):
                        return accept(obs,model)
                    self.remember_model(model)
                    obs,updated=full_handoff(model)
                    if self.goods(obs)=='visible':return obs,None
                    if updated is not None:return accept(obs,updated)
                    print('拍追跡: full画像の更新不成立、同一期限内で初期取得へ戻る',flush=True)
                    # fullの位相が不整合なら、その新しい観測から取得し直す。
                    latest=self.samples[-1] if self.samples and self.samples[-1]['http_start_ns']==obs.get('_http_start_ns') else None
                    self.samples=[] if latest is None else [latest]
                    self.state['samples']=self.samples;self.beat_only=True
            if self.goods(obs)=='visible':
                check_deadline();return obs,None
            check_deadline();self.sleeper((.0,.07,.17)[i%3])
            check_deadline()
            # 4点目以降の候補をfullにし、成立時の余分なhandoff撮影を省く。
            self.beat_only=len(self.samples)<3
            obs=capture()
            if self.goods(obs)=='visible':
                check_deadline();return obs,None
            self.add_sample(obs)
        check_deadline()
        raise ProbeError('beat_unconfirmed')
    def perform(self,action,obs,model=None,count=1,directions=None):
        from . import beat_sync
        from .shop_navigation import closed_gate
        if self.pending or self.state['input_pending'] or obs is not self.last:raise ProbeError('method_not_allowed')
        lead=self.state['dispatch_lead_ns']
        if type(lead) is not int or lead not in LEADS_NS:raise ProbeError('method_not_allowed')
        moving=action in MOVE_POINTS
        movement_scene=self.scene(obs) if moving else None
        route_snapshot=None;route_model_snapshot=None
        prepared=self._prepared_route if moving else None
        self._prepared_route=None;self._route_choice=None
        if prepared is not None:
            expected=directions if directions is not None else (action,)*count if type(count) is int else ()
            if (prepared['directions']!=expected or prepared['decision']!=prepared['decision_state']
                    or not self.route_context_matches(prepared['context'],obs,model)):
                raise ProbeError('navigation_unknown')
            route_snapshot=prepared['context']['scene_state']
            route_model_snapshot=prepared['context']['model_state']
        if directions is not None:
            if (not moving or type(directions) is not tuple or len(directions)!=2 or count!=2
                    or any(type(d) is not str or d not in MOVE_POINTS for d in directions) or directions[0]!=action
                    or sum(x*y for x,y in zip(DIRECTIONS[directions[0]],DIRECTIONS[directions[1]]))!=0
                    or not self.state['lead_confirmed']):raise ProbeError('method_not_allowed')
            if prepared is None:
                planned=self.choose(obs)
                if directions!=self.route_directions(obs,planned,MAX_STEPS-sum(a['scheduled_inputs'] for a in self.state['actions'])):
                    raise ProbeError('method_not_allowed')
                route_snapshot=(movement_scene.tiles.copy(),movement_scene.gold.copy(),movement_scene.protected.copy(),
                                movement_scene.goods,movement_scene.signature)
                route_model_snapshot=deepcopy(model)
                self._prepared_route=None;self._route_choice=None
        gate_sequence=moving and closed_gate(movement_scene,action)
        if type(count) is not int or not 1<=count<=MAX_SEQUENCE or not moving and count!=1:raise ProbeError('method_not_allowed')
        requested=1 if moving else 0
        if moving and self.scene(obs) is None:raise ProbeError('navigation_unknown')
        if moving:
            self.check_timing_scene(obs)
            if not self.timing_route_allowed(obs,action):raise ProbeError('method_not_allowed')
            if count>1 and not self.state['lead_confirmed'] and timing_eligible(movement_scene,action):raise ProbeError('method_not_allowed')
            remaining=MAX_STEPS-sum(a['scheduled_inputs'] for a in self.state['actions'])
            if remaining<1:raise ProbeError('walk_limit')
            if gate_sequence and remaining<2:raise ProbeError('walk_limit')
            if gate_sequence and count!=2:raise ProbeError('method_not_allowed')
            if prepared is None and (count>1 or self.entrance is not None):
                planned=self.choose(obs)
                if planned.get('direction')!=action or (directions is None and count>1 and self.burst_count(obs,planned,MAX_SEQUENCE)<count):
                    raise ProbeError('method_not_allowed')
            count=min(count,remaining)
        if self.state['goods_visible'] and action!='pause':raise ProbeError('method_not_allowed')
        if (action=='resume' and obs['state']!='pause') or (action!='resume' and obs['state']!='floor'):
            raise ProbeError('screen_unconfirmed')
        if len(self.state['actions'])>=MAX_ACTIONS:raise ProbeError('walk_limit')
        target=None
        if moving:
            if (not beat_sync._model_valid(model,required_profile=beat_sync.ZONE1_1_PROFILE)
                    or beat_sync.next_target(model,self.clock()) is None):raise ProbeError('beat_unconfirmed')
        front=self.guard()
        entry={'action':action,'outcome':'not_requested','reason':None,'requested_ns':self.clock(),
               'issued_ns':None,'completed_ns':None,'target_ns':target,'rpc_timings':{},'target_checks':[],
               'requested_inputs':requested,'scheduled_inputs':0,'period_ns':None,'planned_inputs':count if moving else 0,'dispatch_lead_ns':lead if moving else None}
        self.state['actions'].append(entry)
        if directions is not None:entry['planned_directions']=list(directions)
        # 復帰失敗・unknownでも以前のポーズを最終状態に流用しない。
        if action=='resume':self.state['paused']=False
        entry['outcome']='unknown';self.pending=True;self.state['input_pending']=True
        self.checkpoint()
        reserved=None;foreground_refreshed=False
        def current_checks(now):
            if obs is not self.last or self.state['goods_visible'] and action!='pause':
                raise ProbeError('method_not_allowed')
            if (action=='resume' and obs['state']!='pause') or (action!='resume' and obs['state']!='floor'):
                raise ProbeError('screen_unconfirmed')
            if moving:
                if self.state['dispatch_lead_ns']!=lead:raise ProbeError('method_not_allowed')
                if self.scene(obs) is not movement_scene or movement_scene is None:raise ProbeError('navigation_unknown')
                if route_snapshot is not None and not self.route_scene_matches(movement_scene,route_snapshot):
                    raise ProbeError('navigation_unknown')
                if route_model_snapshot is not None and model!=route_model_snapshot:raise ProbeError('beat_unconfirmed')
                if prepared is not None and (prepared['decision']!=prepared['decision_state']
                        or not self.route_context_matches(prepared['context'],obs,model)):
                    raise ProbeError('navigation_unknown')
                if self.goods(obs)=='visible':raise ProbeError('method_not_allowed')
                # 経路は上で同じ観測から確定済み。単一workerは待機中に地形を変更しない。
                # 最終待機後にBFSを繰り返して予定時刻を越えないよう、同一sceneを検査する。
                if not beat_sync._model_valid(model,required_profile=beat_sync.ZONE1_1_PROFILE):
                    raise ProbeError('beat_unconfirmed')
                if self.state['started_ns'] is not None and now-self.state['started_ns']>=WALK_SECONDS*1_000_000_000:
                    raise ProbeError('walk_limit')
        def restore_reserved():
            if reserved is not None:
                self.images,self.report['omitted_images']=reserved
        try:
            if moving:
                # bytesを複製せずRAMの参照を保持。未送信なら容量退避も含めて戻す。
                reserved=(self.images.copy(),self.report['omitted_images'][:])
                self.save('run-099.jpg',obs)
            for attempt in range(MAX_TARGET_ATTEMPTS if moving else 1):
                timeout=self.budget();now=self.clock();current_checks(now)
                timeout=self.budget();now=self.clock()
                if moving:
                    # 前面確認・pending保存・画像予約後に、現在からの未来拍を選ぶ。
                    target=beat_sync.next_target(model,now,lead)
                    if target is None:
                        expired=now-model['last_sample_ns']>beat_sync.FRESH_NS
                        raise ProbeError('dispatch_window_expired' if expired else 'beat_unconfirmed')
                    entry['target_ns']=target;until=target-lead
                    check={'target_ns':target,'checked_ns':now,'status':'expired',
                           'window':{'stage':'preflight','frame_ns':obs['_captured'],
                                     'phase_ns':model['last_sample_ns'],'foreground_ns':front,'required_end_ns':until}}
                    entry['target_checks'].append(check)
                    source_valid=(now<=until and 0<=until-obs['_captured']
                        and until+lead+50_000_000<=obs['_captured']+beat_sync.FRESH_NS
                        and 0<=until-model['last_sample_ns']
                        and until+lead+50_000_000<=model['last_sample_ns']+beat_sync.FRESH_NS
                        and until+lead+50_000_000<=self.stop_ns
                        and (self.state['started_ns'] is None or
                             until+lead+50_000_000<self.state['started_ns']+WALK_SECONDS*1_000_000_000))
                    if (not 0<=until-front or until+DISPATCH_LATE_NS>front+1_000_000_000):
                        if (source_valid and not foreground_refreshed and entry['issued_ns'] is None
                                and entry['scheduled_inputs']==0):
                            # この候補は未送信。画像と位相を延長せず、前面だけ一度更新する。
                            foreground_refreshed=True
                            self.budget();current_checks(self.clock());front=self.guard()
                            check['window']['foreground_ns']=front
                            now=self.clock();check['checked_ns']=now
                            self.budget();current_checks(now)
                            # guardが元の予定送信時刻を越えたら、別の候補へずらさない。
                            if self.clock()>until:raise ProbeError('dispatch_window_expired')
                    # 許容する待機遅れ10msまで含め、前面確認の1秒期限内に収める。
                    if not (now<=until and 0<=until-obs['_captured']<=beat_sync.FRESH_NS
                            and 0<=until-model['last_sample_ns']<=beat_sync.FRESH_NS
                            and 0<=until-front and until+DISPATCH_LATE_NS<=front+1_000_000_000
                            and until<=self.stop_ns-1_000_000
                            and (self.state['started_ns'] is None
                                 or until<self.state['started_ns']+WALK_SECONDS*1_000_000_000)):
                        raise ProbeError('dispatch_window_expired')
                    try:wait_until(until,self.clock,self.sleeper,self.budget,self.spin_wait)
                    except ProbeError:
                        check['checked_ns']=self.clock()
                        check['window'].update(stage='dispatch',required_end_ns=check['checked_ns']+lead+50_000_000)
                        raise
                # 各待機後に取消/同一観測/商品/モデル/期限を再検査。遅れより優先する。
                if moving:
                    check['checked_ns']=self.clock()
                    check['window'].update(stage='dispatch',required_end_ns=check['checked_ns']+lead+50_000_000)
                timeout=self.budget();now=self.clock()
                current_checks(now)
                timeout=self.budget();now=self.clock()
                if moving:
                    check['checked_ns']=now
                    check['window'].update(stage='dispatch',required_end_ns=now+lead+50_000_000)
                    if self.state['started_ns'] is not None and now-self.state['started_ns']>=WALK_SECONDS*1_000_000_000:
                        raise ProbeError('walk_limit')
                if moving and now>until+DISPATCH_LATE_NS:
                    check['status']='late'
                    print('拍入力: 待機が予定より%.1fms遅れたため未送信。'%((now-until)/1e6),flush=True)
                    if attempt+1>=MAX_TARGET_ATTEMPTS:raise ProbeError('dispatch_window_expired')
                    continue
                if not(0<=now-obs['_captured']<=3_000_000_000 and 0<=now-front<=1_000_000_000):
                    raise ProbeError('host_observation_expired')
                if moving:
                    if beat_sync.next_target(model,now) is None or now>target or target-now>model['period_ns']:
                        raise ProbeError('beat_unconfirmed')
                    if count>1:
                        # 閉扉は次拍の前面期限も事前確認。開けるだけの単発へ縮退しない。
                        if gate_sequence and target+model['period_ns']-lead+DISPATCH_LATE_NS>front+1_000_000_000:
                            raise ProbeError('dispatch_window_expired')
                        # 元画像/位相の期限内で送れる最長の直線区間。閉扉は単発へ縮退しない。
                        wanted=count
                        while count>1:
                            planned_end=now+lead+(count-1)*model['period_ns']+50_000_000
                            if (planned_end<=obs['_captured']+beat_sync.FRESH_NS
                                    and planned_end<=model['last_sample_ns']+beat_sync.FRESH_NS
                                    and planned_end<=self.stop_ns
                                    and (self.state['started_ns'] is None or
                                         planned_end<=self.state['started_ns']+WALK_SECONDS*1_000_000_000)):
                                break
                            if gate_sequence:raise ProbeError('dispatch_window_expired')
                            count-=1
                        if count<wanted:
                            entry['reason']='sequence_window_short'
                            print('拍入力: 画像・位相の有効時間に合わせ%d入力に制限します。'%count,flush=True)
                    # 単発と複数→単発縮退にも、選択先行量を含む最短の期限を適用。
                    first_end=now+lead+50_000_000
                    if not (first_end<=obs['_captured']+beat_sync.FRESH_NS
                            and first_end<=model['last_sample_ns']+beat_sync.FRESH_NS
                            and first_end<=self.stop_ns
                            and (self.state['started_ns'] is None or
                                 first_end<=self.state['started_ns']+WALK_SECONDS*1_000_000_000)):
                        raise ProbeError('dispatch_window_expired')
                    check['status']='ready'
                break
        except ProbeError as exc:
            restore_reserved()
            entry['outcome']='not_requested';entry['reason']=code(exc.code)
            self.pending=False;self.state['input_pending']=False;raise
        except BaseException:
            # 未送信画像は戻すが、予期しない準備例外を再試行可能にしない。
            restore_reserved();raise
        entry['issued_ns']=now
        entry['scheduled_inputs']=1 if moving else 0
        sequence_period=model['period_ns'] if moving and count>1 else None
        # 入力より前の観測を、入力後の停止確認や再送判断に流用しない。
        self.last=None
        reply=self.client.call('run_steps',move_batch(action) if moving else base.batch(action),timeout=timeout)
        entry['completed_ns']=self.clock()
        # RPC側の計測点だけを保存する。欠損/失敗をissuedやゲーム受付時刻で補完しない。
        if type(reply.timings) is dict:
            entry['rpc_timings']={key:reply.timings[key] for key in RPC_TIMING_FIELDS
                if type(reply.timings.get(key)) is int and self.outer['start_ns']<=reply.timings[key]<2**63}
        outcome=gesture_evidence(reply.result) if moving else base.resume.batch_evidence(reply.result)[0]
        entry['outcome']=outcome
        if outcome=='not_sent':restore_reserved()
        self.pending=outcome=='unknown';self.state['input_pending']=self.pending
        if outcome!='acknowledged':
            self.checkpoint();raise ProbeError('batch_unknown')
        if moving and count>1:
            # 同じ起点から拍を飛ばさず送る。各ACK後だけ次の使い切りtokenを発行。
            total=count;count=1
            try:
                for ordinal in range(1,total):
                    until=entry['target_ns']+ordinal*sequence_period-lead
                    # 3入力目以降は必要な時だけ前面を再確認。元画像/位相の期限は延ばさない。
                    if ordinal>=2 and until+DISPATCH_LATE_NS>front+1_000_000_000:
                        self.budget();front=self.guard()
                    self.pending=True;self.state['input_pending']=True
                    previous=self.state['actions'][-1]
                    next_action=directions[ordinal] if directions is not None else action
                    token=(object(),next_action,obs,model,front,entry['target_ns'],previous,movement_scene,sequence_period,ordinal,lead)
                    if prepared is not None:
                        token+=(prepared['directions'],(route_snapshot,route_model_snapshot),prepared)
                    elif directions is not None:token+=(directions,(route_snapshot,route_model_snapshot))
                    self._followup_token=token
                    count=self.followup(token,next_action,obs,model,front,entry['target_ns'])
                    if count<ordinal+1:break
            finally:self._followup_token=None
        if moving and count==1 and not self.state['lead_confirmed'] and timing_eligible(movement_scene,action):
            # 速いACKでも対象拍より前の静止画像を失敗として扱わない。
            until=entry['target_ns']+OBSERVE_DELAY_NS
            while self.clock()<until:
                remaining_time=self.budget()
                if self.state['started_ns'] is not None and self.clock()-self.state['started_ns']>=WALK_SECONDS*1_000_000_000:
                    raise ProbeError('walk_limit')
                self.sleeper(min(.05,remaining_time,(until-self.clock())/1e9))
        self.checkpoint()
        return count if moving else 0

    @staticmethod
    def route_scene_matches(scene,snapshot):
        return (scene is not None and scene.tiles==snapshot[0] and scene.gold==snapshot[1]
                and scene.protected==snapshot[2] and scene.goods==snapshot[3] and scene.signature==snapshot[4])

    def followup(self,token,action,obs,model,front,first_target):
        """直前ACKと使い切りtokenに対応する、固定拍列の次の1入力だけ。"""
        from . import beat_sync
        if (type(token) is not tuple or len(token) not in (11,13,14)
                or token is not self._followup_token):raise ProbeError('method_not_allowed')
        self._followup_token=None  # 成否・未送信を問わず一度だけ。後続はperformだけが発行。
        if (token[1]!=action or token[2] is not obs or token[3] is not model
                or token[4]!=front or token[5]!=first_target or token[6] is not self.state['actions'][-1]
                or token[6]['outcome']!='acknowledged' or token[6]['scheduled_inputs']!=1):
            raise ProbeError('method_not_allowed')
        if len(self.state['actions'])>=MAX_ACTIONS:raise ProbeError('walk_limit')
        lead=token[10]
        ordinal=token[9]
        if type(ordinal) is not int or not 1<=ordinal<MAX_SEQUENCE:raise ProbeError('method_not_allowed')
        target=first_target+ordinal*token[8];until=target-lead;scene=token[7]
        entry={'action':action,'outcome':'not_requested','reason':None,'requested_ns':self.clock(),
               'issued_ns':None,'completed_ns':None,'target_ns':target,'rpc_timings':{},'target_checks':[],
               'requested_inputs':1,'scheduled_inputs':0,'period_ns':None,'planned_inputs':0,'dispatch_lead_ns':lead}
        self.state['actions'].append(entry)
        check={'target_ns':target,'checked_ns':self.clock(),'status':'expired',
               'window':{'stage':'followup','frame_ns':obs['_captured'],'phase_ns':model['last_sample_ns'],
                         'foreground_ns':front,'required_end_ns':max(self.clock(),until)+lead+50_000_000}}
        entry['target_checks'].append(check)
        def validate():
            check['checked_ns']=self.clock()
            check['window']['required_end_ns']=max(check['checked_ns'],until)+lead+50_000_000
            timeout=self.budget()
            if (self.last is not None or self.scene(obs) is not scene or scene is None
                    or self.state['dispatch_lead_ns']!=lead or obs['state']!='floor' or self.state['goods_visible'] or self.goods(obs)=='visible'):
                raise ProbeError('method_not_allowed')
            if len(token)>=13 and (type(token[11]) is not tuple
                    or not 1<=ordinal<len(token[11])<=MAX_SEQUENCE
                    or len(token)==13 and (len(token[11])!=2 or ordinal!=1)
                    or token[11][ordinal]!=action or token[11][ordinal-1]!=token[6]['action']
                    or type(token[12]) is not tuple or len(token[12])!=2
                    or not self.route_scene_matches(scene,token[12][0])):
                raise ProbeError('navigation_unknown')
            if len(token)>=13 and model!=token[12][1]:raise ProbeError('beat_unconfirmed')
            if len(token)==14 and (token[13]['decision']!=token[13]['decision_state']
                    or not self.route_context_matches(token[13]['context'],obs,model,ordinal)):
                raise ProbeError('navigation_unknown')
            if (not beat_sync._model_valid(model,required_profile=beat_sync.ZONE1_1_PROFILE)
                    or model['period_ns']!=token[8]):
                raise ProbeError('beat_unconfirmed')
            if sum(a['scheduled_inputs'] for a in self.state['actions'])>=MAX_STEPS:raise ProbeError('walk_limit')
            timeout=self.budget();now=self.clock();check['checked_ns']=now
            check['window']['required_end_ns']=max(now,until)+lead+50_000_000
            if now>until+DISPATCH_LATE_NS:
                check['status']='late';raise ProbeError('dispatch_window_expired')
            planned_end=max(now,until)+lead+50_000_000
            if not (0<=now-obs['_captured'] and 0<=now-model['last_sample_ns'] and 0<=now-front<=1_000_000_000
                    and planned_end<=obs['_captured']+beat_sync.FRESH_NS
                    and planned_end<=model['last_sample_ns']+beat_sync.FRESH_NS
                    and planned_end<=self.stop_ns
                    and (self.state['started_ns'] is None or
                         planned_end<=self.state['started_ns']+WALK_SECONDS*1_000_000_000)):
                raise ProbeError('host_observation_expired')
            return timeout,now
        try:
            timeout,now=wait_until(until,self.clock,self.sleeper,validate,self.spin_wait)
        except ProbeError as exc:
            entry['reason']=code(exc.code);self.pending=False;self.state['input_pending']=False
            if exc.code not in ('dispatch_window_expired','host_observation_expired'):raise
            print('連続入力: 次拍に間に合わないため%d回目以降は未送信。結果を確認します。'%(ordinal+1),flush=True)
            return ordinal
        check['status']='ready';entry['issued_ns']=now;entry['scheduled_inputs']=1;entry['outcome']='unknown'
        self.pending=True;self.state['input_pending']=True
        reply=self.client.call('run_steps',move_batch(action),timeout=timeout)
        entry['completed_ns']=self.clock()
        if type(reply.timings) is dict:
            entry['rpc_timings']={key:reply.timings[key] for key in RPC_TIMING_FIELDS
                if type(reply.timings.get(key)) is int and self.outer['start_ns']<=reply.timings[key]<2**63}
        outcome=gesture_evidence(reply.result);entry['outcome']=outcome
        self.pending=outcome=='unknown';self.state['input_pending']=self.pending
        # 第1入力は送信済み。第2入力がnot_sentでもrun-099を巻き戻さない。
        if outcome!='acknowledged':raise ProbeError('batch_unknown')
        return ordinal+1
    def note_step(self,index,direction,before,after,outcome,decision,count=1):
        name='run-%03d.jpg'%(100+index);self.save(name,after)
        self.state['events'].append({'index':index,'direction':direction,'motion':outcome,
            'before_sha256':before['_sha'],'after_sha256':after['_sha'],'image':name,
            'target':decision.get('target'),'goods':self.goods(after),'scheduled_inputs':count})
        if 'directions' in decision:
            self.state['events'][-1].update(directions=list(decision['directions']),displacement=decision.get('displacement'))
        self.visits[tuple(self.state['position'])]=self.visits.get(tuple(self.state['position']),0)+1
        self.checkpoint()
    def finish(self,reason,obs):
        self.finishing=True
        self.state['reason']=code(reason);self.checkpoint()
        if self.pending or self.state['input_pending']:return
        if any(a['action']=='pause' for a in self.state['actions']):return
        # 古い/欠損画像は使わず、pause前に重い解析なしで一度だけ取得する。
        # 取得失敗後のworker再入でも古いlastや再試行に戻らない。
        captured=obs.get('_captured') if obs else None
        fresh_ns=PAUSE_FRAME_NS if obs and obs['state']=='floor' else 3_000_000_000
        if obs is not self.last or type(captured) is not int or not 0<=self.clock()-captured<=fresh_ns:
            if self.finish_refresh_attempted:return
            self.finish_refresh_attempted=True;self.last=None
            obs=self.observe()
        if obs is not self.last:return
        if obs and obs['state']=='pause':
            self.state['paused']=True;self.save('stopped.jpg',obs);return
        if not obs or obs['state']!='floor':return
        # pause ACK後の画像取得失敗でもトグルを再送しない。
        if any(a['action']=='pause' for a in self.state['actions']):return
        self.perform('pause',obs)
        self.model=None;self.samples=[]
        for _ in range(4):
            after=self.observe()
            if after['state']=='pause':
                self.state['paused']=True;self.save('stopped.jpg',after);return


def walk(driver,initial=None):
    w=driver.state;w['started_ns']=driver.clock();refreshes=0
    if initial is None:
        driver.perform('resume',driver.last)
        obs=driver.observe()
    else:
        driver.budget()
        if (initial is not driver.last or initial is not driver.handoff_frame or driver.pending
                or w['input_pending'] or initial.get('state')!='floor' or driver.scene(initial) is None
                or not 0<=driver.clock()-initial['_captured']<=3_000_000_000):
            raise ProbeError('host_observation_expired')
        driver.handoff_frame=None
        obs=initial
    # 復帰中の画像は短く再取得。ポーズに対する方向入力は禁止。
    for _ in range(3):
        if obs['state']=='floor':break
        obs=driver.observe()
    if obs['state']!='floor':raise ProbeError('screen_unconfirmed')
    index=1
    while index<=MAX_STEPS:
        if driver.goods(obs)=='visible':
            w['goods_visible']=True;driver.save('found.jpg',obs);driver.checkpoint()
            driver.finish('goods_visible',obs);return
        if driver.clock()-w['started_ns']>=WALK_SECONDS*1_000_000_000:
            driver.finish('walk_limit',obs);return
        if getattr(driver,'timing_anchor',None) is not None:
            driver.budget();driver.check_timing_scene(obs)
        obs,model=driver.synchronize(obs)
        if driver.goods(obs)=='visible':
            w['goods_visible']=True;driver.save('found.jpg',obs);driver.checkpoint()
            driver.finish('goods_visible',obs);return
        if getattr(driver,'timing_anchor',None) is not None:
            driver.budget();driver.check_timing_scene(obs)
        decision=driver.choose(obs);direction=decision.get('direction')
        if direction not in MOVE_POINTS:
            driver.finish('goods_partial' if driver.goods(obs)=='partial' else 'no_safe_path',obs);return
        before=obs;action_count=len(w['actions'])
        if hasattr(driver,'route_directions'):
            directions=driver.route_directions(before,decision,MAX_STEPS-index+1);count=len(directions)
        else:
            count=driver.burst_count(before,decision,MAX_STEPS-index+1);directions=(direction,)*count
        mixed=len(directions)==2 and directions[0]!=directions[1]
        if mixed:count=2
        if count==0:
            driver.finish('walk_limit' if MAX_STEPS-index+1<2 else 'no_safe_path',obs);return
        print('経路判断: %s / 予定%d入力 / %s'%(direction,count,decision.get('reason')),flush=True)
        try:
            count=(driver.perform(direction,before,model,count=count,directions=directions) if mixed
                   else driver.perform(direction,before,model,count=count))
        except ProbeError as exc:
            entry=w['actions'][-1] if len(w['actions'])==action_count+1 else None
            unsent=(entry is not None and entry['action']==direction and entry['outcome']=='not_requested'
                    and entry['issued_ns'] is None and entry['completed_ns'] is None and entry['rpc_timings']=={})
            if (exc.code!='dispatch_window_expired' or not unsent or driver.pending
                    or w['input_pending'] or refreshes>=MAX_REFRESHES):raise
            driver.budget()
            if driver.clock()-w['started_ns']>=WALK_SECONDS*1_000_000_000:raise ProbeError('walk_limit')
            refreshes+=1
            driver.beat_only=False;obs=driver.observe()
            continue
        actual=directions[:count] if mixed else None
        after=driver.observe();outcome='unknown';displacement=None
        for attempt in range(3):
            if driver.goods(after)=='visible':
                w['goods_visible']=True;driver.save('found.jpg',after);driver.checkpoint()
                record=dict(decision,directions=actual,displacement=None) if mixed else decision
                driver.note_step(index,direction,before,after,'goods_visible',record,count)
                driver.finish('goods_visible',after);return
            if mixed and count==2:
                measurement=driver.route_movement(before,after,actual)
                outcome=measurement['motion'];displacement=measurement['delta']
            else:
                outcome=driver.movement(before,after,direction,expected_steps=count)
                if mixed and outcome=='moved':displacement=DIRECTIONS[direction]
                elif mixed and outcome=='blocked':displacement=(0,0)
            if outcome!='tween' or attempt==2:break
            after=driver.observe()
        if mixed and outcome in ('moved','partial') and displacement is not None:
            w['position'][0]+=displacement[0];w['position'][1]+=displacement[1]
            w['moves_confirmed']+=abs(displacement[0])+abs(displacement[1])
        elif outcome=='gate_entered':
            dx,dy=DIRECTIONS[direction];w['position'][0]+=dx;w['position'][1]+=dy
            w['moves_confirmed']+=1;w['door_changes']+=1
        elif outcome=='moved':
            dx,dy=DIRECTIONS[direction];w['position'][0]+=dx*count;w['position'][1]+=dy*count;w['moves_confirmed']+=count
        elif outcome=='partial' and count==2:
            dx,dy=DIRECTIONS[direction];w['position'][0]+=dx;w['position'][1]+=dy;w['moves_confirmed']+=1
        elif outcome=='door_opened':w['door_changes']+=1
        elif outcome=='terrain_opened':w['terrain_changes']+=1
        record=dict(decision,directions=actual,displacement=list(displacement) if displacement is not None else None) if mixed else decision
        driver.note_step(index,direction,before,after,outcome,record,count)
        timing=driver.timing_result(before,after,direction,outcome,count)
        if timing=='exhausted':driver.finish('timing_not_found',after);return
        if timing=='retry':
            # 変位照合で約1.2秒古くなったafterを、次候補の入力許可へ流用しない。
            # 入力済み・blocked確定後の通常観測であり、未送信回復の2回枠はリセットしない。
            driver.timing_anchor=(frozenset(driver.scene(after).gold),direction)
            driver.budget()
            if index+count>MAX_STEPS or driver.clock()-w['started_ns']>=WALK_SECONDS*1_000_000_000:
                driver.finish('walk_limit',after);return
            driver.beat_only=False;obs=driver.observe()
            driver.budget();driver.check_timing_scene(obs)
            index+=count;continue
        driver.timing_anchor=None
        print('歩行%d: %s / %d拍入力 / %s / 商品: %s'%(index,direction,count,outcome,driver.goods(after)),flush=True)
        if outcome not in ('moved','gate_entered','door_opened','terrain_opened'):
            driver.finish('unexpected_movement' if outcome=='unexpected' else 'movement_unconfirmed',after);return
        obs=after
        index+=count
    driver.finish('walk_limit',obs)


def parser():
    ap=base.parser();ap.description='TEST-042: 金壁発見後、測定済み1-1周期範囲とHUDで商品が見える位置へ。'
    ap.add_argument('--worker-mode',choices=('exec','fork'),default='exec',help=base.argparse.SUPPRESS)
    ap.set_defaults(output='runtime/test-042');return ap


def worker(args):
    entered=time.monotonic_ns()
    folder=Path(args.output);control=Path(args.checkpoint_dir)
    try:r=read_report(control/'report.json',args.run_id,args.start_ns)
    except (ValueError,OSError,ProbeError):return 74
    r['worker_mode']=args.worker_mode
    r['startup'].update(worker_module_started_ns=_MODULE_STARTED_NS,worker_entered_ns=entered,
                        worker_validated_ns=time.monotonic_ns())
    d=None
    try:
        with base.device_lock():
            key,tok=base.load_pairing(args.token_store,args.store_key)
            r['startup']['pairing_ready_ns']=time.monotonic_ns()
            crypto=base.Crypto(native=not args.python_crypto);r['search']['crypto_engine']=crypto.engine
            r['startup']['crypto_ready_ns']=time.monotonic_ns()
            with base.OwnedRpcTimer() as timer:
                client=WalkClient(base.HttpTransport(),key,tok,timeout=8,crypto=crypto,deadline_owner=timer)
                d=Driver(client,r,folder,args.stop_ns,control)
                r['startup']['driver_ready_ns']=time.monotonic_ns()
                client.call('launch_app',{'bundle_id':base.GAME},timeout=d.budget())
                r['startup']['launch_ready_ns']=time.monotonic_ns()
                base.collect(d,max_restarts=MAX_RESTARTS,candidate_handoff=d.accept_candidate)
                hand=d.handoff_frame if d.handoff_frame is d.last else None
                r['search']['status']='completed' if r['search']['paused'] or hand is not None else 'stopped'
                r['search']['control_reason']=r['search']['reason'];r['search']['control_end_ns']=d.clock()
                if (r['search']['candidate'] and (r['search']['paused'] or hand is not None)
                        and not d.handoff_rejected
                        and (not d.analysis_failed or hand is not None and d.goods(hand)=='visible')):
                    r['phase']='walk';client.walking=True;d.checkpoint()
                    try:
                        if hand is None:walk(d)
                        else:walk(d,initial=hand)
                        r['reason']=r['walk']['reason']
                        r['status']='completed' if r['walk']['goods_visible'] and r['walk']['paused'] else 'stopped'
                    except (Exception,KeyboardInterrupt) as exc:
                        reason=(code(exc.code) if isinstance(exc,ProbeError) else 'user_interrupt' if isinstance(exc,KeyboardInterrupt)
                                else 'output_write_failed' if isinstance(exc,OSError) else 'internal_error')
                        if reason=='internal_error':d.record_failure('control',exc)
                        r.update(status='stopped',reason=reason)
                        try:d.finish(r['walk']['reason'] or reason,d.last)
                        except (Exception,KeyboardInterrupt):pass
                else:r.update(status='stopped',reason=('walk_analysis_failed' if d.analysis_failed or d.handoff_rejected
                    else 'navigation_unknown') if r['search']['candidate'] else 'gold_not_found')
    except (ProbeError,KeyboardInterrupt,OSError) as exc:
        reason=code(exc.code) if isinstance(exc,ProbeError) else 'user_interrupt' if isinstance(exc,KeyboardInterrupt) else 'output_write_failed'
        r.update(status='stopped',reason=reason)
    except Exception:r.update(status='stopped',reason='internal_error')
    r.update(control_reason=r['reason'],control_end_ns=time.monotonic_ns(),end_ns=time.monotonic_ns())
    if r['phase']=='walk':r['walk']['end_ns']=r['control_end_ns']
    r['phase']='done'
    try:
        write(control,r)
        if d:
            if d.last:d.save('last.jpg',d.last)
            d.export_images()
        r['end_ns']=time.monotonic_ns();write(control,r)
    except OSError:return 2
    return 0


def run(args):
    if args.worker:return worker(args)
    root=Path(args.output).resolve();root.mkdir(parents=True,exist_ok=True)
    run_id=uuid.uuid4().hex;start=time.monotonic_ns()
    folder=root/('shop-walk-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+run_id[:8]);folder.mkdir(mode=0o700)
    control=Path(tempfile.mkdtemp(prefix='necro-walk-'));r=new_report(start,run_id)
    r['startup'].update(parent_module_started_ns=_MODULE_STARTED_NS,parent_report_ready_ns=time.monotonic_ns())
    write(control,r)
    command=[sys.executable,'-m','necroprobe.shop_walk','--worker','--output',str(folder),'--checkpoint-dir',str(control),
        '--run-id',run_id,'--start-ns',str(start),'--stop-ns',str(start+180_000_000_000),'--token-store',args.token_store,
        '--worker-mode','exec']
    if args.store_key is not None:command+=['--store-key',args.store_key]
    if args.python_crypto:command.append('--python-crypto')
    print('TEST-042: 金壁→測定済み1-1周期範囲とライブHUD→新鮮な地形で商品が見える位置へ。画面端0、同じ向きでゲームを表示してください。',flush=True)
    from . import bootstrap
    child_args=parser().parse_args(command[3:]);child_args.worker_mode='fork'
    modes=[]
    def inherited_worker():
        global _MODULE_STARTED_NS
        base.supervisor._cancel_requested=False
        _MODULE_STARTED_NS=time.monotonic_ns()
        return worker(child_args)
    def spawn(selected_command):
        return bootstrap.spawn_worker(selected_command,inherited_worker,on_mode=modes.append)
    diagnostics={};reason=base.supervisor.supervise(command,max(.001,180-(time.monotonic_ns()-start)/1e9),diagnostics,spawn=spawn)
    try:r=read_report(control/'report.json',run_id,start)
    except (ValueError,OSError,ProbeError):r['search']['counts_certain']=False;reason=reason or 'report_read_failed'
    if modes:r['worker_mode']=modes[-1]
    r['worker_returncode']=diagnostics.get('returncode');r['worker_exit_confirmed']=diagnostics.get('exit_confirmed')
    if r['worker_exit_confirmed'] is False:r['search']['counts_certain']=False;reason='worker_cleanup_failed'
    if reason or r['status']=='running':r.update(status='stopped',reason=code(reason or 'worker_failed'))
    r['end_ns']=time.monotonic_ns();write(folder,r,'parent-result.json')
    if r['worker_exit_confirmed'] is not False:write(folder,r);shutil.rmtree(control,ignore_errors=True)
    w=r['walk'];paused=w['paused'] if w['started_ns'] is not None else r['search']['paused']
    print('終了: %s / 歩行確認: %d / 商品可視: %s / ポーズ確認: %s'%(r['reason'],w['moves_confirmed'],w['goods_visible'],paused),flush=True)
    print('worker起動方式: %s'%(r['worker_mode'] or '未起動'),flush=True)
    print('入力先行: %dms / 実1歩確認: %s / 調整試行: %d'%(w['dispatch_lead_ns']//1_000_000,w['lead_confirmed'],len(w['lead_trials'])),flush=True)
    print('開扉確認: %d / 茶壁の開通確認: %d'%(w['door_changes'],w['terrain_changes']),flush=True)
    print('地形解析エンジン: %s / 移動判定エンジン: %s'%(w['navigation_engine'],w['motion_engine']),flush=True)
    if w['failure']:print('停止箇所: %s / 例外種類: %s / Pillow: %s'%(w['failure']['stage'],w['failure']['kind'],w['pillow_version']),flush=True)
    print('予定拍での実受付は未検証 / 画像保存完了: %s / 保存先: %s'%(r['search']['export_complete'],folder),flush=True)
    if not paused:print('ポーズ未確認です。必要なら手動でポーズしてください。',flush=True)
    return 0 if r['status']=='completed' else 2


def main(argv=None):
    args=parser().parse_args(argv);previous={}
    if not args.worker:
        base.supervisor._cancel_requested=False
        def interrupt(_sig,_frame):base.supervisor._cancel_requested=True
        for sig in (signal.SIGINT,signal.SIGTERM):previous[sig]=signal.getsignal(sig);signal.signal(sig,interrupt)
    try:return run(args)
    except ProbeError as exc:print('TEST-042停止: '+code(exc.code),file=sys.stderr);return 2
    except OSError:print('TEST-042: 結果保存に失敗しました。',file=sys.stderr);return 2
    finally:
        for sig,handler in previous.items():signal.signal(sig,handler)

if __name__=='__main__':raise SystemExit(main())
