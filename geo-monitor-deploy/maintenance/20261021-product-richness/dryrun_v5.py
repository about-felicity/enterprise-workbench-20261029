import sys,json,collections
from pathlib import Path
sys.path.insert(0,'/opt/monitor/geo-capture/maintenance/20261021-product-richness/stage/engine')
from geo_source_cards.genre_pools import classify_source
sources=json.loads(Path('/opt/monitor/geo-content/runtime/runs/creation-1792556219-bbc55e13/days/2026-10-21/media_articles.json').read_text())
rows=[classify_source(v) for v in sources];result={'rows':len(rows),'counts':dict(collections.Counter(v['genre']+':'+v['status'] for v in rows)),'excluded_for_neutral_details':sum(bool(v['products_without_neutral_details']) for v in rows)}
Path('/opt/monitor/geo-capture/maintenance/20261021-product-richness/source-selection-v5.json').write_text(json.dumps(result));print(json.dumps(result))
