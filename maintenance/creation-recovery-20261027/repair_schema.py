import sys,json,hashlib,shutil,os,time
from pathlib import Path
base=Path('/opt/monitor/geo-content/maintenance/recovery-20261027')
manifest=json.loads(Path('/tmp/schema-manifest.json').read_text())
target=Path('/opt/monitor/geo-content/engine/geo_source_cards/rewrite_v2/structure_parser.py')
candidate=Path('/tmp/recovery-structure-parser.py')
assert hashlib.sha256(candidate.read_bytes()).hexdigest()==manifest['new']
if hashlib.sha256(target.read_bytes()).hexdigest()!=manifest['new']:
 assert hashlib.sha256(target.read_bytes()).hexdigest()==manifest['old']
 shutil.copy2(target,base/'code-before/structure_parser.py')
 tmp=target.with_suffix('.tmp');shutil.copyfile(candidate,tmp)
 os.chmod(tmp,target.stat().st_mode);os.chown(tmp,target.stat().st_uid,target.stat().st_gid);os.replace(tmp,target)
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,recovery
from geo_source_cards.runtime import atomic_json,process_lock
from geo_source_cards.rewrite_v2 import integration,structure_parser
from geo_source_cards.rewrite_v2.common import seal
from geo_source_cards.daily_editorial import publish_ticket
root=runtime.BASE/'runs/creation-1793063678-424352dc'
with process_lock(root/'api/worker.lock',blocking=False):
 assert recovery.safe_original(root)
 ticketpath=root/'queue/55d3bf01b7eedefe800ff61c/ticket.json';t=runtime.read(ticketpath)
 assert t['state']=='needs_attention'
 backup=base/'schema-recovery';backup.mkdir(exist_ok=True)
 shutil.copy2(ticketpath,backup/'ticket.json')
 data=runtime.read(root/t['location']/'research_input.json')
 url=data['reference_design']['primary_url']
 source=next(s for row in data['observations'] for s in row['sources'] if s['url']==url)
 text=source['article']['text']
 answer=runtime.read(root/'api/runs/ad68a0d4aa82b81b4fd3dc3c/skeleton-call/answer.json')
 assert answer['finish_reason']=='stop'
 skeleton=structure_parser.validate(json.loads(answer['content']))
 key=structure_parser.identity(text);cache=integration.cache_root(root)/'skeleton'/(key+'.json')
 with process_lock(cache.with_suffix('.lock'),blocking=True):
  if cache.exists():structure_parser.checked(runtime.read(cache),text)
  else:atomic_json(cache,seal({'protocol':structure_parser.PROTOCOL,'cache_key':key,'source_text':text,'skeleton':skeleton,'approval':None}))
 meta={**t['meta'],'replaces':t['id'],'revision':t['meta'].get('revision',0)+1,'schema_recovery':True}
 replacement=publish_ticket(root,t['stage'],root/t['location'],list(t['inputs']),t['outputs'],meta)
 atomic_json(ticketpath,{**t,'state':'revision_requested','replaced_by':replacement})
 daypath=root/'days/2026-10-26/day.json';day=runtime.read(daypath);shutil.copy2(daypath,backup/'day.json')
 atomic_json(daypath,{**day,'status':'producing'})
 active=runtime.read(root/'api/active.json')
 if active.get('ticket')==t['id']:atomic_json(root/'api/active.json',{**active,'state':'SUBMITTED','schema_recovery':True})
 runtime.resume(root,check_balance=False);recovery.succeeded(root)
 atomic_json(backup/'result.json',{'replacement':replacement,'cache_key':key,'at':time.time(),'original_response_reused':True})
 print(json.dumps({'deployed':True,'resumed':root.name,'cached_response':True}))
