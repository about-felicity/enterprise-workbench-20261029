
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import json, sqlite3, subprocess, time
from pathlib import Path
base=Path('/home/user/redroid-doubao/batches')
for batch in ('geo-products-21x5-20261013','geo-products-21x5-account2-relogin-20261013'):
    p=base/batch
    health=json.loads((p/'bridge_health.json').read_text())
    service='redroid-geo-products-account2.service' if 'account2' in batch else 'redroid-geo-products.service'
    actual=subprocess.run(['systemctl','is-active',service],capture_output=True,text=True).stdout.strip()
    health['service_state']=actual
    health['snapshot_age_seconds']=time.time()-health.get('time',0)
    if health.get('status','').startswith('running'):
        if actual!='active':
            health['recorded_status']=health['status'];health['status']='stopped'
        elif time.time()>health.get('heartbeat_expires_at',health.get('time',0)+45):
            health['recorded_status']=health['status'];health['status']='stale'
    print(json.dumps(health,ensure_ascii=False,indent=2))
    c=sqlite3.connect('file:'+str(p/'tasks.sqlite')+'?mode=ro',uri=True)
    times=[r[0] for r in c.execute("select time from events where event='send_click_intent_committed' order by time")]
    print('minimum_send_interval',min([b-a for a,b in zip(times,times[1:])], default=None))
    receipts=list((p/'receipts').glob('*.json'))
    if receipts:
        r=json.loads(receipts[-1].read_text())
        print(json.dumps({'device':r['source_device'],'question':r['question'],'analysis':r['analysis'],'storage':r['save']['storage']},ensure_ascii=False))
sql="SELECT source_device,COALESCE(NULLIF(record->>'status',''),CASE WHEN length(COALESCE(record->>'answerText',''))>0 AND record->>'complete'='true' THEN 'captured' ELSE 'unknown' END),length(record->>'answerText'),jsonb_array_length(record->'items') FROM monitor_ingest_events WHERE model_id='doubao' AND source_device IN ('doubao-hpe14-13-test','doubao-hpe14-account2') ORDER BY stored_at DESC LIMIT 4;"
subprocess.run(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-At','-c',sql],check=True)
