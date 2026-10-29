import sys,json,sqlite3,xml.etree.ElementTree as ET
from pathlib import Path
sys.path[:0]=['/home/user/redroid-doubao/geo-batch-code','/home/user/redroid-yuanbao']
from draft_submission_recovery import exact_draft,absent_proof
from question_only_core import baseline
from unattended_worker import databases
from question_only_adapters import android
from question_only_adapters import DoubaoReader
D=Path('/opt/monitor/geo-capture/maintenance/20261022-native-stall');old=json.loads((D/'before.json').read_text());r=next(r for r in old['batches'] if r['model']=='doubao1');task=r['task'];root=Path(r['root'])
before=json.loads((root/(task['task_id']+'-attempt-0.pre-send.json')).read_text());paths=databases('doubao-hpe14-13-test');after=baseline(paths,task['wire_question'])
device=android('doubao1','127.0.0.1:5557','/home/user/redroid-doubao/linux-tools/platform-tools/adb').device
xml=device.dump_hierarchy();out={'current':device.app_current(),'exact_draft':exact_draft(xml,task['wire_question']),'absent_proof':absent_proof(before,after) is not None,'differences':[]}
with sqlite3.connect(root.joinpath('tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row;fresh=dict(db.execute('select * from tasks where task_id=?',(task['task_id'],)).fetchone())
fresh.pop('result_json',None);out['current_task']=fresh;out['observed']=DoubaoReader(root,'doubao-hpe14-13-test').lookup(fresh)
for a,b in zip(before['databases'],after['databases']):
 old={json.dumps(v,sort_keys=True) for v in a['prior_requests']};new={json.dumps(v,sort_keys=True) for v in b['prior_requests']}
 out['differences'].append({'database':a['database'],'new_conversations':sorted(set(b['conversations'])-set(a['conversations'])),'removed_conversations':sorted(set(a['conversations'])-set(b['conversations'])),
 'new_fingerprints':list(new-old),'removed_fingerprints':list(old-new)})
p=root/(task['task_id']+'-attempt-0.draft-submit-recovery.json');out['state']=json.loads(p.read_text()) if p.is_file() else None
if out['state'] and out['state'].get('proof'):out['state']['proof']='<persisted baseline proof>'
out['ui']=[{k:n.get(k) for k in ('text','content-desc','resource-id','enabled','bounds') if n.get(k)} for n in ET.fromstring(xml).iter('node') if n.get('text') or n.get('content-desc') or 'action_send' in n.get('resource-id','')]
print(json.dumps(out,ensure_ascii=False)[:10000])
