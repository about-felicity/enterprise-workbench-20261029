"""Backed-up, idempotent projection repair. Never alters native queues or raw bodies."""
import collections
import copy
import json
from pathlib import Path
import sys
import time

sys.path.insert(0,'/app')
from monitor_core import database as db
from monitor_core.native_text import decode_native_text,clean_native_text
from monitor_core.product_analysis import merge_explicit_owned_products,compact,equivalent_name
import save_doubao_refs as saver

APPLY='--apply' in sys.argv
ROOT=Path('/app/geo-capture/maintenance/20261017-yuanbao-text-audit')
ROOT.mkdir(parents=True,exist_ok=True)

def review_products(row,clean):
    original=row['payload'] or {}
    products=copy.deepcopy(original.get('products') or [])
    for product in products:
        for key in ['brand','brand_name','product','product_name','name','evidence']:
            if isinstance(product.get(key),str):product[key]=clean_native_text(product[key])
    reason=''
    if row['model_id']=='yuanbao' and str(row['day'])=='2026-10-17':reason='today_native_text_reanalysis'
    if original.get('product_review_status') in {'ai_pending','pending'}:reason=reason or 'retry_after_native_text_repair'
    try:
        saver.validate_grounded_ai_products(clean,products)
        filtered=saver.filter_products_for_question(row['question'],products)
        if len(filtered)!=len(products):reason=reason or 'category_or_instruction_filtered'
        products=merge_explicit_owned_products(clean,row['question'],filtered)
        saver.validate_grounded_ai_products(clean,products)
        # Do not trust old paid results that missed now-readable product headings.
        headings=saver.filter_products_for_question(row['question'],saver.extract_structured_product_headings(clean,row['question']))
        for heading in headings:
            name=compact(heading.get('product_name'))
            if name and not any(equivalent_name(name,compact(p.get('product_name'))) for p in products):
                reason=reason or 'readable_heading_missing_from_old_analysis'
                break
    except ValueError as error:
        reason=reason or 'old_analysis_not_grounded_after_text_repair'
    return products,reason

with db.connection() as conn:
    rows=conn.execute("SELECT * FROM monitor_runs WHERE model_id='yuanbao' AND (answer LIKE '%@mark_underline=%' OR answer LIKE '%@replace=%' OR answer LIKE '%@replace_goods&%') ORDER BY day,sequence_no").fetchall()

plan=[];reasons=collections.Counter();days=collections.Counter();skipped=[]
for row in rows:
    clean,normalization=decode_native_text(row['answer'])
    if not normalization:continue
    if not clean.strip():skipped.append(row['run_id']);continue
    products,reason=review_products(row,clean)
    item={'model_id':row['model_id'],'run_id':row['run_id'],'day':str(row['day']),
          'raw_answer':row['answer'],'clean_answer':clean,'normalization':normalization,
          'products':products,'reanalysis_reason':reason}
    plan.append(item);days[item['day']]+=1
    if reason:reasons[reason]+=1

# Other models are audited for the same proven advice-as-product defect. Their
# prose and unrelated product results remain untouched.
with db.connection() as conn:
    other=conn.execute("SELECT model_id,run_id,day,payload FROM monitor_runs WHERE day='2026-10-17' AND model_id<>'yuanbao'").fetchall()
bad_other=[]
for row in other:
    bad=[p for p in (row['payload'] or {}).get('products',[]) if saver._evidence_negates_product(p.get('evidence'),p.get('product_name'))]
    if bad:bad_other.append({'model_id':row['model_id'],'run_id':row['run_id'],'products':bad})

report={'apply':APPLY,'projection_rows':len(plan),'days':days,'reanalysis':reasons,
        'total_reanalysis':sum(reasons.values()),'empty_text_skipped':skipped,
        'other_models_proven_negative_products':len(bad_other),'other_negative_examples':bad_other[:10]}
(ROOT/'repair-plan.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False),flush=True)
if not APPLY:raise SystemExit(0)
assert not skipped,'Inspect rich-media-only records explicitly before applying'
backup=ROOT/('database-before-'+str(int(time.time()))+'.jsonl')
scopes=set()
with backup.open('x',encoding='utf-8') as stream,db.connection() as conn:
    backup.chmod(0o600)
    for item in plan:
        row=conn.execute('SELECT * FROM monitor_runs WHERE model_id=%s AND run_id=%s FOR UPDATE',(item['model_id'],item['run_id'])).fetchone()
        assert row['answer']==item['raw_answer'],'Projection changed since plan; inspect instead of overwriting'
        products=conn.execute('SELECT * FROM monitor_products WHERE model_id=%s AND run_id=%s',(item['model_id'],item['run_id'])).fetchall()
        brands=conn.execute('SELECT * FROM monitor_brands WHERE model_id=%s AND run_id=%s',(item['model_id'],item['run_id'])).fetchall()
        stream.write(json.dumps({'run':dict(row),'products':[dict(x) for x in products],'brands':[dict(x) for x in brands]},ensure_ascii=False,default=str)+'\n');stream.flush()
        payload=dict(row['payload'] or {})
        payload.update(answer=item['clean_answer'],answer_raw=item['raw_answer'],native_text_normalization=item['normalization'])
        if item['reanalysis_reason']:
            normalized=[]
            payload.update(products=[],product_review_status='ai_pending',product_analysis_model='',
                           product_extraction_method='pending_native_text_repair',product_review_reason=item['reanalysis_reason'])
        else:normalized=item['products'];payload['products']=normalized
        clean_brands=sorted({str(x.get('brand_name') or x.get('brand') or '').strip() for x in normalized}-{''})
        conn.execute('DELETE FROM monitor_products WHERE model_id=%s AND run_id=%s',(item['model_id'],item['run_id']))
        conn.execute('DELETE FROM monitor_brands WHERE model_id=%s AND run_id=%s',(item['model_id'],item['run_id']))
        with conn.cursor() as cur:db._write_children(cur,item['model_id'],item['run_id'],[],clean_brands,normalized)
        conn.execute('UPDATE monitor_runs SET answer=%s,payload=%s,record_hash=%s,product_ai_retry_count=0,product_ai_next_retry_at=NULL,updated_at=now() WHERE model_id=%s AND run_id=%s',
            (item['clean_answer'],db.Jsonb(payload),db._json_hash(payload),item['model_id'],item['run_id']))
        # Only existing enrichment fields change; original web_body, capture_result,
        # source list, request ID and native snapshot remain verbatim.
        conn.execute("UPDATE monitor_ingest_events SET record=jsonb_set(jsonb_set(record,'{products}',%s::jsonb,true),'{product_review_status}',%s::jsonb,true) WHERE model_id=%s AND run_id=%s",
            (json.dumps(normalized,ensure_ascii=False),json.dumps(payload.get('product_review_status','')),item['model_id'],item['run_id']))
        scopes.update(db._scope_keys(item['model_id'],item['day']))
    with conn.cursor() as cur:db._bump_versions(cur,scopes)
    conn.commit()
for item in bad_other:
    db.reset_product_analysis(item['model_id'],item['run_id'],'proven_negative_advice_is_not_a_recommended_product')
report.update(backup=str(backup),applied=len(plan),other_requeued=len(bad_other))
(ROOT/'repair-applied.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({'applied':len(plan),'reanalysis':sum(reasons.values()),'other_requeued':len(bad_other),'backup':str(backup)},ensure_ascii=False))
