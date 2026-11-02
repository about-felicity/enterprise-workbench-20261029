import json,hashlib,sqlite3,urllib.request
from pathlib import Path
base=Path('/opt/monitor/geo-content/maintenance/api-http-recovery-20261029')
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:3000/api/geo-creation/status',timeout=20) as r:panel=json.load(r)
task=next(t for t in panel['studio']['daily_tasks'] if t['plan_id']=='plan-3224f5a2caac465a988083ae15ab0865' and t['date']=='2026-10-29')
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 used=db.execute('select coalesce(sum(coalesce(c.charged,c.reserved)),0) from costs c join studio_cost_scopes s on s.id=c.id where s.scope=? and s.task_day=?',(task['plan_id'],task['date'])).fetchone()[0]
original=json.loads((base/'approved-before.json').read_text())
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in original.items())
result={k:task.get(k) for k in ['name','status','articles','writing_jobs','writing_complete','error','api_recovery']}
result.update(charged_plus_reserved_cny=round(used,6),original_16_unchanged=True)
print(json.dumps(result,ensure_ascii=False),flush=True)
for identity in ['creation-1793252901-ec370f70','creation-1793252898-0afc24a2','creation-1793252896-76293dac','creation-1793252890-7d974528']:
 root=Path('/opt/monitor/geo-content/runtime/runs')/identity
 read=lambda n:json.loads((root/n).read_text()) if (root/n).exists() else {}
 control=read('control.json');active=read('api/active.json');day=read('days/2026-10-29/day.json')
 print(json.dumps({'job':identity,'control':control,'active_stage':active.get('stage'),'active_state':active.get('state'),'day':day},ensure_ascii=False))
(base/'latest-progress.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
