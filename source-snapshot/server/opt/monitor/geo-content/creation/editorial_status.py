"""Expose terminal editorial reasons; never clear or resume their jobs."""
from pathlib import Path
from .runtime import read


def execution_health(root,tickets,day):
    """Project current state; a historical requesting log is not an active send."""
    root=Path(root);historical=read(root/'api/health.json');active=read(root/'api/active.json')
    status=active.get('state')
    if status=='REQUESTING':
        calls=[read(p) for p in (root/'api/runs'/active['run_id']).rglob('api_state.json')]
        status='request_unknown' if any(c.get('state')=='REQUEST_UNKNOWN' or c.get('state')=='HTTP_REJECTED' and c.get('http_status',0)>=500 for c in calls) else 'requesting'
    elif status=='RESPONDED':status='response_saved'
    elif status=='AUTHORIZING':status='authorizing'
    else:
        pending=any(t.get('state') in {'pending','claimed'} for t in tickets)
        if day.get('status') in {'complete','complete_with_failures'}:status=day['status']
        elif pending:status='queued'
        elif any(t.get('waiting_skeleton') for t in tickets):status='needs_attention'
        elif any(t.get('state')=='needs_attention' for t in tickets):status='completed_with_failures'
        else:status='idle'
    return {'status':status,'state':status.upper(),'active_execution':bool(active and active.get('state') in {'REQUESTING','RESPONDED','AUTHORIZING'}),
        'historical_observation':historical,'historical_status_is_not_current':historical.get('status')!=status}


def blocks(root,tickets):
    root=Path(root);latest={}
    for ticket in tickets:
        key=tuple(ticket.get('meta',{}).get(k) for k in ('date','category','number'))
        if ticket.get('created_at','')>latest.get(key,{}).get('created_at',''):latest[key]=ticket
    results=[]
    for key,ticket in latest.items():
        if ticket.get('state')!='needs_attention':continue
        row={'date':key[0],'category':key[1],'number':key[2],'ticket':ticket['id']}
        if ticket.get('meta',{}).get('workflow')=='rewrite-v2':
            results.append({**row,'status':'WAITING_SKELETON_APPROVAL' if ticket.get('waiting_skeleton') else 'REWRITE_V2_STOPPED',
                            'reasons':[ticket.get('error','等待人工处理')]})
            continue
        run=root/'api/runs'/ticket.get('execution',{}).get('run_id','missing')
        rejected=read(run/'compilation_rejection.json')
        location=root/ticket['location'];writer=location.parent/'writer' if ticket.get('stage')=='review' else location
        routing=read(writer/'repair_route.json')
        if routing:
            import hashlib
            path=writer/'draft.md'
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=routing.get('draft_sha256'):routing={}
        if rejected:results.append({**row,'status':rejected['status'],'reasons':rejected.get('reasons',[])})
        elif routing.get('action') in {'REPLAN','NEED_MORE_EVIDENCE','REVIEW_DISPUTED','REPAIR_EXHAUSTED'}:
            results.append({**row,'status':routing['action'],'reasons':routing.get('unresolved_review',[]) or [i['reason'] for i in routing.get('issues',[])]})
        elif read(root/'queue'/ticket['id']/'auto_repair_blocked.json').get('status')=='REPAIR_EXHAUSTED':
            results.append({**row,'status':'REPAIR_EXHAUSTED','reasons':['两轮修订后仍未通过，已停止自动重写']})
    return results
