import json,sys,traceback
from pathlib import Path
sys.path.insert(0,'/opt/monitor/geo-capture')
import all_channel_soak as s
p=json.loads((s.BASE/'all_channel_soak_current.json').read_text());m=s.read(Path(p['root'])/'manifest.json')
for model,job in m['jobs'].items():
    try:print(model,{'verified':len(s.audit(model,job,set()))},s.queue_metrics(model,job))
    except Exception as e:print(model,type(e).__name__,str(e))
print('jobs',m['jobs'])
