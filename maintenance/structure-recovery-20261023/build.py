"""Freeze new candidate and package offline execution files, never production."""
import hashlib,json,subprocess,zipfile
from pathlib import Path
D=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files={}
for p in sorted((D/'candidate-source').rglob('*.py')):
 r=p.relative_to(D/'candidate-source');old=D/'baseline-source'/r
 dest=D/'isolated/current'/('' if r.parts[0]=='creation' else 'engine')/r
 assert dest.is_file() and sha(dest)==sha(p),'Run tests to sync the execution copy first'
 files[r.as_posix()]={'sha256':sha(p),'baseline_sha256':sha(old) if old.exists() else None,'change':'added' if not old.exists() else 'unchanged' if sha(old)==sha(p) else 'modified'}
expected={'geo_source_cards/api_worker.py','geo_source_cards/structure_analyzer.py','geo_source_cards/section_writer.py','tests/test_three_agent_quality.py',
          'geo_source_cards/consumer_prompts.py','geo_source_cards/article_logic.py','geo_source_cards/review_arbitration.py'}
assert {p for p,v in files.items() if v['change']=='modified'}==expected
assert {p for p,v in files.items() if v['change']=='added'}=={'geo_source_cards/structure_protocol.py','tests/test_structure_recovery.py'}
out={'version':'candidate-structure-recovery-v3-20261023','base_version':'candidate-b2-repair-entry-v2-20261023','files':files,
 'execution_source_sha256':{p.relative_to(D/'isolated/current').as_posix():sha(p) for p in (D/'isolated/current').rglob('*.py')},'real_api_calls':0,'budget_changed':False,'deployed':False}
(D/'manifest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
r=subprocess.run(['git','diff','--no-index','--no-ext-diff','--',str(D/'baseline-source'),str(D/'candidate-source')],capture_output=True)
assert r.returncode==1;(D/'candidate.diff').write_bytes(r.stdout)
with zipfile.ZipFile(D/'offline-stage.zip','w',zipfile.ZIP_DEFLATED) as z:
 for folder in ('candidate-source','baseline-source','isolated/current','fixtures','real-fixtures','history'):
  for p in (D/folder).rglob('*'):
   if p.is_file() and p.suffix in {'.py','.json','.md','.txt'} and '__pycache__' not in p.parts:z.write(p,p.relative_to(D))
 for name in ('manifest.json','offline_guard.py','run.py','probe.py','engine-modules.json','test_acceptance_edges.py'):z.write(D/name,name)
print(json.dumps({'version':out['version'],'manifest_files':len(files),'all_execution_source_files':len(out['execution_source_sha256']),'changed_runtime_files':6,'added_runtime_files':1,'stage_zip_bytes':(D/'offline-stage.zip').stat().st_size}))
