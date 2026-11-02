from pathlib import Path
import sqlite3,subprocess,json
b=Path('/home/user/redroid-doubao');w=b/'expansion-20261102';r=b/'batches/geo-expand-doubao4-20261102-strict'
def clicks():
 with sqlite3.connect(r/'tasks.sqlite') as d:return d.execute("select count(*) from events where event='send_click_intent_committed'").fetchone()[0]
if clicks():print('already sent; no change')
else:
 subprocess.run(['systemctl','stop','geo-expand-strict4-20261102'],check=True)
 p=w/'strict_worker.py';s=p.read_text().replace("with queue.db:queue.event(task['task_id'],'send_uncertain',type(error).__name__)","with queue.db:queue.event(task['task_id'],'send_uncertain',type(error).__name__+': '+str(error)[:200])");p=w/'strict_debug_worker.py';p.write_text(s)
 subprocess.run(['systemd-run','--unit','geo-expand-strict-debug4-20261102','--property','MemoryMax=512M','--property','WorkingDirectory='+str(b/'geo-batch-code'),str(b/'worker-venv/bin/python'),'-u',str(p),'--config',str(w/'strict4.json')],check=True)
