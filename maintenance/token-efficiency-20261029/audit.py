import json,sqlite3,collections,hashlib
from pathlib import Path
root=Path('/opt/monitor/geo-content');out={'files':{},'stages':{},'largest':[]}
for n in ['deepseek_api.py','rewrite_v2/common.py','rewrite_v2/full_writer.py','rewrite_v2/integration.py','rewrite_v2/material_manager.py','rewrite_v2/structure_parser.py']:
 p=root/'engine/geo_source_cards'/n;out['files'][n]=hashlib.sha256(p.read_bytes()).hexdigest()
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 out['ledger_schema']=db.execute('pragma table_info(costs)').fetchall()
for jp in (root/'runtime/runs').glob('creation-*/job.json'):
 j=json.loads(jp.read_text())
 if j.get('date')!='2026-10-29':continue
 for p in jp.parent.rglob('response.json'):
  try:d=json.loads(p.read_text())
  except Exception:continue
  usage=d.get('usage')
  if not usage:continue
  req=p.parent/'request.json';rq=json.loads(req.read_text()) if req.exists() else {};state=p.parent/'api_state.json';st=json.loads(state.read_text()) if state.exists() else {}
  stage=st.get('stage') or next((n for n in ['writer','research','taxonomy','review'] if n in str(p)), 'other')
  agg=out['stages'].setdefault(stage,{'calls':0,'prompt_tokens':0,'completion_tokens':0,'prompt_cache_hit_tokens':0,'prompt_cache_miss_tokens':0});agg['calls']+=1
  for k in list(agg)[1:]:agg[k]+=usage.get(k,0) or 0
  out['largest'].append({'path':str(p.relative_to(root)),'usage':usage,'request_chars':len(json.dumps(rq,ensure_ascii=False)),'request_keys':list(rq),'state_keys':list(st)})
out['largest']=sorted(out['largest'],key=lambda r:r['usage'].get('total_tokens',0),reverse=True)[:6]
Path('/tmp/token-efficiency-audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False,indent=2))
