"""Live summaries for the new account1 batch and the resumed account2 batch."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import json,sqlite3,subprocess,time
from pathlib import Path
base=Path('/home/user/redroid-doubao/batches')
for service,batch in [('redroid-geo-products.service','geo-products-21x5-account1-20261014'),('redroid-geo-products-account2.service','geo-products-21x5-account2-relogin-20261013')]:
 root=base/batch
 active=subprocess.run(['systemctl','is-active',service],capture_output=True,text=True).stdout.strip()
 db=sqlite3.connect((root/'tasks.sqlite').as_uri()+'?mode=ro',uri=True)
 counts=dict(db.execute('select state,count(*) from tasks group by state'))
 health=json.loads((root/'bridge_health.json').read_text()) if (root/'bridge_health.json').exists() else {}
 receipts=[]
 for p in sorted((root/'receipts').glob('*.json'),key=lambda p:p.stat().st_mtime):
  r=json.loads(p.read_text());a=r['analysis']
  assert a['answer_present'] and a['source_capture_complete'] and a['source_count']==a['expected_source_count']
  receipts.append(a)
 clicks=[r[0] for r in db.execute("select time from events where event='send_click_intent_committed' order by time")]
 print(json.dumps({'batch':batch,'service':active,'tasks':counts,'processed_receipts':len(receipts),'minimum_send_interval':min([b-a for a,b in zip(clicks,clicks[1:])],default=None),'health_status':health.get('status'),'health_age_seconds':time.time()-health.get('time',time.time()),'last_receipt':receipts[-1] if receipts else None},ensure_ascii=False))
old=json.loads((base/'geo-products-21x5-20261013/bridge_health.json').read_text())
assert old['captured']==old['geo_processed']==105 and old['status']=='complete'
print('Account1 historical batch remains complete: 105/105')
