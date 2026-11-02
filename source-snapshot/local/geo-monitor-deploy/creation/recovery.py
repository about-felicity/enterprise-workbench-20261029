"""Durable backoff for proven read-only/preflight failures, never paid sends."""
import time
from datetime import datetime,timedelta
from geo_source_cards.runtime import atomic_json,process_lock
from geo_source_cards.pipeline_control import state,event,BEIJING
from .runtime import read

def safe_original(root):
    active=read(root/'api/active.json')
    if not active or active.get('state')=='SUBMITTED':return True
    run_id=active.get('run_id','')
    if not run_id or '/' in run_id or '\\' in run_id:return False
    run=root/'api/runs'/run_id
    for p in run.rglob('api_state.json'):
        value=read(p)
        uncertain=value.get('state') in {'REQUESTING','REQUEST_UNKNOWN'} or value.get('state')=='HTTP_REJECTED' and value.get('http_status',0)>=500
        if uncertain and not (p.parent/'response.json').is_file():return False
    return True


def http_failure(root):
    """Describe only a finished HTTP gateway failure, never a live/unknown send."""
    active=read(root/'api/active.json')
    if active.get('state')!='REQUESTING':return {}
    run_id=active.get('run_id','')
    if not run_id or '/' in run_id or '\\' in run_id:return {}
    missing=[]
    for p in (root/'api/runs'/run_id).rglob('api_state.json'):
        if not (p.parent/'response.json').is_file():missing.append((p,read(p)))
    if not missing or any(v.get('state')!='HTTP_REJECTED' or v.get('http_status') not in {502,503,504} for _,v in missing):return {}
    ticket=read(root/'queue'/active.get('ticket','missing')/'ticket.json')
    codes=sorted({v['http_status'] for _,v in missing})
    meta=ticket.get('meta',{});attempts=meta.get('operator_http_retries',0) if meta.get('operator_http_retry_stage',ticket.get('stage'))==ticket.get('stage') else 0
    return {'http_status':codes,'retry_available':attempts<1,
            'run_id':run_id,'ticket':active['ticket'],
            'calls':[{'path':p.relative_to(root).as_posix(),'reservation':v.get('reservation')} for p,v in missing]}


def recover_http_failure(root):
    """One explicit operator replacement; preserve uncertain billing and inputs."""
    from . import runtime
    from geo_source_cards.daily_editorial import publish_ticket
    with process_lock(root/'api/worker.lock',blocking=False),process_lock(root/'coordinator.lock',blocking=False):
        failure=http_failure(root)
        if not failure:return None
        if not state(root).get('paused'):raise ValueError('该执行尚未暂停，请等待当前请求结束后再核对')
        if not failure['retry_available']:raise ValueError('这个阶段已补做过一次，仍未收到答复；已停止继续付费重试，请检查API连接')
        active=read(root/'api/active.json');path=root/'queue'/active['ticket']/'ticket.json';ticket=read(path)
        record=root/'api/http-recovery'/(active['run_id']+'.json')
        if not record.exists():
            atomic_json(record,{'state':'prepared','at':time.time(),'original_active':active,'original_ticket':ticket,
                               'failure':failure,'original_cost_reservations_preserved':True,
                               'authorization':'REDACTED_CONFIGURE_LOCALLY'})
        meta={**ticket['meta'],'revision':ticket['meta'].get('revision',0)+1,'replaces':ticket['id'],
              'operator_http_retries':1,'operator_http_retry_stage':ticket['stage']}
        replacement=publish_ticket(root,ticket['stage'],root/ticket['location'],list(ticket['inputs']),ticket['outputs'],meta)
        atomic_json(path,{**ticket,'state':'revision_requested','replaced_by':replacement,
                          'error':'HTTP网关异常，无可用答复；原请求与费用预留已保留，用户核对后补做此阶段'})
        atomic_json(root/'api/active.json',{**active,'state':'SUBMITTED'})
        atomic_json(record,{**read(record),'state':'replaced','replacement':replacement,'finished_at':time.time()})
        event(root,'recovery','HTTP故障阶段已安排一次补做；保留原费用预留，预算不变',replacement=replacement)
        return replacement

def defer(root,error,now=None):
    now=time.time() if now is None else now
    readonly=(error.code=='balance_unavailable' or error.code=='balance_http_429' or error.code.startswith('balance_http_5'))
    budget=error.code=='budget_exceeded'
    if error.uncertain or not (readonly or budget) or not safe_original(root):return False
    with process_lock(root/'control.lock',blocking=True):
        control=state(root)
        if control.get('paused') and not (budget and control.get('reason') in {'budget','budget_exceeded'}):return False
        path=root/'known_preflight_retry.json';old=read(path);attempt=old.get('attempts',0)+1
        if budget:
            tomorrow=(datetime.fromtimestamp(now,BEIJING)+timedelta(days=1)).replace(hour=0,minute=0,second=5,microsecond=0)
            next_at=tomorrow.timestamp()
        else:next_at=now+min(900,30*2**min(attempt-1,5))
        atomic_json(path,{'state':'waiting','code':error.code,'attempts':attempt,'next_at':next_at,
                         'control_revision':control.get('revision',0),'budget_pause':budget and control.get('paused',False),
                         'request_retry_forbidden':True,'original_run_id':read(root/'api/active.json').get('run_id')})
    event(root,'recovery','已知预检故障退避；保留原执行，未重发付费请求',code=error.code,next_at=next_at)
    return True

def ready(root,now=None):
    now=time.time() if now is None else now
    record=read(root/'known_preflight_retry.json')
    if record.get('state')!='waiting':return True
    if now<record['next_at']:return False
    if not safe_original(root):return False
    if record.get('budget_pause'):
        with process_lock(root/'control.lock',blocking=True):
            control=state(root)
            if (control.get('revision',0)!=record['control_revision'] or not control.get('paused')
                or control.get('reason') not in {'budget','budget_exceeded'}):return False
            atomic_json(root/'control.json',{'paused':False,'revision':control.get('revision',0)+1,
                                           'resumed_epoch':now,'automatic_reason':'next_day_budget_preflight'})
    return True

def succeeded(root):
    path=root/'known_preflight_retry.json';record=read(path)
    if record.get('state')=='waiting':atomic_json(path,{**record,'state':'recovered','recovered_at':time.time()})
