import json,tempfile,os,hashlib,sys,collections
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content/engine','/opt/monitor/geo-content','/home/user/geo-editorial/venv/lib/python3.10/site-packages']
from geo_source_cards.rewrite_v2.full_writer import serialize_writer_data
out={'requests':0,'before_chars':0,'after_chars':0,'same_data':True,'same_suffix':True,'prefix_before_chars':0,'prefix_after_chars':0};groups={};seen=set()
with tempfile.TemporaryDirectory() as tmp:
 for jp in Path('/opt/monitor/geo-content/runtime/runs').glob('creation-*/job.json'):
  if json.loads(jp.read_text()).get('date')!='2026-10-29':continue
  for p in jp.parent.rglob('request.json'):
   if str(p.resolve()) in seen:continue
   seen.add(str(p.resolve()));rq=json.loads(p.read_text());m=rq.get('messages',[])
   if len(m)!=2 or not m[1]['content'].startswith('{'):continue
   text=m[1]['content']
   try:data,end=json.JSONDecoder().raw_decode(text)
   except ValueError:continue
   if not isinstance(data,dict) or not {'material','skeleton','reference','assignment'}<=data.keys():continue
   folder=Path(tmp)/str(out['requests']);folder.mkdir();compact=serialize_writer_data(data,folder);new=compact+text[end:]
   assert json.loads(compact)==data and new[len(compact):]==text[end:]
   out['requests']+=1;out['before_chars']+=len(text);out['after_chars']+=len(new)
   key=hashlib.sha256(json.dumps(data['material'],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
   if key in groups:
    old_prior,new_prior=groups[key];out['prefix_before_chars']+=len(os.path.commonprefix([text,old_prior]));out['prefix_after_chars']+=len(os.path.commonprefix([new,new_prior]))
   groups[key]=(text,new)
out['removed_format_chars']=out['before_chars']-out['after_chars'];out['note']='Offline character counts, not billed tokens or measured provider cache savings. All source data and instructions retained; no paid calls.'
Path('/opt/monitor/geo-content/maintenance/token-efficiency-20261029/measurement.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
