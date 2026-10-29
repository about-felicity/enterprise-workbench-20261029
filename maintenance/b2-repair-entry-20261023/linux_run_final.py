"""Run isolated tests using target Linux dependencies, no service/API requests."""
import hashlib,json,os,sqlite3,subprocess,time,zipfile
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261023-b2-repair-entry-v2-final')
assert not D.exists(),'Preserve earlier versions';D.mkdir(parents=True)
with zipfile.ZipFile('/tmp/b2-repair-entry-stage.zip') as z:
 for name in z.namelist():
  assert not Path(name).is_absolute() and '..' not in Path(name).parts;z.extract(name,D)
def protected():
 base=Path('/opt/monitor/geo-content');paths=list((base/'engine/geo_source_cards').glob('*.py'))+list((base/'creation').glob('*.py'))
 R=base/'runtime/acceptance/20261022-three-agent';auth=json.loads((R/'authorization.json').read_text())
 paths += [Path(p) for p in auth.get('original_hashes',{})]+[R/p for p in ('job.json','authorization.json','control.json','api/active.json')]
 paths += [Path('/home/user/geo-editorial/runtime-api/settings.json')]
 with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
  rows=db.execute('select * from costs order by id').fetchall();scopes=db.execute('select * from studio_cost_scopes order by id').fetchall()
 return {'files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None for p in paths},
  'ledger_rows':len(rows),'ledger_logical_sha256':hashlib.sha256(json.dumps([rows,scopes],sort_keys=True).encode()).hexdigest()}
before=protected();(D/'production-before.json').write_text(json.dumps(before,indent=2))
manifest=json.loads((D/'manifest.json').read_text())
for p,v in manifest['files'].items():assert hashlib.sha256((D/'candidate-source'/p).read_bytes()).hexdigest()==v['sha256']
results=[];env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
# Required order: new specialized cases first; then old checks and regressions.
for mode in ('special','prior','edges','engine','creation'):
 r=subprocess.run(['/opt/monitor/geo-capture/venv/bin/python','-B',str(D/'run.py'),mode],cwd=D,env=env,capture_output=True,text=True,timeout=150)
 (D/(mode+'-launcher.log')).write_text(r.stdout+r.stderr)
 value=json.loads((D/'logs'/('linux-'+mode+'.json')).read_text()) if (D/'logs'/('linux-'+mode+'.json')).exists() else {'launcher_error':r.stderr[-2000:]}
 results.append({'mode':mode,'exit':r.returncode,**value});print(json.dumps(results[-1]),flush=True)
r=subprocess.run(['/opt/monitor/geo-capture/venv/bin/python','-B',str(D/'probe.py')],cwd=D,env=env,capture_output=True,text=True,timeout=45)
(D/'probe-launcher.log').write_text(r.stdout+r.stderr);print(r.stdout[-3000:],flush=True);assert r.returncode==0,r.stderr
after=protected();(D/'production-after.json').write_text(json.dumps(after,indent=2))
assert before==after,'Protected files or ledger changed'
out={'at':time.time(),'production_and_ledger_unchanged':True,'results':results,'real_api_calls':0,'balance_calls':0,
 'external_business_service_calls':0,'dependencies_installed':False,'deployed':False,'transport_note':'SSH only for offline staging/execution; no model, balance, browser or business services used'}
(D/'linux-results.json').write_text(json.dumps(out,indent=2));print(json.dumps({'production_and_ledger_unchanged':True,'directory':str(D)}))
