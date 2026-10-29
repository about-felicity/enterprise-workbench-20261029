import sys,json,shutil,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation.materials import prepare,InsufficientMaterials
from creation.runtime import read
from geo_source_cards.runtime import process_lock,atomic_json
backup=Path('/opt/monitor/geo-content/maintenance/source-parser-20261026/jobs');backup.mkdir(exist_ok=True)
for ident in ['creation-1792985669-3b9f6b9b','creation-1792985671-e668c23b','creation-1792985673-e3995d45']:
 root=Path('/opt/monitor/geo-content/runtime/runs')/ident
 with process_lock(root/'api/worker.lock'):
  job=read(root/'job.json');day=root/'days'/job['date']/'day.json'
  assert job['preparation']=='insufficient' and read(day)['status']=='blocked_insufficient_sources'
  assert not read(day).get('input_sha256')
  assert not (backup/ident).exists()
  shutil.copytree(root,backup/ident)
  # Cache contains falsely successful sidebar-only bodies; retain it in backup.
  shutil.move(str(root/'private_source_analysis'),str(root/'private_source_analysis.before-parser-fix'))
  day.unlink()
  try:
   job.pop('material_shortfall',None);job['preparation']='pending'
   prepare(root,job)
   result={'status':'source_parser_repaired','message':'已重新提取真实来源正文，恢复原任务分析'}
  except InsufficientMaterials as e:
   result={'status':'blocked_insufficient_sources','message':str(e)}
   atomic_json(day,result);job.update(preparation='insufficient',material_shortfall=str(e));atomic_json(root/'job.json',job)
  atomic_json(root/'geo_worker.json',{'at':time.time(),'result':result})
  print(json.dumps({'job':ident,**result},ensure_ascii=False),flush=True)
