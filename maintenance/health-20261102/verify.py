import collections,hashlib,json,sqlite3,subprocess,time,urllib.request
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8804/api/status',timeout=40) as r:d=json.load(r)
print('TIME',datetime.now(ZoneInfo('Asia/Shanghai')).isoformat())
for day in ['2026-11-01','2026-11-02']:
 tasks=[t for t in d['studio']['daily_tasks'] if t['date']==day]
 print('SUMMARY',day,json.dumps({'articles':sum(t['articles'] for t in tasks),'states':dict(collections.Counter(t['status'] for t in tasks)),'tasks':[{k:t.get(k) for k in ['name','status','articles','error','jobs']} for t in tasks]},ensure_ascii=False))
base=Path('/opt/monitor/geo-capture')
for p in base.glob('batches/*20261101*'):
 print('ROOT',str(p),[x.name for x in p.iterdir()])
for folder in ['/home/user/redroid-doubao','/home/user/redroid-yuanbao']:
 p=Path(folder)
 print('NATIVE_ROOT',folder,[str(x) for x in p.glob('*') if x.is_dir()])
print('SERVICES',subprocess.run(['systemctl','list-units','--all','--no-pager','--plain','*deepseek*','geo-content-worker*'],capture_output=True,text=True).stdout)
p=Path('/opt/monitor/geo-content/engine/geo_source_cards/rewrite_v2/full_writer.py')
print('HASH',hashlib.sha256(p.read_bytes()).hexdigest())
