"""One-time engine fix and explicit reprocessing of this known, fully settled test."""
import json,shutil,sqlite3,subprocess,sys,time,zipfile
from pathlib import Path
base=Path('/opt/monitor/geo-content');backup=Path('/opt/monitor/geo-capture/maintenance/20261020-whitening-product-engine')
ids=['creation-1792475798-478ca528','creation-1792475798-7d2fc250'];roots=[base/'runtime/runs'/v for v in ids]
def assert_settled():
 for root in roots:
  active=json.loads((root/'api/active.json').read_text()) if (root/'api/active.json').exists() else {}
  assert active.get('state') not in ('REQUESTING','REQUEST_UNKNOWN'),str(root)
  for file in (root/'queue').glob('*/ticket.json'):
   assert json.loads(file.read_text())['state'] not in ('claimed','pending'),str(file)
 with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
  assert db.execute("select count(*) from costs c join studio_cost_scopes s on s.id=c.id where s.scope=? and c.charged is null",('plan-6334cde812bd49549df6efd87a51e3b3',)).fetchone()[0]==0
assert_settled();backup.mkdir(parents=True,mode=0o700,exist_ok=False)
subprocess.run(['systemctl','stop','geo-content-worker.service'],check=True)
try:
 assert_settled()
 for file in (base/'runtime/runs').glob('*/job.json'):
  if file.parent in roots:continue
  control=json.loads((file.parent/'control.json').read_text())
  day=json.loads(file.read_text())['date'];status=json.loads((file.parent/'days'/day/'day.json').read_text()).get('status') if (file.parent/'days'/day/'day.json').exists() else None
  assert control.get('paused') or status=='complete','Unexpected live unrelated writing job'
 with zipfile.ZipFile('/tmp/engine-product-patch.zip') as z:
  for name in z.namelist():
   if not name.startswith('geo_source_cards/'):continue
   target=base/'engine'/name
   if target.exists():shutil.copy2(target,backup/(target.name+'.before'))
   data=z.read(name);compile(data,str(target),'exec');temp=target.with_suffix('.product-new');temp.write_bytes(data);temp.replace(target)
 for root in roots:
  old=backup/root.name;old.mkdir()
  for receipt in (root/'approved').glob('*/*/*/receipt.json'):
   item=json.loads(receipt.read_text());rev=root/'revocations/processing-v1.json';rev.parent.mkdir(exist_ok=True)
   rev.write_text(json.dumps({'word_sha256':item['word_sha256'],'reason':'旧洗发水限定识别器把面霜盘点错分科普；保留原稿和回执，仅撤回本次测试错误分类成稿','at':time.time()},ensure_ascii=False))
  for name in ('queue','api'):
   if (root/name).exists():shutil.move(str(root/name),old/name)
  shutil.move(str(root/'days/2026-10-20'),old/'day')
  (old/'reason.json').write_text(json.dumps({'reason':'product_category_parser_fix','no_unknown_or_unsettled_calls':True,'keep_platform_observations':True,'keep_paid_cost_ledger':True}))
 sys.path[:0]=[str(base),str(base/'engine')]
 from geo_source_cards.daily_editorial import prepare_day
 from geo_source_cards.runtime import atomic_json
 for root in roots:
  p=prepare_day(root,root/'geo_articles.jsonl',root/'product.json','2026-10-20',max_per_category=1)
  j=json.loads((root/'job.json').read_text());j['prepared']=p;j['processing_revision']='task-product-identity-v1';atomic_json(root/'job.json',j)
 print(json.dumps({'deployed':True,'reprocessed_test_jobs':ids,'platform_questions_not_resent':True,'old_approval_revoked_with_original_preserved':True,'backup':str(backup)}),flush=True)
finally:subprocess.run(['systemctl','start','geo-content-worker.service'],check=True)
