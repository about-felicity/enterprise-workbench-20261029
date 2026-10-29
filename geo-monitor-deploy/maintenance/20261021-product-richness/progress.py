import json,sys,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import studio,materials,runtime
R=Path('/opt/monitor/geo-capture/maintenance/20261021-product-richness');t=runtime.read(R/'task.json');p=studio.plan(t['plan_id'])
day=runtime.read(studio.day_path(t['plan_id'],t['date']));jobs=[]
for jid in day.get('jobs',{}).values():
 root=runtime.job_root(jid);j=runtime.read(root/'job.json');tickets=[runtime.read(f) for f in (root/'queue').glob('*/ticket.json')];states={}
 for v in tickets:
  key=v.get('stage','')+':'+v.get('state','');states[key]=states.get(key,0)+1
 jobs.append({'job_id':jid,'article_goal':runtime.read(root/'article_goal.json'),'day':runtime.read(root/'days'/t['date']/'day.json'),'worker':runtime.read(root/'geo_worker.json'),'control':runtime.read(root/'control.json'),'active':runtime.read(root/'api/active.json'),'tickets':states,'failures':[{'id':v['id'],'meta':v.get('meta'),'error':v.get('error')} for v in tickets if v.get('state')=='needs_attention'],'approved':[{'id':a['id'],'title':a['title'],'quality_status':a.get('quality_status')} for a in runtime.articles(root)]})
out={'at':time.time(),'plan_id':t['plan_id'],'date':t['date'],'capture':materials.progress(t['date'],store_root=studio.capture_root(t['plan_id'])),'task_state':day.get('status'),'paused':day.get('paused'),'error':day.get('error'),'jobs':jobs}
(R/'progress.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
