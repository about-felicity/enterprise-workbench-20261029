"""Request a safe drain without killing an in-flight UI/native send."""
import sys,subprocess,time,json,os
from pathlib import Path
base=Path('/home/user/redroid-doubao');sys.path.insert(0,str(base/'geo-batch-code'))
from unattended_core import Queue
from unattended_worker import atomic_json
batch,action=sys.argv[1:3]
services={'geo-products-21x5-account1-20261014':'redroid-geo-products.service','geo-products-21x5-account2-relogin-20261013':'redroid-geo-products-account2.service'}
assert batch in services and action in ('pause','status','resume')
root=base/'batches'/batch;marker=root/'maintenance_pause.json';service=services[batch]
os.umask(0o077)
if action=='pause':
 atomic_json(marker,{'time':time.time(),'reason':'Requested maintenance: finish in-flight task and processed delivery before stopping'})
 print('Safe maintenance pause requested; no service or App force-stop performed')
elif action=='resume':
 q=Queue(root/'tasks.sqlite');assert not q.summary().get('needs_attention'),'Reconcile blocked tasks first'
 assert marker.exists(),'No maintenance pause marker'
 assert subprocess.run(['systemctl','is-active',service],capture_output=True,text=True).stdout.strip() in ('inactive','failed')
 marker.unlink();subprocess.run(['systemctl','start',service],check=True)
 print('Maintenance pause cleared; original queue resumed')
else:
 state=subprocess.run(['systemctl','is-active',service],capture_output=True,text=True).stdout.strip()
 worker=json.loads((root/'health.json').read_text())
 print(json.dumps({'service':state,'pause_requested':marker.exists(),'worker_status':worker.get('status'),'drained':state=='inactive' and worker.get('status')=='maintenance_paused'},ensure_ascii=False))
