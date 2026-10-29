"""Always restore the ordinary enrichment daemon after the one-off repair."""
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path('/opt/monitor/geo-capture/maintenance/20261017-yuanbao-text-audit')
if '--child' in sys.argv:
 try:
  result=subprocess.run(['docker','exec','monitor-dashboard-api','python','/app/geo-capture/maintenance/20261017-yuanbao-text-audit/reanalyse.py'])
  print('repair_exit='+str(result.returncode),flush=True)
 finally:subprocess.run(['docker','start','monitor-product-worker'],check=True)
 raise SystemExit(0)
config=json.loads(subprocess.check_output(['docker','inspect','monitor-product-worker']))[0]
keys={'REMOTE_PRODUCT_AI_CALLS_PER_HOUR','REMOTE_PRODUCT_AI_MODEL_BATCH','REMOTE_PRODUCT_AI_RETRY_DELAY'}
limits=dict(value.split('=',1) for value in config['Config']['Env'] if value.split('=',1)[0] in keys)
assert set(limits)==keys
(ROOT/'review-limits.json').write_text(json.dumps(limits,indent=2))
with (ROOT/'reanalysis.log').open('a') as log:
 process=subprocess.Popen([sys.executable,__file__,'--child'],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({'pid':process.pid,'limits':limits}))
