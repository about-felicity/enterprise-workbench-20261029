"""Durable backoff for proven read-only/preflight failures, never paid sends."""
import time
from datetime import datetime,timedelta
from geo_source_cards.runtime import atomic_json,process_lock
from geo_source_cards.pipeline_control import state,event,BEIJING
from .runtime import read

def safe_original(root):
    active=read(root/'api/active.json')
    if not active:return True
    run_id=active.get('run_id','')
    if not run_id or '/' in run_id or '\\' in run_id:return False
    run=root/'api/runs'/run_id
    for p in run.rglob('api_state.json'):
        if read(p).get('state') in {'REQUESTING','REQUEST_UNKNOWN'} and not (p.parent/'response.json').is_file():return False
    return True

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
