"""Build a separate local replay tree from immutable source/evidence copies."""
import difflib,hashlib,json,shutil,zipfile
from pathlib import Path
D=Path(__file__).resolve().parent;B=D.parents[1];C=B/'maintenance/real-acceptance-20261022/candidate-source';S=D/'isolated'
if S.exists():raise SystemExit('Existing replay retained; do not overwrite')
S.mkdir()
production=B/'source-snapshot/server/opt/monitor/geo-content/engine/geo_source_cards'
shutil.copytree(production,S/'engine/geo_source_cards')
shutil.copytree(B/'geo-source-card-collectors/tests',S/'engine/tests',ignore=shutil.ignore_patterns('__pycache__'))
shutil.copytree(B/'source-snapshot/server/opt/monitor/geo-content/creation',S/'creation')
shutil.copytree(B/'geo-monitor-deploy/tests',S/'creation_tests',ignore=shutil.ignore_patterns('__pycache__'))
manifest={};diff=[]
for p in sorted(C.rglob('*.py')):
 relative=p.relative_to(C);target=S/'engine'/relative;target.parent.mkdir(parents=True,exist_ok=True)
 old=production/relative.name if relative.parts[0]=='geo_source_cards' else None
 manifest[str(relative).replace('\\','/')]={'candidate_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'production_sha256':hashlib.sha256(old.read_bytes()).hexdigest() if old and old.exists() else None}
 if old and old.exists():diff.extend(difflib.unified_diff(old.read_text('utf8').splitlines(True),p.read_text('utf8').splitlines(True),fromfile='production/'+str(relative),tofile='frozen-candidate/'+str(relative)))
 shutil.copyfile(p,target)
with zipfile.ZipFile(B/'maintenance/real-acceptance-20261022/evidence.zip') as z:
 selected=[n for n in z.namelist() if n.startswith(('api/runs/','days/','queue/')) and n.endswith(('.json','.md','.txt'))]
 for name in selected:
  target=S/'evidence'/name
  if not target.resolve().is_relative_to((S/'evidence').resolve()):raise ValueError('Archive path escape')
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(name))
 manifest['evidence_archive']={'sha256':hashlib.sha256(Path(z.filename).read_bytes()).hexdigest(),'extracted_files':len(selected)}
(D/'frozen-manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf8')
(D/'candidate-v-production.diff').write_text(''.join(diff),encoding='utf8')
print(json.dumps({'isolated':str(S),'frozen_files':len(manifest)-1,'evidence_files':len(selected)}))
