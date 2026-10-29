"""Decode remaining mini-program controls and preserve all prior raw provenance."""
import copy
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,'/app')
from monitor_core import database as db
from monitor_core.native_text import decode_native_text,clean_native_text
from monitor_core.product_analysis import merge_explicit_owned_products
import save_doubao_refs as saver
root=Path('/app/geo-capture/maintenance/20261017-yuanbao-text-audit')
changed=0;requeued=[];scopes=set()
backup=root/('database-before-mini-program-fix-'+str(int(time.time()))+'.jsonl')
with backup.open('x',encoding='utf-8') as out,db.connection() as conn:
 backup.chmod(0o600)
 rows=conn.execute("SELECT * FROM monitor_runs WHERE model_id='yuanbao' AND (answer LIKE '%@replace%' OR answer LIKE '%@stylelink%' OR answer LIKE '%@mark_%') FOR UPDATE").fetchall()
 for row in rows:
  payload=dict(row['payload'] or {})
  raw=payload.get('answer_raw') or row['answer']
  clean,report=decode_native_text(raw)
  assert report.get('unhandled_controls',0)==0,'Unknown native markup must remain flagged for explicit review'
  products=copy.deepcopy(payload.get('products') or [])
  child_products=conn.execute('SELECT * FROM monitor_products WHERE model_id=%s AND run_id=%s',('yuanbao',row['run_id'])).fetchall()
  child_brands=conn.execute('SELECT * FROM monitor_brands WHERE model_id=%s AND run_id=%s',('yuanbao',row['run_id'])).fetchall()
  out.write(json.dumps({'run':dict(row),'products':[dict(x) for x in child_products],'brands':[dict(x) for x in child_brands]},ensure_ascii=False,default=str)+'\n');out.flush()
  for product in products:
   for key in ['brand','brand_name','product','product_name','name','evidence']:
    if isinstance(product.get(key),str):product[key]=clean_native_text(product[key])
  if payload.get('product_review_status')=='ai_verified':
   try:
    products=merge_explicit_owned_products(clean,row['question'],products)
    saver.validate_grounded_ai_products(clean,products)
   except ValueError:
    products=[];payload.update(product_review_status='ai_pending',product_extraction_method='pending_native_text_repair',product_review_reason='mini_program_markup_grounding_recheck');requeued.append(row['run_id'])
  payload.update(answer=clean,answer_raw=raw,native_text_normalization=report,products=products)
  brands=sorted({p.get('brand_name') or p.get('brand') or '' for p in products}-{''})
  conn.execute('DELETE FROM monitor_products WHERE model_id=%s AND run_id=%s',('yuanbao',row['run_id']))
  conn.execute('DELETE FROM monitor_brands WHERE model_id=%s AND run_id=%s',('yuanbao',row['run_id']))
  with conn.cursor() as cur:db._write_children(cur,'yuanbao',row['run_id'],[],brands,products)
  conn.execute('UPDATE monitor_runs SET answer=%s,payload=%s,record_hash=%s,updated_at=now() WHERE model_id=%s AND run_id=%s',(clean,db.Jsonb(payload),db._json_hash(payload),'yuanbao',row['run_id']))
  scopes.update(db._scope_keys('yuanbao',row['day']));changed+=1
 # These failed under the superseded decoder/avoidance rule. A single fresh
 # review after the proven algorithm fix is intentional, not an unbounded retry.
 reset=conn.execute("UPDATE monitor_runs SET product_ai_next_retry_at=NULL,product_ai_retry_count=0 WHERE payload->>'product_extraction_method'='pending_native_text_repair' AND payload->>'product_review_status'='ai_pending' RETURNING run_id").fetchall()
 with conn.cursor() as cur:db._bump_versions(cur,scopes)
 conn.commit()
report={'mini_program_projection_rows':changed,'new_grounding_rechecks':requeued,'retry_after_algorithm_fix':len(reset),'backup':str(backup)}
(root/'mini-program-repair.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
