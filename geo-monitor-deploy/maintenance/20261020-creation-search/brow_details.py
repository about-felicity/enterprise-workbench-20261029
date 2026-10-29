import json,sys
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
t=runtime.read(Path('/opt/monitor/geo-capture/maintenance/20261020-brow-daily/task.json'))
out=[]
for f in (runtime.BASE/'runs').glob('*/job.json'):
    j=runtime.read(f)
    if j.get('studio_plan_id')!=t['plan_id']:continue
    r=f.parent;d=r/'days'/j['date'];sources=runtime.read(d/'media_articles.json',[])
    sources={s['url']:s for s in sources} if isinstance(sources,list) else {}
    allocation=runtime.read(d/'article_allocation.json');chosen=[]
    for category,urls in allocation.get('selected',{}).items():
        for url in urls:
            a=sources.get(url,{}).get('article',{})
            chosen.append({'category':category,'title':a.get('title'),'chars':len(a.get('text','')),'preview':a.get('text','')[:150]})
    failures=[]
    for p in (r/'queue').glob('*/ticket.json'):
        ticket=runtime.read(p)
        if ticket.get('state')!='needs_attention':continue
        loc=r/ticket['location']
        failures.append({'id':ticket['id'],'stage':ticket['stage'],'error':ticket.get('error'),'meta':ticket.get('meta'),'location':ticket['location'],'result':runtime.read(loc/'result.json')})
    active=runtime.read(r/'api/active.json');call={}
    if active.get('run_id'):
        path=r/'api/runs'/active['run_id']/'call'
        call={'files':[p.name for p in path.glob('*')],'state':runtime.read(path/'api_state.json').get('state')}
    calls=[]
    for p in (r/'api/runs').glob('*/call/api_state.json'):
        s=runtime.read(p)
        calls.append({'run':p.parents[1].name,'keys':list(s),'state':s.get('state'),'failure_code':s.get('failure_code'),'http_status':s.get('http_status'),'files':[f.name for f in p.parent.iterdir()]})
    out.append({'id':j['job_id'],'chosen':chosen,'failures':failures,'active':active,'call':call,'calls':calls})
Path('/tmp/brow-details.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps([{'id':r['id'],'failures':r['failures'],'active':r['active']} for r in out] if '--failures' in sys.argv else out,ensure_ascii=False))
