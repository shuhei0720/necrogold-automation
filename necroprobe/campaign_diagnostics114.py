"""Optional, bounded TEST114 diagnostics. Never evidence for input authority."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import re
import time
import uuid

MAX_BYTES = 256 * 1024
MAX_RUNS = 32
MAX_MARKERS = 64
SCHEMA = 'necroprobe-private-diagnostics114-v1'
MEMBER = 'private-diagnostics.json'
RPC_BINS = frozenset(('setup','start','cancel','status','manifest','records','images','published','diagnostic'))
PHASES = frozenset(('session_wait','records_collect','images_collect','evidence_verify','inventory',
    'zip_build','zip_verify','copy','copy_hash','archive_hash','publish_ack','predecessor',
    'next_start','diagnostic_rpc','campaign_seal','schema_prepare'))
RPC_ERRORS = frozenset(('rpc_error','connection_error','http_body_limit','http_body_truncated',
    'response_mac_mismatch','rpc_deadline','cancel_requested','invalid_cycle_response',
    'cycle_evidence_storage_unavailable','pending','storage','not_admitted','other'))
STAGES = frozenset(('request_crypto','http','response_json','response_auth','response_crypto','result_json','complete','unknown'))
DIAG_ERRORS = frozenset(('budget','rpc','shape','observer','storage','size','cancelled','clock'))
TIMES = ('request_start_ns','http_start_ns','http_end_ns','decrypt_start_ns','decrypt_end_ns','response_end_ns')
PARTS = ('request_crypto','http','response_parse_auth','decrypt','result_parse')
UUID = re.compile(r'[0-9a-f]{32}\Z')
SHA = re.compile(r'[0-9a-f]{64}\Z')
MAX_NS = 2**63-1


def _ns(value):
    return type(value) is int and 0 <= value <= MAX_NS


def _id(value):
    return type(value) is str and UUID.fullmatch(value) is not None


def _raw(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')


def observer(client):
    try:
        return getattr(client,'_diagnostics114',None) if getattr(client,'diagnostics114',False) is True else None
    except Exception:
        return None


def notify(client, method, *args, **kwargs):
    try:
        target = observer(client)
        if target is not None:
            return getattr(target,method)(*args,**kwargs)
    except Exception:
        pass  # Optional observation cannot replace a primary result/exception.
    return None


def now(client):
    target=observer(client)
    if target is None:return None
    try:
        value=time.monotonic_ns()
        if not _ns(value):raise ValueError('clock')
        return value
    except Exception:
        try:target.errors.add('clock')
        except Exception:pass
        return None


@contextmanager
def span(client, name, run_id=None):
    if observer(client) is None:
        yield
        return
    start = now(client)
    try:
        yield
    finally:
        notify(client,'phase',name,run_id,start,now(client))


def attach(client, base):
    if getattr(client,'diagnostics114',False) is not True:
        return None
    try:
        value = DiagnosticCollector114(base)
        client._diagnostics114 = value
        return value
    except Exception:
        return None


def admit_readonly114(method, params):
    """Only the new entry calls this; no generic/client/native allowlist changes."""
    if method == 'recent_logs':
        return type(params) is dict and set(params)=={'max_elements'} and type(params['max_elements']) is int and params['max_elements']==500
    return (method=='necro_native_status' and type(params) is dict and set(params)=={'run_id','keepalive'}
        and _id(params['run_id']) and params['keepalive'] is False)


# Exact known G1 grammar only. No matching line, URL or arbitrary body is saved.
_MARKERS = {
 '🔼 runner brought forward (foreground for LN prompt)':'lan_foreground',
 '⚠️ could not bring the runner forward':'lan_foreground_failed',
 '📡 Nearby refused (Local Network) — bringing the runner forward to request access':'nearby_foreground',
 '⚠️ Nearby refused (Local Network) and the runner could not come forward to ask':'nearby_foreground_failed',
 '🔙 Callback opened via XCTest daemon':'callback_opened',
 '🏠 LoopCtrl is in the background after bootstrap — bringing it back':'bootstrap_foreground',
 '🏠 LoopCtrl reopened':'bootstrap_opened',
 '🏠 couldn\'t reopen LoopCtrl':'bootstrap_failed',
}
for _event in ('didFinishLaunching','didBecomeActive','willResignActive','didEnterBackground','willEnterForeground','willTerminate'):
    _MARKERS['🔄 app '+_event] = 'app_'+_event
for _event in ('willConnect','didActivate','willDeactivate','didEnterBackground','willEnterForeground','didDisconnect'):
    _MARKERS['🔄 scene '+_event] = 'scene_'+_event
_DYNAMIC_MARKERS = (
 (re.compile(r'🔙 Callback opened via UIApplication \(attempt [123]\)\Z'),'callback_opened'),
 (re.compile(r'🔙 Callback open failed, retrying \([123]\)\Z'),'callback_failed'),
 (re.compile(r'🔙 Callback gave up after [123] attempts\Z'),'callback_failed'),
 (re.compile(r'🧵 activate abandoned after 5s — still running in the background\Z'),'activate_abandoned'),
 (re.compile(r'🧵 abandoned activate finally ended after [0-9]{1,6}s\Z'),'activate_late_completed'),
 (re.compile(r'⏱ [✓✗] activate_app [0-9]{1,6}ms(?: \(queue [0-9]{1,6}ms\))?\Z'),'activate_completed'),
)
MARKER_KINDS = frozenset(_MARKERS.values()) | frozenset(kind for _,kind in _DYNAMIC_MARKERS)


def marker(line):
    if type(line) is not str or len(line)>1024:
        return None
    match=re.fullmatch(r'\[([0-9]{2}):([0-9]{2}):([0-9]{2})\.([0-9]{3})\] (.+)',line)
    if not match:
        return None
    hour,minute,second,millisecond=map(int,match.groups()[:4])
    if hour>23 or minute>59 or second>59:
        return None
    body=match.group(5);kind=_MARKERS.get(body)
    if kind is None:
        kind=next((code for pattern,code in _DYNAMIC_MARKERS if pattern.fullmatch(body)),None)
    return None if kind is None else {'wall_ms':((hour*60+minute)*60+second)*1000+millisecond,'kind':kind}


def _summary():
    return dict(count=0,total_ns=0,max_ns=0,first_ns=0,last_ns=0)


def _add(value,start,end):
    if not (_ns(start) and _ns(end) and end>=start):
        return
    value['count']=min(MAX_NS,value['count']+1)
    value['total_ns']=min(MAX_NS,value['total_ns']+end-start)
    value['max_ns']=max(value['max_ns'],end-start)
    value['first_ns']=start if value['count']==1 else min(value['first_ns'],start)
    value['last_ns']=max(value['last_ns'],end)


class DiagnosticCollector114:
    def __init__(self,base,*,clock=time.monotonic_ns):
        self.base=Path(base);self.clock=clock;self.invocation_id=uuid.uuid4().hex
        self.started=clock();self.runs={};self.dropped=0;self.markers=[];self.marker_dropped=0
        self.setup={};self.errors=set();self.observed=set()

    def row(self,run_id):
        if not _id(run_id):
            return None
        if run_id not in self.runs:
            if len(self.runs)>=MAX_RUNS:
                del self.runs[next(iter(self.runs))];self.dropped+=1
            self.runs[run_id]=dict(run_id=run_id,rpc={},phases={},native=None,readonly_attempts=0,readonly_errors=[])
        return self.runs[run_id]

    def phase(self,name,run_id,start,end):
        if not (_ns(start) and _ns(end) and end>=start):
            self.errors.add('clock');return
        if name not in PHASES:
            return
        row=self.row(run_id)
        if row is not None:
            _add(row['phases'].setdefault(name,_summary()),start,end)

    def rpc(self,method,params,result=None,error=None,failure=None,start=0,end=0):
        mode=params.get('mode') if type(params) is dict else None
        bins={'prepare':'setup','trial_support':'setup','status':'status','manifest':'manifest',
            'record':'records','batch':'images','chunk':'images','published':'published'}
        name=('start' if method=='necro_native_start' else 'cancel' if method=='necro_native_cancel'
            else 'diagnostic' if method in ('recent_logs','necro_native_status') else bins.get(mode))
        if name not in RPC_BINS:
            return
        row=self.row(params.get('run_id')) if name!='setup' else None
        target=row['rpc'] if row else self.setup
        value=target.setdefault(name,dict(_summary(),parts={key:0 for key in PARTS},request_bytes=0,
            encrypted_response_bytes=0,missing_timings=0,errors={},stages={}))
        _add(value,start,end)
        timings=getattr(result,'timings',None)
        if type(failure) is dict:
            timings=failure.get('host_timings')
            stage=failure.get('stage');stage=stage if stage in STAGES else 'unknown'
            value['stages'][stage]=value['stages'].get(stage,0)+1
        if error is not None:
            code=getattr(error,'code',None);code=code if code in RPC_ERRORS else 'other'
            if getattr(error,'error_shape_valid',False) is True:
                code={-32094:'pending',-32096:'storage',-32095:'not_admitted'}.get(getattr(error,'rpc_code',None),code)
            value['errors'][code]=value['errors'].get(code,0)+1
        if type(timings) is dict and all(_ns(timings.get(key)) for key in TIMES) and all(
                timings[TIMES[i]]<=timings[TIMES[i+1]] for i in range(5)):
            for index,key in enumerate(PARTS):
                value['parts'][key]=min(MAX_NS,value['parts'][key]+timings[TIMES[index+1]]-timings[TIMES[index]])
            for key in ('request_bytes','encrypted_response_bytes'):
                if _ns(timings.get(key)):value[key]=min(MAX_NS,value[key]+timings[key])
        else:value['missing_timings']+=1

    def _native(self,result,run_id):
        if type(result) is not dict or result.get('run_id')!=run_id or type(result.get('report')) is not dict:
            raise ValueError('shape')
        report=result['report'];clock=report.get('clock_id')
        if not _id(clock):raise ValueError('shape')
        keys=('device_now_ns','last_capture_id','live_completed_prefix','walk_started_ns','phase','beat_period_ns')
        if not all(_ns(report.get(key)) for key in keys):raise ValueError('shape')
        output={key:report[key] for key in keys};output['clock_id']=clock
        samples=report.get('captures')
        if type(samples) is not list or len(samples)>256:raise ValueError('shape')
        summary={key:0 for key in ('count','capture_total_ns','capture_max_ns','decode_total_ns','analysis_total_ns','observe_total_ns')}
        pairs=(('start_ns','end_ns','capture_total_ns'),('end_ns','decode_end_ns','decode_total_ns'),
            ('analysis_start_ns','analysis_end_ns','analysis_total_ns'),('observe_start_ns','observe_end_ns','observe_total_ns'))
        for sample in samples:
            if type(sample) is not dict:continue
            if all(_ns(sample.get(a)) and _ns(sample.get(b)) and sample[b]>=sample[a] for a,b,_ in pairs):
                summary['count']+=1
                for a,b,key in pairs:summary[key]=min(MAX_NS,summary[key]+sample[b]-sample[a])
                summary['capture_max_ns']=max(summary['capture_max_ns'],sample['end_ns']-sample['start_ns'])
        output['captures']=summary
        return output

    def terminal(self,client,run_id,status):
        if run_id in self.observed or not _id(run_id) or type(status) is not dict or not (
                status.get('terminal') is True and status.get('workers_drained') is True
                and type(status.get('input_state')) is int and status['input_state'] in (0,3,4)
                and status.get('native_inflight') is False):
            return
        self.observed.add(run_id);row=self.row(run_id);began=self.clock();deadline=began+2_000_000_000
        sentinel=object();saved={key:getattr(client,key,sentinel) for key in ('last_failure','_rpc_timings','_rpc_stage')}
        transport=getattr(client,'transport',None);saved_transport=getattr(transport,'last_diagnostic',sentinel)
        try:
            for method,params in (('necro_native_status',dict(run_id=run_id,keepalive=False)),('recent_logs',dict(max_elements=500))):
                now=self.clock()
                if now>=deadline:row['readonly_errors'].append('budget');break
                row['readonly_attempts']+=1
                try:
                    reply=client.call(method,params,timeout=min(2.0,(deadline-now)/1e9))
                    self.rpc(method,params,reply,start=now,end=self.clock())
                    result=reply.result if hasattr(reply,'result') else reply
                    if method=='necro_native_status':row['native']=self._native(result,run_id)
                    else:
                        if (type(result) is not dict or set(result)!={'lines','count','total','hint'}
                            or type(result['lines']) is not list or len(result['lines'])>500
                            or type(result['count']) is not int or result['count']!=len(result['lines'])
                            or type(result['total']) is not int or not 0<=result['count']<=result['total']<=MAX_NS
                            or type(result['hint']) is not str or len(result['hint'])>8192):
                            raise ValueError('shape')
                        for line in result['lines']:
                            item=marker(line)
                            if item is not None and item not in self.markers:
                                self.markers.append(item)
                                if len(self.markers)>MAX_MARKERS:self.markers.pop(0);self.marker_dropped+=1
                except Exception as failure:
                    row['readonly_errors'].append('shape' if isinstance(failure,ValueError) else 'rpc')
        finally:
            for key,value in saved.items():
                if value is sentinel:
                    if hasattr(client,key):delattr(client,key)
                else:setattr(client,key,value)
            if transport is not None:
                if saved_transport is sentinel:
                    if hasattr(transport,'last_diagnostic'):delattr(transport,'last_diagnostic')
                else:transport.last_diagnostic=saved_transport
            self.phase('diagnostic_rpc',run_id,began,self.clock())

    def seal(self,ledger):
        try:
            value=dict(schema=SCHEMA,invocation_id=self.invocation_id,campaign_id=ledger['campaign_id'],
                revision=ledger['revision'],campaign_index_sha256=hashlib.sha256(_raw(ledger)).hexdigest(),
                host_clock='time.monotonic_ns',started_host_ns=self.started,diagnostics_sealed_at_ns=self.clock(),
                campaign_bundle_tail_unmeasured=True,runs=list(self.runs.values()),runs_dropped=self.dropped,
                setup_rpc=self.setup,markers=self.markers,markers_dropped=self.marker_dropped,errors=sorted(self.errors))
            while len(_raw(value))>MAX_BYTES and value['runs']:
                value['runs'].pop(0);value['runs_dropped']+=1
            if len(_raw(value))>MAX_BYTES:raise ValueError('size')
            return _raw(value)
        except Exception:
            return unavailable(ledger)


def unavailable(ledger):
    return _raw(dict(schema=SCHEMA,status='unavailable',campaign_id=ledger['campaign_id'],
        revision=ledger['revision'],campaign_index_sha256=hashlib.sha256(_raw(ledger)).hexdigest()))


def valid_sealed(raw,ledger):
    """Local artifacts are data, not authority. Reject unknown/free-form fields."""
    try:
        if type(raw) is not bytes or len(raw)>MAX_BYTES:return False
        value=json.loads(raw)
        if _raw(value)!=raw:return False
        identity=dict(schema=SCHEMA,campaign_id=ledger['campaign_id'],revision=ledger['revision'],
            campaign_index_sha256=hashlib.sha256(_raw(ledger)).hexdigest())
        if any(value.get(key)!=item for key,item in identity.items()):return False
        if value.get('status')=='unavailable':return set(value)==set(identity)|{'status'}
        keys=set(identity)|{'invocation_id','host_clock','started_host_ns','diagnostics_sealed_at_ns',
            'campaign_bundle_tail_unmeasured','runs','runs_dropped','setup_rpc','markers','markers_dropped','errors'}
        if set(value)!=keys or not _id(value['invocation_id']) or value['host_clock']!='time.monotonic_ns' or value['campaign_bundle_tail_unmeasured'] is not True:return False
        if not all(_ns(value[key]) for key in ('started_host_ns','diagnostics_sealed_at_ns','runs_dropped','markers_dropped')):return False
        if type(value['errors']) is not list or not set(value['errors'])<=DIAG_ERRORS:return False
        if type(value['runs']) is not list or len(value['runs'])>MAX_RUNS or type(value['markers']) is not list or len(value['markers'])>MAX_MARKERS:return False
        for item in value['markers']:
            if type(item) is not dict or set(item)!={'wall_ms','kind'} or not _ns(item['wall_ms']) or item['wall_ms']>=86400000 or item['kind'] not in MARKER_KINDS:return False
        def numeric_tree(tree,allowed):
            return type(tree) is dict and set(tree)<=set(allowed) and all(_ns(v) for v in tree.values())
        def stats(tree):
            if type(tree) is not dict or not set(tree)<=RPC_BINS:return False
            for item in tree.values():
                if type(item) is not dict or set(item)!={'count','total_ns','max_ns','first_ns','last_ns','parts','request_bytes','encrypted_response_bytes','missing_timings','errors','stages'}:return False
                if not numeric_tree({k:v for k,v in item.items() if k not in ('parts','errors','stages')},set(item)):return False
                if not numeric_tree(item['parts'],PARTS) or not numeric_tree(item['errors'],RPC_ERRORS) or not numeric_tree(item['stages'],STAGES):return False
            return True
        if not stats(value['setup_rpc']):return False
        seen=set()
        for row in value['runs']:
            if type(row) is not dict or set(row)!={'run_id','rpc','phases','native','readonly_attempts','readonly_errors'} or not _id(row['run_id']) or row['run_id'] in seen:return False
            seen.add(row['run_id'])
            if not stats(row['rpc']) or type(row['phases']) is not dict or not set(row['phases'])<=PHASES:return False
            if any(not numeric_tree(item,set(_summary())) or set(item)!=set(_summary()) for item in row['phases'].values()):return False
            if not _ns(row['readonly_attempts']) or row['readonly_attempts']>2 or type(row['readonly_errors']) is not list or len(row['readonly_errors'])>2 or not set(row['readonly_errors'])<=DIAG_ERRORS:return False
            native=row['native']
            if native is not None:
                nk={'device_now_ns','last_capture_id','live_completed_prefix','walk_started_ns','phase','beat_period_ns','clock_id','captures'}
                if type(native) is not dict or set(native)!=nk or not _id(native['clock_id']) or not numeric_tree({k:v for k,v in native.items() if k not in ('clock_id','captures')},nk):return False
                if not numeric_tree(native['captures'],{'count','capture_total_ns','capture_max_ns','decode_total_ns','analysis_total_ns','observe_total_ns'}):return False
        return True
    except (TypeError,ValueError,KeyError,AttributeError):
        return False
