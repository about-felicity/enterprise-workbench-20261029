"""Disposable Linux verification; only writes under this new maintenance dir."""
import hashlib,json,os,sqlite3,subprocess,time,zipfile
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261023-b1-b2-acceptance-prep')
assert not D.exists(),'Do not overwrite prior evidence';D.mkdir(parents=True)
with zipfile.ZipFile('/tmp/b1-b2-prep-stage.zip') as z:
 for name in z.namelist():
  assert not Path(name).is_absolute() and '..' not in Path(name).parts
  z.extract(name,D)
def integrity():
 with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
  costs=db.execute('select * from costs order by id').fetchall();scopes=db.execute('select * from studio_cost_scopes order by id').fetchall()
 prod=Path('/opt/monitor/geo-content');engine=prod/'engine/geo_source_cards'
 paths=[engine/p for p in ('structure_analyzer.py','section_writer.py','review_quality.py','review_arbitration.py','daily_editorial.py','repair_router.py')]
 paths += [prod/'creation/runtime.py',Path('/home/user/geo-editorial/runtime-api/settings.json')]
 R=prod/'runtime/acceptance/20261022-three-agent'
 auth=json.loads((R/'authorization.json').read_text());paths += [Path(p) for p in auth.get('original_hashes',{})]
 paths +=[R/p for p in ('authorization.json','control.json','job.json','api/active.json')]
 return {'ledger_rows':len(costs),'ledger_sha256':hashlib.sha256(json.dumps([costs,scopes],sort_keys=True).encode()).hexdigest(),
  'files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None for p in paths}}
before=integrity();(D/'production-before.json').write_text(json.dumps(before,indent=2))
results=[];env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
for mode in ('new','edges','engine','creation','baseline-creation'):
 r=subprocess.run(['/opt/monitor/geo-capture/venv/bin/python','-B',str(D/'run_suite.py'),mode],cwd=D,env=env,capture_output=True,text=True,timeout=120)
 (D/(mode+'-launcher.log')).write_text(r.stdout+r.stderr)
 result=json.loads((D/(mode+'.json')).read_text()) if (D/(mode+'.json')).exists() else {'launcher_error':r.stderr[-2500:]}
 results.append({'mode':mode,'exit':r.returncode,**result})
 print(json.dumps(results[-1]),flush=True)
after=integrity();(D/'production-after.json').write_text(json.dumps(after,indent=2))
out={'at':time.time(),'production_ledger_budget_originals_unchanged':before==after,'results':results,'deployed':False,'real_api_calls':0,'balance_calls':0}
(D/'linux-results.json').write_text(json.dumps(out,indent=2));assert before==after
print(json.dumps({'production_unchanged':before==after,'maintenance_directory':str(D)}))
