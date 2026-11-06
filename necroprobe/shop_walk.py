"""TEST-016: 画面端0で1歩ずつ拍に合わせ、商品可視で止める限定実機版。

HTTP中点と150ms先行は未校正の推定。予定拍での実受付を保証しない。
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import shutil
import signal
import sys
import tempfile
import time
import uuid

from . import VERSION, restart_loop as base
from .validation import ProbeError, json_object

REVISION='shop-walk-v1'
MOVE_POINTS={'up':(290,838),'down':(124,838),'left':(207,49),'right':(207,838)}
DIRECTIONS={'up':(0,-1),'down':(0,1),'left':(-1,0),'right':(1,0)}
MAX_STEPS=16
WALK_SECONDS=45
MAX_RESTARTS=12
LEAD_NS=150_000_000
REASONS={'goods_visible','goods_partial','no_safe_path','movement_unconfirmed','unexpected_movement',
         'beat_unconfirmed','walk_limit','gold_not_found','approach','navigation_unknown'}


def code(reason):return reason if reason in REASONS else base.code(reason)


def move_batch(direction):
    x,y=MOVE_POINTS[direction]
    return {'steps':[{'method':'wait_for','params':{'foreground':base.GAME,'timeout':.5}},
        {'method':'gesture','params':{'fingers':[[{'x':x,'y':y,'t':0},{'x':x,'y':y,'t':.05}]]}}],
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
        'position':[0,0],'moves_confirmed':0,'door_changes':0,'actions':[],'events':[],
        'samples':[],'models':[],'input_pending':False,
        'navigation_ms':[],'beat_extract_ms':[],'motion_ms':[],'beat_fit_ms':[]}


def new_report(start,run_id):
    return {'version':VERSION,'test_id':'TEST-016','revision':REVISION,'run_id':run_id,
        'start_ns':start,'end_ns':None,'phase':'search','status':'running','reason':None,
        'control_reason':None,'control_end_ns':None,'worker_returncode':None,'worker_exit_confirmed':None,
        'search':base.new_report(start,run_id),'walk':new_walk()}


def write(folder,report,name='report.json'):
    base.atomic_write(Path(folder)/name,json.dumps(report,ensure_ascii=False,allow_nan=False,indent=2).encode())


def read_report(path,run_id,start):
    with Path(path).open('rb') as source:r=json_object(source.read(131073),131072)
    req=base.supervisor.require
    req(type(r) is dict and set(r)==set(new_report(start,run_id)))
    for k,v in [('version',VERSION),('test_id','TEST-016'),('revision',REVISION),('run_id',run_id),('start_ns',start)]:
        req(type(r[k]) is type(v) and r[k]==v)
    req(r['phase'] in ('search','walk','done'))
    req(r['status'] in ('running','completed','stopped'))
    for key in ('reason','control_reason'):req(r[key] is None or type(r[key]) is str and code(r[key])==r[key])
    for key in ('end_ns','control_end_ns'):req(r[key] is None or type(r[key]) is int and start<=r[key]<2**63)
    req(r['worker_exit_confirmed'] is None or type(r['worker_exit_confirmed']) is bool)
    req(r['worker_returncode'] is None or type(r['worker_returncode']) is int and -255<=r['worker_returncode']<=255)
    base.validate_report(r['search'],run_id,start)
    w=r['walk'];req(type(w) is dict and set(w)==set(new_walk()))
    for key in ('goods_visible','paused','input_pending'):req(type(w[key]) is bool)
    req(w['device_timing_verified'] is False and w['dispatch_timing_calibrated'] is False and w['dispatch_lead_ns']==LEAD_NS)
    req(w['reason'] is None or type(w['reason']) is str and code(w['reason'])==w['reason'])
    for key in ('started_ns','end_ns'):req(w[key] is None or type(w[key]) is int and start<=w[key]<2**63)
    req(type(w['position']) is list and len(w['position'])==2 and all(type(v) is int and -16<=v<=16 for v in w['position']))
    for key in ('moves_confirmed','door_changes'):req(type(w[key]) is int and 0<=w[key]<=MAX_STEPS)
    for key,limit in [('actions',MAX_STEPS+2),('events',MAX_STEPS),('samples',12),('models',MAX_STEPS+1)]:
        req(type(w[key]) is list and len(w[key])<=limit and all(type(v) is dict for v in w[key]))
    for a in w['actions']:
        req(set(a)=={'action','outcome','requested_ns','issued_ns','completed_ns','target_ns'})
        req(a['action'] in (*MOVE_POINTS,'resume','pause'))
        req(a['outcome'] in ('not_requested','unknown','not_sent','acknowledged'))
        for k in ('requested_ns','issued_ns','completed_ns','target_ns'):
            req(a[k] is None or type(a[k]) is int and start<=a[k]<2**63)
    for key in ('navigation_ms','beat_extract_ms','motion_ms','beat_fit_ms'):
        req(type(w[key]) is list and len(w[key])<=240)
        req(all(type(v) in (float,int) and math.isfinite(v) and 0<=v<=180_000 for v in w[key]))
    return r


class Driver(base.RuntimeDriver):
    def __init__(self,client,outer,folder,stop_ns,control,clock=time.monotonic_ns):
        self.outer=outer;self.state=outer['walk'];self.model=None;self.samples=[];self.visits={(0,0):1}
        super().__init__(client,outer['search'],folder,stop_ns,clock,control,self.analyze_frame)
    def analyze_frame(self,image,obs):
        if self.outer['phase']!='walk' or obs['state']!='floor':return None
        from . import beat_sync,shop_navigation
        begin=self.clock();scene=shop_navigation.scan(image);scanned=self.clock()
        beat=beat_sync.extract(image);finished=self.clock()
        self.state['navigation_ms'].append((scanned-begin)/1e6)
        self.state['beat_extract_ms'].append((finished-scanned)/1e6)
        return {'scene':scene,'beat':beat}
    def checkpoint(self):
        before=self.clock();write(self.control_dir,self.outer)
        if len(self.report['checkpoint_ms'])<512:self.report['checkpoint_ms'].append((self.clock()-before)/1e6)
    def observe(self):
        observed=super().observe()
        if self.outer['phase']=='walk' and self.goods(observed)=='visible' and not self.state['goods_visible']:
            self.state['goods_visible']=True
            self.save('found.jpg',observed)
            self.checkpoint()
        return observed
    def goods(self,obs):
        extra=obs.get('_extra')
        return extra['scene'].goods if extra else 'unknown'
    def choose(self,obs):
        from .shop_navigation import choose
        return choose(obs['_extra']['scene'],tuple(self.state['position']),self.visits)
    def movement(self,before,after,direction):
        from .shop_navigation import motion
        if not before.get('_extra') or not after.get('_extra'):return 'unknown'
        before_ns=self.clock();result=motion(before['_extra']['scene'],after['_extra']['scene'],direction)
        self.state['motion_ms'].append((self.clock()-before_ns)/1e6);return result
    def fit_beat(self):
        from .beat_sync import fit
        before=self.clock();result=fit(self.samples)
        self.state['beat_fit_ms'].append((self.clock()-before)/1e6);return result
    def add_sample(self,obs):
        from .beat_sync import make_sample
        extra=obs.get('_extra')
        if not extra or extra.get('beat') is None:return None
        sample=make_sample(extra['beat'],obs['_http_start_ns'],obs['_http_end_ns'])
        self.samples=(self.samples+[sample])[-12:];self.state['samples']=self.samples
        return sample
    def synchronize(self,obs):
        from . import beat_sync
        sample=self.add_sample(obs)
        if self.model and sample and beat_sync.compatible(self.model,sample):
            updated=self.fit_beat()
            if updated:self.model=updated
            if beat_sync.next_target(self.model,self.clock()) is not None:return obs,self.model
        self.model=None
        # 不均一間隔で別解を減らす。未知画面も含め最大12回で打切り。
        self.samples=[] if sample is None else [sample]
        for i in range(12):
            if len(self.samples)>=8:
                model=self.fit_beat()
                if model:
                    self.model=model;self.state['models'].append(model);self.checkpoint()
                    return obs,model
            if self.goods(obs)=='visible':return obs,None
            if self.clock()-self.state['started_ns']>=WALK_SECONDS*1_000_000_000:raise ProbeError('walk_limit')
            self.budget();self.sleeper((.0,.07,.17)[i%3])
            obs=self.observe()
            if self.goods(obs)=='visible':return obs,None
            self.add_sample(obs)
        raise ProbeError('beat_unconfirmed')
    def perform(self,action,obs,model=None):
        from . import beat_sync
        if self.pending or self.state['input_pending'] or obs is not self.last:raise ProbeError('method_not_allowed')
        moving=action in MOVE_POINTS
        if self.state['goods_visible'] and action!='pause':raise ProbeError('method_not_allowed')
        if (action=='resume' and obs['state']!='pause') or (action!='resume' and obs['state']!='floor'):
            raise ProbeError('screen_unconfirmed')
        if len(self.state['actions'])>=MAX_STEPS+2:raise ProbeError('walk_limit')
        target=None
        if moving:
            # 既測定の前面照会とcheckpointを先行時間に加算。150msは未校正。
            front_ms=self.report['foreground_ms'][-1] if self.report['foreground_ms'] else 150
            checkpoint_ms=self.report['checkpoint_ms'][-1] if self.report['checkpoint_ms'] else 80
            preparation_ns=int(min(500,front_ms+checkpoint_ms)*1e6)
            target=beat_sync.next_target(model,self.clock(),LEAD_NS+preparation_ns)
            if target is None:raise ProbeError('beat_unconfirmed')
            until=target-LEAD_NS-preparation_ns
            while self.clock()<until:
                remain=self.budget();self.sleeper(min(.05,remain,max(0,(until-self.clock())/1e9)))
        front=self.guard()
        entry={'action':action,'outcome':'not_requested','requested_ns':self.clock(),
               'issued_ns':None,'completed_ns':None,'target_ns':target}
        self.state['actions'].append(entry)
        # 復帰失敗・unknownでも以前のポーズを最終状態に流用しない。
        if action=='resume':self.state['paused']=False
        entry['outcome']='unknown';self.pending=True;self.state['input_pending']=True
        self.checkpoint()
        now=self.clock()
        try:
            timeout=self.budget()
            if moving and self.state['started_ns'] is not None and now-self.state['started_ns']>=WALK_SECONDS*1_000_000_000:
                raise ProbeError('walk_limit')
            if not(0<=now-obs['_captured']<=3_000_000_000 and 0<=now-front<=1_000_000_000):raise ProbeError('host_observation_expired')
            if moving and (now>target or target-now>model['period_ns']):raise ProbeError('beat_unconfirmed')
        except ProbeError:
            entry['outcome']='not_requested';self.pending=False;self.state['input_pending']=False;raise
        entry['issued_ns']=now
        result=self.client.call('run_steps',move_batch(action) if moving else base.batch(action),timeout=timeout).result
        entry['completed_ns']=self.clock()
        outcome=gesture_evidence(result) if moving else base.resume.batch_evidence(result)[0]
        entry['outcome']=outcome
        self.pending=outcome=='unknown';self.state['input_pending']=self.pending
        self.checkpoint()
        if outcome!='acknowledged':raise ProbeError('batch_unknown')
    def note_step(self,index,direction,before,after,outcome,decision):
        name='run-%03d.jpg'%(100+index);self.save(name,after)
        self.state['events'].append({'index':index,'direction':direction,'motion':outcome,
            'before_sha256':before['_sha'],'after_sha256':after['_sha'],'image':name,
            'target':decision.get('target'),'goods':self.goods(after)})
        self.visits[tuple(self.state['position'])]=self.visits.get(tuple(self.state['position']),0)+1
        self.checkpoint()
    def finish(self,reason,obs):
        self.state['reason']=code(reason);self.checkpoint()
        if self.pending or self.state['input_pending']:return
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
    w=driver.state;w['started_ns']=driver.clock()
    driver.perform('resume',driver.last)
    obs=driver.observe()
    # 復帰中の画像は短く再取得。ポーズに対する方向入力は禁止。
    for _ in range(3):
        if obs['state']=='floor':break
        obs=driver.observe()
    if obs['state']!='floor':raise ProbeError('screen_unconfirmed')
    for index in range(1,MAX_STEPS+1):
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
        before=obs;driver.perform(direction,before,model)
        after=driver.observe();outcome='unknown'
        for attempt in range(3):
            if driver.goods(after)=='visible':
                w['goods_visible']=True;driver.save('found.jpg',after);driver.checkpoint()
                driver.note_step(index,direction,before,after,'goods_visible',decision)
                driver.finish('goods_visible',after);return
            outcome=driver.movement(before,after,direction)
            if outcome!='tween' or attempt==2:break
            after=driver.observe()
        if outcome=='moved':
            dx,dy=DIRECTIONS[direction];w['position'][0]+=dx;w['position'][1]+=dy;w['moves_confirmed']+=1
        elif outcome=='door_opened':w['door_changes']+=1
        driver.note_step(index,direction,before,after,outcome,decision)
        print('歩行%d: %s / %s / 商品: %s'%(index,direction,outcome,driver.goods(after)),flush=True)
        if outcome not in ('moved','door_opened'):
            driver.finish('unexpected_movement' if outcome=='unexpected' else 'movement_unconfirmed',after);return
        obs=after
    driver.finish('walk_limit',obs)


def parser():
    ap=base.parser();ap.description='TEST-016: 金壁発見後、拍を推定し1歩ずつ商品が見える位置へ。'
    ap.set_defaults(output='runtime/test-016');return ap


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
                    except (ProbeError,KeyboardInterrupt,OSError) as exc:
                        reason=code(exc.code) if isinstance(exc,ProbeError) else 'user_interrupt' if isinstance(exc,KeyboardInterrupt) else 'output_write_failed'
                        r.update(status='stopped',reason=reason)
                        try:d.finish(r['walk']['reason'] or reason,d.last)
                        except (ProbeError,OSError,KeyboardInterrupt):pass
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
    print('TEST-016: 金壁→拍の推定→1歩ずつ商品が見える位置へ。画面端0、同じ向きでゲームを表示してください。',flush=True)
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
    except ProbeError as exc:print('TEST-016停止: '+code(exc.code),file=sys.stderr);return 2
    except OSError:print('TEST-016: 結果保存に失敗しました。',file=sys.stderr);return 2
    finally:
        for sig,handler in previous.items():signal.signal(sig,handler)

if __name__=='__main__':raise SystemExit(main())
