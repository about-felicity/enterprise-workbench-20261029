import datetime,json,sqlite3,subprocess
from pathlib import Path
def read(p):
 try:return json.loads(p.read_text())
 except (OSError,ValueError):return {}
base=Path('/opt/monitor/geo-capture')
print('time',datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat())
rows=[]
for p in (base/'batches').glob('*/manifest.json'):
 v=read(p);rows.append((v.get('created_at',0),p.parent,v))
for _,root,v in sorted(rows,key=lambda r:r[0])[-12:]:
 h=read(root/'bridge_health.json');print('batch',json.dumps({'id':root.name,'model':v.get('model'),'created_at':v.get('created_at'),'status':h.get('status'),'tasks':h.get('tasks'),'error':h.get('last_error'),'pause':(root/'pause.json').exists()},ensure_ascii=False))
for p in base.glob('*'):
 if p.suffix=='.json' and any(s in p.name for s in ['schedule','daily','current']):print('control_file',p.name,json.dumps(read(p),ensure_ascii=False)[:2000])
print('units',subprocess.check_output(['systemctl','list-units','--all','--no-pager','--plain','geo-daily*','geo-web@*','geo-wenxin*'],text=True)[-6500:])
print('daily_logs',subprocess.run(['journalctl','-u','geo-daily-dispatch.service','--since','today','-n','25','--no-pager'],capture_output=True,text=True).stdout[-4500:])
