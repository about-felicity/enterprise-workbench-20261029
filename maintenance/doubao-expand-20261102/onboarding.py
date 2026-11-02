from pathlib import Path
import hashlib,json,subprocess,zipfile
def modify(s):
 old="not any(n.get('text') or n.get('content-desc') or n.get('resource-id','').endswith('/content_view') for n in rows[0].iter())"
 new="[n.get('resource-id','') for n in rows[0].iter()]==['',prefix+'content_view',prefix+'onboarding'] and not any(n.get('text') or n.get('content-desc') for n in rows[0].iter())"
 assert old in s
 return s.replace(old,new).replace("('','发消息')","('','发消息','发消息或按住说话')")
if Path('/home/user/redroid-doubao').exists():
 b=Path('/home/user/redroid-doubao');w=b/'expansion-20261102';p=w/'expansion_adapters.py';s=modify(p.read_text())
 for n in [3,4]:subprocess.run(['systemctl','stop',f'geo-expand-checked{n}-20261102'],check=True)
 p.write_text(s)
 for n in [3,4]:subprocess.run(['systemd-run','--unit',f'geo-expand-final{n}-20261102','--property','MemoryMax=512M','--property','WorkingDirectory='+str(b/'geo-batch-code'),str(b/'worker-venv/bin/python'),'-u',str(w/'question_only_worker.py'),'--config',str(w/f'smoke{n}.json')],check=True)
else:
 w=Path('maintenance/doubao-expand-20261102');p=Path('redroid-deploy/question_only_adapters.py');p.write_bytes(modify(p.read_text(encoding='utf-8')).encode())
 with zipfile.ZipFile(w/'lanes.zip') as z:m=json.loads(z.read('manifest.json'))
 m[p.as_posix()]['sha']=hashlib.sha256(p.read_bytes()).hexdigest()
 with zipfile.ZipFile(w/'lanes.zip','w',zipfile.ZIP_DEFLATED) as z:
  for name in m:z.write(name,name)
  z.writestr('manifest.json',json.dumps(m))
