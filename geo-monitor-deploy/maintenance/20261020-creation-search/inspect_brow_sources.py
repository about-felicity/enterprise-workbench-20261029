import hashlib,json
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit
task=json.loads(Path('/opt/monitor/geo-capture/maintenance/20261020-brow-daily/task.json').read_text());root=Path(task['root'])/'days'/task['start_date']
out={}
for model in ('baidu_ai','wenxin_card'):
 rows=[];urls=set();domains=Counter()
 for line in (root/model/'results.jsonl').read_text().splitlines():
  if not line.strip():continue
  row=json.loads(line);body=row.get('body','');sources=row.get('sources',[])
  for s in sources:
   u=s.get('url','');urls.add(u);domains[urlsplit(u).hostname or 'unknown']+=1
  rows.append({'question':row.get('question'),'body_length':len(body),'body_complete':row.get('body_capture_complete'),'source_complete':row.get('source_capture_complete'),'sources':len(sources),'body_sha256':hashlib.sha256(body.encode()).hexdigest()})
 out[model]={'observations':rows,'unique_source_urls':len(urls),'domains':dict(domains)}
Path('/tmp/brow-source-audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False))
