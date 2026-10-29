import json,sys,time,sqlite3
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
r=runtime.job_root('creation-1792556219-bbc55e13');articles=[]
for a in runtime.articles(r):
 p=r/'approved'/a['id'];d=runtime.read(p/'product_detail_review.json');articles.append({'id':a['id'],'title':a['title'],'product_hanzi':d.get('actual_hanzi'),'facts':len(d.get('used_fact_ids',[])),'reports':len(d.get('used_report_ids',[]))})
db=sqlite3.connect('file:'+str(runtime.SHARED/'api/costs.sqlite')+'?mode=ro',uri=True)
costs=db.execute("select c.category,c.article,count(*),round(sum(coalesce(c.charged,c.reserved)),5) from costs c join studio_cost_scopes s on c.id=s.id where s.job=? group by c.category,c.article",(r.name,)).fetchall();db.close()
tickets=[runtime.read(p) for p in (r/'queue').glob('*/ticket.json')];active=runtime.read(r/'api/active.json');day=runtime.read(r/'days/2026-10-21/day.json')
out={'at':time.time(),'count':len(articles),'articles':articles,'costs':costs,'active':{k:active.get(k) for k in ['state','stage','started_epoch']},'control':runtime.read(r/'control.json'),'failures':[{'id':v['id'],'stage':v['stage'],'meta':v['meta'],'error':v.get('error')} for v in tickets if v['state']=='needs_attention'],'pending':sum(v['state'] in ['pending','claimed'] for v in tickets),'day_state':day.get('status')}
Path('/opt/monitor/geo-capture/maintenance/20261021-product-richness/compact-progress.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
