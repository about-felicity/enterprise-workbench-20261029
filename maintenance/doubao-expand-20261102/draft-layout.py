import subprocess,sqlite3
from pathlib import Path
b=Path('/home/user/redroid-doubao');w=b/'expansion-20261102'
a=w/'expansion_adapters.py';s=a.read_text().replace("if len(lists)==1 and len(lists[0])==2:\n        greeting,suggestions=lists[0]","rows=list(lists[0]) if len(lists)==1 else []\n    if len(rows)==3 and not any(n.get('text') or n.get('content-desc') or n.get('resource-id','').endswith('/content_view') for n in rows[0].iter()):rows=rows[1:]\n    if len(rows)==2:\n        greeting,suggestions=rows")
assert s!=a.read_text()
for n in (3,4):
 subprocess.run(['systemctl','stop',f'geo-expand-welcome{n}-20261102'],check=True)
 r=b/'batches'/f'geo-expand-doubao{n}-20261102-smoke'
 with sqlite3.connect(r/'tasks.sqlite') as d:
  assert not d.execute("select 1 from events where event='send_click_intent_committed'").fetchone()
  assert not d.execute("select 1 from tasks where request_id is not null").fetchone()
 code="""import uiautomator2 as u,sys; d=u.connect(sys.argv[1]); e=d(resourceId='com.larus.nova:id/input_text'); assert e.get_text()=='推荐一款睫毛增长液'; e.clear_text()"""
 subprocess.run([str(b/'worker-venv/bin/python'),'-c',code,f'127.0.0.1:556{n}'],check=True)
a.write_text(s)
for n in (3,4):
 subprocess.run(['systemd-run','--unit',f'geo-expand-checked{n}-20261102','--property','MemoryMax=512M','--property','WorkingDirectory='+str(b/'geo-batch-code'),str(b/'worker-venv/bin/python'),'-u',str(w/'question_only_worker.py'),'--config',str(w/f'smoke{n}.json')],check=True)
