from pathlib import Path
from urllib.parse import urlsplit
import json,sqlite3,collections,subprocess,sys
fleet=json.loads(Path('/opt/monitor/geo-capture/fleet.json').read_text())['collectors']
def diff(a,b,k,out):
 if type(a)!=type(b):out.add(k);return
 if isinstance(a,dict):
  for f in a.keys()|b.keys():
   if f not in a or f not in b:out.add(k+'.'+f)
   else:diff(a[f],b[f],k+'.'+f,out)
 elif isinstance(a,list):
  if len(a)!=len(b):out.add(k+'.length')
  for i,j in zip(a,b):diff(i,j,k+'[]',out)
 elif a!=b:out.add(k)
for n in [1,2,3,4]:
 r=Path(next(x['health'] for x in fleet if x['name']==f'豆包 {n}')).parent;cnt=collections.Counter()
 for p in (r/'outbox').glob('*.json'):
  v=json.loads(p.read_text())['payload']['native_result'];binding=json.loads(next(r.glob(v['task_id']+'-attempt-*.binding.json')).read_text())
  with sqlite3.connect(Path(binding['database']).as_uri()+'?mode=ro',uri=True) as d:
   raw=json.loads(d.execute('select content from im_message where local_message_id=? and conversation_id=?',(v['answer_id'],v['conversation_id'])).fetchone()[0])
  o=set();diff(raw,v['raw_answer_blocks'],'',o);cnt.update(o)
 print(n,cnt.most_common(25))
sql="""select json_build_object('raw', (select json_agg(x->>'url') from jsonb_array_elements(e.record->'items') x),'saved',(select json_agg(json_build_array(url,canonical_url)) from monitor_sources s where s.model_id=e.model_id and s.run_id=e.run_id)) from monitor_ingest_events e where run_id='doubao-232b8a967f3b56a5fd1e'"""
v=json.loads(subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',sql],text=True))
print('missing:',set(v['raw'])-{x[0] for x in v['saved']})
print('retained:',v['saved'])
