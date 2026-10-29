"""Start the newly requested account1 batch while preserving completed history."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import sys,os,json,sqlite3,subprocess,shutil,time
from pathlib import Path
os.umask(0o077)
base=Path('/home/user/redroid-doubao')
sys.path.insert(0,str(base/'geo-batch-code'))
from unattended_core import Queue
from active_database_accounts import current_uid
service='redroid-geo-products.service'
assert current_uid('doubao-hpe14-13-test').endswith('385833')
assert subprocess.run(['systemctl','is-active',service],capture_output=True,text=True).stdout.strip() in ('inactive','failed')
old=base/'batches/geo-products-21x5-20261013'
health=json.loads((old/'bridge_health.json').read_text())
assert health['status']=='complete' and health['captured']==health['geo_processed']==105
with sqlite3.connect((old/'tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 assert db.execute("select count(*) from tasks where state='completed'").fetchone()[0]==105
batch='geo-products-21x5-account1-20261014';root=base/'batches'/batch
assert not root.exists(),'Batch already exists; inspect it instead of executing setup again'
questions=json.loads((base/'geo-batch-code/geo_questions.json').read_text('utf-8-sig'))
assert len(questions)==len(set(questions))==21
q=Queue(root/'tasks.sqlite');q.enqueue(batch,questions*5,True)
assert q.summary()=={'pending':105}
unit=Path('/etc/systemd/system/redroid-geo-products.service')
backup=base/'account1-new-batch-backup-20261014'
assert not backup.exists();backup.mkdir(mode=0o700)
shutil.copy2(unit,backup/unit.name)
shutil.copy2(old/'bridge_health.json',backup/'completed-old-batch-health.json')
shutil.copyfile(base/'redroid-geo-products.account1-new.service',unit)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','reset-failed',service],check=True)
subprocess.run(['systemctl','start',service],check=True)
assert json.loads((old/'bridge_health.json').read_text())==health
print('Account1 new independent 105-task batch started; old 105/105 preserved:',batch,flush=True)
