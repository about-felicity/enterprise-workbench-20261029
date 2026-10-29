import sys,json,hashlib,shutil,os,subprocess,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from geo_source_cards.runtime import atomic_json,process_lock
base=Path('/opt/monitor/geo-content/maintenance/direct-output-20261026');base.mkdir(exist_ok=True)
r=Path('/opt/monitor/geo-content/runtime/runs/creation-1792985673-e3995d45')
manifest=json.loads(Path('/tmp/direct-output-manifest.json').read_text())
with process_lock(r/'api/worker.lock'):
 for row in manifest['files']:
  assert hashlib.sha256(Path(row['server']).read_bytes()).hexdigest()==row['before'],row['name']
  assert hashlib.sha256(Path('/tmp/direct-output',row['name']).read_bytes()).hexdigest()==row['sha256']
 shutil.copytree(r,base/'job-before')
 for row in manifest['files']:
  dst=Path(row['server']);shutil.copy2(dst,base/row['name']);tmp=dst.with_name(dst.name+'.direct-tmp')
  shutil.copy2(Path('/tmp/direct-output',row['name']),tmp);os.chmod(tmp,dst.stat().st_mode);os.chown(tmp,dst.stat().st_uid,dst.stat().st_gid);os.replace(tmp,dst)
 from geo_source_cards.rewrite_v2 import integration,material_manager
 from geo_source_cards.rewrite_v2.common import seal
 from geo_source_cards.daily_editorial import publish_ticket,tick
 from geo_source_cards.staged_editorial import read
 policy=read(r/'rewrite_policy.json');policy.update(article_delivery='direct',max_targeted_repairs=0)
 atomic_json(r/'rewrite_policy.json',policy)
 # Recover a known, completed response; no request replay and no new charge.
 ticket=r/'queue/21fbe2410b7808e4fd5f2024/ticket.json';job=read(ticket);writer=r/job['location']
 raw=read(r/'api/runs'/job['execution']['run_id']/'call/answer.json')
 assert raw['finish_reason']=='stop'
 answer=json.loads(raw['content']);assert isinstance(answer.get('draft_markdown'),str) and answer['draft_markdown'].strip()
 material=seal({'raw_product':read(writer/'product.json'),'layers':{k:[] for k in material_manager.LAYERS},'usage_rules':[],'protocol':'original-product-direct-v1'})
 integration.materialize(job,writer,{**answer,'material':material})
 integration.finalize(r,writer.parent/'review')
 atomic_json(ticket,{**job,'state':'accepted','delivery_mode':'direct','recovered_from_completed_response':True,'accepted_at':time.time()})
 ticket=r/'queue/122afeed608f2db573089737/ticket.json';job=read(ticket)
 integration.finalize(r,r/job['location'])
 atomic_json(ticket,{**job,'state':'accepted','delivery_mode':'direct','accepted_at':time.time()})
 # This prior failure occurred before any writer request. Create its writer ticket.
 ticket=r/'queue/35268c3bbc809989849e3be9/ticket.json';job=read(ticket)
 assert not (r/'api/runs'/job['execution']['run_id']/'call/api_state.json').exists()
 replacement=publish_ticket(r,'writer',r/job['location'],list(job['inputs']),job['outputs'],{**job['meta'],'revision':1,'replaces':job['id'],'direct_output_recovery':True})
 atomic_json(ticket,{**job,'state':'revision_requested','replaced_by':replacement})
 day=r/'days/2026-10-26/day.json';atomic_json(day,{**read(day),'status':'producing'})
 tick(r)
 manifest.update(tests=41,recovered_articles=2,backup=str(base))
 atomic_json(base/'release.json',manifest)
subprocess.run(['systemctl','restart','geo-content-api'],check=True)
print(json.dumps(manifest))
