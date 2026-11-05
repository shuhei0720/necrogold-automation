"""TEST-014: iPhoneで金壁候補まで反復する上限付き実機版。"""
import argparse
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
from pathlib import Path
import re
import signal
import sys
import time
import uuid

from . import VERSION, input_path as supervisor, resume_once as resume
from .capture import inspect_payload, validate_source_geometry
from .crypto import Crypto
from .deadlines import OwnedRpcTimer
from .protocol import Client, GAME, HttpTransport, load_pairing
from .session import atomic_write, safe_info
from .validation import ProbeError, json_object

REVISION = 'gold-restart-v1'
SESSION_SECONDS = 180
MAX_RESTARTS = 30
MAX_ACTIONS = 64
MAX_OBSERVATIONS = 240
POINTS = {'resume': (297, 448), 'pause': (390, 448), 'restart': (144, 448)}
ERRORS = resume.ERRORS | {'batch_unknown','screen_unconfirmed','new_run_unconfirmed','already_running',
                        'observation_limit','pause_unconfirmed','gold_candidate','restart_limit','time_limit'}


def batch(action):
    x,y=POINTS[action]
    return {'steps':[{'method':'wait_for','params':{'foreground':GAME,'timeout':.5}},
                     {'method':'tap','params':{'x':x,'y':y,'fast':True,'settle':False}}], 'observe':'none'}


class RestartClient(Client):
    def __init__(self,*args,**kwargs):
        kwargs.update(allow_launch=True,source_geometry=True)
        super().__init__(*args,**kwargs)
        self.batches=0; self.launch_sent=False
    def _validate(self,method,params):
        if method=='run_steps' and any(resume.exact(params,batch(a)) for a in POINTS): return
        expected={'device_info':{},'launch_app':{'bundle_id':GAME},'screenshot':resume.CAPTURE_PARAMS}.get(method)
        if expected is None or not resume.exact(params,expected): raise ProbeError('method_not_allowed')
    def call(self,method,params=None,*,timeout=None):
        params={} if params is None else params
        self._validate(method,params)
        if method=='run_steps':
            if self.batches>=MAX_ACTIONS: raise ProbeError('method_not_allowed')
            self.batches+=1
        if method=='launch_app':
            if self.launch_sent: raise ProbeError('method_not_allowed')
            self.launch_sent=True
        return super().call(method,params,timeout=timeout)


def code(value):
    return value if type(value) is str and (value in ERRORS or re.fullmatch(r'http_status_[1-5][0-9]{2}',value)) else 'internal_error'


def new_report(start,run_id):
    return {'version':VERSION,'test_id':'TEST-014','revision':REVISION,'run_id':run_id,
            'start_ns':start,'end_ns':None,'status':'running','reason':None,
            'candidate':False,'paused':False,'restarts_confirmed':0,'actions':[],'runs':[],
            'capture_ms':[],'analysis_ms':[],'input_ms':[], 'worker_exit_confirmed':None,
            'worker_returncode':None,'crypto_engine':None,'counts_certain':True}


def write(folder,report,name='report.json'):
    atomic_write(Path(folder)/name,json.dumps(report,ensure_ascii=False,allow_nan=False,indent=2).encode())


def read_report(path,run_id,start):
    with Path(path).open('rb') as source:
        r=json_object(source.read(65537),65536)
    require=supervisor.require
    require(set(r)==set(new_report(start,run_id)))
    for k,v in [('version',VERSION),('test_id','TEST-014'),('revision',REVISION),('run_id',run_id),('start_ns',start)]:
        require(type(r[k]) is type(v) and r[k]==v)
    require(r['status'] in ('running','completed','stopped'))
    require(r['reason'] is None or (type(r['reason']) is str and code(r['reason'])==r['reason']))
    for k in ('candidate','paused','counts_certain'): require(type(r[k]) is bool)
    require(type(r['restarts_confirmed']) is int and 0<=r['restarts_confirmed']<=MAX_RESTARTS)
    require(r['worker_exit_confirmed'] is None or type(r['worker_exit_confirmed']) is bool)
    require(r['worker_returncode'] is None or (type(r['worker_returncode']) is int and -255<=r['worker_returncode']<=255))
    require(r['crypto_engine'] in (None,'native_i386','python'))
    require(r['end_ns'] is None or (type(r['end_ns']) is int and start<=r['end_ns']<2**63))
    for k in ('capture_ms','analysis_ms','input_ms'):
        require(type(r[k]) is list and len(r[k])<=MAX_OBSERVATIONS)
        require(all(type(v) in (int,float) and math.isfinite(v) and 0<=v<=SESSION_SECONDS*1000 for v in r[k]))
    require(type(r['actions']) is list and len(r['actions'])<=MAX_ACTIONS)
    for a in r['actions']:
        require(type(a) is dict and set(a)=={'action','outcome','start_ns'})
        require(a['action'] in POINTS and a['outcome'] in ('not_requested','not_sent','acknowledged','unknown'))
        require(type(a['start_ns']) is int and start<=a['start_ns']<2**63)
    require(type(r['runs']) is list and len(r['runs'])<=MAX_RESTARTS+1)
    for row in r['runs']:
        require(type(row) is dict and set(row)=={'index','sha256','gold','gold_peak','seen_ns'})
        require(type(row['index']) is int and 1<=row['index']<=MAX_RESTARTS+1)
        require(type(row['sha256']) is str and re.fullmatch('[0-9a-f]{64}',row['sha256']) is not None)
        require(row['gold'] in ('clear','candidate','unknown'))
        require(type(row['gold_peak']) is int and 0<=row['gold_peak']<=255)
        require(type(row['seen_ns']) is int and start<=row['seen_ns']<2**63)
    return r


@contextmanager
def device_lock(path=None):
    """workerが排他を保持。親が終了しても生存workerからロックを奪わない。"""
    path=Path(path) if path else Path.home()/'.necroprobe'/'restart.lock'
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a') as lock:
        try: fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError: raise ProbeError('already_running') from None
        try: yield
        finally: fcntl.flock(lock.fileno(),fcntl.LOCK_UN)


class RuntimeDriver:
    def __init__(self,client,report,folder,stop_ns,clock=time.monotonic_ns):
        self.client,self.report,self.folder,self.stop_ns,self.clock=client,report,Path(folder),stop_ns,clock
        self.last=None; self.pending=False
    def budget(self):
        remain=(self.stop_ns-self.clock())/1e9
        if remain<.001: raise ProbeError('session_deadline')
        return min(8,remain)
    def bounded(self): return self.clock()>=self.stop_ns-8_000_000_000
    def checkpoint(self): write(self.folder,self.report)
    def guard(self):
        info=safe_info(self.client.call('device_info',{},timeout=self.budget()).result)
        replied=self.clock()
        if info['foreground']!='game' or info['screen_locked'] is not False: raise ProbeError('foreground_not_verified')
        if not all(c in info['advertised_known_capabilities'] for c in resume.CAPABILITIES): raise ProbeError('capabilities_missing')
        return replied
    def observe(self):
        from .gold_scan import analyze
        if len(self.report['capture_ms'])>=MAX_OBSERVATIONS: raise ProbeError('observation_limit')
        self.guard()
        started=self.clock()
        payload=self.client.call('screenshot',dict(resume.CAPTURE_PARAMS),timeout=self.budget()).result
        raw,image=inspect_payload(payload)
        validate_source_geometry(payload,image,resume.CAPTURE_PARAMS)
        g=image['reported_geometry']
        if (image['pixel_width'],image['pixel_height'],g['source_orientation'],g['point_width'],g['point_height'])!=(896,414,2,414,896):
            raise ProbeError('source_geometry_invalid')
        decoded=self.clock()
        obs=analyze(raw)
        done=self.clock()
        self.report['capture_ms'].append((decoded-started)/1e6)
        self.report['analysis_ms'].append((done-decoded)/1e6)
        obs.update(_raw=raw,_captured=started,_sha=hashlib.sha256(raw).hexdigest())
        self.last=obs
        return obs
    def tap(self,action,observed):
        if self.pending or observed is not self.last: raise ProbeError('method_not_allowed')
        if self.report['candidate'] and action!='pause': raise ProbeError('method_not_allowed')
        if (action=='pause' and observed['state']!='floor') or (action!='pause' and observed['state']!='pause'):
            raise ProbeError('screen_unconfirmed')
        if action=='restart' and not observed['restart_label']: raise ProbeError('screen_unconfirmed')
        front=self.guard()
        if len(self.report['actions'])>=MAX_ACTIONS: raise ProbeError('method_not_allowed')
        entry={'action':action,'outcome':'not_requested','start_ns':self.clock()}
        self.report['actions'].append(entry)
        entry['outcome']='unknown'; self.pending=True
        self.checkpoint()
        now=self.clock()
        try:
            timeout=self.budget()
            if not(0<=now-observed['_captured']<=3_000_000_000 and 0<=now-front<=1_000_000_000):
                raise ProbeError('host_observation_expired')
        except ProbeError:
            entry['outcome']='not_requested';self.pending=False
            raise
        result=self.client.call('run_steps',batch(action),timeout=timeout).result
        self.report['input_ms'].append((self.clock()-now)/1e6)
        outcome,_=resume.batch_evidence(result)
        entry['outcome']=outcome
        self.pending=outcome=='unknown'
        self.checkpoint()
        if outcome!='acknowledged': raise ProbeError('batch_unknown')
    def save(self,name,observed): atomic_write(self.folder/name,observed['_raw'])
    def record_run(self,observed):
        index=len(self.report['runs'])+1
        self.save('run-%03d.jpg'%index,observed)
        self.report['runs'].append({'index':index,'sha256':observed['_sha'],'gold':observed['gold'],
                                   'gold_peak':observed['gold_peak'],'seen_ns':self.clock()})
        self.checkpoint()
        print('第%d回: %s / リスタート確認 %d回'%(index,{'clear':'金壁なし','candidate':'金壁候補','unknown':'未判定'}[observed['gold']],self.report['restarts_confirmed']),flush=True)
    def changed(self,a,b):
        from .gold_scan import changed
        return changed(a['fingerprint'],b['fingerprint'])


def collect(driver,max_restarts=MAX_RESTARTS):
    """一度候補を見たら保持。曖昧入力には以後の入力を追加しない。"""
    r=driver.report
    def latch(obs):
        if obs['state']=='floor' and obs['gold']=='candidate' and not r['candidate']:
            r.update(candidate=True,reason='gold_candidate')
            driver.save('found.jpg',obs)
            driver.checkpoint()
    def pause_and_finish(obs,reason):
        r['reason']=reason
        if reason=='gold_candidate':
            latch(obs)
        driver.checkpoint()
        driver.tap('pause',obs)
        for _ in range(6):
            after=driver.observe()
            latch(after)
            if after['state']=='pause':
                r['paused']=True; driver.save('stopped.jpg',after); return r
        r['reason']='pause_unconfirmed'
        return r
    def ready(previous=None):
        for _ in range(6):
            obs=driver.observe()
            if obs['state']=='floor' and obs['gold']=='candidate': return obs
            if obs['state']=='floor' and (previous is None or driver.changed(previous,obs)): return obs
        raise ProbeError('new_run_unconfirmed' if previous else 'screen_unconfirmed')
    obs=None
    for _ in range(6):
        obs=driver.observe()
        if obs['state'] in ('pause','floor'): break
    else: raise ProbeError('screen_unconfirmed')
    driver.save('initial.jpg',obs)
    if obs['state']=='pause':
        driver.tap('resume',obs)
        obs=ready()
    driver.record_run(obs)
    while True:
        if obs['gold']=='candidate': return pause_and_finish(obs,'gold_candidate')
        if r['restarts_confirmed']>=max_restarts: return pause_and_finish(obs,'restart_limit')
        if driver.bounded(): return pause_and_finish(obs,'time_limit')
        # 連続した同一ランの有効なclearだけを2回と数える。
        prior=obs if obs['gold']=='clear' else None
        for _ in range(6):
            current=driver.observe()
            if current['state']=='floor' and current['gold']=='candidate': return pause_and_finish(current,'gold_candidate')
            clear=current['state']=='floor' and current['gold']=='clear'
            if clear and prior is not None and not driver.changed(prior,current):
                obs=current; break
            prior=current if clear else None
        else: raise ProbeError('screen_unconfirmed')
        if driver.bounded(): return pause_and_finish(obs,'time_limit')
        driver.tap('pause',obs)
        for _ in range(6):
            menu=driver.observe()
            latch(menu)
            if menu['state']=='pause' and r['candidate']:
                r['paused']=True;driver.save('stopped.jpg',menu);return r
            if menu['state']=='pause' and menu['restart_label']: break
        else: raise ProbeError('screen_unconfirmed')
        # 終了予算に入ったら、既にポーズしているのでリスタートしない。
        if driver.bounded():
            r.update(paused=True,reason='time_limit');driver.save('stopped.jpg',menu);return r
        driver.tap('restart',menu)
        after=ready(obs)
        if after['gold']=='candidate':
            if driver.changed(obs,after):
                r['restarts_confirmed']+=1
                driver.record_run(after)
            return pause_and_finish(after,'gold_candidate')
        r['restarts_confirmed']+=1
        obs=after
        driver.record_run(obs)


def parser():
    ap=argparse.ArgumentParser(description='TEST-014: 金壁候補まで最大30回/180秒、発見したらポーズ。')
    ap.add_argument('--output',default='runtime/test-014')
    ap.add_argument('--token-store',default=str(Path.home()/'.loopctrl/token.json'))
    ap.add_argument('--store-key',default=None)
    ap.add_argument('--python-crypto',action='store_true')
    ap.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    ap.add_argument('--stop-ns',type=int,default=0,help=argparse.SUPPRESS)
    ap.add_argument('--start-ns',type=int,default=0,help=argparse.SUPPRESS)
    ap.add_argument('--run-id',default=None,help=argparse.SUPPRESS)
    return ap


def worker(args):
    folder=Path(args.output)
    try: report=read_report(folder/'report.json',args.run_id,args.start_ns)
    except (ValueError,OSError,ProbeError): return 74
    driver=None
    try:
        with device_lock():
            key,tok=load_pairing(args.token_store,args.store_key)
            crypto=Crypto(native=not args.python_crypto)
            report['crypto_engine']=crypto.engine
            with OwnedRpcTimer() as timer:
                client=RestartClient(HttpTransport(),key,tok,timeout=8,crypto=crypto,deadline_owner=timer)
                driver=RuntimeDriver(client,report,folder,args.stop_ns)
                client.call('launch_app',{'bundle_id':GAME},timeout=driver.budget())
                collect(driver)
                report['status']='completed' if report['paused'] else 'stopped'
    except ProbeError as exc: report.update(status='stopped',reason=code(exc.code))
    except KeyboardInterrupt: report.update(status='stopped',reason='user_interrupt')
    except OSError: report.update(status='stopped',reason='output_write_failed')
    except Exception: report.update(status='stopped',reason='internal_error')
    report['end_ns']=time.monotonic_ns()
    try:
        if driver and driver.last is not None: driver.save('last.jpg',driver.last)
        write(folder,report)
    except OSError: return 2
    return 0


def run(args):
    if args.worker:return worker(args)
    base=Path(args.output).resolve();base.mkdir(parents=True,exist_ok=True)
    run_id=uuid.uuid4().hex;start=time.monotonic_ns()
    folder=base/('gold-loop-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+run_id[:8]);folder.mkdir(mode=0o700)
    report=new_report(start,run_id);write(folder,report)
    command=[sys.executable,'-m','necroprobe.restart_loop','--worker','--output',str(folder),
             '--start-ns',str(start),'--stop-ns',str(start+SESSION_SECONDS*1_000_000_000),'--run-id',run_id,'--token-store',args.token_store]
    if args.store_key is not None:command+=['--store-key',args.store_key]
    if args.python_crypto:command.append('--python-crypto')
    print('TEST-014: 金壁候補まで最大30回/180秒。ゲームを表示したまま待ってください。',flush=True)
    diagnostics={}
    reason=supervisor.supervise(command,max(.001,SESSION_SECONDS-(time.monotonic_ns()-start)/1e9),diagnostics)
    try: report=read_report(folder/'report.json',run_id,start)
    except (ValueError,OSError,ProbeError):
        report['counts_certain']=False;reason=reason or 'report_read_failed'
    report['worker_exit_confirmed']=diagnostics.get('exit_confirmed')
    report['worker_returncode']=diagnostics.get('returncode')
    if report['worker_exit_confirmed'] is False:
        report['counts_certain']=False;reason='worker_cleanup_failed'
    if reason or report['status']=='running':report.update(status='stopped',reason=code(reason or 'worker_failed'))
    report['end_ns']=time.monotonic_ns();write(folder,report,'parent-result.json')
    if report['worker_exit_confirmed'] is not False:write(folder,report)
    labels={'gold_candidate':'金壁候補を検出','restart_limit':'リスタート上限','time_limit':'時間上限'}
    print('終了: '+labels.get(report['reason'],report['reason'] or 'unknown')+' / ポーズ確認: '+str(report['paused']),flush=True)
    print('リスタート確認: '+(str(report['restarts_confirmed']) if report['counts_certain'] else '不明')+' / 保存先: '+str(folder),flush=True)
    if not report['paused']:print('ポーズ未確認です。ゲーム画面を確認し、必要なら手動でポーズしてください。',flush=True)
    return 0 if report['status']=='completed' else 2


def main(argv=None):
    args=parser().parse_args(argv);previous={}
    if not args.worker:
        supervisor._cancel_requested=False
        def interrupt(_sig,_frame):supervisor._cancel_requested=True
        for sig in (signal.SIGINT,signal.SIGTERM):
            previous[sig]=signal.getsignal(sig);signal.signal(sig,interrupt)
    try:return run(args)
    except ProbeError as exc:print('TEST-014停止: '+code(exc.code),file=sys.stderr);return 2
    except OSError:print('TEST-014: 結果保存に失敗しました。',file=sys.stderr);return 2
    finally:
        for sig,handler in previous.items():signal.signal(sig,handler)

if __name__=='__main__':raise SystemExit(main())
