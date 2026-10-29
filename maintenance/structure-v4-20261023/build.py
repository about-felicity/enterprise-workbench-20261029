import hashlib,json,shutil,subprocess,zipfile
from pathlib import Path
D=Path(__file__).resolve().parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for p in (D/'candidate-source').rglob('*.py'):
 r=p.relative_to(D/'candidate-source');t=D/'isolated/current/engine'/r;shutil.copy2(p,t)
m={'version':'candidate-structure-recovery-v4-20261023','base_version':'candidate-structure-recovery-v3-20261023',
 'base_manifest_sha256':'b2fffe9a51e968689dfba104918f77545278e51c2bf5cad7a78ec538e96030ed',
 'files':{p.relative_to(D/'candidate-source').as_posix():{'sha256':sha(p),'baseline_sha256':sha(D/'baseline-source'/p.relative_to(D/'candidate-source')) if (D/'baseline-source'/p.relative_to(D/'candidate-source')).is_file() else None} for p in (D/'candidate-source').rglob('*.py')},
 'execution_source_sha256':{p.relative_to(D/'isolated/current').as_posix():sha(p) for p in (D/'isolated/current').rglob('*.py')},
 'production_deployed':False}
(D/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf8')
r=subprocess.run(['git','diff','--no-index','--no-ext-diff','--',str(D/'baseline-source'),str(D/'candidate-source')],capture_output=True);assert r.returncode==1
(D/'candidate.diff').write_bytes(r.stdout)
protected=json.loads((D/'protected-before.json').read_text('utf8'));assert all(sha(Path(p))==s for p,s in protected.items())
with zipfile.ZipFile(D/'offline-stage.zip','w',zipfile.ZIP_DEFLATED) as z:
 for folder in ('candidate-source','baseline-source','isolated/current','fixtures','real-fixtures','history','real-history'):
  for p in (D/folder).rglob('*'):
   if p.is_file() and '__pycache__' not in p.parts:z.write(p,str(p.relative_to(D)))
 for n in ('manifest.json','run.py','offline_guard.py','engine-modules.json','test_acceptance_edges.py','candidate.diff'):z.write(D/n,n)
print(json.dumps({'manifest_sha256':sha(D/'manifest.json'),'execution_files':len(m['execution_source_sha256']),'protected_unchanged':len(protected),'changed_runtime_files':2,'new_tests':1}))
