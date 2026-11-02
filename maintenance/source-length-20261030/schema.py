import json,sqlite3,collections
from pathlib import Path
p=Path('/opt/monitor/doubao_source_content.db')
with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as db:
 print('SCHEMA',db.execute('pragma table_info(source_content)').fetchall())
 print('CONTENT_STATUS',db.execute('select status,count(*) from source_content group by status').fetchall())
 print('SAMPLE',db.execute('select url,status,text_length,length(content_text),extraction_quality from source_content where status in (\'ok\',\'fetched\',\'success\') limit 2').fetchall())
files=list(Path('/opt/monitor/geo-capture/batches').glob('*/results.jsonl'));print('FILES',len(files));counts=collections.Counter();dates=collections.Counter();samples=[]
for p in files:
 for line in p.open():
  if not line.strip():continue
  r=json.loads(line)
  if r.get('model') not in ['baidu_ai','wenxin_card']:continue
  counts[r['model']]+=1;dates[str(r.get('captured_at'))[:10]]+=1
  if len(samples)<2:samples.append({k:r.get(k) for k in ['model','captured_at','task_id','batch','duplicate_of','round','body_capture_complete','source_capture_complete']})
print('COUNTS',dict(counts),'DATES',sorted(dates.items()),'SAMPLES',samples)
