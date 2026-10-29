import sys,json,sqlite3,xml.etree.ElementTree as ET
from pathlib import Path
sys.path[:0]=['/home/user/redroid-doubao/geo-batch-code','/home/user/redroid-yuanbao']
from question_only_adapters import android
from history_refresh import original_pair_matches
from native_core import text_entities,enum
out={}
yr=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261022-090005-705819fb')
with sqlite3.connect(yr.joinpath('tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row;t=dict(db.execute("select * from tasks where state='prepared' order by ordinal limit 1").fetchone())
native=json.loads((yr/(t['task_id']+'.native.json')).read_text());binding=json.loads((yr/(t['task_id']+'.binding.json')).read_text())
d=android('yuanbao',None,None).device;nodes=list(ET.fromstring(d.dump_hierarchy()).iter('node'))
out['yuanbao']={'pair_matches':original_pair_matches(binding,t,native),'binding':binding,'question':native.get('question'),'question_text':'\n\n'.join(text_entities(native.get('question_entities',[]))),'task':{k:t[k] for k in ('task_id','wire_question','request_id')},'edit_nodes':[dict(n.attrib) for n in nodes if n.get('class')=='android.widget.EditText'],'restore':json.loads((yr/(t['task_id']+'.history-restore.json')).read_text()) if (yr/(t['task_id']+'.history-restore.json')).exists() else None}
dr=Path('/home/user/redroid-doubao/batches/geo-panel-doubao1-20261022-090003-0fe844d7')
p=next(dr.glob('63edea8a-3cb5-5644-847f-876237246e2a-attempt-0.binding.json'));b=json.loads(p.read_text())
with sqlite3.connect(Path(b['database']).as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row;out['doubao']=[{k:r[k] for k in ('local_message_id','user_type','local_index','server_index','content','status') if k in r.keys()} for r in db.execute('select * from im_message where conversation_id=? order by local_index',(b['conversation_id'],))]
Path('/opt/monitor/geo-capture/maintenance/20261022-native-stall/current-blockers.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False)[:14000])
