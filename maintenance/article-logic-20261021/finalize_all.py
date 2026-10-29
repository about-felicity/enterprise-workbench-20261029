"""Install tested final rules and record a pre-overnight source revision."""
import os,sys,json,time,shutil,subprocess
from pathlib import Path
from datetime import datetime
B=Path('/opt/monitor/geo-content');M=Path('/opt/monitor/geo-capture/maintenance/20261021-all-logic')
S=Path('/opt/monitor/geo-capture/maintenance/20261021-article-logic/stage')
py='/home/user/geo-editorial/venv/bin/python'
shutil.copy2('/tmp/geo-logic-v2-final.py',S/'engine/geo_source_cards/article_logic.py')
shutil.copy2('/tmp/geo-logic-v2-tests.py',S/'tests/test_article_logic.py')
env={**os.environ,'PYTHONPATH':str(S)+':'+str(S/'engine')}
for args in [['discover','-s','tests','-p','test_*.py'],['discover','-s','creation','-t','.', '-p','test_*.py']]:
 subprocess.run([py,'-B','-m','unittest',*args],cwd=S,env=env,check=True)
# Do not interrupt a paid response. The business worker has been idle throughout
# the audit; recheck its active file immediately before the short reload.
for p in (B/'runtime/runs').glob('*/api/active.json'):
 assert json.loads(p.read_text()).get('state') in (None,'SUBMITTED'),'Paid request active: '+str(p)
backup=M/('final-source-backup-'+str(time.time_ns()));backup.mkdir()
subprocess.run(['systemctl','stop','geo-content-worker'],check=True)
try:
 for source,target in [('/tmp/geo-logic-v2-final.py',B/'engine/geo_source_cards/article_logic.py'),('/tmp/geo-creation-readme-v2.md',B/'creation/README.md')]:
  shutil.copy2(target,backup/target.name);shutil.copy2(source,target)
finally:subprocess.run(['systemctl','start','geo-content-worker'],check=True)
subprocess.run(['systemctl','restart','geo-content-api'],check=True)
sys.path[:0]=[str(B),str(B/'engine')]
from creation import observation as o
baseline=o.OUTPUT/'baseline.json';shutil.copy2(baseline,backup/'baseline.json')
now=datetime.now(o.ZONE)
assert now.date().isoformat()=='2026-10-21','Cannot finalize across the observed overnight workload'
data=o.read(baseline);current=o.collect(now)
assert set(current['unknown_request_ids'])<=set(data['unknown_request_ids'])
for path,expected in o.read(M/'controls-before.json').items():
 assert o.file_sha(Path(path))==expected,'Original task control changed: '+path
data.setdefault('source_revisions_before_overnight',[]).append({'at':current['at'],
 'reason':'User requested every saved article checked for logic and section order; final article-logic-v2 and generation rules',
 'prior_baseline':str(backup/'baseline.json'),'old_fingerprint':data.get('source_fingerprint'),'new_fingerprint':current['source_fingerprint']})
data.update(source_fingerprint=current['source_fingerprint'],setup_finalized_at=current['at'])
baseline.write_text(json.dumps(data,ensure_ascii=False,indent=2));o.main()
print(json.dumps({'services_reloaded':['geo-content-worker','geo-content-api'],'original_controls_unchanged':True,
 'unknown_ids':current['unknown_request_ids'],'ledger':current['ledger'],
 'source_revision_at':current['at'],'overnight_acceptance':'not_yet_due'},ensure_ascii=False))
