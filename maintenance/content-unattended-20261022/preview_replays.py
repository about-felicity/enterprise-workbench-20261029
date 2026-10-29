"""Try parser-fixed, paid, complete responses on copies; never invokes an API."""
import sys,json,shutil,hashlib,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from geo_source_cards.api_worker import materialize
from geo_source_cards.staged_editorial import check,research_for_writer
D=Path('/opt/monitor/geo-capture/maintenance/20261022-content-unattended');seed=runtime.read(D/'trial-requeued.json')
rows=[]
for identity in sorted({a['job'] for a in seed['articles']}):
 root=runtime.job_root(identity);tickets=[runtime.read(p) for p in (root/'queue').glob('*/ticket.json')]
 for source in (root/'api/runs').glob('*'):
  error=runtime.read(source/'materialization_error.json').get('message','')
  if 'Paragraph repair made no change' not in error:continue
  old=next((t for t in tickets if t.get('execution',{}).get('run_id')==source.name),None)
  if not old or not old.get('meta',{}).get('paragraph_repair'):continue
  writer=root/old['location'];spec=runtime.read(source/'paragraph_repair.json')
  if runtime.read(source/'call/api_state.json').get('state')!='RESPONDED':continue
  if not (writer/'draft.md').is_file() or hashlib.sha256((writer/'draft.md').read_bytes()).hexdigest()!=spec.get('base_sha256'):continue
  if any(not (source/n).is_file() or hashlib.sha256((source/n).read_bytes()).hexdigest()!=h for n,h in old['inputs'].items()):continue
  scratch=D/'response-replay-preview'/source.name/'article';scratch.mkdir(parents=True,exist_ok=True)
  for path in writer.parent.glob('research*'):
   if path.is_dir():shutil.copytree(path,scratch/path.name,dirs_exist_ok=True)
  target=scratch/'writer';shutil.copytree(writer,target,dirs_exist_ok=True)
  for name in old['inputs']:shutil.copy2(source/name,target/name)
  row={'job':identity,'source_run':source.name,'source_ticket':old['id'],'category':old['meta']['category'],'number':old['meta']['number'],
       'response_sha256':hashlib.sha256((source/'call/response.json').read_bytes()).hexdigest()}
  try:
   materialize(old,target,runtime.read(source/'call/response.json'))
   row['checks']=check(research_for_writer(target),target)
   row['edited_ids']=runtime.read(target/'paragraph_repair_audit.json').get('edited_ids')
  except Exception as e:row['error']=type(e).__name__+': '+str(e)[:500]
  rows.append(row)
report={'at':time.time(),'new_paid_calls':0,'candidates':rows}
runtime.atomic_json(D/'response-replay-preview.json',report);print(json.dumps(report,ensure_ascii=False))
