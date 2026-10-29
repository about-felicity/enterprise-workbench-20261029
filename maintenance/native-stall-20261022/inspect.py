"""Read-only snapshots of current native batches; never send or clear tasks."""
import json,sqlite3,time
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261022-native-stall');D.mkdir(parents=True,exist_ok=True)
configs=[Path('/opt/monitor/geo-capture/panel/jobs')/name for name in ('geo-panel-doubao1-20261022-090003-0fe844d7.json','geo-panel-doubao2-20261022-090004-564a33f1.json','geo-panel-yuanbao-20261022-090005-705819fb.json')]
reports=[]
for config in configs:
 c=json.loads(config.read_text());base=Path('/home/user/redroid-yuanbao' if c['model']=='yuanbao' else '/home/user/redroid-doubao');root=base/'batches'/c['batch']
 read=lambda p:json.loads(p.read_text()) if p.is_file() else {}
 with sqlite3.connect(root.joinpath('tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  db.row_factory=sqlite3.Row
  report={'model':c['model'],'batch':c['batch'],'root':str(root),'health':read(root/'bridge_health.json'),
   'pause':read(root/'maintenance_pause.json'),'counts':dict(db.execute('select state,count(*) from tasks group by state').fetchall())}
  current=db.execute("select * from tasks where state!='completed' and state!='completed_nontext' order by ordinal limit 1").fetchone()
  if current:
   task=dict(current);task.pop('result_json',None);report['task']=task
   report['events']=[dict(r) for r in db.execute('select * from events where task_id=? order by time desc limit 7',(task['task_id'],))]
   report['clicks']=db.execute("select count(*) from events where task_id=? and event='send_click_intent_committed'",(task['task_id'],)).fetchone()[0]
   for suffix in ('native','binding','render','history-refresh','pre-send'):
    p=root/(task['task_id']+'.'+suffix+'.json');value=read(p)
    if p.is_file():
     saved=D/c['model']/('before-'+suffix+'.json');saved.parent.mkdir(exist_ok=True)
     if not saved.exists():saved.write_text(json.dumps(value,ensure_ascii=False))
    if suffix=='native':
     report['native']={k:value.get(k) for k in ('message','question','content','conversation','last')}
     report['native_keys']=list(value)
    elif suffix in {'binding','history-refresh'}:report[suffix]=value
   report['root_json_files']=[p.name for p in root.glob('*.json') if task['task_id'] not in p.name and not p.name.startswith('pre')][-12:]
  reports.append(report)
out={'at':time.time(),'batches':reports};destination=D/'before.json'
if destination.exists():destination=D/('snapshot-'+str(time.time_ns())+'.json')
destination.write_text(json.dumps(out,ensure_ascii=False,indent=2))
for r in reports:
 r.pop('native',None)
print(json.dumps(out,ensure_ascii=False))
