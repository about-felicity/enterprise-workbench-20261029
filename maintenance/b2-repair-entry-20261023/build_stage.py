"""Freeze the independent version and package only isolated offline sources."""
import hashlib,json,subprocess,zipfile
from pathlib import Path
D=Path(__file__).resolve().parent;C=D/'candidate-source';B=D/'baseline-source'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files={}
for p in sorted(C.rglob('*.py')):
 relative=p.relative_to(C);old=B/relative
 files[str(relative).replace('\\','/')]={'sha256':sha(p),'baseline_sha256':sha(old) if old.exists() else None,
  'change':'added' if not old.exists() else 'unchanged' if p.read_bytes()==old.read_bytes() else 'modified'}
assert [p for p,v in files.items() if v['change']=='modified']==['geo_source_cards/repair_router.py']
out={'version':'candidate-b2-repair-entry-v2-20261023','base_version':'candidate-b1-b2-v1-20261023','files':files,'deployment':False,'real_api_calls':0}
(D/'manifest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
r=subprocess.run(['git','diff','--no-index','--no-ext-diff','--',str(B),str(C)],capture_output=True)
assert r.returncode==1;(D/'candidate.diff').write_bytes(r.stdout)
with zipfile.ZipFile(D/'offline-stage.zip','w',zipfile.ZIP_DEFLATED) as z:
 for name in ('candidate-source','baseline-source','isolated/current','fixtures','real-fixtures'):
  for p in (D/name).rglob('*'):
   if p.is_file() and p.suffix in ('.py','.json') and '__pycache__' not in p.parts:z.write(p,p.relative_to(D))
 for name in ('run.py','probe.py','offline_guard.py','engine-modules.json','test_acceptance_edges.py','manifest.json'):z.write(D/name,name)
print(json.dumps({'version':out['version'],'files':len(files),'modified_runtime_files':1,'bytes':(D/'offline-stage.zip').stat().st_size}))
