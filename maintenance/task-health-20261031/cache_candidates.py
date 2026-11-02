import datetime,json,sqlite3,sys,time
from pathlib import Path
from zoneinfo import ZoneInfo
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,materials,source_adapter
from creation.owned_sources import ownership
from geo_source_cards.source_scope import anchors,evaluate
from geo_source_cards.article_quality import normalize
with sqlite3.connect('file:/opt/monitor/doubao_source_content.db?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 for p in (runtime.BASE/'runs').glob('*/job.json'):
  job=runtime.read(p);root=p.parent
  if job.get('date')!='2026-10-31' or job.get('preparation')!='insufficient':continue
  sources={s['url']:s for r in materials.read_lines(root/'private_observations.jsonl') for s in r.get('sources',[])}
  terms=anchors([job['question']],runtime.read(root/'product.json'));valid=[]
  for url,s in sources.items():
   row=db.execute('select * from source_content where url=?',(url,)).fetchone()
   try:
    full=source_adapter.article(row,url)
    at=datetime.datetime.strptime(row['fetched_at'],'%Y-%m-%d %H:%M:%S').replace(tzinfo=ZoneInfo('Asia/Shanghai')).timestamp()
    if not 0<=time.time()-at<=7*86400:continue
    candidate={**s,'article':normalize(full)}
    if candidate['article']['status']!='fetched' or ownership(candidate)['owned'] or evaluate(candidate,terms)['status']=='off_topic':continue
   except (ValueError,TypeError):continue
   valid.append({'url':url,'title':full['title'],'age_hours':round((time.time()-at)/3600,1),'chars':len(full['text'])})
  print('CANDIDATES',json.dumps({'job':root.name,'question':job['question'],'count':len(valid),'sources':valid[:3]},ensure_ascii=False),flush=True)
