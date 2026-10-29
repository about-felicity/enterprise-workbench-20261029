import json,sys,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from geo_source_cards.runtime import atomic_json,process_lock
r=Path('/opt/monitor/geo-content/runtime/runs/creation-1792556219-bbc55e13')
with process_lock(r/'coordinator.lock',blocking=True):
 p=r/'queue/1ca111ca3ff172d74ccf1e59/ticket.json';v=json.loads(p.read_text());assert v['state']=='needs_attention';assert 'research_material_insufficient' in v['error']
 proof=[p for p in (r/'api/runs').glob('*/preflight_rejection.json') if json.loads(p.read_text()).get('ticket')==v['id']]
 assert len(proof)==1 and json.loads(proof[0].read_text())['request_sent'] is False
 atomic_json(p,{**v,'previous_state':v['state'],'state':'revision_requested','replaced_by':'374569988419d6d94aa88476','resolution':'known_unsent_automatic_preflight_retry_superseded_by_same_source_research','at':time.time()})
print('Retired known unsent duplicate preflight attempt; paid history and replacement research preserved')
