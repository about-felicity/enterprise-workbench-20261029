import subprocess,time
from pathlib import Path
B=Path(__file__).resolve().parent
for attempt in range(15):
 result=subprocess.run(['/home/user/geo-editorial/venv/bin/python','-B',str(B/'deploy.py')],capture_output=True,text=True,timeout=60)
 if result.returncode==0:
  print(result.stdout);raise SystemExit(0)
 if 'Another collector uses this runtime' not in result.stderr:
  print(result.stdout);print(result.stderr);raise SystemExit(result.returncode)
 print('Shared browser is finishing an existing capture; no service has been stopped.',flush=True)
 time.sleep(4)
raise SystemExit('No idle browser boundary within 60 seconds; production unchanged.')
