"""Retry the observed failed native request once, preserving its local ID."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import sys,os,json,sqlite3,time,subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from unattended_core import Queue,lookup
from unattended_worker import Android,databases
from active_database_accounts import current_uid
os.umask(0o077)
c='doubao-hpe14-account2';uid=current_uid(c)
assert uid.endswith('066524')
assert subprocess.run(['systemctl','is-active','redroid-geo-products-account2.service'],capture_output=True,text=True).stdout.strip() in ('inactive','failed')
root=Path('/home/user/redroid-doubao/batches/geo-products-21x5-account2-relogin-20261013')
q=Queue(root/'tasks.sqlite');t=q.next_task()
assert t['ordinal']==1 and t['state']=='prepared' and t['request_id']=='c47f2d74-642f-4c93-9745-b0fe2c5fbfec'
assert not q.db.execute("select 1 from events where task_id=? and event='operator_retry_after_fts_repair'",(t['task_id'],)).fetchone()
dbpath=next(p for p in databases(c) if p.name=='im_database_'+uid)
db=sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
r=db.execute('select local_message_id,message_id,server_index,status,conversation_id from im_message where local_message_id=?',(t['request_id'],)).fetchone()
assert r and r['status']==12 and r['message_id'] is None and r['server_index']==0
assert db.execute('select count(*) from im_conversation where conversation_id=? and is_deleted=0',(r['conversation_id'],)).fetchone()[0]==1
assert 'unicode61' in db.execute("select sql from sqlite_master where name='fts_im_conversation'").fetchone()[0]
assert db.execute("select count(*) from sqlite_master where type='trigger' and tbl_name='im_conversation'").fetchone()[0]==4
assert lookup(databases(c),t)['request_id']==t['request_id']
a=Android('127.0.0.1:5558','/home/user/redroid-doubao/linux-tools/platform-tools/adb')
assert any(e.get('text')==t['wire_question'] for e in ET.fromstring(a.device.dump_hierarchy()).iter('node'))
retry=a.device(resourceId='com.larus.nova:id/retry')
assert retry.exists and retry.count==1
backup=root/('before-native-fts-retry-'+str(int(time.time()))+'.sqlite')
with sqlite3.connect(backup) as dest:q.db.backup(dest)
with q.db:
    q.event(t['task_id'],'operator_retry_after_fts_repair',json.dumps({'native_before':dict(r),'reason':'Conversation metadata now persisted; unicode61 FTS/triggers survive restart; retry same rejected native local ID'}))
    q.db.execute('update tasks set prepared_at=? where task_id=?',(time.time(),t['task_id']))
    q.event(t['task_id'],'send_click_intent_committed','Native retry of same local ID after durable FTS fix; no new question created')
a.tap(retry)
print('Native retry clicked once on existing request; local ID preserved',flush=True)
subprocess.run(['systemctl','start','redroid-geo-products-account2.service'],check=True)
