import json,sqlite3,sys,time,traceback
from pathlib import Path
sys.path[:0]=['/home/user/redroid-doubao/geo-batch-code','/home/user/redroid-yuanbao']
from question_only_adapters import yuanbao_reader
R=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261021-090004-d6fb7a84')
D=Path('/opt/monitor/geo-capture/maintenance/20261021-yuanbao-stall');D.mkdir(parents=True,exist_ok=True)
db=sqlite3.connect('file:'+str(R/'tasks.sqlite')+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
t=dict(db.execute("select * from tasks where state='prepared'").fetchone());t.pop('result_json',None)
out={'at':time.time(),'task':t,'events':[dict(x) for x in db.execute('select * from events where task_id=? order by time desc limit 12',(t['task_id'],))]}
reader=yuanbao_reader(R)
try:
 observed=reader.lookup(t)
 (D/'observed.json').write_text(json.dumps(observed,ensure_ascii=False))
 out['observed']={k:v for k,v in observed.items() if k not in ('native_snapshot','body_parts','raw_source_entries','sources','citations','rich_cards')}
except Exception as e:out['error']=type(e).__name__+': '+str(e);out['trace']=traceback.format_exc()
finally:reader.close()
for suffix in ('binding','native'):
 p=R/(t['task_id']+'.'+suffix+'.json')
 if not p.exists():continue
 raw=json.loads(p.read_text());(D/('original-'+suffix+'.json')).write_text(json.dumps(raw,ensure_ascii=False))
 if suffix=='binding':out['binding']=raw
 else:
  out['native_summary']={k:{a:b for a,b in raw.get(k,{}).items() if a not in ('content','cookie','token','authorization','headers')} for k in ('question','message','last','conversation')}
  c=raw.get('content',{});out['content_summary']={k:v for k,v in c.items() if k not in ('entities','text','data')};out['entity_count']=len(c.get('entities',[]))
(D/'inspect.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False)[:14000])
