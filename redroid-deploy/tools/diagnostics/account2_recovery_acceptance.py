"""Compare GEO stored payloads against native capture, redact output, persist acceptance."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import json,sqlite3,subprocess,time,hashlib,os
from pathlib import Path
from active_database_accounts import current_uid
os.umask(0o077)
base=Path('/home/user/redroid-doubao')
batch='geo-products-21x5-account2-relogin-20261013';root=base/'batches'/batch
q=sqlite3.connect((root/'tasks.sqlite').as_uri()+'?mode=ro',uri=True);q.row_factory=sqlite3.Row
tasks=[dict(r) for r in q.execute("select * from tasks where state='completed' order by ordinal")]
sql="SELECT jsonb_build_object('request_id',record->>'native_request_id','answerText',record->'answerText','items',record->'items','citations',record->'citations','search_queries',record->'search_queries','status',record->>'status') FROM monitor_ingest_events WHERE source_device='doubao-hpe14-account2' AND record->>'batch_id'='"+batch+"';"
raw=subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-At','-c',sql],text=True)
records=[json.loads(line) for line in raw.splitlines() if line.strip()]
info=json.loads(subprocess.check_output(['docker','inspect','doubao-hpe14-account2']))[0]
uid=current_uid('doubao-hpe14-account2')
native_path=Path(next(m['Source'] for m in info['Mounts'] if m['Destination']=='/data'))/'data/com.larus.nova/databases'/('im_database_'+uid)
native=sqlite3.connect(native_path.as_uri()+'?mode=ro',uri=True)
checks=[]
for t in tasks:
    r=json.loads(t['result_json'])
    rid=hashlib.sha256(('redroid-doubao:'+t['task_id']+':'+str(r['request_id'])).encode()).hexdigest()
    receipt=root/'receipts'/(rid+'.json')
    if not receipt.exists():continue
    stored=[v for v in records if v['request_id']==r['request_id']]
    assert len(stored)==1
    s=stored[0]
    assert s['status']=='success' and s['answerText']==r['body_markdown'] and s['items']==r['sources'] and s['citations']==r['citations'] and s['search_queries']==r['search_queries']
    a=json.loads(receipt.read_text())['analysis']
    assert a['answer_present'] and a['source_capture_complete'] and a['source_count']==a['expected_source_count']==len(r['sources'])
    request=native.execute('select message_id,server_index from im_message where local_message_id=?',(r['request_id'],)).fetchone()
    assert request and request[0] and request[1]>0
    count=0
    for row in native.execute('select fts_content,content from im_message where user_type=1 and instr(content,?)>0',(t['task_id'],)):
        blocks=json.loads(row[1]);text='\n\n'.join(b['content']['text_block']['text'] for b in blocks if 'text_block' in b['content'])
        if row[0]==t['wire_question'] or text==t['wire_question']:count+=1
    assert count==1
    checks.append({'ordinal':t['ordinal'],'body_length':len(r['body_markdown']),'source_count':len(r['sources']),'geo_content_exact':True,'geo_processed':True,'native_requests':count,'server_confirmed':True})
assert len(checks)>=3 and [c['ordinal'] for c in checks]==list(range(1,len(checks)+1))
since=q.execute("select time from events where event='operator_retry_after_fts_repair'").fetchone()[0]
clicks=[r[0] for r in q.execute("select time from events where event='send_click_intent_committed' and time>=? order by time",(since,))]
minimum=min([b-a for a,b in zip(clicks,clicks[1:])]);assert minimum>=30
health=json.loads((root/'bridge_health.json').read_text())
assert health['status']=='complete' or (time.time()-health['time']<45 and health['status'].startswith('running'))
actual=subprocess.run(['systemctl','is-active','redroid-geo-products-account2.service'],capture_output=True,text=True).stdout.strip()
assert actual=='active' or (actual=='inactive' and health['status']=='complete')
first=json.loads((base/'batches/geo-products-21x5-20261013/bridge_health.json').read_text())
assert first['status']=='complete' and first['captured']==first['geo_processed']==105
# Shut down only the temporary account2 diagnostic listener.
pid=subprocess.run(['docker','exec','doubao-hpe14-account2','pidof','frida-server'],capture_output=True,text=True).stdout.strip()
if pid:
    assert pid.isdigit()
    command=subprocess.check_output(['docker','exec','doubao-hpe14-account2','cat','/proc/'+pid+'/cmdline'])
    assert command.startswith(b'/data/local/tmp/frida-server\0')
    subprocess.run(['docker','exec','doubao-hpe14-account2','kill','-TERM',pid],check=True)
subprocess.run([str(base/'linux-tools/platform-tools/adb'),'-s','127.0.0.1:5558','forward','--remove','tcp:27043'],capture_output=True)
result={'verified_at':time.time(),'batch':batch,'service':'active','consecutive_geo_processed':len(checks),'verified_tasks':checks,'minimum_send_interval':minimum,'first_account_captured':105,'first_account_geo_processed':105,'diagnostic_listener_stopped':True,'health':health}
path=base/'account2/recovery-acceptance-20261014.json'
path.write_text(json.dumps(result,ensure_ascii=False,indent=2));path.chmod(0o600)
print(json.dumps(result,ensure_ascii=False,indent=2))
