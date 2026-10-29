import sys,json,hashlib,shutil,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from geo_source_cards.runtime import atomic_json,process_lock
from geo_source_cards.daily_editorial import publish_ticket
D=Path('/opt/monitor/geo-capture/maintenance/20261022-content-unattended');marker=D/'known-responses-recovered.json'
assert not marker.exists(),'Already published; inspect queue instead'
rows=runtime.read(D/'response-replay-preview.json')['candidates'];selected={}
for row in rows:
 if row.get('error'):continue
 key=(row['job'],row['category'],row['number'])
 if key not in selected or len(row['checks']['failures'])<len(selected[key]['checks']['failures']):selected[key]=row
published=[]
for (identity,category,number),row in selected.items():
 root=runtime.job_root(identity);source=root/'api/runs'/row['source_run'];old=runtime.read(root/'queue'/row['source_ticket']/'ticket.json')
 writer=root/old['location'];spec=runtime.read(source/'paragraph_repair.json')
 assert runtime.read(root/'control.json').get('paused')
 assert runtime.read(root/'api/active.json').get('state') in (None,'SUBMITTED')
 assert hashlib.sha256((writer/'draft.md').read_bytes()).hexdigest()==spec['base_sha256']
 assert runtime.read(source/'call/api_state.json').get('state')=='RESPONDED'
 with process_lock(root/'coordinator.lock',blocking=True):
  saved=D/'before-known-response-replay'/row['source_run'];shutil.copytree(writer,saved/'writer')
  jobs=[runtime.read(p) for p in (root/'queue').glob('*/ticket.json')]
  for name in old['inputs']:shutil.copy2(source/name,writer/name)
  atomic_json(writer/'known_response.json',{k:row[k] for k in ('source_run','source_ticket','response_sha256')})
  meta={**old['meta'],'revision':1,'replaces':old['id'],'known_response_replay':True,
        'response_replay_release':'noop-parser-v2'}
  ticket=publish_ticket(root,'writer',writer,[*old['inputs'],'known_response.json'],old['outputs'],meta)
  for previous in jobs:
   if (previous['meta'].get('category'),previous['meta'].get('number'))!=(category,number):continue
   if previous['state'] in {'pending','needs_attention'}:
    atomic_json(root/'queue'/previous['id']/'ticket.json',{**previous,'state':'revision_requested','replaced_by':ticket,
       'operator_reason':'Known completed writer response locally reprocessed; no new writer API call'})
  published.append({'job':identity,'category':category,'number':number,'ticket':ticket,'source_run':row['source_run']})
atomic_json(marker,{'at':time.time(),'articles':published,'new_writer_api_calls':0})
for identity in sorted({a['job'] for a in runtime.read(D/'trial-requeued.json')['articles']}):runtime.resume(runtime.job_root(identity))
print(json.dumps(runtime.read(marker),ensure_ascii=False))
