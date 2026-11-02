import subprocess,time
from pathlib import Path
b=Path('/home/user/redroid-doubao');ps=[]
for n in [4,3]:
 if n==3:
  for _ in range(40):
   if not subprocess.run(['pgrep','-f','^/home/user/redroid-doubao/worker-venv/bin/python .*doubao-ref-sample.py 3$'],stdout=subprocess.DEVNULL).returncode:time.sleep(1)
   else:break
  else:continue
 p=Path(f'/tmp/doubao-panel-url-{n}.log');out=p.open('w')
 ps.append(subprocess.Popen([str(b/'worker-venv/bin/python'),'-u','/tmp/doubao-url-panel.py',str(n)],stdout=out,stderr=subprocess.STDOUT))
for p in ps:p.wait(timeout=450)
for n in [3,4]:
 p=Path(f'/tmp/doubao-panel-url-{n}.log')
 if p.exists():print(n,p.read_text()[-1600:])
