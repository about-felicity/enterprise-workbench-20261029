import json,collections
from pathlib import Path
for p in [Path('/opt/monitor/deepseek_monitor/deepseek_results.jsonl'),*Path('/opt/monitor/geo-capture/batches').glob('*/results.jsonl')]:
 if not p.exists():continue
 counts=collections.Counter();dates=collections.Counter();sample=None
 for line in p.open():
  if not line.strip():continue
  try:r=json.loads(line)
  except ValueError:continue
  m=r.get('model') or r.get('model_id')
  if p.name=='deepseek_results.jsonl' or 'deepseek' in str(m):
   counts[str(m)]+=1;dates[str(r.get('captured_at') or r.get('finished_at') or r.get('day'))[:10]]+=1
   if sample is None:sample={k:r.get(k) for k in r if k not in ['body','page_body','answer','answer_text','raw_text','response','sources','products']};sample['source_sample']=(r.get('sources') or [])[:1]
 if counts:print('FILE',str(p),'COUNTS',dict(counts),'DATES',sorted(dates.items()),'SAMPLE',json.dumps(sample,ensure_ascii=False)[:2000])
