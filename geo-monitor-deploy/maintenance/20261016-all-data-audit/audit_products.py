"""Audit actual child-table product rows against original recommendation body."""
import json,subprocess,re
from pathlib import Path
sql="""select coalesce(json_agg(t),'[]') from (
select r.model_id,r.run_id,r.answer,p.payload product
from monitor_runs r join monitor_products p on p.model_id=r.model_id and p.run_id=r.run_id
where r.day='2026-10-16')t"""
rows=json.loads(subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',sql],text=True,timeout=60))
norm=lambda s:re.sub(r'\s+','',str(s)).lower()
errors=[];literal=0;no_evidence=0
for row in rows:
 product=row['product'];evidence=product.get('evidence','')
 if not evidence:no_evidence+=1;continue
 if norm(evidence) in norm(row['answer']):literal+=1
 elif evidence not in ('跨模型产品词表精确命中',):errors.append({k:v for k,v in row.items() if k!='answer'})
report={'product_rows':len(rows),'literal_evidence_verified':literal,'missing_evidence':no_evidence,'unmatched_evidence':errors}
Path('/opt/monitor/geo-capture/maintenance/20261016-all-data-audit/product-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
