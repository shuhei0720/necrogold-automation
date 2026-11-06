"""TEST-030: 確認済みの直線床で単一タッチを次拍へ2回送る商品接近の限定版。

HTTP中点と150ms先行は未校正の推定。予定拍での実受付を保証しない。
"""
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
import time
import uuid

from . import VERSION, restart_loop as base
from .validation import ProbeError, json_object

REVISION='shop-walk-v15'
MOVE_POINTS={'up':(290,838),'down':(124,838),'left':(207,49),'right':(207,838)}
DIRECTIONS={'up':(0,-1),'down':(0,1),'left':(-1,0),'right':(1,0)}
MAX_STEPS=16
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
         'walk_analysis_failed','dispatch_window_expired','sequence_window_short'}
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
    from PIL import __version__ as pillow_version
    from . import navigation_stats,motion_stats
    if not isinstance(pillow_version,str) or re.fullmatch(VERSION_PATTERN,pillow_version) is None:pillow_version=None
    return {'started_ns':None,'end_ns':None,'reason':None,'goods_visible':False,'paused':False,
        'device_timing_verified':False,'dispatch_timing_calibrated':False,'dispatch_lead_ns':LEAD_NS,
        'position':[0,0],'moves_confirmed':0,'door_changes':0,'terrain_changes':0,'actions':[],'events':[],
        'samples':[],'models':[],'input_pending':False,
        'navigation_ms':[],'beat_extract_ms':[],'motion_ms':[],'beat_fit_ms':[],
        'failure':None,'pillow_version':pillow_version,'navigation_engine':navigation_stats.ENGINE,'motion_engine':motion_stats.ENGINE}


def new_report(start,run_id):
    return {'version':VERSION,'test_id':'TEST-030','revision':REVISION,'run_id':run_id,
        'start_ns':start,'end_ns':None,'phase':'search','status':'running','reason':None,
        'control_reason':None,'control_end_ns':None,'worker_returncode':None,'worker_exit_confirmed':None,
        'search':base.new_report(start,run_id),'walk':new_walk()}


def write(folder,report,name='report.json'):
    base.atomic_write(Path(folder)/name,json.dumps(report,ensure_ascii=False,allow_nan=False,indent=2).encode())


def read_report(path,run_id,start):
    with Path(path).open('rb') as source:r=json_object(source.read(131073),131072)
    req=base.supervisor.require
    req(type(r) is dict and set(r)==set(new_report(start,run_id)))
    for k,v in [('version',VERSION),('test_id','TEST-030'),('revision',REVISION),('run_id',run_id),('start_ns',start)]:
        req(type(r[k]) is type(v) and r[k]==v)
    req(r['phase'] in ('search','walk','done'))
    req(r['status'] in ('running','completed','stopped'))
    for key in ('reason','control_reason'):req(r[key] is None or type(r[key]) is str and code(r[key])==r[key])
    for key in ('end_ns','control_end_ns'):req(r[key] is None or type(r[key]) is int and start<=r[key]<2**63)
    req(r['worker_exit_confirmed'] is None or type(r['worker_exit_confirmed']) is bool)
    req(r['worker_returncode'] is None or type(r['worker_returncode']) is int and -255<=r['worker_returncode']<=255)
    base.validate_report(r['search'],run_id,start)
    w=r['walk'];req(type(w) is dict and set(w)==set(new_walk()))
    for engine in ('navigation_engine','motion_engine'):
        req(type(w[engine]) is str and w[engine] in ('native_i386','pillow'))
    req(w['pillow_version'] is None or type(w['pillow_version']) is str and re.fullmatch(VERSION_PATTERN,w['pillow_version']) is not None)
    failure=w['failure']
    req(failure is None or type(failure) is dict and set(failure)=={'stage','kind'}
        and type(failure['stage']) is str and type(failure['kind']) is str
        and failure['stage'] in ('navigation','beat_extract','control') and failure['kind'] in FAILURE_KINDS)
    for key in ('goods_visible','paused','input_pending'):req(type(w[key]) is bool)
    req(w['device_timing_verified'] is False and w['dispatch_timing_calibrated'] is False and w['dispatch_lead_ns']==LEAD_NS)
    req(w['reason'] is None or type(w['reason']) is str and code(w['reason'])==w['reason'])
    for key in ('started_ns','end_ns'):req(w[key] is None or type(w[key]) is int and start<=w[key]<2**63)
    req(type(w['position']) is list and len(w['position'])==2 and all(type(v) is int and -16<=v<=16 for v in w['position']))
    for key in ('moves_confirmed','door_changes','terrain_changes'):req(type(w[key]) is int and 0<=w[key]<=MAX_STEPS)
    for key,limit in [('actions',MAX_ACTIONS),('events',MAX_STEPS),('samples',12),('models',MAX_STEPS+1)]:
        req(type(w[key]) is list and len(w[key])<=limit and all(type(v) is dict for v in w[key]))
    from . import beat_sync
    req(all(beat_sync._sample_valid(sample) for sample in w['samples']))
    req(all(beat_sync._model_valid(model,required_profile=beat_sync.ZONE1_1_PROFILE) for model in w['models']))
    for a in w['actions']:
        req(set(a)=={'action','outcome','reason','requested_ns','issued_ns','completed_ns','target_ns','rpc_timings','target_checks',
                    'requested_inputs','scheduled_inputs','period_ns','planned_inputs'})
        timings=a['rpc_timings']
        req(type(timings) is dict and set(timings)<=set(RPC_TIMING_FIELDS))
        req(all(type(value) is int and start<=value<2**63 for value in timings.values()))
        req(a['action'] in (*MOVE_POINTS,'resume','pause'))
        req(type(a['requested_inputs']) is int and type(a['scheduled_inputs']) is int)
        req(0<=a['scheduled_inputs']<=a['requested_inputs']<=1)
        req(a['requested_inputs']==1 if a['action'] in MOVE_POINTS else a['requested_inputs']==0)
        req(a['period_ns'] is None)
        req(type(a['planned_inputs']) is int and 0<=a['planned_inputs']<=2)
        req(a['action'] in MOVE_POINTS or a['planned_inputs']==0)
        checks=a['target_checks']
        req(type(checks) is list and len(checks)<=MAX_TARGET_ATTEMPTS)
        req(a['action'] in MOVE_POINTS or not checks)
        for check in checks:
            req(type(check) is dict and set(check)=={'target_ns','checked_ns','status'})
            req(all(type(check[key]) is int and start<=check[key]<2**63 for key in ('target_ns','checked_ns')))
            req(type(check['status']) is str and check['status'] in ('ready','late','expired'))
        req(a['outcome'] in ('not_requested','unknown','not_sent','acknowledged'))
        req(a['reason'] is None or type(a['reason']) is str and code(a['reason'])==a['reason'])
        for k in ('requested_ns','issued_ns','completed_ns','target_ns'):
            req(a[k] is None or type(a[k]) is int and start<=a[k]<2**63)
    req(sum(a['scheduled_inputs'] for a in w['actions'])<=MAX_STEPS)
    for key in ('navigation_ms','beat_extract_ms','motion_ms','beat_fit_ms'):
        req(type(w[key]) is list and len(w[key])<=240)
        req(all(type(v) in (float,int) and math.isfinite(v) and 0<=v<=180_000 for v in w[key]))
    return r


class Driver(base.RuntimeDriver):
    def __init__(self,client,outer,folder,stop_ns,control,clock=time.monotonic_ns):
        # 初回importの準備費用を撮影済み画像の鮮度へ持ち込まない。
        # TEST022初回fullの遅延原因がimportだけだったとは未確定。
        from . import beat_sync,shop_navigation
        self.outer=outer;self.state=outer['walk'];self.model=None;self.samples=[];self.visits={(0,0):1}
        self.analysis_failed=False;self.finishing=False;self.finish_refresh_attempted=False;self.sync_deadline=None
        self.beat_only=False;self.tracked_frame=None;self._followup_token=None;self.entrance=None
        super().__init__(client,outer['search'],folder,stop_ns,clock,control,self.analyze_frame)
    def budget(self):
        if base.supervisor._cancel_requested:raise ProbeError('cancelled')
        remaining=super().budget()
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
        if self.outer['phase']!='walk' or obs['state']!='floor' or self.analysis_failed or self.finishing:return None
        from . import beat_sync,shop_navigation,navigation_stats
        stage='navigation';scene=None
        try:
            if not self.beat_only:
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
    def observe(self):
        observed=super().observe()
        if self.outer['phase']=='walk' and self.goods(observed)=='visible' and not self.state['goods_visible']:
            self.state['goods_visible']=True
            self.save('found.jpg',observed)
            self.checkpoint()
        if self.analysis_failed and not self.finishing:raise ProbeError('walk_analysis_failed')
        return observed
    def scene(self,obs):
        extra=obs.get('_extra')
        return extra.get('scene') if extra else None
    def goods(self,obs):
        scene=self.scene(obs)
        return scene.goods if scene is not None else 'unknown'
    def choose(self,obs):
        from .shop_navigation import choose
        scene=self.scene(obs)
        if scene is None:return {'direction':None,'reason':'navigation_unknown','target':None}
        return choose(scene,tuple(self.state['position']),self.visits,entrance=self.entrance)
    def burst_count(self,obs,decision,remaining):
        from .shop_navigation import burst_count
        return min(remaining,burst_count(self.scene(obs),decision,tuple(self.state['position']),entrance=self.entrance))
    def movement(self,before,after,direction,expected_steps=1):
        from .shop_navigation import motion,entered_gate
        from . import motion_stats
        a,b=self.scene(before),self.scene(after)
        if a is None or b is None:return 'unknown'
        # 変位照合の前に今回のHUDを追跡。重い処理後に古くなっても標本は失わない。
        if self.model is not None and after is self.last and after is not self.tracked_frame:
            sample=self.add_sample(after)
            updated=self.track_beat(self.model) if sample is not None else None
            self.model=updated;self.tracked_frame=after if updated is not None else None
            if updated is not None:self.remember_model(updated)
        before_ns=self.clock()
        try:
            result=motion(a,b,direction,expected_steps=expected_steps)
            if self.entrance is None:
                self.entrance=entered_gate(a,b,direction,tuple(self.state['position']),expected_steps,result)
            return result
        finally:
            self.state['motion_ms'].append((self.clock()-before_ns)/1e6)
            self.state['motion_engine']=motion_stats.ENGINE
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
        def check_deadline():
            self.budget()
            now=self.clock()
            if now>=deadline:
                self.model=None
                raise ProbeError('beat_sync_timeout')
            if now-self.state['started_ns']>=WALK_SECONDS*1_000_000_000:raise ProbeError('walk_limit')
        def latest_full(frame):
            return (frame is self.last and frame['state']=='floor' and self.scene(frame) is not None
                    and 0<=self.clock()-frame['_captured']<=beat_sync.FRESH_NS)
        def accept(frame,model):
            check_deadline()
            if not latest_full(frame):raise ProbeError('navigation_unknown')
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
            check_deadline();fresh=self.observe();check_deadline()
            if self.goods(fresh)=='visible':return fresh,None
            if not latest_full(fresh):raise ProbeError('navigation_unknown')
            latest=self.add_sample(fresh)
            updated=self.track_beat(model) if latest is not None else None
            check_deadline()
            return fresh,updated
        print('拍同期: 開始（最大%d秒）'%SYNC_SECONDS,flush=True)
        check_deadline()
        if self.goods(obs)=='visible':return obs,None
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
        for i in range(12):
            check_deadline()
            print('拍標本: %d/4（取得%d/12）'%(len(self.samples),i),flush=True)
            if len(self.samples)>=4:
                model=self.fit_beat();check_deadline()
                if model:
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
            obs=self.observe()
            check_deadline()
            if self.goods(obs)=='visible':
                check_deadline();return obs,None
            self.add_sample(obs)
        check_deadline()
        raise ProbeError('beat_unconfirmed')
    def perform(self,action,obs,model=None,count=1):
        from . import beat_sync
        if self.pending or self.state['input_pending'] or obs is not self.last:raise ProbeError('method_not_allowed')
        moving=action in MOVE_POINTS
        movement_scene=self.scene(obs) if moving else None
        if type(count) is not int or count not in (1,2) or not moving and count!=1:raise ProbeError('method_not_allowed')
        requested=1 if moving else 0
        if moving and self.scene(obs) is None:raise ProbeError('navigation_unknown')
        if moving:
            remaining=MAX_STEPS-sum(a['scheduled_inputs'] for a in self.state['actions'])
            if remaining<1:raise ProbeError('walk_limit')
            if count==2 or self.entrance is not None:
                planned=self.choose(obs)
                if planned.get('direction')!=action or (count==2 and self.burst_count(obs,planned,2)!=2):
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
               'requested_inputs':requested,'scheduled_inputs':0,'period_ns':None,'planned_inputs':count if moving else 0}
        self.state['actions'].append(entry)
        # 復帰失敗・unknownでも以前のポーズを最終状態に流用しない。
        if action=='resume':self.state['paused']=False
        entry['outcome']='unknown';self.pending=True;self.state['input_pending']=True
        self.checkpoint()
        reserved=None
        def current_checks(now):
            if obs is not self.last or self.state['goods_visible'] and action!='pause':
                raise ProbeError('method_not_allowed')
            if (action=='resume' and obs['state']!='pause') or (action!='resume' and obs['state']!='floor'):
                raise ProbeError('screen_unconfirmed')
            if moving:
                if self.scene(obs) is not movement_scene or movement_scene is None:raise ProbeError('navigation_unknown')
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
                    target=beat_sync.next_target(model,now,LEAD_NS)
                    if target is None:
                        expired=now-model['last_sample_ns']>beat_sync.FRESH_NS
                        raise ProbeError('dispatch_window_expired' if expired else 'beat_unconfirmed')
                    entry['target_ns']=target;until=target-LEAD_NS
                    check={'target_ns':target,'checked_ns':now,'status':'expired'}
                    entry['target_checks'].append(check)
                    if not (now<=until and 0<=until-obs['_captured']<=beat_sync.FRESH_NS
                            and 0<=until-model['last_sample_ns']<=beat_sync.FRESH_NS
                            and 0<=until-front<=1_000_000_000
                            and until<=self.stop_ns-1_000_000
                            and (self.state['started_ns'] is None
                                 or until<self.state['started_ns']+WALK_SECONDS*1_000_000_000)):
                        raise ProbeError('dispatch_window_expired')
                    while self.clock()<until:
                        remain=self.budget();self.sleeper(min(.05,remain,max(0,(until-self.clock())/1e9)))
                # 各待機後に取消/同一観測/商品/モデル/期限を再検査。遅れより優先する。
                if moving:check['checked_ns']=self.clock()
                timeout=self.budget();now=self.clock()
                current_checks(now)
                timeout=self.budget();now=self.clock()
                if moving:
                    check['checked_ns']=now
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
                    if count==2:
                        # 端末の受付期限ではなくホスト予定の末尾。RPC/端末遅延は未校正。
                        planned_end=now+LEAD_NS+model['period_ns']+50_000_000
                        if not (planned_end<=obs['_captured']+beat_sync.FRESH_NS
                                and planned_end<=model['last_sample_ns']+beat_sync.FRESH_NS
                                and planned_end<=self.stop_ns
                                and (self.state['started_ns'] is None or
                                     planned_end<=self.state['started_ns']+WALK_SECONDS*1_000_000_000)):
                            count=1;entry['reason']='sequence_window_short'
                            print('拍入力: 2拍分の画像・位相の有効時間が足りず、1入力に制限します。',flush=True)
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
        sequence_period=model['period_ns'] if moving and count==2 else None
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
        if moving and count==2:
            # 保存/画像/前面照会は挟まず、同じ起点の次拍に単一タッチを1回だけ送る。
            # 端末のforegroundチェックは各run_stepsに含まれる。
            self.pending=True;self.state['input_pending']=True
            token=(object(),action,obs,model,front,entry['target_ns'],entry,movement_scene,sequence_period)
            self._followup_token=token
            try:count=self.followup(token,action,obs,model,front,entry['target_ns'])
            finally:self._followup_token=None
        self.checkpoint()
        return count if moving else 0

    def followup(self,token,action,obs,model,front,first_target):
        """同一呼出し内のACK済み1入力に対する、取り消し可能な次拍1入力だけ。"""
        from . import beat_sync
        if token is None or token is not self._followup_token:raise ProbeError('method_not_allowed')
        self._followup_token=None  # 成否・未送信を問わず一度だけ。再入で3入力目を作らない。
        if (token[1]!=action or token[2] is not obs or token[3] is not model
                or token[4]!=front or token[5]!=first_target or token[6] is not self.state['actions'][-1]
                or token[6]['outcome']!='acknowledged' or token[6]['scheduled_inputs']!=1):
            raise ProbeError('method_not_allowed')
        if len(self.state['actions'])>=MAX_ACTIONS:raise ProbeError('walk_limit')
        target=first_target+token[8];until=target-LEAD_NS;scene=token[7]
        entry={'action':action,'outcome':'not_requested','reason':None,'requested_ns':self.clock(),
               'issued_ns':None,'completed_ns':None,'target_ns':target,'rpc_timings':{},'target_checks':[],
               'requested_inputs':1,'scheduled_inputs':0,'period_ns':None,'planned_inputs':0}
        self.state['actions'].append(entry)
        check={'target_ns':target,'checked_ns':self.clock(),'status':'expired'}
        entry['target_checks'].append(check)
        def validate():
            timeout=self.budget()
            if (self.last is not None or self.scene(obs) is not scene or scene is None
                    or obs['state']!='floor' or self.state['goods_visible'] or self.goods(obs)=='visible'):
                raise ProbeError('method_not_allowed')
            if (not beat_sync._model_valid(model,required_profile=beat_sync.ZONE1_1_PROFILE)
                    or model['period_ns']!=token[8]):
                raise ProbeError('beat_unconfirmed')
            if sum(a['scheduled_inputs'] for a in self.state['actions'])>=MAX_STEPS:raise ProbeError('walk_limit')
            timeout=self.budget();now=self.clock();check['checked_ns']=now
            if now>until+DISPATCH_LATE_NS:
                check['status']='late';raise ProbeError('dispatch_window_expired')
            planned_end=max(now,until)+LEAD_NS+50_000_000
            if not (0<=now-obs['_captured'] and 0<=now-model['last_sample_ns'] and 0<=now-front<=1_000_000_000
                    and planned_end<=obs['_captured']+beat_sync.FRESH_NS
                    and planned_end<=model['last_sample_ns']+beat_sync.FRESH_NS
                    and planned_end<=self.stop_ns
                    and (self.state['started_ns'] is None or
                         planned_end<=self.state['started_ns']+WALK_SECONDS*1_000_000_000)):
                raise ProbeError('host_observation_expired')
            return timeout,now
        try:
            timeout,now=validate()
            while now<until:
                self.sleeper(min(.05,timeout,(until-now)/1e9));timeout,now=validate()
        except ProbeError as exc:
            entry['reason']=code(exc.code);self.pending=False;self.state['input_pending']=False
            if exc.code not in ('dispatch_window_expired','host_observation_expired'):raise
            print('連続入力: 次拍に間に合わないため2回目は未送信。1回目の結果を確認します。',flush=True)
            return 1
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
        return 2
    def note_step(self,index,direction,before,after,outcome,decision,count=1):
        name='run-%03d.jpg'%(100+index);self.save(name,after)
        self.state['events'].append({'index':index,'direction':direction,'motion':outcome,
            'before_sha256':before['_sha'],'after_sha256':after['_sha'],'image':name,
            'target':decision.get('target'),'goods':self.goods(after),'scheduled_inputs':count})
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


def walk(driver):
    w=driver.state;w['started_ns']=driver.clock();refreshes=0
    driver.perform('resume',driver.last)
    obs=driver.observe()
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
        obs,model=driver.synchronize(obs)
        if driver.goods(obs)=='visible':
            w['goods_visible']=True;driver.save('found.jpg',obs);driver.checkpoint()
            driver.finish('goods_visible',obs);return
        decision=driver.choose(obs);direction=decision.get('direction')
        if direction not in MOVE_POINTS:
            driver.finish('goods_partial' if driver.goods(obs)=='partial' else 'no_safe_path',obs);return
        before=obs;action_count=len(w['actions'])
        count=driver.burst_count(before,decision,MAX_STEPS-index+1)
        print('経路判断: %s / 予定%d入力 / %s'%(direction,count,decision.get('reason')),flush=True)
        try:count=driver.perform(direction,before,model,count=count)
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
        after=driver.observe();outcome='unknown'
        for attempt in range(3):
            if driver.goods(after)=='visible':
                w['goods_visible']=True;driver.save('found.jpg',after);driver.checkpoint()
                driver.note_step(index,direction,before,after,'goods_visible',decision,count)
                driver.finish('goods_visible',after);return
            outcome=driver.movement(before,after,direction,expected_steps=count)
            if outcome!='tween' or attempt==2:break
            after=driver.observe()
        if outcome=='moved':
            dx,dy=DIRECTIONS[direction];w['position'][0]+=dx*count;w['position'][1]+=dy*count;w['moves_confirmed']+=count
        elif outcome=='partial' and count==2:
            dx,dy=DIRECTIONS[direction];w['position'][0]+=dx;w['position'][1]+=dy;w['moves_confirmed']+=1
        elif outcome=='door_opened':w['door_changes']+=1
        elif outcome=='terrain_opened':w['terrain_changes']+=1
        driver.note_step(index,direction,before,after,outcome,decision,count)
        print('歩行%d: %s / %d拍入力 / %s / 商品: %s'%(index,direction,count,outcome,driver.goods(after)),flush=True)
        if outcome not in ('moved','door_opened','terrain_opened'):
            driver.finish('unexpected_movement' if outcome=='unexpected' else 'movement_unconfirmed',after);return
        obs=after
        index+=count
    driver.finish('walk_limit',obs)


def parser():
    ap=base.parser();ap.description='TEST-030: 金壁発見後、測定済み1-1周期範囲とHUDで商品が見える位置へ。'
    ap.set_defaults(output='runtime/test-030');return ap


def worker(args):
    folder=Path(args.output);control=Path(args.checkpoint_dir)
    try:r=read_report(control/'report.json',args.run_id,args.start_ns)
    except (ValueError,OSError,ProbeError):return 74
    d=None
    try:
        with base.device_lock():
            key,tok=base.load_pairing(args.token_store,args.store_key)
            crypto=base.Crypto(native=not args.python_crypto);r['search']['crypto_engine']=crypto.engine
            with base.OwnedRpcTimer() as timer:
                client=WalkClient(base.HttpTransport(),key,tok,timeout=8,crypto=crypto,deadline_owner=timer)
                d=Driver(client,r,folder,args.stop_ns,control)
                client.call('launch_app',{'bundle_id':base.GAME},timeout=d.budget())
                base.collect(d,max_restarts=MAX_RESTARTS)
                r['search']['status']='completed' if r['search']['paused'] else 'stopped'
                r['search']['control_reason']=r['search']['reason'];r['search']['control_end_ns']=d.clock()
                if r['search']['candidate'] and r['search']['paused']:
                    r['phase']='walk';client.walking=True;d.checkpoint()
                    try:
                        walk(d)
                        r['reason']=r['walk']['reason']
                        r['status']='completed' if r['walk']['goods_visible'] and r['walk']['paused'] else 'stopped'
                    except (Exception,KeyboardInterrupt) as exc:
                        reason=(code(exc.code) if isinstance(exc,ProbeError) else 'user_interrupt' if isinstance(exc,KeyboardInterrupt)
                                else 'output_write_failed' if isinstance(exc,OSError) else 'internal_error')
                        if reason=='internal_error':d.record_failure('control',exc)
                        r.update(status='stopped',reason=reason)
                        try:d.finish(r['walk']['reason'] or reason,d.last)
                        except (Exception,KeyboardInterrupt):pass
                else:r.update(status='stopped',reason='gold_not_found')
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
    control=Path(tempfile.mkdtemp(prefix='necro-walk-'));r=new_report(start,run_id);write(control,r)
    command=[sys.executable,'-m','necroprobe.shop_walk','--worker','--output',str(folder),'--checkpoint-dir',str(control),
        '--run-id',run_id,'--start-ns',str(start),'--stop-ns',str(start+180_000_000_000),'--token-store',args.token_store]
    if args.store_key is not None:command+=['--store-key',args.store_key]
    if args.python_crypto:command.append('--python-crypto')
    print('TEST-030: 金壁→測定済み1-1周期範囲とライブHUD→新鮮な地形で商品が見える位置へ。画面端0、同じ向きでゲームを表示してください。',flush=True)
    diagnostics={};reason=base.supervisor.supervise(command,max(.001,180-(time.monotonic_ns()-start)/1e9),diagnostics)
    try:r=read_report(control/'report.json',run_id,start)
    except (ValueError,OSError,ProbeError):r['search']['counts_certain']=False;reason=reason or 'report_read_failed'
    r['worker_returncode']=diagnostics.get('returncode');r['worker_exit_confirmed']=diagnostics.get('exit_confirmed')
    if r['worker_exit_confirmed'] is False:r['search']['counts_certain']=False;reason='worker_cleanup_failed'
    if reason or r['status']=='running':r.update(status='stopped',reason=code(reason or 'worker_failed'))
    r['end_ns']=time.monotonic_ns();write(folder,r,'parent-result.json')
    if r['worker_exit_confirmed'] is not False:write(folder,r);shutil.rmtree(control,ignore_errors=True)
    w=r['walk'];paused=w['paused'] if w['started_ns'] is not None else r['search']['paused']
    print('終了: %s / 歩行確認: %d / 商品可視: %s / ポーズ確認: %s'%(r['reason'],w['moves_confirmed'],w['goods_visible'],paused),flush=True)
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
    except ProbeError as exc:print('TEST-030停止: '+code(exc.code),file=sys.stderr);return 2
    except OSError:print('TEST-030: 結果保存に失敗しました。',file=sys.stderr);return 2
    finally:
        for sig,handler in previous.items():signal.signal(sig,handler)

if __name__=='__main__':raise SystemExit(main())
