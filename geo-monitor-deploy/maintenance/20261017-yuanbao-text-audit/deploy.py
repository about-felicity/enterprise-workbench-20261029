import hashlib
from pathlib import Path
import shutil
import subprocess
import time

root=Path('/opt/monitor')
stage=Path('/tmp/geo-yuanbao-text-candidate')
backup=root/'geo-capture/backups'/('yuanbao-native-text-'+str(int(time.time())))
backup.mkdir(mode=0o700)
files=['monitor_core/native_text.py','monitor_core/ingestion.py','monitor_core/owned_products.py',
       'monitor_core/product_analysis.py','monitor_core/analytics.py','save_doubao_refs.py']
expected={
 'monitor_core/ingestion.py':'e70b4ee66e8ce82f92bb6fe98e9c798c2c192e6cdc02cc56812f852f4eabcb89',
 'monitor_core/owned_products.py':'094d2df5589fc95023640e3f2bcb399887eb0777f0a8bf8658edf61dc7d517e4',
 'monitor_core/product_analysis.py':'7e8704ac1f60e3b7a4c77a8d47ed02888e679fc368a1d9a0c342b932f97c4071'}
for name in files:
 compile((stage/name).read_text(),name,'exec')
 if name in expected:assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected[name]
 if (root/name).exists():
  target=backup/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/name,target)
# Stop only enrichment while its source and projections are repaired. Collection
# queues and Android processes remain active and durable.
subprocess.run(['docker','stop','monitor-product-worker'],check=True,timeout=45)
for name in files:
 target=root/name;temporary=target.with_name(target.name+'.native-text-stage')
 shutil.copy2(stage/name,temporary);temporary.chmod(0o644);temporary.replace(target)
subprocess.run(['docker','restart','monitor-result-receiver'],check=True,timeout=45)
subprocess.run(['docker','restart','monitor-dashboard-api'],check=True,timeout=45)
print('source_backup='+str(backup))
print('Enrichment paused for transactional repair; capture workers unchanged')
