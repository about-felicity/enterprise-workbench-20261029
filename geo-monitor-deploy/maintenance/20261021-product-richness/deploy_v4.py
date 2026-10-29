import json,sys,shutil,subprocess,time
from pathlib import Path
B=Path('/opt/monitor/geo-content');M=Path('/opt/monitor/geo-capture/maintenance/20261021-product-richness');r=B/'runtime/runs/creation-1792556219-bbc55e13'
assert not (M/'deployed-v4.json').exists()
for p in (B/'runtime/runs').glob('*/api/active.json'):
 a=json.loads(p.read_text());assert a.get('state') in (None,'SUBMITTED'),str(p)
c=json.loads((r/'control.json').read_text());assert c==json.loads((M/'maintenance-v4-pause.json').read_text())
subprocess.run(['systemctl','stop','geo-content-worker'],check=True)
for n in ['api_worker.py','genre_outline.py','consumer_prompts.py']:
 src=M/'stage/engine/geo_source_cards'/n;dst=B/'engine/geo_source_cards'/n;bk=M/'backup-v4'/n;bk.parent.mkdir(exist_ok=True);shutil.copy2(dst,bk);shutil.copy2(src,dst)
(M/'deployed-v4.json').write_text(json.dumps({'at':time.time(),'paid_requests_finished':True,'maintenance_pause':c}))
subprocess.run(['systemctl','start','geo-content-worker'],check=True)
print('v4 applied at safe request boundary; scoped maintenance pause remains')
