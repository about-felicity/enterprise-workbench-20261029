"""End-to-end current-attempt and GEO acceptance for both resumed batches."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import json,sqlite3,subprocess,time,hashlib,os
from pathlib import Path
from active_database_accounts import current_uid
os.umask(0o077)
base=Path('/home/user/redroid-doubao');reports=[]
for c,batch,service,first_recovered in [('doubao-hpe14-13-test','geo-products-21x5-account1-20261014','redroid-geo-products.service',14),('doubao-hpe14-account2','geo-products-21x5-account2-relogin-20261013','redroid-geo-products-account2.service',68)]:
 root=base/'batches'/batch
 q=sqlite3.connect((root/'tasks.sqlite').as_uri()+'?mode=ro',uri=True);q.row_factory=sqlite3.Row
 selected=[]
 for t in q.execute("select * from tasks where state='completed' order by ordinal"):
  t=dict(t);r=json.loads(t['result_json']);rid=hashlib.sha256(('redroid-doubao:'+t['task_id']+':'+r['request_id']).encode()).hexdigest()
  p=root/'receipts'/(rid+'.json')
  if p.exists():selected.append((t,r,json.loads(p.read_text())))
 sql="SELECT jsonb_build_object('request_id',record->>'native_request_id','answerText',record->'answerText','items',record->'items','citations',record->'citations','search_queries',record->'search_queries') FROM monitor_ingest_events WHERE source_device='"+c+"' AND record->>'batch_id'='"+batch+"';"
 stored=[json.loads(l) for l in subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-At','-c',sql],text=True).splitlines() if l.strip()]
 info=json.loads(subprocess.check_output(['docker','inspect',c]))[0];uid=current_uid(c)
 mount=Path(next(m['Source'] for m in info['Mounts'] if m['Destination']=='/data'))
 native=sqlite3.connect((mount/'data/com.larus.nova/databases'/('im_database_'+uid)).as_uri()+'?mode=ro',uri=True);native.row_factory=sqlite3.Row
 checks=[]
 for t,r,receipt in selected:
  records=[s for s in stored if s['request_id']==r['request_id']];assert len(records)==1
  s=records[0]
  assert s['answerText']==r['body_markdown'] and s['items']==r['sources'] and s['citations']==r['citations'] and s['search_queries']==r['search_queries']
  a=receipt['analysis'];assert a['answer_present'] and a['source_capture_complete'] and a['source_count']==a['expected_source_count']==len(r['sources'])
  request=native.execute('select message_id,server_index from im_message where local_message_id=?',(r['request_id'],)).fetchone()
  assert request and request['message_id'] and request['server_index']>0
  requests=[]
  for row in native.execute('select local_message_id,content,fts_content from im_message where user_type=1 and (fts_content=? or instr(content,?)>0)',(t['wire_question'],t['task_id'])):
   blocks=json.loads(row['content']);text='\n\n'.join(b['content']['text_block']['text'] for b in blocks if 'text_block' in b['content'])
   if row['fts_content']==t['wire_question'] or text==t['wire_question']:requests.append(row['local_message_id'])
  assert requests==[r['request_id']]
  checks.append({'ordinal':t['ordinal'],'body_length':len(r['body_markdown']),'source_count':len(r['sources']),'geo_exact':True,'current_attempt_requests':1})
 recovered=[r for r in checks if r['ordinal']>=first_recovered]
 assert len(recovered)>=3 and [r['ordinal'] for r in recovered]==list(range(first_recovered,first_recovered+len(recovered)))
 since=q.execute("select min(time) from events where event in ('capture_retry_scheduled','operator_storage_recovery_scheduled')").fetchone()[0]
 clicks=[r[0] for r in q.execute("select time from events where event='send_click_intent_committed' and time>=? order by time",(since,))]
 minimum=min([b-a for a,b in zip(clicks,clicks[1:])]);assert minimum>=45
 health=json.loads((root/'bridge_health.json').read_text())
 actual=subprocess.run(['systemctl','is-active',service],capture_output=True,text=True).stdout.strip()
 if health['status']=='complete':
  assert len(checks)==105 and actual in ('inactive','active')
 else:
  assert time.time()-health['time']<45 and health['status'].startswith('running') and actual=='active'
 assert 'unicode61' in native.execute("select sql from sqlite_master where name='fts_im_conversation'").fetchone()[0]
 assert native.execute("select count(*) from sqlite_master where type='trigger' and tbl_name='im_conversation'").fetchone()[0]==4
 pid=subprocess.check_output(['docker','exec',c,'pidof','com.larus.nova'],text=True).strip()
 maps=subprocess.check_output(['docker','exec',c,'cat','/proc/'+pid+'/maps'],text=True)
 groups={}
 for line in maps.splitlines():
  if 'FlowIMSDKconversation-local-manager' in line:
   parts=line.split();p=Path(parts[-1]);assert p.suffix in ('.blk','.chk')
   groups.setdefault(str(p.parent),{})[p.suffix]=parts[4]
 assert groups and all(set(g)=={'.blk','.chk'} and g['.blk']!=g['.chk'] for g in groups.values())
 reports.append({'container':c,'batch':batch,'geo_processed_verified':len(checks),'consecutive_recovered':len(recovered),'minimum_new_send_interval':minimum,'failed_attempts_preserved':q.execute('select count(*) from failed_attempts').fetchone()[0],'cache_mapping_collision':False,'health':health,'verified_recovered_tasks':recovered})
old=json.loads((base/'batches/geo-products-21x5-20261013/bridge_health.json').read_text());assert old['captured']==old['geo_processed']==105 and old['status']=='complete'
for c,serial,port in [('doubao-hpe14-13-test','127.0.0.1:5557','27044'),('doubao-hpe14-account2','127.0.0.1:5558','27043')]:
 pid=subprocess.run(['docker','exec',c,'pidof','frida-server'],capture_output=True,text=True).stdout.strip()
 if pid:
  assert pid.isdigit();command=subprocess.check_output(['docker','exec',c,'cat','/proc/'+pid+'/cmdline']);assert command.startswith(b'/data/local/tmp/frida-server\0')
  subprocess.run(['docker','exec',c,'kill','-TERM',pid],check=True)
 subprocess.run([str(base/'linux-tools/platform-tools/adb'),'-s',serial,'forward','--remove','tcp:'+port],capture_output=True)
result={'verified_at':time.time(),'historical_account1_processed':105,'reports':reports,'diagnostic_listeners_stopped':True}
p=base/'dual-pause-fix-acceptance-20261014.json';p.write_text(json.dumps(result,ensure_ascii=False,indent=2));p.chmod(0o644)
print(json.dumps(result,ensure_ascii=False,indent=2))
