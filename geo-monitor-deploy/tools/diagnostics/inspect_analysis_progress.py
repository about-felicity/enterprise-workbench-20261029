"""Read-only GEO analysis progress; allowlisted metrics, no credentials/bodies."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
from collections import Counter, deque
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import time

BASE=Path('/opt/monitor')
NOW=datetime.now(timezone(timedelta(hours=8)))
DAY=NOW.date().isoformat()


def query(sql):
    result=subprocess.run(['docker','exec','monitor-postgres','psql','-X','-qAt','-v','ON_ERROR_STOP=1','-U','monitor_app','-d','monitor',
        '-c',"SET statement_timeout='20s'; SET default_transaction_read_only=on; SELECT coalesce(json_agg(q),'[]') FROM ("+sql+") q"],capture_output=True,text=True,check=True,timeout=30)
    return json.loads(result.stdout.strip())


def literal(value):return "'"+value.replace("'","''")+"'"


def grouped_product(where):
    return query("SELECT model_id,coalesce(nullif(payload->>'product_review_status',''),'unset') review_status,count(*) runs,"+
        "count(*) FILTER(WHERE product_ai_retry_count>=10) retry_exhausted,"+
        "count(*) FILTER(WHERE product_ai_next_retry_at>now()) cooling_down,"+
        "min(finished_at) oldest,max(updated_at) latest_update FROM monitor_runs WHERE "+where+
        " GROUP BY model_id,review_status ORDER BY model_id,review_status")


with closing(sqlite3.connect((BASE/'geo-capture/panel/control.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
    jobs=[dict(zip(('model','batch'),row)) for row in db.execute('select s.model,s.current_batch from settings s')]
batches=','.join(literal(job['batch']) for job in jobs)
focus="e.record->>'batch_id' IN ("+batches+")"
today="day="+literal(DAY)+"::date AND status='success'"
report={'checked_at':NOW.isoformat(timespec='seconds'),'day':DAY,'current_batches':jobs}
report['today_product_analysis']=grouped_product(today)
report['global_pending_product_analysis']=grouped_product("payload->>'product_review_status'='ai_pending' AND status='success'")
report['current_batch_product_analysis']=query("WITH selected AS (SELECT DISTINCT e.record->>'batch_id' batch,r.model_id,r.run_id,r.payload->>'product_review_status' review_status,r.product_ai_retry_count FROM monitor_ingest_events e JOIN monitor_runs r ON e.model_id=r.model_id AND e.run_id=r.run_id WHERE "+focus+") SELECT batch,model_id,coalesce(review_status,'unset') review_status,count(*) unique_runs,count(*) FILTER(WHERE product_ai_retry_count>=10) retry_exhausted FROM selected GROUP BY batch,model_id,review_status ORDER BY batch,review_status")
report['recent_product_updates']=query("SELECT model_id,payload->>'product_review_status' review_status,count(*) updated_rows FROM monitor_runs WHERE updated_at>=now()-interval '60 minutes' AND status='success' GROUP BY model_id,review_status ORDER BY model_id,review_status")
report['today_products']=query("SELECT p.model_id,count(*) extracted_product_rows,count(distinct p.run_id) answers_with_products FROM monitor_products p JOIN monitor_runs r USING(model_id,run_id) WHERE r.day="+literal(DAY)+"::date GROUP BY p.model_id ORDER BY p.model_id")
report['provider_incidents']=query("SELECT incident_type,status,count(*) incidents,sum(affected_runs) affected_runs,max(last_failure_at) last_failure FROM product_analysis_incidents GROUP BY incident_type,status")
today_sources=query("SELECT DISTINCT s.model_id,s.url,s.source_type FROM monitor_sources s JOIN monitor_runs r USING(model_id,run_id) WHERE r.day="+literal(DAY)+"::date AND r.status='success' AND s.production_valid AND s.url<>''")
focus_sources=query("SELECT DISTINCT e.record->>'batch_id' batch,s.model_id,s.url,s.source_type FROM monitor_ingest_events e JOIN monitor_sources s ON e.model_id=s.model_id AND e.run_id=s.run_id WHERE "+focus+" AND s.production_valid AND s.url<>''")
urls=sorted({row['url'] for row in today_sources+focus_sources})
cache={}
with closing(sqlite3.connect((BASE/'doubao_source_content.db').as_uri()+'?mode=ro',uri=True,timeout=10)) as db:
    limit=time.monotonic()+20
    db.set_progress_handler(lambda:int(time.monotonic()>limit),100000)
    report['global_archived_bodies']=[{'status':row[0],'unique_urls':row[1],'last_fetched':row[2]} for row in db.execute('SELECT status,count(*),max(fetched_at) FROM source_content GROUP BY status')]
    for offset in range(0,len(urls),400):
        chunk=urls[offset:offset+400]
        for row in db.execute('SELECT url,status,text_length,fetched_at FROM source_content WHERE url IN ('+','.join('?' for _ in chunk)+')',chunk):
            cache[row[0]]={'status':row[1],'text_length':row[2],'fetched_at':row[3]}


def source_summary(rows,key):
    groups={}
    for row in rows:
        group=groups.setdefault(row[key],{})
        kind=row['source_type'] or 'unset'
        group.setdefault(kind,{})[row['url']]=cache.get(row['url'],{'status':'not_archived'})['status']
    return [{'group':name,'source_type':kind,'unique_urls':len(values),'statuses':dict(Counter(values.values()))} for name,g in groups.items() for kind,values in g.items()]


report['today_source_bodies_by_type']=source_summary(today_sources,'model_id')
report['current_batch_source_bodies_by_type']=source_summary(focus_sources,'batch')
lines=list(deque((BASE/'runtime/remote_product_ai_worker.log').open(encoding='utf8'),maxlen=3000))
counts=Counter();accepted=0;deferred=0;errors=Counter();last_event=None
for line in lines:
    try:
        when=datetime.strptime(line[:19],'%Y-%m-%d %H:%M:%S').replace(tzinfo=NOW.tzinfo)
        if when<NOW-timedelta(hours=1):continue
        value=json.loads(line[20:]);status=value.get('status','unknown');counts[status]+=1
        accepted+=int(value.get('accepted_items',0))+(status=='ai_verified')
        deferred+=int(value.get('rows_deferred',0))
        err=value.get('error','')
        if err:errors['timeout' if 'timed out' in err.lower() else '503' if '503' in err else 'json_parse' if 'Expecting value' in err else 'other']+=1
        last_event={'at':line[:19],'status':status}
    except (ValueError,TypeError):pass
report['product_worker_last_hour']={'events':dict(counts),'accepted_rows_logged':accepted,'deferred_attempt_rows':deferred,'errors':dict(errors),'last_event':last_event}
rate=json.loads((BASE/'runtime/remote_product_ai_rate_state.json').read_text())
report['product_worker_rate']={'configured_limit':rate.get('hourly_limit'),'reservations_last_hour':sum(1 for x in rate.get('calls',[]) if time.time()-x<3600)}
report['content_worker_last_lines']=[line.strip() for line in deque((BASE/'doubao_source_content_worker.log').open(encoding='utf8'),maxlen=50) if 'pass processed=' in line][-3:]
output=BASE/'geo-capture/analysis-progress-current.json'
output.write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
