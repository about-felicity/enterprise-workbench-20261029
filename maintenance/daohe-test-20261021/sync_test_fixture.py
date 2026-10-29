import sys,shutil,json,time
from pathlib import Path
from datetime import datetime
M=Path('/opt/monitor/geo-capture/maintenance/20261021-daohe-test');B=Path('/opt/monitor/geo-content');target=B/'creation/test_workflow.py'
backup=M/('test-fixture-sync-'+str(time.time_ns()));backup.mkdir();shutil.copy2(target,backup/target.name);shutil.copyfile('/tmp/geo-daohe-test-workflow.py',target)
sys.path[:0]=[str(B),str(B/'engine')]
from creation import observation as o
p=o.OUTPUT/'baseline.json';shutil.copy2(p,backup/'baseline.json');data=o.read(p);current=o.collect(datetime.now(o.ZONE))
data.setdefault('source_revisions_before_overnight',[]).append({'at':current['at'],'reason':'Synchronize tested article-budget isolation regression fixture with recovery mapping; test source only, no service reload or runtime changes','prior_baseline':str(backup/'baseline.json'),'old_fingerprint':data.get('source_fingerprint'),'new_fingerprint':current['source_fingerprint']})
data.update(source_fingerprint=current['source_fingerprint']);p.write_text(json.dumps(data,ensure_ascii=False,indent=2));print(json.dumps({'fixture_updated':True,'service_reloaded':False}))
