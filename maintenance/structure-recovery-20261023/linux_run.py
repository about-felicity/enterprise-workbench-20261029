"""Target Linux read-only protection + isolated offline regressions/probes."""
import hashlib,json,os,sqlite3,subprocess,time,zipfile
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261023-structure-recovery-v3-final')
assert not D.exists(),'Never overwrite frozen evidence';D.mkdir(parents=True)
with zipfile.ZipFile('/tmp/structure-recovery-v3-stage.zip') as z:
 for name in z.namelist():
  assert not Path(name).is_absolute() and '..' not in Path(name).parts;z.extract(name,D)
def protected():
 base=Path('/opt/monitor/geo-content');paths=list((base/'engine/geo_source_cards').glob('*.py'))+list((base/'creation').glob('*.py'))
 frozen=Path('/opt/monitor/geo-capture/maintenance/20261023-b2-repair-entry-v2-final')
 paths += [p for p in frozen.rglob('*') if p.is_file()]
 R=base/'runtime/acceptance/20261023-rank01-staged/rank01-staged-20261023T120816-e50a98ac'
 auth=json.loads((R/'preflight.json').read_text());paths += [Path(p) for p in auth['protected_before']]
 paths += [p for p in R.rglob('*') if p.is_file()]
 paths += [Path('/home/user/geo-editorial/runtime-api/settings.json')]
 with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
  rows=db.execute('select * from costs order by id').fetchall();scopes=db.execute('select * from studio_cost_scopes order by id').fetchall()
 return {'files':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()},'ledger_rows':len(rows),
  'ledger_logical_sha256':hashlib.sha256(json.dumps([rows,scopes],sort_keys=True).encode()).hexdigest()}
before=protected();(D/'production-before.json').write_text(json.dumps(before,indent=2))
manifest=json.loads((D/'manifest.json').read_text())
for name,v in manifest['files'].items():assert hashlib.sha256((D/'candidate-source'/name).read_bytes()).hexdigest()==v['sha256']
for name,h in manifest['execution_source_sha256'].items():assert hashlib.sha256((D/'isolated/current'/name).read_bytes()).hexdigest()==h
results=[];env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1'
for mode in ('special','prior','engine','creation'):
 r=subprocess.run(['/opt/monitor/geo-capture/venv/bin/python','-B',str(D/'run.py'),mode],cwd=D,env=env,capture_output=True,text=True,timeout=180)
 (D/(mode+'-launcher.log')).write_text(r.stdout+r.stderr)
 value=json.loads((D/'logs'/('linux-'+mode+'.json')).read_text()) if (D/'logs'/('linux-'+mode+'.json')).exists() else {'launcher_error':r.stderr[-2000:]}
 results.append({'mode':mode,'exit':r.returncode,**value});print(json.dumps(results[-1]),flush=True)
r=subprocess.run(['/opt/monitor/geo-capture/venv/bin/python','-B',str(D/'probe.py')],cwd=D,env=env,capture_output=True,text=True,timeout=60)
(D/'probe-launcher.log').write_text(r.stdout+r.stderr);print(r.stdout[-3000:],flush=True)
after=protected();(D/'production-after.json').write_text(json.dumps(after,indent=2))
out={'version':manifest['version'],'production_and_ledger_unchanged':before==after,'protected_file_count':len(before['files']),'ledger_rows':after['ledger_rows'],
 'results':results,'probe_exit':r.returncode,'real_api_calls':0,'balance_queries':0,'external_business_service_calls':0,'budget_changed':False,'dependencies_installed':False,'deployed':False,
 'transport_note':'SSH only for target isolated execution; test/probe processes deny external sockets and unmocked HTTP'}
(D/'linux-results.json').write_text(json.dumps(out,indent=2));print(json.dumps({'production_and_ledger_unchanged':before==after,'probe_exit':r.returncode,'directory':str(D)}))
assert before==after;assert r.returncode==0;assert all(v['exit']==0 for v in results)
