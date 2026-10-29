import os,sys,json,time,tempfile,subprocess
from pathlib import Path
with tempfile.TemporaryDirectory() as tmp:
 root=Path(tmp);job=root/'runs/creation-1000-00000001';job.mkdir(parents=True)
 (job/'job.json').write_text(json.dumps({'date':'2026-10-26'}))
 code="""import sys,subprocess
from pathlib import Path
from creation import parallel
parallel.Scheduler.start=lambda self,root:subprocess.Popen([sys.executable,'-c',"import time;from pathlib import Path;time.sleep(2);Path("+repr(str(root/'done'))+").touch()"])
parallel.run()
"""
 proc=subprocess.Popen([sys.executable,'-c',code],env={**os.environ,'GEO_CREATION_ROOT':tmp})
 deadline=time.time()+10
 try:
  while time.time()<deadline:
   try:
    if json.loads((root/'worker_health.json').read_text())['active_jobs']:break
   except (FileNotFoundError,ValueError):pass
   time.sleep(.05)
  else:raise AssertionError('supervisor did not launch')
  proc.terminate();time.sleep(.2);assert proc.poll() is None,'did not drain'
  assert proc.wait(timeout=8)==0
  assert (job/'done').exists()
  health=json.loads((root/'worker_health.json').read_text());assert health['status']=='draining' and not health['active_jobs']
  print(json.dumps({'graceful_sigterm_drain':True}))
 finally:
  if proc.poll() is None:proc.kill();proc.wait()
