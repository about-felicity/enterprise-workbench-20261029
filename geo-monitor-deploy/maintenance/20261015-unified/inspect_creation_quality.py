import json
from pathlib import Path
root=Path('/opt/monitor/geo-content/runtime/runs/creation-1792060761-3c2baae0')
for path in (root/'queue').glob('*/ticket.json'):
    ticket=json.loads(path.read_text())
    if ticket['state']!='needs_attention':continue
    location=root/ticket['location']
    print(json.dumps({'ticket':ticket,'location_files':[p.name for p in location.iterdir()],
                     'repair_blocked':(path.parent/'auto_repair_blocked.json').exists(),
                     'repair_exhausted':(path.parent/'auto_repair_exhausted.json').exists()},ensure_ascii=False))
    research=location/'research_input.json'
    if research.exists():
        value=json.loads(research.read_text());blueprint=value.get('reference_design',{})
        print(json.dumps({'reference_design':blueprint,'observations':[{'source_urls':[s['url'] for s in r.get('sources',[])]} for r in value.get('observations',[])]},ensure_ascii=False))
