import sys,json,sqlite3,xml.etree.ElementTree as ET,time
from pathlib import Path
sys.path[:0]=['/home/user/redroid-doubao/geo-batch-code','/home/user/redroid-yuanbao']
from question_only_adapters import android,yuanbao_reader
from history_refresh import original_pair_matches
D=Path('/opt/monitor/geo-capture/maintenance/20261022-native-stall');root=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261022-090005-705819fb')
with sqlite3.connect(root.joinpath('tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row;task=dict(db.execute("select * from tasks where state='prepared' order by ordinal limit 1").fetchone())
native=json.loads((root/(task['task_id']+'.native.json')).read_text());binding=json.loads((root/(task['task_id']+'.binding.json')).read_text());assert original_pair_matches(binding,task,native)
a=android('yuanbao',None,None);nodes=list(ET.fromstring(a.device.dump_hierarchy()).iter('node'))
assert any(n.get('text','').startswith('Hi，') for n in nodes)
assert not any(n.get('class')=='android.widget.EditText' and n.get('text') for n in nodes)
drawer=a.device(description='抽屉页入口');assert drawer.count==1;a.tap(drawer);time.sleep(3)
xml=a.device.dump_hierarchy();(D/'yuanbao-drawer.xml').write_text(xml)
r=yuanbao_reader(root)
try:entries=r.history_entries()
finally:r.close()
out={'ui':[{k:n.get(k) for k in ('text','content-desc','resource-id') if n.get(k)} for n in ET.fromstring(xml).iter('node') if n.get('text') or n.get('content-desc')],'entries':entries}
(D/'drawer-proof.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False)[:11000]);a.device.press('back')
