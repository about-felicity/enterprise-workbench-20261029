"""Export metadata only; no raw answers, account data, cookies or QR images."""
import json
from pathlib import Path
import subprocess
import time
import urllib.request

BASE=Path('/opt/monitor/geo-capture')
pointer=json.loads((BASE/'all_channel_soak_current.json').read_text())
root=Path(pointer['root']);manifest=json.loads((root/'manifest.json').read_text())
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://127.0.0.1:8803/api/panel',timeout=15) as stream:panel=json.load(stream)
models={}
for model in panel['models']:
    name=model['id'];current=model['current'];expected=manifest['jobs'][name]
    assert current['batch']==expected['batch']
    assert model['settings']==manifest['original'][name]['settings']
    models[name]={k:current[k] for k in ('batch','state','service_state','captured','processed','unique_processed','duplicates','unavailable','updated_at')}
    models[name]['default_settings_restored']=True
before=manifest['docker_before']
after=subprocess.check_output(['docker','inspect',*manifest['containers'],'--format','{{.Name}} {{.State.StartedAt}}'],text=True).strip()
historical={}
for batch in ('geo-products-21x5-account1-20261014','geo-products-21x5-account2-relogin-20261013'):
    health=json.loads((Path('/home/user/redroid-doubao/batches')/batch/'bridge_health.json').read_text())
    assert health['captured']==health['geo_processed']==105
    historical[batch]={'captured':105,'processed':105}
status=json.loads((root/'status.json').read_text())
record={'exported_at':time.time(),'test':pointer,'models':models,'historical_doubao':historical,
        'containers_unchanged_since_start':before==after,
        'deadline_timer_active':subprocess.run(['systemctl','is-active',pointer['deadline_timer']],capture_output=True,text=True).stdout.strip()=='active',
        'projection_enabled':False,'test_complete':False,'anomalies':status.get('anomalies',[]),
        'scope':'Live startup snapshot only. Startup recorder gaps and two Doubao pre-send failures are retained. No two-hour pass claimed.'}
target=Path('/tmp/ALL_CHANNEL_SOAK_START_20261015.json')
target.write_text(json.dumps(record,ensure_ascii=False,indent=2));target.chmod(0o644)
print(json.dumps(record,ensure_ascii=False))
