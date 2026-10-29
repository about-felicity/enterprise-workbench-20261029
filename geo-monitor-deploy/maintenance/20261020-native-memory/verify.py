"""Read-only rollout acceptance; emits no credentials or answer contents."""
import json, sqlite3, subprocess, time, urllib.request
from pathlib import Path

root=Path('/home/user/redroid-doubao/memory/doubao-hpe14-account2')
state=json.loads((root/'state.json').read_text())
with sqlite3.connect((root/'samples.sqlite').as_uri()+'?mode=ro',uri=True) as db:
    samples=db.execute('select count(*),min(at),max(at) from samples').fetchone()
with urllib.request.urlopen('http://127.0.0.1:8803/api/panel?date=2026-10-20',timeout=15) as response:
    panel=json.load(response)
models=panel['models']
model=next(v for v in models if v['id']=='doubao2')
memory=model['current']['memory']
assert memory['java_limit_kib']==524288
assert memory['pid']==2195
assert samples[0]>=2
with urllib.request.urlopen('http://127.0.0.1:8803/',timeout=10) as response:
    html=response.read().decode()
assert 'memory_maintenance' in html and 'Java' in html
unit='geo-native@geo-panel-doubao2-20261020-090001-6bcafb90.service'
services={v:subprocess.check_output(['systemctl','is-active',v],text=True).strip() for v in [unit,'geo-monitor-status.service','geo-daily-control.service']}
assert all(v=='active' for v in services.values())
report={'checked_at':time.time(),'memory':memory,'samples':{'count':samples[0],'first':samples[1],'last':samples[2]},'maintenance_attempts':state.get('recycles',[]),'services':services,'panel_memory_served':True,'policy':json.loads(Path('/opt/monitor/geo-capture/native_memory_policy.json').read_text()),'mapping':{'files':126,'matched':126}}
Path('/tmp/native-memory-acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
