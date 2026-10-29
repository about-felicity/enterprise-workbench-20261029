"""Replay saved, proven card captures; never opens a browser or changes tasks."""
from datetime import datetime
from zoneinfo import ZoneInfo
import json
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, '/opt/monitor/geo-capture')
from capture_bridge import Delivery, envelope, full_result, read_rows, verify_receipt

BASE = Path('/opt/monitor/geo-capture')
ROOT = BASE / 'maintenance/20261016-daily-observations'
ROOT.mkdir(exist_ok=True)
DAY = '2026-10-16'

def query(sql):
    return json.loads(subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',
        "select coalesce(json_agg(t),'[]') from ("+sql+")t"],text=True))

def counts():
    return query("select question,payload->>'capture_mode' mode,count(*) observations from monitor_runs where model_id='wenxin' and day='2026-10-16' and status='success' group by 1,2 order by 1,2")

before = ROOT / 'before.json'
if not before.exists():
    before.write_text(json.dumps(counts(), ensure_ascii=False, indent=2))
lanes = []
for configpath in sorted((BASE/'panel/jobs').glob('geo-panel-baidu-ai-*.json')):
    config = json.loads(configpath.read_text())
    original = BASE/'batches'/config['batch']
    rows = []
    for row in read_rows(original/'collector/tasks.sqlite',config['batch']):
        if row['state'] != 'completed':continue
        value = json.loads(row['result'])
        captured = datetime.fromisoformat(value['captured_at'].replace('Z','+00:00'))
        if captured.tzinfo is None:captured=captured.replace(tzinfo=ZoneInfo('Asia/Shanghai'))
        if captured.astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat()!=DAY:continue
        if full_result(value):rows.append(row)
    if not rows:continue
    lane = ROOT/config['batch']
    lanes.append((Delivery(lane,config,Path('/opt/monitor')),rows,config))

for attempt in range(180):
    reports=[]
    for delivery,rows,config in lanes:
        result=delivery.sync(rows)
        reports.append({'batch':config['batch'],**result})
    complete=all(r['captured']==r['processed'] and not r['errors'] for r in reports)
    (ROOT/'progress.json').write_text(json.dumps({'at':time.time(),'complete':complete,'lanes':reports},ensure_ascii=False,indent=2))
    if complete:break
    time.sleep(3)
else:raise RuntimeError('Delivery incomplete; original saved captures remain intact')

ids=[]
for delivery,rows,config in lanes:
    for row in rows:
        item=envelope(row,json.loads(row['result']),config)
        verify_receipt(json.loads((delivery.root/'receipts'/(item['request_id']+'.json')).read_text()),item)
        ids.append(item['request_id'])
stored=query("select e.request_id,e.record,r.day,r.payload from monitor_ingest_events e join monitor_runs r on r.model_id=e.model_id and r.run_id=e.run_id where e.model_id='wenxin' and e.request_id in ("+','.join("'"+rid+"'" for rid in ids)+")")
indexed={v['request_id']:v for v in stored}
for delivery,rows,config in lanes:
    for row in rows:
        item=envelope(row,json.loads(row['result']),config)
        actual=indexed[item['request_id']]
        assert actual['day']==DAY
        for field in ('web_body','sources','capture_result','capture_task_id','batch_id','round'):
            assert actual['record'][field]==item['record'][field],field
report={'at':time.time(),'complete':True,'full_observations_verified':len(ids),'after':counts(),'lanes':reports}
(ROOT/'verified.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
