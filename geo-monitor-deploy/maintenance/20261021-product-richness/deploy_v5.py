import json,subprocess,shutil,time
from pathlib import Path
B=Path('/opt/monitor/geo-content');M=Path('/opt/monitor/geo-capture/maintenance/20261021-product-richness');r=B/'runtime/runs/creation-1792556219-bbc55e13';mark=M/'deployed-v5.json';assert not mark.exists()
assert json.loads((r/'days/2026-10-21/day.json').read_text())['status']=='complete','Wait for 14 article completion'
for p in (B/'runtime/runs').glob('*/api/active.json'):
 assert json.loads(p.read_text()).get('state') in (None,'SUBMITTED'),str(p)
subprocess.run(['systemctl','stop','geo-content-worker'],check=True)
try:
 dst=B/'engine/geo_source_cards/genre_pools.py';backup=M/'backup-v5';backup.mkdir();shutil.copy2(dst,backup/'genre_pools.py');shutil.copy2(M/'stage/engine/geo_source_cards/genre_pools.py',dst)
 mark.write_text(json.dumps({'at':time.time(),'no_inflight_request':True,'future_source_selection_guard':True,'complete_original_test_unchanged':True}))
finally:subprocess.run(['systemctl','start','geo-content-worker'],check=True)
subprocess.run(['systemctl','restart','geo-content-api'],check=True)
print('Future source eligibility guard applied after all 14 completed')
