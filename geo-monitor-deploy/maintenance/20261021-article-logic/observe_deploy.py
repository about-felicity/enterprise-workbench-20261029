"""Deploy observer coverage and preserve an explicit pre-overnight revision."""
import os,sys,subprocess,shutil,json,time
from pathlib import Path
from datetime import datetime
B=Path('/opt/monitor/geo-content');M=Path('/opt/monitor/geo-capture/maintenance/20261021-article-logic');S=M/'stage'
for source,name in [('/tmp/geo-observation-logic.py','observation.py'),('/tmp/geo-test-observation-logic.py','test_observation.py')]:shutil.copy2(source,S/'creation'/name)
subprocess.run(['/home/user/geo-editorial/venv/bin/python','-B','-m','unittest','creation.test_observation'],cwd=S,env={**os.environ,'PYTHONPATH':str(S)+':'+str(S/'engine')},check=True)
backup=M/('observer-backup-'+str(time.time_ns()));backup.mkdir()
for source,name in [('/tmp/geo-observation-logic.py','observation.py'),('/tmp/geo-test-observation-logic.py','test_observation.py'),('/tmp/geo-panel-logic.html','panel.html')]:
 target=B/'creation'/name;shutil.copy2(target,backup/name);shutil.copy2(source,target)
sys.path[:0]=[str(B),str(B/'engine')]
from creation import observation as o
assert datetime.now(o.ZONE).date().isoformat()=='2026-10-21'
baseline=o.OUTPUT/'baseline.json';saved=backup/'baseline.json';shutil.copy2(baseline,saved)
data=o.read(baseline);current=o.collect(datetime.now(o.ZONE))
assert set(current['unknown_request_ids'])<=set(data['unknown_request_ids']),'New unknown requests must be resolved independently'
data.setdefault('source_revisions_before_overnight',[]).append({'at':current['at'],'reason':'User-reported whole-article logic failure: added independent gate and nested request observation, prior baseline and all samples retained','prior_baseline':str(saved),'old_fingerprint':data.get('source_fingerprint'),'new_fingerprint':current['source_fingerprint']})
data['source_fingerprint']=current['source_fingerprint'];data['setup_finalized_at']=current['at']
baseline.write_text(json.dumps(data,ensure_ascii=False,indent=2));o.main()
