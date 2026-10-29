import json,re
from pathlib import Path
root=Path('/opt/monitor/geo-content/runtime/runs/creation-1792556219-bbc55e13/days/2026-10-21');out=[]
for name in ('sources.json','media_articles.json'):
 p=root/name
 if not p.exists():continue
 v=json.loads(p.read_text());v=v.get('sources',v.get('articles',[])) if isinstance(v,dict) else v
 for i,s in enumerate(v):
  a=s.get('article') or {};title=a.get('title') or s.get('title','');body=a.get('text','')
  if re.search(r'涂抹|凝胶|清洗|泥膜',title):out.append({'file':str(p),'index':i,'title':title,'url':s.get('url'),'chars':len(body)})
print(json.dumps(out[:30],ensure_ascii=False))
