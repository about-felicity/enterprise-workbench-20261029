import json,shutil,subprocess
from pathlib import Path
base=Path('/opt/monitor/geo-content');backup=Path('/opt/monitor/geo-capture/maintenance/20261020-whitening-product-engine')
def check_idle():
 for path in (base/'runtime/runs').glob('*/job.json'):
  root=path.parent
  if json.loads((root/'control.json').read_text()).get('paused'):continue
  job=json.loads(path.read_text());day=json.loads((root/'days'/job['date']/'day.json').read_text())
  assert day.get('status')=='complete','Do not restart active article execution'
check_idle();subprocess.run(['systemctl','stop','geo-content-worker.service'],check=True)
try:
 check_idle()
 for name,source in [('creation/article_export.py','/tmp/whitening-article-export.py'),('creation/test_article_export.py','/tmp/whitening-test-article-export.py'),('engine/geo_source_cards/genre_prompts.py','/tmp/whitening-generic-genre-prompts.py')]:
  target=base/name
  if target.exists():shutil.copy2(target,backup/(target.name+'.final-before'))
  compile(Path(source).read_text(),str(target),'exec');temp=target.with_suffix('.final-new');shutil.copy2(source,temp);temp.replace(target)
finally:subprocess.run(['systemctl','start','geo-content-worker.service'],check=True)
subprocess.run(['systemctl','restart','geo-content-api.service'],check=True)
print('Idle engine prompt and export metadata fixes deployed; paid execution and historical artifacts preserved.')
