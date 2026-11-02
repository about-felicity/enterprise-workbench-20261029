import collections,json,sqlite3,time
from pathlib import Path
from urllib.parse import urlsplit
base=Path('/opt/monitor/geo-content/runtime/runs')
with sqlite3.connect('file:/opt/monitor/doubao_source_content.db?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 columns=[r[1] for r in db.execute('pragma table_info(source_content)')]
 print('COLUMNS',columns)
 for p in base.glob('*/job.json'):
  job=json.loads(p.read_text());root=p.parent
  if job.get('date')!='2026-10-31' or job.get('preparation')!='insufficient':continue
  paths=sorted(root.glob('private_source_analysis*/articles.jsonl'),key=lambda p:p.stat().st_mtime,reverse=True)
  if not paths:continue
  rows=[json.loads(line) for line in paths[0].read_text().split('\n') if line.strip()]
  sources={s['url']:s for row in rows for s in row.get('sources',[])}
  counts=collections.Counter();cached=[]
  for url,s in sources.items():
   article=s.get('article',{})
   counts[(urlsplit(url).hostname,article.get('status'))]+=1
   row=db.execute('select * from source_content where url=?',(url,)).fetchone()
   if row and row['status']=='ok':cached.append({k:row[k] for k in columns if k not in ['content_text','text','html','payload','content','raw_html']})
  print('SOURCES',json.dumps({'job':root.name,'question':job['question'],'domains':[{'host':k[0],'status':k[1],'count':v} for k,v in counts.items()],'global_cached':cached},ensure_ascii=False))
