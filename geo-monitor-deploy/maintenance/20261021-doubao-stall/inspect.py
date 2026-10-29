import json,sqlite3,sys,time,traceback,shutil
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from question_only_adapters import DoubaoReader
root=Path('/home/user/redroid-doubao/batches/geo-panel-doubao1-20261021-090003-e1d20b1d')
out=Path('/opt/monitor/geo-capture/maintenance/20261021-doubao-stall');out.mkdir(parents=True,exist_ok=True)
db=sqlite3.connect('file:'+str(root/'tasks.sqlite')+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
t=dict(db.execute("select * from tasks where state='prepared'").fetchone());t.pop('result_json',None)
report={'at':time.time(),'task':t,'events':[dict(x) for x in db.execute('select * from events where task_id=? order by time desc limit 5',(t['task_id'],))]}
r=DoubaoReader(root,'doubao-hpe14-13-test');before,bound=r.paths(t)
for p in (before,bound):
 if p.exists() and not (out/p.name).exists():shutil.copy2(p,out/p.name)
try:
 o=r.lookup(t);report['observed']={k:v for k,v in o.items() if k not in ('raw_answer_blocks','raw_question_blocks','sources','citations','body_parts')}
except Exception as e:report.update(error=type(e).__name__+': '+str(e),trace=traceback.format_exc())
binding=json.loads(bound.read_text()) if bound.exists() else None;report['binding']=binding
if binding:
 with sqlite3.connect('file:'+binding['database']+'?mode=ro',uri=True) as native:
  native.row_factory=sqlite3.Row
  rows=[dict(x) for x in native.execute('select * from im_message where conversation_id=? order by local_index',(binding['conversation_id'],))]
  (out/'native-rows.json').write_text(json.dumps(rows,ensure_ascii=False))
  report['rows']=[{**{k:x.get(k) for k in ('local_message_id','message_id','user_type','local_index','server_index','status')},'content':x.get('content')} for x in rows]
(out/'inspect.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False)[:17000])
