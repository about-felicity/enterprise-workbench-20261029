import collections
import json
from pathlib import Path
import re
import sys
sys.path.insert(0,'/app')
from monitor_core.database import connection
from monitor_core.native_text import decode_native_text
import save_doubao_refs as saver
ROOT=Path('/app/geo-capture/maintenance/20261017-yuanbao-text-audit')
backup=sorted(ROOT.glob('database-before-[0-9]*.jsonl'))[0]
original=[json.loads(x)['run'] for x in backup.read_text().splitlines()]
ids=[r['run_id'] for r in original]
assert len(ids)==632 and len(set(ids))==632
with connection() as conn:
 rows=conn.execute("SELECT * FROM monitor_runs WHERE model_id='yuanbao' AND run_id=ANY(%s::text[])",(ids,)).fetchall()
 records=conn.execute("SELECT run_id,record FROM monitor_ingest_events WHERE model_id='yuanbao' AND run_id=ANY(%s::text[])",(ids,)).fetchall()
 all_today=conn.execute("SELECT model_id,run_id,question,answer,payload FROM monitor_runs WHERE day='2026-10-17'").fetchall()
 source_counts=conn.execute("SELECT run_id,count(*) n FROM monitor_sources WHERE model_id='yuanbao' AND run_id=ANY(%s::text[]) GROUP BY run_id",(ids,)).fetchall()
keyed={r['run_id']:r for r in rows};source_counts={r['run_id']:r['n'] for r in source_counts}
raw_verified=0;source_expected_matches=0
for before in original:
 after=keyed[before['run_id']];payload=after['payload']
 expected,report=decode_native_text(before['answer'])
 assert after['answer']==expected
 assert payload['answer_raw']==before['answer']
 assert not report.get('unhandled_controls')
 for k in ['model_id','run_id','sequence_no','question','day','serial']:
  assert str(after[k])==str(before[k]),(before['run_id'],k)
 assert re.findall(r'\[citation:\d+\]',before['answer'])==re.findall(r'\[citation:\d+\]',after['answer'])
 expected_count=(before.get('payload') or {}).get('expected_source_count')
 if expected_count is not None:
  assert source_counts.get(before['run_id'],0)==expected_count,(before['run_id'],source_counts.get(before['run_id']),expected_count)
  source_expected_matches+=1
for event in records:
 original_body=event['record'].get('web_body') or event['record'].get('reply') or event['record'].get('answer') or ''
 assert original_body==keyed[event['run_id']]['payload']['answer_raw']
 raw_verified+=1
before_today=json.loads((ROOT/'today-before.json').read_text())
today_keyed={(r['model_id'],r['run_id']):r for r in all_today}
other_unchanged=0
for row in before_today:
 if row['model_id']!='yuanbao':
  assert today_keyed[(row['model_id'],row['run_id'])]['answer']==row['answer'];other_unchanged+=1
bad=[]
for row in all_today:
 for product in row['payload'].get('products') or []:
  if saver._evidence_negates_product(product.get('evidence'),product.get('product_name')):
   bad.append({'model':row['model_id'],'run':row['run_id'],'product':product.get('product_name')})
assert not bad,bad
pending=[{'run_id':r['run_id'],'day':str(r['day'])} for r in rows if r['payload'].get('product_review_status')=='ai_pending']
assert not pending,pending
report={'repaired_rows':len(rows),'original_raw_ingest_bodies_verified':raw_verified,
        'source_counts_preserved':source_expected_matches,'ids_dates_devices_sequences_preserved':True,
        'citation_markers_preserved':True,'other_today_bodies_unchanged':other_unchanged,
        'all_affected_product_reviews_complete':True,'negative_advice_products_remaining':0}
(ROOT/'final-database-qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
