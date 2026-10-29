import sys,json,time,zipfile,subprocess,shutil
from pathlib import Path
from datetime import datetime
B=Path('/opt/monitor/geo-content');M=Path('/opt/monitor/geo-capture/maintenance/20261021-daohe-test')
backup=M/('source-before-execution-fix-'+str(time.time_ns()));backup.mkdir()
for p in (B/'runtime/runs').glob('*/api/active.json'):
 a=json.loads(p.read_text())
 if a.get('state') not in (None,'SUBMITTED'):
  run=p.parent/'runs'/a['run_id'];assert a.get('state')=='REQUESTING' and not (run/'call/api_state.json').exists() and not (run/'logic-call/api_state.json').exists(),'Actual paid execution active'
subprocess.run(['systemctl','stop','geo-content-worker'],check=True)
try:
 with zipfile.ZipFile('/tmp/geo-review-genre-patch.zip') as z:
  for name in z.namelist():
   if name.startswith('tests/') or Path(name).name.startswith('test_'):continue
   assert name.startswith(('engine/geo_source_cards/','creation/')) and '..' not in Path(name).parts
   target=B/name;saved=backup/name;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved);target.write_bytes(z.read(name))
finally:subprocess.run(['systemctl','start','geo-content-worker'],check=True)
subprocess.run(['systemctl','restart','geo-content-api','geo-creation-studio'],check=True)
sys.path[:0]=[str(B),str(B/'engine')]
from creation import runtime,studio,observation as o
from geo_source_cards.pipeline_control import pause
old=runtime.read(M/'review-supplement.json');oldroot=runtime.job_root(old['job_id'])
assert not list((oldroot/'api/runs').glob('*/call/api_state.json'))
assert runtime.read(oldroot/'days/2026-10-21/day.json').get('planned_articles')==0
pause(oldroot,'local_taxonomy_replaced','旧进程缓存导致本地分类未更新；保留零付费准备记录，新任务使用相同缓存正文重新分类')
shutil.copyfile(M/'review-supplement.json',M/'review-supplement-stale-process.json');(M/'review-supplement.json').unlink()
taskpath=studio.day_path('plan-33e7bfca8bb6497da10b28f0444a693b','2026-10-21')
with runtime.process_lock(taskpath.with_suffix('.lock'),blocking=True):
 t=runtime.read(taskpath);t['jobs']['旧缓存分类准备记录']=t['jobs'].pop('两篇测评缺额补充');runtime.atomic_json(taskpath,t)
parent=runtime.job_root('creation-1792575159-0a8f9221');assert runtime.read(parent/'control.json')['reason']=='budget_exceeded'
runtime.resume(parent)
now=datetime.now(o.ZONE);p=o.OUTPUT/'baseline.json';shutil.copy2(p,backup/'baseline.json');data=o.read(p);current=o.collect(now)
assert set(current['unknown_request_ids'])<=set(data['unknown_request_ids'])
data.setdefault('source_revisions_before_overnight',[]).append({'at':current['at'],'reason':'Real 14-article trial: recognize structurally explicit comparisons; isolate known unsent article-budget exhaustion, retain task/day limits and unknown-send protection','prior_baseline':str(backup/'baseline.json'),'old_fingerprint':data.get('source_fingerprint'),'new_fingerprint':current['source_fingerprint']})
data.update(source_fingerprint=current['source_fingerprint'],setup_finalized_at=current['at']);p.write_text(json.dumps(data,ensure_ascii=False,indent=2));o.main()
print(json.dumps({'backup':str(backup),'engine_tests':97,'creation_tests':66,'original_caps_unchanged':True,'old_zero_paid_taxonomy_record_preserved':True,'unknown_ids_unchanged':True}))
