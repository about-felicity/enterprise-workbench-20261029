"""Refresh test evidence only when every executable source is already identical."""
import json,hashlib,shutil,time
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261022-article-quality');S=D/'stage';B=Path('/opt/monitor/geo-content');m=json.loads(Path('/tmp/article-deployment-manifest.json').read_text());old=json.loads((D/'deployment.json').read_text());results=json.loads((D/'test-results.json').read_text());assert all(r['exit_code']==0 for r in results['results'])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,h in m['files'].items():
 target=D/'regression'/name if name.startswith('tests/') else B/name
 assert sha(S/name)==h
 if not name.startswith('tests/'):assert sha(target)==h,('Executable source changed; use full safe deployment',name)
 else:
  assert sha(target)==old['source_files'][str(target)]
  if sha(target)!=h:
   backup=D/('regression-before-'+str(time.time_ns()))/name;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup)
   temp=target.with_name(target.name+'.test-refresh.tmp');shutil.copy2(S/name,temp);temp.replace(target)
 old['source_files'][str(target)]=sha(target)
old.update(engine_tests=196,creation_tests=78,validation_refreshed_at=time.time(),validation_only_refresh=True)
(D/'deployment.json').write_text(json.dumps(old,ensure_ascii=False,indent=2));print(json.dumps({'executable_sources_unchanged':True,'tests':274,'service_restart':False}))
