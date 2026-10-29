import sys,json,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from geo_source_cards.runtime import atomic_json
p=Path('/opt/monitor/geo-content/runtime/worker_drain.json');atomic_json(p,{'enabled':False,'reason':'User-authorized recovery; allow in-flight requests to finish','at':time.time()})
print('draining set')

