"""Deploy a tested patch at a drained API boundary and retain observation history."""
import sys,json,time,zipfile,subprocess,shutil
from pathlib import Path
from datetime import datetime
B=Path('/opt/monitor/geo-content');M=Path('/opt/monitor/geo-capture/maintenance/20261021-daohe-test')
general='--general-rules' in sys.argv
roster='--roster-evidence' in sys.argv
backup=M/(('source-before-roster-evidence-fix-' if roster else 'source-before-general-rules-fix-' if general else 'source-before-review-outline-fix-')+str(time.time_ns()));backup.mkdir()
for p in (B/'runtime/runs').glob('*/api/active.json'):
 a=json.loads(p.read_text());run=p.parent/'runs'/a.get('run_id','none')
 for name in ('call','logic-call'):
  f=run/name/'api_state.json'
  if f.exists():assert json.loads(f.read_text()).get('state') not in {'REQUESTING','REQUEST_UNKNOWN'},'Actual paid execution active'
subprocess.run(['systemctl','stop','geo-content-worker'],check=True)
try:
 with zipfile.ZipFile('/tmp/geo-review-genre-patch.zip') as z:
  for name in z.namelist():
   if name.startswith('tests/'):continue
   assert name in ({'engine/geo_source_cards/reference_design.py','engine/geo_source_cards/consumer_prompts.py','engine/geo_source_cards/consumer_voice.py'} if roster else {'engine/geo_source_cards/article_logic.py','engine/geo_source_cards/consumer_voice.py'} if general else {'engine/geo_source_cards/genre_outline.py'})
   target=B/name;saved=backup/name;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved);target.write_bytes(z.read(name))
finally:subprocess.run(['systemctl','start','geo-content-worker'],check=True)
sys.path[:0]=[str(B),str(B/'engine')]
from creation import runtime,studio,observation as o
s=runtime.read(M/'task.json');task=runtime.read(studio.day_path(s['plan_id'],s['date']))
for jid in task['jobs'].values():
 root=runtime.job_root(jid)
 if runtime.read(root/'control.json').get('reason')=='maintenance_drain':runtime.resume(root)
now=datetime.now(o.ZONE);p=o.OUTPUT/'baseline.json';shutil.copy2(p,backup/'baseline.json');data=o.read(p);current=o.collect(now)
assert set(current['unknown_request_ids'])<=set(data['unknown_request_ids'])
reason='Real trial found unrelated product-category examples leaking from universal writer rules; make rules conditional and keep product label text distinct from production commentary' if general else 'Real trial found review outline projection dropping comparison role headings; preserve required review roles with source-backed opinions and normal downstream checks'
if roster:reason='Real trial found action advice counted as products and pending report/approval identifiers losing qualifiers; add generic guards and require the complete outline in its actual original order, preserve original source records'
data.setdefault('source_revisions_before_overnight',[]).append({'at':current['at'],'reason':reason,'prior_baseline':str(backup/'baseline.json'),'old_fingerprint':data.get('source_fingerprint'),'new_fingerprint':current['source_fingerprint']})
data.update(source_fingerprint=current['source_fingerprint'],setup_finalized_at=current['at']);p.write_text(json.dumps(data,ensure_ascii=False,indent=2));sys.argv=[sys.argv[0]];o.main()
result={'at':current['at'],'backup':str(backup),'engine_tests':111 if roster else 108 if general else 106,'creation_tests':69 if general or roster else 66,'paid_calls_drained_before_restart':True,'unknown_ids_unchanged':True};runtime.atomic_json(M/('roster-evidence-fix-deployment.json' if roster else 'general-rules-fix-deployment.json' if general else 'review-outline-fix-deployment.json'),result);print(json.dumps(result))
