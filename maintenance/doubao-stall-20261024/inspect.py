import json,sqlite3,sys,time
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from question_only_core import baseline,correlate,message_text
from unattended_worker import databases
import uiautomator2 as u2
R=Path('/home/user/redroid-doubao/batches/geo-panel-doubao1-20261024-090002-8e65185c')
D=Path('/opt/monitor/geo-capture/maintenance/20261024-doubao-stall');D.mkdir(parents=True,exist_ok=True)
c=sqlite3.connect('file:'+str(R/'tasks.sqlite')+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
t=dict(c.execute("select * from tasks where state='prepared'").fetchone());t.pop('result_json',None)
events=[dict(r) for r in c.execute('select * from events where task_id=? order by time desc limit 12',(t['task_id'],))]
stem=t['task_id']+'-attempt-'+str(t['capture_retries']);before=json.loads((R/(stem+'.pre-send.json')).read_text())
paths=databases('doubao-hpe14-13-test');after=baseline(paths,t['question'])
report={'at':time.time(),'task':t,'events':events,'current_databases':list(map(str,paths)),'baseline_summary':[],'matches':[]}
for old in before['databases']:
 with sqlite3.connect('file:'+old['database']+'?mode=ro',uri=True) as db:
  db.row_factory=sqlite3.Row
  summary={'database':old['database'],'before_max':old['max_rowid'],'now_max':db.execute('select max(rowid) from im_message').fetchone()[0]}
  report['baseline_summary'].append(summary)
  for row in db.execute('select rowid,* from im_message where user_type=1'):
   try:matches=message_text(row)==t['question']
   except Exception:continue
   if matches:report['matches'].append({k:row[k] for k in row.keys() if k in ['rowid','local_message_id','message_id','conversation_id','local_index','server_index','status','created_at','create_time','content']})
try:report['correlate']=correlate(before,t['question'])
except Exception as e:report['correlate_error']=str(e)
device=u2.connect('127.0.0.1:5557');report['app']=device.app_current();xml=device.dump_hierarchy();(D/'current.xml').write_text(xml);device.screenshot(str(D/'current.png'))
import xml.etree.ElementTree as ET
report['visible']=[{k:n.get(k) for k in ('resource-id','text','content-desc','bounds')} for n in ET.fromstring(xml).iter('node') if n.get('text') or n.get('content-desc')]
(D/'before.json').write_text(json.dumps(before,ensure_ascii=False));(D/'after.json').write_text(json.dumps(after,ensure_ascii=False));(D/'inspect.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
