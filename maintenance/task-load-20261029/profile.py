import os,time,json,cProfile,pstats,io,sys,urllib.request,hashlib
from pathlib import Path
base=Path('/opt/monitor/geo-content')
for n in ['creation/service.py','creation/runtime.py','creation/panel.html']:
 p=base/n;print('HASH',n,hashlib.sha256(p.read_bytes()).hexdigest())
print('SERVICE',__import__('subprocess').check_output(['systemctl','show','geo-content-api','-p','Environment','-p','ExecStart']).decode())
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for path in ['/api/uploads','/api/panel']:
 t=time.monotonic()
 try:
  with op.open('http://127.0.0.1:8804'+path,timeout=45) as r:b=r.read();print('HTTP',path,round(time.monotonic()-t,3),len(b),r.status)
 except Exception as e:print('HTTP',path,type(e).__name__,round(time.monotonic()-t,3))
sys.path[:0]=[str(base),str(base/'engine')]
from creation import runtime
pr=cProfile.Profile();pr.enable();t=time.monotonic();result=runtime.status();pr.disable();print('STATUS',time.monotonic()-t,'jobs',len(result['jobs']));s=io.StringIO();pstats.Stats(pr,stream=s).sort_stats('cumtime').print_stats(22);print(s.getvalue())
