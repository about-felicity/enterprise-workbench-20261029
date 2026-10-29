import json,sys,sqlite3
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation.runtime import SharedBudget as Budget
from creation.runtime import read
root=Path('/opt/monitor/geo-content/runtime/runs/creation-1792575159-0a8f9221');out=[];budget=Budget(root)
for p in (root/'queue').glob('*/ticket.json'):
 j=read(p)
 if j.get('meta',{}).get('compiler_pilot_release')!='practical-v1':continue
 run=root/'api/runs'/j.get('execution',{}).get('run_id','missing');raw=read(run/'call/answer.json');a=read(run/'call/response.json')
 if j['stage']=='writer':
  doc=a.get('document',{});out.append({'category':j['meta']['category'],'stage':'writer','state':j['state'],'run':str(run),'raw_finish':raw.get('finish_reason'),'usage':raw.get('usage'),'sections':len(doc.get('sections',[])),'intro':len(doc.get('introduction',[])),'conclusion':len(doc.get('conclusion',[])),'remaining':budget.remaining(j['meta'],'writer')})
 if j['stage']=='review':
  spans=read(run/'claim_spans.json');out.append({'category':j['meta']['category'],'stage':'review','state':j['state'],'run':str(run),'C34':spans.get('C34'),'C60':spans.get('C60'),'remaining':budget.remaining(j['meta'],'review'),'failures':a.get('failures')})
budget.close();print(json.dumps(out,ensure_ascii=False))
