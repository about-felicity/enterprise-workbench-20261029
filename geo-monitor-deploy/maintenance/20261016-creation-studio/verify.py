import json,subprocess,sys
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import materials,source_adapter
R=Path('/opt/monitor/geo-content/maintenance/20261016-creation-studio')
cfg=materials.settings();cat=materials.catalog()
coverage={q:sum(len(materials.records(day,q,list(materials.CHANNELS))) for day in cat['dates']) for q in cfg['questions']}
assert all(coverage.values()),coverage
sql="SELECT question,count(*) AS n FROM monitor_runs WHERE day>='2026-10-16' AND question IN ("+','.join(source_adapter.literal(q) for q in cfg['questions'])+") GROUP BY question"
leaks=source_adapter.query(sql);assert not leaks,leaks
health=materials.status();assert health['health']['status']=='scheduled' and not health['health']['active_channels']
release=json.loads((R/'release.json').read_text());assert release['collectors_unchanged']
assert all(subprocess.check_output(['systemctl','is-active',s],text=True).strip()=='active' for s in ['geo-content-api','geo-content-worker','geo-creation-materials'])
assert subprocess.check_output(['systemctl','is-enabled','geo-creation-materials'],text=True).strip()=='enabled'
result={'private_questions':len(cfg['questions']),'historical_observations':sum(coverage.values()),'questions_with_historical_data':sum(bool(v) for v in coverage.values()),'today_private_questions_in_main_geo':leaks,'next_run':health['next_run'],'health':health['health'],'collectors_unchanged':True}
(R/'verified-runtime.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='health'},ensure_ascii=False))
