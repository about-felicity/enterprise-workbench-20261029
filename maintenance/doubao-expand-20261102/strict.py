import json, subprocess
from pathlib import Path
b=Path('/home/user/redroid-doubao');w=b/'expansion-20261102'
s=(w/'question_only_worker.py').read_text().replace('from expansion_adapters import','from question_only_adapters import')
p=w/'strict_worker.py';p.write_text(s)
for n in [3,4]:
 subprocess.run(['systemctl','stop',f'geo-expand-final{n}-20261102'],check=True)
 cfg=json.loads((w/f'smoke{n}.json').read_text());cfg.update(batch=f'geo-expand-doubao{n}-20261102-strict',questions=['推荐一款眼霜'])
 f=w/f'strict{n}.json';assert not f.exists();f.write_text(json.dumps(cfg,ensure_ascii=False))
 subprocess.run(['systemd-run','--unit',f'geo-expand-strict{n}-20261102','--property','MemoryMax=512M','--property','WorkingDirectory='+str(b/'geo-batch-code'),str(b/'worker-venv/bin/python'),'-u',str(p),'--config',str(f)],check=True)
