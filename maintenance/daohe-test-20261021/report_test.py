"""Produce a factual per-sample report, keeping generation separate from acceptance."""
import sys,json,time,sqlite3,hashlib,re
from pathlib import Path
from collections import Counter
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,studio
M=Path('/opt/monitor/geo-capture/maintenance/20261021-daohe-test');s=runtime.read(M/'task.json');task=runtime.read(studio.day_path(s['plan_id'],s['date']));articles=[];jobs=[]
for jid in task['jobs'].values():
 root=runtime.job_root(jid);tickets=[runtime.read(p) for p in (root/'queue').glob('*/ticket.json')]
 approved={a['id']:a for a in runtime.articles(root)}
 jobs.append({'id':jid,'control':runtime.read(root/'control.json'),'pending':sum(t['state'] in {'pending','claimed'} for t in tickets)})
 for folder in sorted((root/'days'/s['date']/'jobs').glob('*/*')):
  number=int(folder.name);category=folder.parent.name;relative=s['date']+'/'+category+'/'+folder.name
  related=[t for t in tickets if t['meta'].get('category')==category and t['meta'].get('number')==number]
  failures=sorted([t for t in related if t.get('error')],key=lambda t:t.get('created_at',''),reverse=True)
  errors=list(dict.fromkeys(t['error'] for t in failures));writer=folder/'writer';draft=writer/'draft.md';text=draft.read_text('utf-8-sig') if draft.exists() else ''
  knowledge=runtime.read(writer/'knowledge.json');blueprint=knowledge.get('reference_design') or runtime.read(folder/'research/research_input.json').get('reference_design',{})
  a=approved.get(relative);ready=a is not None and a['quality_status']=='ready'
  articles.append({'job':jid,'category':category,'number':number,'id':relative,'status':'ready' if ready else 'draft_needs_revision' if text else 'no_valid_draft',
   'title':text.splitlines()[0].lstrip('# ') if text else blueprint.get('primary_title',''),'draft_sha256':hashlib.sha256(draft.read_bytes()).hexdigest() if text else '',
   'body_hanzi':len(re.findall('[\u4e00-\u9fff]',text)),'primary_url':blueprint.get('primary_url'),'primary_title':blueprint.get('primary_title'),
   'quality_issues':a.get('quality_issues',[]) if a else [],'current_rejections':[{k:t.get(k) for k in ('id','stage','state','error')} for t in related if t['state']=='needs_attention'],
   'quality_failure_history':[e for e in errors if 'budget_exceeded' not in e][:4],'latest_error':errors[0] if errors else None})
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 fees=db.execute('select coalesce(sum(c.charged),0),coalesce(sum(case when c.charged is null then c.reserved else 0 end),0) from costs c join studio_cost_scopes s on c.id=s.id where s.scope=?',(s['plan_id'],)).fetchone()
 for a in articles:
  a['charged']=db.execute('select coalesce(sum(c.charged),0) from costs c join studio_cost_scopes s on c.id=s.id where s.job=? and c.category=? and c.article=?',(a['job'],a['category'],str(a['number']))).fetchone()[0]
report={'at':time.time(),'plan':s['plan_id'],'target':14,'requested_genres':{'排行类':7,'测评类':7},'allocated':dict(Counter(a['category'] for a in articles)),'samples':len(articles),
 'drafts':sum(a['status']!='no_valid_draft' for a in articles),'ready':sum(a['status']=='ready' for a in articles),'charged':fees[0],'reserved':fees[1],
 'task_cap':5.25,'article_cap':.35,'shared_cap':runtime.pipeline_control.settings(runtime.SHARED)['daily_budget_cny'],'jobs':jobs,'articles':articles}
runtime.atomic_json(M/'test-report.json',report)
print(json.dumps({k:v for k,v in report.items() if k!='articles'},ensure_ascii=False))
