import json
from pathlib import Path
root=Path('/opt/monitor/geo-content/studio')
for lid in ['library-1ec41916a4274125af9ee1b01a694631','library-3e3a558b9ef4409bbbcd2560fbefc51c']:
 r=json.loads((root/'library'/(lid+'.json')).read_text());u=r['uploads'][-1];e=json.loads((root/'imports'/u['import_id']/'extraction.json').read_text())
 print(json.dumps({'library':lid,'name':r['name'],'text':e['text'][:2400]},ensure_ascii=False))
