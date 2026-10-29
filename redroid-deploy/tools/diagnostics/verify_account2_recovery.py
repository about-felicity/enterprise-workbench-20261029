"""Read-only recovery acceptance; print lengths/counts, never chat or credentials."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import json,sqlite3,subprocess,time,sys,re
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from active_database_accounts import current_uid
from unattended_worker import databases
c='doubao-hpe14-account2'
root=Path('/home/user/redroid-doubao/batches/geo-products-21x5-account2-relogin-20261013')
q=sqlite3.connect((root/'tasks.sqlite').as_uri()+'?mode=ro',uri=True);q.row_factory=sqlite3.Row
uid=current_uid(c)
dbpath=next(p for p in databases(c) if p.name=='im_database_'+uid)
db=sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
health=json.loads((root/'bridge_health.json').read_text())
service=subprocess.run(['systemctl','is-active','redroid-geo-products-account2.service'],capture_output=True,text=True).stdout.strip()
pid=subprocess.check_output(['docker','exec',c,'pidof','com.larus.nova'],text=True).strip()
maps=subprocess.check_output(['docker','exec',c,'cat','/proc/'+pid+'/maps'],text=True)
cache=[]
for line in maps.splitlines():
    if 'FlowIMSDKconversation-local-manager' in line:
        parts=line.split(); p=parts[-1]
        cache.append({'map_bytes':int(parts[0].split('-')[1],16)-int(parts[0].split('-')[0],16),'inode':parts[4],'path_length':len(p),'basename_length':len(Path(p).name),'suffix':Path(p).suffix})
native_conversations=db.execute('select count(*) from im_conversation where is_deleted=0').fetchone()[0]
clicks=[r[0] for r in q.execute("select time from events where event='send_click_intent_committed' and time>1791959000 order by time")]
completed=[]
for row in q.execute("select * from tasks where state='completed' order by ordinal"):
    t=dict(row); result=json.loads(t['result_json'])
    count=db.execute('select count(*) from im_message where user_type=1 and instr(content,?)>0',(t['task_id'],)).fetchone()[0]
    native=db.execute('select message_id,server_index,status from im_message where local_message_id=?',(result['request_id'],)).fetchone()
    current=0
    for r in db.execute('select fts_content,content from im_message where user_type=1 and instr(content,?)>0',(t['task_id'],)):
        blocks=json.loads(r['content']);text='\n\n'.join(b['content']['text_block']['text'] for b in blocks if 'text_block' in b['content'])
        if r['fts_content']==t['wire_question'] or text==t['wire_question']:current+=1
    completed.append({'ordinal':t['ordinal'],'body_length':len(result['body_markdown']),'sources':len(result['sources']),'citations':len(result['citations']),'native_requests_all_attempts':count,'current_attempt_requests':current,'server_confirmed':bool(native and native['message_id'] and native['server_index']>0)})
receipts=[]
for p in (root/'receipts').glob('*.json'):
    r=json.loads(p.read_text());a=r.get('analysis',{})
    receipts.append({'answer_present':a.get('answer_present'),'source_count':a.get('source_count'),'expected_source_count':a.get('expected_source_count'),'source_capture_complete':a.get('source_capture_complete')})
active=q.execute("select ordinal,state,error,prepared_at from tasks where state!='completed' order by ordinal limit 1").fetchone()
print(json.dumps({'service':service,'health':health,'health_age_seconds':time.time()-health['time'],'current_uid_tail':uid[-6:],'valid_conversations':native_conversations,'cache_maps':cache,'completed':completed,'processed_receipts':receipts,'minimum_recovery_send_interval':min([b-a for a,b in zip(clicks,clicks[1:])],default=None),'active_task':dict(active) if active else None},ensure_ascii=False,indent=2),flush=True)
