"""Build disposable offline tests without touching the frozen candidate tree."""
import ast,hashlib,json,shutil,subprocess,zipfile
from pathlib import Path
D=Path(__file__).resolve().parent;W=D.parents[1];F=W/'maintenance/b1-b2-candidate-20261023'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
protected={str(p.relative_to(W)).replace('\\','/'):sha(p) for p in F.rglob('*') if p.is_file()}
manifest=json.loads((F/'manifest.json').read_text('utf8'))
assert all(sha(F/'candidate-source'/p)==r['sha256'] for p,r in manifest['files'].items())
protected.update({p:sha(W/p) for p in ('CURRENT_PROJECT_HANDOFF.md','PROJECT_STATUS.md','SOURCE_CONTROL.md')})
if (D/'protected-before.json').exists():assert json.loads((D/'protected-before.json').read_text('utf8'))==protected
else:(D/'protected-before.json').write_text(json.dumps(protected,ensure_ascii=False,indent=2),encoding='utf8')
if not (D/'git-status-before.txt').exists():(D/'git-status-before.txt').write_text(subprocess.check_output(['git','status','--porcelain'],cwd=W,text=True,encoding='utf8'),encoding='utf8')
for flavor,source in [('candidate',F/'isolated'),('baseline',F/'isolated/baseline')]:
 for package in ('creation','engine'):
  for p in (source/package).rglob('*.py'):
   if '__pycache__' in p.parts:continue
   dest=D/flavor/package/p.relative_to(source/package);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
for p in (F/'candidate-source').rglob('*.py'):
 relative=p.relative_to(F/'candidate-source');dest=D/'candidate'/('engine' if relative.parts[0]!='creation' else '')/relative
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
shutil.copytree(F/'fixtures',D/'fixtures',dirs_exist_ok=True)
shutil.copyfile(F/'offline_guard.py',D/'offline_guard.py')
tree=ast.parse((W/'maintenance/candidate-validation-20261023/regressions.py').read_text('utf8'))
modules=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='modules' for t in n.targets))
(D/'engine-modules.json').write_text(json.dumps(modules),encoding='utf8')
(D/'candidate-sha.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
with zipfile.ZipFile(D/'offline-stage.zip','w',zipfile.ZIP_DEFLATED) as z:
 for folder in ('candidate','baseline','fixtures'):
  for p in (D/folder).rglob('*'):
   if p.is_file() and p.suffix in ('.py','.json'):z.write(p,p.relative_to(D))
 for name in ('offline_guard.py','engine-modules.json','candidate-sha.json','run_suite.py','test_acceptance_edges.py'):
  z.write(D/name,name)
print(json.dumps({'preserved_files':len(protected),'candidate_files':len(manifest['files']),'stage_bytes':(D/'offline-stage.zip').stat().st_size}))
