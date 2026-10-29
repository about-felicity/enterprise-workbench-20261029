"""Compact audit status and exact remaining-read material, without paid calls."""
import sys,json,sqlite3
from pathlib import Path
from collections import Counter
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
M=Path('/opt/monitor/geo-capture/maintenance/20261021-all-logic');A=runtime.BASE/'logic-review/20261021-all'
inventory=runtime.read(M/'inventory.json');report=runtime.read(M/'audit.json');validated=runtime.read(M/'validated-audit.json');results={r['key']:r for r in report.get('articles',[])}
for row in validated.get('articles',[]):
 if row.get('cached_validation_only'):results[row['key']]=row
items=inventory['approved_versions']+inventory['non_current_drafts'];fallback=[]
for item in items:
 row=results.get(item['key'],{})
 if row.get('state') in {'budget_blocked','known_response_error','input_or_review_incomplete'}:
  path=Path(item['folder'])/'draft.md' if item.get('folder') else Path(item['path'])
  fallback.append({**item,'audit_state':row['state'],'audit_reason':row.get('reason'),'text':path.read_text('utf-8-sig'),'product':runtime.read(item['product_path'])})
(M/'manual-review-input.json').write_text(json.dumps(fallback,ensure_ascii=False))
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 ledger=db.execute('select sum(charged),sum(case when charged is null then reserved else 0 end) from costs where date=?',('2026-10-21',)).fetchone()
unknown=[]
for p in A.rglob('api_state.json'):
 s=runtime.read(p)
 if s.get('state')=='REQUEST_UNKNOWN' or s.get('state')=='HTTP_REJECTED' and s.get('http_status',0)>=500:unknown.append(s.get('reservation'))
print(json.dumps({'requested':len(items),'recorded':len(results),'states':dict(Counter(r['state'] for r in results.values())),'finished':bool(report.get('finished_at')),'today_charged':ledger[0],'today_reserved_including_active':ledger[1],'new_unknown_request_ids':unknown,'manual_review_input_count':len(fallback)},ensure_ascii=False))
