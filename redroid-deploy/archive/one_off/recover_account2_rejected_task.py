"""Audit native rejection and recover only current batch ordinal 1, once."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import sys,sqlite3,json,subprocess,os,time
from pathlib import Path
os.umask(0o077)
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from unattended_core import Queue,lookup
from unattended_worker import databases,Android
from active_database_accounts import current_uid
c='doubao-hpe14-account2'
assert current_uid(c).endswith('066524')
assert subprocess.run(['systemctl','is-active','redroid-geo-products-account2.service'],capture_output=True,text=True).stdout.strip() in ('inactive','failed')
root=Path('/home/user/redroid-doubao/batches/geo-products-21x5-account2-relogin-20261013')
q=Queue(root/'tasks.sqlite')
t=dict(q.db.execute('select * from tasks where ordinal=1').fetchone())
assert t['task_id']=='a3c95521-ed78-5656-ab91-871ccd8a5751' and t['state']=='prepared'
assert t['request_id'] in (None,'c10c6d72-e1be-4776-a36c-de9f25144bf8')
assert lookup(databases(c),t)['status']=='absent'
assert not q.db.execute("select 1 from events where task_id=? and event='operator_recover_native_rejected'",(t['task_id'],)).fetchone()
evidence=[]
for folder in Path('/home/user/redroid-doubao/account2').glob('im-cache-before-rebuild-*'):
    for p in folder.rglob('im_database_*'):
        if p.name.endswith(('-wal','-shm')): continue
        db=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
        try:
            for row in db.execute('select local_message_id,message_id,server_index,status from im_message where local_message_id=? or instr(content,?)>0',('c10c6d72-e1be-4776-a36c-de9f25144bf8',t['task_id'])):
                evidence.append(dict(row))
        finally: db.close()
assert evidence and all(r['message_id'] is None and r['server_index']==0 for r in evidence),evidence
print(json.dumps({'task':t['ordinal'],'native_failure_evidence':evidence,'current_exact_request':'absent','events':[r[0] for r in q.db.execute('select event from events where task_id=?',(t['task_id'],))]}),flush=True)
if '--resume' not in sys.argv: raise SystemExit(0)
android=Android('127.0.0.1:5558','/home/user/redroid-doubao/linux-tools/platform-tools/adb')
android.ready()
assert lookup(databases(c),t)['status']=='absent'
backup=root/('before-native-rejected-recovery-'+str(int(time.time()))+'.sqlite')
with sqlite3.connect(backup) as dest:q.db.backup(dest)
with q.db:
    q.event(t['task_id'],'operator_recover_native_rejected',json.dumps({'old_request_id':t['request_id'],'native_evidence':evidence,'reason':'Houdini path truncation bypass installed; current task exact request absent; historic native send has no server ID/index; one controlled recovery authorized'}))
def click():
    assert lookup(databases(c),t)['status']=='absent'
    with q.db:
        q.db.execute('update tasks set prepared_at=?,request_id=null,error=null where task_id=?',(time.time(),t['task_id']))
        q.event(t['task_id'],'send_click_intent_committed','One controlled recovery after proven native rejection; earlier failed send events retained.')
android.send(t['wire_question'],click)
print('Recovery send clicked once; queue stays prepared for native result reconciliation.',flush=True)
subprocess.run(['systemctl','start','redroid-geo-products-account2.service'],check=True)
