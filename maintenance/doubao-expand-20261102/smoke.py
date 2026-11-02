import subprocess,json
from pathlib import Path
base=Path('/home/user/redroid-doubao');w=base/'expansion-20261102';source=base/'geo-batch-code/question_only_worker.py'
s=source.read_text();s=s.replace("'doubao2':('doubao-hpe14-account2','127.0.0.1:5558'),","'doubao2':('doubao-hpe14-account2','127.0.0.1:5558'),\n         'doubao3':('doubao-hpe14-account3','127.0.0.1:5563'),\n         'doubao4':('doubao-hpe14-account4','127.0.0.1:5564'),").replace("('doubao1','doubao2')","('doubao1','doubao2','doubao3','doubao4')")
(w/'question_only_worker.py').write_text(s)
for n in [3,4]:
 c=f'doubao-hpe14-account{n}'
 for name in ['frida-server','u2','u2.jar']:
  p=w/name
  if not p.exists():subprocess.run(['docker','cp','doubao-hpe14-account2:/data/local/tmp/'+name,str(p)],check=True)
  subprocess.run(['docker','cp',str(p),c+':/data/local/tmp/'+name],check=True)
  subprocess.run(['docker','exec',c,'chmod','755','/data/local/tmp/'+name],check=True)
 cfg={'model':f'doubao{n}','batch':f'geo-expand-doubao{n}-20261102-smoke','questions':['推荐一款睫毛增长液'],'rounds':1,'interval':60,'prompt_mode':'question_only'}
 p=w/f'smoke{n}.json';assert not p.exists(),'Already prepared, inspect service before retry';p.write_text(json.dumps(cfg,ensure_ascii=False))
 subprocess.run(['systemd-run','--unit',f'geo-expand-smoke{n}-20261102','--property','MemoryMax=512M','--property','WorkingDirectory='+str(base/'geo-batch-code'),str(base/'worker-venv/bin/python'),'-u',str(w/'question_only_worker.py'),'--config',str(p)],check=True)
 print('SMOKE_STARTED',n,flush=True)
