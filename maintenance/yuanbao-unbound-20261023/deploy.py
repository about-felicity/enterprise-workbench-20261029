import ast,hashlib,json,shutil,subprocess,time
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261023-yuanbao-unbound');S=D/'stage'
unit='geo-native@geo-panel-yuanbao-20261023-090004-d6b66215.service'
assert subprocess.check_output(['systemctl','show',unit,'-p','ActiveState','--value'],text=True).strip() in ('inactive','failed')
m=json.loads(Path('/tmp/yuanbao-unbound-manifest.json').read_text());hash=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for key,row in m.items():
 src=S/key;target=Path(row['target']);assert hash(src)==row['sha256'],key
 assert (hash(target) if target.exists() else None)==row['before'],('Production source changed',key)
 if src.suffix=='.py':ast.parse(src.read_text())
backup=D/('source-before-'+str(time.time_ns()));backup.mkdir()
for key,row in m.items():
 target=Path(row['target'])
 if target.exists():
  saved=backup/key;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved)
for key,row in m.items():
 target=Path(row['target']);target.parent.mkdir(parents=True,exist_ok=True)
 tmp=target.with_name(target.name+'.unbound23.tmp');shutil.copy2(S/key,tmp);tmp.chmod(0o644);tmp.replace(target)
out={'at':time.time(),'backup':str(backup),'files':{r['target']:hash(Path(r['target'])) for r in m.values()},'queue_reset':False,'question_resent':False,'other_services_restarted':False}
(D/'deployment.json').write_text(json.dumps(out,indent=2));(S/'manifest.json').write_text(json.dumps(m,indent=2))
subprocess.run(['systemctl','unmask','--runtime',unit],check=True);subprocess.run(['systemctl','daemon-reload'],check=True);subprocess.run(['systemctl','start',unit],check=True)
print(json.dumps(out))
