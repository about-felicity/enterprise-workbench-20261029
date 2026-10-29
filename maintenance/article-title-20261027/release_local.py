import hashlib,json
from pathlib import Path
D=Path(__file__).parent;W=D.parents[1]
mapping={'geo-monitor-deploy/creation/runtime.py':'/opt/monitor/geo-content/creation/runtime.py','geo-source-card-collectors/geo_source_cards/article_title.py':'/opt/monitor/geo-content/engine/geo_source_cards/article_title.py','geo-source-card-collectors/geo_source_cards/rewrite_v2/full_writer.py':'/opt/monitor/geo-content/engine/geo_source_cards/rewrite_v2/full_writer.py','geo-source-card-collectors/geo_source_cards/rewrite_v2/integration.py':'/opt/monitor/geo-content/engine/geo_source_cards/rewrite_v2/integration.py'}
(D/'verification/release.json').write_text(json.dumps({'files':[{'source':s,'server':p,'sha256':hashlib.sha256((W/s).read_bytes()).hexdigest()} for s,p in mapping.items()]},indent=2))
