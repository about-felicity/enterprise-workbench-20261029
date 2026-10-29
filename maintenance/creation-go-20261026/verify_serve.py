import os,json,tempfile,time,subprocess,signal
from pathlib import Path
binary='/tmp/creation-go-20261026/creation-go/creation-runner'
with tempfile.TemporaryDirectory() as tmp:
 r=Path(tmp);key=r/'key';key.write_text('sk-'+'x'*24)
 adapter=r/'fixture.sh';adapter.write_text('#!/bin/sh\nr="$GEO_CREATION_ROOT/runs/$5"\ntouch "$r/started"\nwhile [ ! -f "$GEO_CREATION_ROOT/finish" ]; do sleep 0.1; done\nmkdir -p "$r/days/2026-10-26"\nprintf \'{"status":"complete"}\' > "$r/days/2026-10-26/day.json"\n');adapter.chmod(0o700)
 for i in range(10):
  job=r/'runs'/('creation-1000-'+format(i,'08x'));job.mkdir(parents=True);(job/'job.json').write_text(json.dumps({'date':'2026-10-26','studio_plan_id':str(i)}))
 p=subprocess.Popen([binary,'serve'],env={**os.environ,'GEO_CREATION_ROOT':tmp,'GEO_CREATION_KEY_FILE':str(key),'GEO_CREATION_PYTHON':str(adapter),'GEO_CREATION_CONCURRENCY':'10'})
 try:
  until=time.time()+10
  while time.time()<until:
   if len(list((r/'runs').glob('*/started')))==10:break
   time.sleep(.1)
  else:raise AssertionError('ten tasks did not start')
  p.send_signal(signal.SIGTERM);time.sleep(.3);assert p.poll() is None
  (r/'finish').touch();assert p.wait(timeout=10)==0
  health=json.loads((r/'worker_health.json').read_text());assert health['status']=='draining' and not health['active_jobs']
  assert not (r/'model.sock').exists()
  print(json.dumps({'go_serve_ten_jobs':True,'graceful_stop':True,'socket_cleaned':True,'paid_requests':0}))
 finally:
  (r/'finish').touch()
  if p.poll() is None:p.terminate();p.wait(timeout=10)
