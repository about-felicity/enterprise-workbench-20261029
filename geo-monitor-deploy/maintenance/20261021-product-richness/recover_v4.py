import json,sys,shutil,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from geo_source_cards.runtime import atomic_json,atomic_write,process_lock
from geo_source_cards import daily_editorial as d
from geo_source_cards.staged_editorial import prepare
from geo_source_cards.prompt_compaction import research_key
from geo_source_cards.pipeline_control import event
r=Path('/opt/monitor/geo-content/runtime/runs/creation-1792556219-bbc55e13');m=Path('/opt/monitor/geo-capture/maintenance/20261021-product-richness');mark=m/'recover-v4.json'
assert not mark.exists();control=d.read(r/'control.json');assert control==d.read(m/'maintenance-v4-pause.json');assert d.read(r/'api/active.json')['state']=='SUBMITTED'
replacements={}
for number in [3,4]:
 old=r/f'days/2026-10-21/jobs/排行类/{number:02d}';inp=d.read(old/'research/research_input.json');loc=old.with_name(old.name+'-projection-repair')
 assert not loc.exists();loc.mkdir();atomic_write(loc/'articles.jsonl',''.join(json.dumps(v,ensure_ascii=False)+'\n' for v in inp['observations']));atomic_json(loc/'source_product.json',inp['product'])
 prepare(loc/'research',loc/'articles.jsonl',loc/'source_product.json',reference_design=inp['reference_design']);assert research_key(loc/'research')==research_key(old/'research')
 cache=r/'api/research_cache'/(research_key(loc/'research')+'.json');assert cache.is_file()
 shutil.copy2(old/'category.json',loc/'category.json');atomic_json(loc/'local_projection_repair.json',{'original':str(old.relative_to(r)),'cache_sha256':d.file_hash(cache),'method':'same source and original cached response; deterministic neutral clause projection; no new research API required','at':time.time()})
 ticket=d.publish_ticket(r,'research',loc/'research',['research_input.json','research_task.txt'],['research_result.json'],{'date':'2026-10-21','category':'排行类','number':number,'local_projection_repair':1});replacements[number]=ticket
 with process_lock(r/'coordinator.lock',blocking=True):
  for p in (r/'queue').glob('*/ticket.json'):
   v=d.read(p)
   if v['id']==ticket or v['meta'].get('category')!='排行类' or v['meta'].get('number')!=number or v['stage']!='writer':continue
   assert v['state'] in ['needs_attention','revision_requested']
   if v['state']=='needs_attention':assert 'research_material_insufficient' in v['error']
   atomic_json(p,{**v,'previous_state':v['state'],'state':'revision_requested','replaced_by':ticket,'resolution':'same_source_neutral_projection_from_original_cache'})
plan=d.read(r/'days/2026-10-21/category_plan.json')
for v in plan['planned']:
 if v['category']=='排行类' and v['number'] in replacements:v['replaces_ticket']=v['ticket'];v['ticket']=replacements[v['number']]
atomic_json(r/'days/2026-10-21/category_plan.json',plan)
with process_lock(r/'control.lock',blocking=True):
 assert d.read(r/'control.json')==control
 atomic_json(r/'control.json',{'paused':False,'revision':control['revision']+1,'resumed_epoch':time.time(),'resolved_system_pause':control,'reason':'document_and_evidence_projection_fixed'})
mark.write_text(json.dumps({'at':time.time(),'replacements':replacements,'original_budget_ledger_preserved':True,'no_unknown_replay':True},ensure_ascii=False,indent=2));event(r,'quality','三级标题兼容与同一来源中性资料投影修复完成，解除本次维护暂停',replacements=replacements);print(mark.read_text())
