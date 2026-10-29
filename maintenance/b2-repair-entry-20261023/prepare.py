"""Copy a frozen candidate into a new isolated, offline repair version."""
import hashlib,json,shutil,subprocess
from pathlib import Path
D=Path(__file__).resolve().parent;W=D.parents[1];F=W/'maintenance/b1-b2-candidate-20261023';P=W/'maintenance/acceptance-prep-20261023'
assert not (D/'candidate-source').exists(),'Never overwrite a candidate version'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
protected={str(p.relative_to(W)).replace('\\','/'):sha(p) for base in (F,P) for p in base.rglob('*') if p.is_file()}
(D/'protected-before.json').write_text(json.dumps(protected,ensure_ascii=False,indent=2),encoding='utf8')
(D/'git-status-before.txt').write_text(subprocess.check_output(['git','status','--porcelain'],cwd=W,text=True,encoding='utf8'),encoding='utf8')
shutil.copytree(F/'candidate-source',D/'candidate-source');shutil.copytree(F/'candidate-source',D/'baseline-source')
for label,src in [('current',D/'candidate-source'),('baseline',D/'baseline-source')]:
 for package in ('engine','creation'):
  for p in (F/'isolated'/package).rglob('*.py'):
   if '__pycache__' in p.parts:continue
   out=D/'isolated'/label/package/p.relative_to(F/'isolated'/package);out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,out)
 for p in src.rglob('*.py'):
  relative=p.relative_to(src);out=D/'isolated'/label/('' if relative.parts[0]=='creation' else 'engine')/relative
  shutil.copyfile(p,out)
shutil.copytree(F/'fixtures',D/'fixtures');shutil.copyfile(P/'offline_guard.py',D/'offline_guard.py')
shutil.copyfile(P/'test_acceptance_edges.py',D/'test_acceptance_edges.py');shutil.copyfile(P/'engine-modules.json',D/'engine-modules.json')
saved=json.loads((W/'maintenance/candidate-validation-20261023/replay-results.json').read_text('utf8'))['samples'][0]
history=Path(saved['work_dir']);research=D/'real-fixtures/research';research.mkdir(parents=True)
for name in ('research_input.json','research_result.json'):shutil.copyfile(history/'research'/name,research/name)
origin=W/'maintenance/candidate-validation-20261023/isolated/evidence/api/runs'/saved['run_id']/'answer.json'
shutil.copyfile(origin,D/'real-fixtures/answer.json')
print(json.dumps({'protected_files':len(protected),'candidate_source_files':len(list((D/'candidate-source').rglob('*.py'))),'saved_real_sample':saved['run_id']}))
