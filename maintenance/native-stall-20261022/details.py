import sys,json,sqlite3,xml.etree.ElementTree as ET
from pathlib import Path
sys.path[:0]=['/home/user/redroid-yuanbao','/home/user/redroid-doubao/geo-batch-code','/home/user/redroid-doubao']
D=Path('/opt/monitor/geo-capture/maintenance/20261022-native-stall');old=json.loads((D/'before.json').read_text());out={}
for r in old['batches']:
 if 'task' not in r:continue
 task=r['task'];root=Path(r['root']);(D/r['model']).mkdir(exist_ok=True)
 if r['model']=='yuanbao':
  raw=json.loads((root/(task['task_id']+'.native.json')).read_text());docs=[]
  for entity in raw['entities']:
   kind=entity.get('type');kind=kind.get('text') if isinstance(kind,dict) else kind
   if kind!='SEARCH_GUIDE':continue
   search=entity['searchEntity'];items=json.loads(search['docsJson'])
   docs += [{'index':i,'doc':d,'fields_missing':[k for k in ('title','url','docId') if not d.get(k)]} for i,d in enumerate(items)]
  out['yuanbao']={'source_counts':len(docs),'question':task['question'],'documents':docs,'states':{k:raw[k] for k in ('message','content','conversation') if k in raw}}
 else:
  from unattended_worker import databases
  from question_only_core import baseline,correlate
  base_path=root/(task['task_id']+'-attempt-0.pre-send.json');base=json.loads(base_path.read_text())
  paths=databases('doubao-hpe14-13-test')
  out['doubao1']={'before':base,'paths':[str(p) for p in paths],'current_baseline':baseline(paths,task['question'])}
  try:out['doubao1']['correlate']=correlate(base,task['question'])
  except Exception as e:out['doubao1']['correlate_error']=str(e)
 from question_only_adapters import android
 device=android(r['model'],{'yuanbao':'127.0.0.1:5559','doubao1':'127.0.0.1:5557'}[r['model']],'/home/user/redroid-doubao/linux-tools/platform-tools/adb')
 xml=device.device.dump_hierarchy();(D/r['model']/'before-ui.xml').write_text(xml)
 out[r['model']]['ui']=[{k:n.get(k) for k in ('text','content-desc','resource-id','class','bounds') if n.get(k)} for n in ET.fromstring(xml).iter('node') if n.get('text') or n.get('content-desc') or n.get('class')=='android.widget.EditText']
outpath=D/'details.json';outpath.write_text(json.dumps(out,ensure_ascii=False,indent=2));outpath.chmod(0o644)
summary=out.get('doubao1',{}).copy()
for key in ('before','current_baseline'):
 if key in summary:summary[key]={'created_at':summary[key]['created_at'],'databases':[{'database':v['database'],'max_rowid':v['max_rowid'],'conversation_count':len(v['conversations']),'prior_request_count':len(v['prior_requests'])} for v in summary[key]['databases']]}
summary['ui']=[{k:v for k,v in n.items() if k in ('text','content-desc','resource-id')} for n in summary.get('ui',[])]
print(json.dumps({'doubao1':summary, 'yuanbao':{k:v for k,v in out.get('yuanbao',{}).items() if k not in ('documents','states')},
 'bad_docs':[d for d in out.get('yuanbao',{}).get('documents',[]) if d['fields_missing'] or not str(d['doc'].get('url','')).startswith(('http:','https:'))]},ensure_ascii=False)[:20000])
