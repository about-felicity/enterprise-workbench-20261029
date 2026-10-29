import json,subprocess,urllib.request,time,unicodedata,re,hashlib
from pathlib import Path
ROOT=Path('/opt/monitor/geo-capture/maintenance/20261016-all-data-audit')
def query(sql):
 return json.loads(subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',"select coalesce(json_agg(t),'[]') from ("+sql+")t"],text=True))
pending=query("select model_id,run_id,question,product_ai_retry_count,product_ai_next_retry_at,updated_at,payload-'capture_result'-'web_body'-'sources'-'source_entries'-'citations'-'native_result'-'answerText'-'items' metadata from monitor_runs where day='2026-10-16' and payload->>'product_review_status'='ai_pending'")
with urllib.request.urlopen('http://127.0.0.1:8765/api/analytics?view=overview&date=2026-10-16',timeout=120) as response:data=json.load(response)
(ROOT/'analytics.json').write_text(json.dumps(data,ensure_ascii=False))
rows=[r for r in data['owned_product_daily'] if r['date']=='2026-10-16']
errors=[];counts={};cells=[]
for row in rows:
 for model,s in row['models'].items():
  pieces=s.get('surfaces') or {model:s}
  for name,value in pieces.items():
   cells.append({'question':row['question'],'product':row['product'],'model':model,'surface':name,**value})
   if value['recommendation_runs']>value['eligible_runs']:errors.append({'kind':'recommendations_exceed_denominator','cell':cells[-1]})
   if value['state']=='not_listed' and value.get('pending_runs',0):errors.append({'kind':'pending_marked_not_listed','cell':cells[-1]})
   if value['eligible_runs']==0 and value['state'] not in ('not_collected',):errors.append({'kind':'empty_sample_wrong_state','cell':cells[-1]})
   counts[name]=counts.get(name,0)+1
raw=query("select r.model_id,r.question,r.payload->>'capture_mode' mode,r.answer,r.payload->>'product_review_status' review from monitor_runs r where day='2026-10-16' and status='success' and coalesce(r.payload->>'body_capture_complete','true')='true'")
def key(answer):return re.sub(r'[\u200b-\u200f\u202a-\u202e\u2060\ufeff\s]+','',unicodedata.normalize('NFKC',answer))
for cell in cells:
 if cell['model']=='quark':continue
 eligible=[r for r in raw if r['model_id']==cell['model'] and r['question']==cell['question'] and (cell['model']!='wenxin' or (r['mode']=='baidu_search_ai')==(cell['surface']=='baidu_card'))]
 if cell['surface']=='baidu_card':
  expected_raw=len(eligible);eligible=list({key(r['answer']):r for r in sorted(eligible,key=lambda r:r['review']=='ai_verified')}.values())
  if cell.get('raw_eligible_runs')!=expected_raw:errors.append({'kind':'baidu_raw_denominator_mismatch','question':cell['question']})
 if cell['eligible_runs']!=len(eligible):errors.append({'kind':'denominator_mismatch','question':cell['question'],'surface':cell['surface'],'expected':len(eligible),'actual':cell['eligible_runs']})
 expected_rate=round(cell['recommendation_runs']*100/cell['eligible_runs'],2) if cell['eligible_runs'] else 0
 if cell['recommendation_rate']!=expected_rate:errors.append({'kind':'rate_mismatch','cell':cell})
log=Path('/opt/monitor/runtime/remote_product_ai_worker.log')
rejections={};log_events={}
for line in log.read_text().splitlines():
 if not line.startswith('2026-10-16 '):continue
 try:entry=json.loads(line[line.index('{'):])
 except (ValueError,TypeError):continue
 status=entry.get('status','unknown');log_events[status]=log_events.get(status,0)+1
 for reason in entry.get('rejected',{}).values():
  category=reason.split(':',1)[0];rejections[category]=rejections.get(category,0)+1
report={'at':time.time(),'products':len(rows),'questions':len(set(r['question'] for r in rows)),'cells_per_model':counts,'errors':errors,'pending_reviews':pending,'cells':cells,'top_keys':list(data),'worker_log_today':log_events,'rejected_product_reasons_today':rejections,'independent_denominator_and_rate_check':True}
(ROOT/'analytics-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in report.items() if k not in ('cells','pending_reviews')},ensure_ascii=False))
print('pending_errors',json.dumps([{'model':r['model_id'],'question':r['question'],'retry':r['product_ai_retry_count'],'next':r['product_ai_next_retry_at'],'metadata':{k:v for k,v in r['metadata'].items() if any(token in k for token in ('error','retry','review','analysis'))}} for r in pending],ensure_ascii=False))
