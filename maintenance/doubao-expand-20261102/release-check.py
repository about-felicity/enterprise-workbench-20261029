import hashlib,json,subprocess,zipfile
from pathlib import Path
from urllib.request import urlopen
z=zipfile.ZipFile('/tmp/doubao-strict-lanes-20261102.zip');rows=[]
for name,v in json.loads(z.read('manifest.json')).items():
 digest=hashlib.sha256(Path(v['target']).read_bytes()).hexdigest();assert digest==v['sha'];rows.append({'source':name,'server':v['target'],'sha256':digest})
p=Path('/home/user/redroid-doubao/expansion-20261102/release.json');p.write_text(json.dumps({'files':rows}))
sql="""select e.source_device,r.run_id,r.status,r.day from monitor_ingest_events e join monitor_runs r on r.run_id=e.run_id and r.model_id=e.model_id where r.run_id in ('doubao-4751bae598f9ce1f0699','doubao-cb266853877d29c13a50')"""
print(subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',sql],text=True))
v=json.load(urlopen('http://127.0.0.1:8803/api/panel',timeout=25))
print([(x['id'],x['current']['processed'],x['daily']['completed'],x['daily']['target']) for x in v['models'][-2:]])
print(subprocess.check_output(['systemctl','is-active','geo-monitor-status','geo-daily-control','geo-daily-dispatch.timer'],text=True))
