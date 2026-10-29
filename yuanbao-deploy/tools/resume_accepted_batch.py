"""Release the owned three-question acceptance cap, then resume the same batch."""
from contextlib import closing
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time
import uuid

import requests

BASE=Path('/home/user/redroid-yuanbao')
ROOT=BASE/'batches/geo-yuanbao-21x5-20261015'
SERVICE='geo-native@'+ROOT.name+'.service'
audit=json.loads((ROOT/'capture-audit.json').read_text())
assert audit['captured']==audit['processed']==3 and audit['all_processed_database_fidelity']
with closing(sqlite3.connect((ROOT/'tasks.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
    assert db.execute("select count(*) from tasks where state not in ('pending','completed')").fetchone()[0]==0
assert json.loads((ROOT/'maintenance_pause.json').read_text())['source']=='acceptance_limit'
dropin=Path('/etc/systemd/system')/(SERVICE+'.d')/'acceptance.conf'
assert dropin.read_text().strip()=='[Service]\nEnvironment=YUANBAO_CAPTURE_LIMIT=3'
assert subprocess.run(['systemctl','is-active',SERVICE],capture_output=True,text=True).stdout.strip()=='inactive'
backup=BASE/'diagnostics'/('acceptance-release-'+str(int(time.time())))
backup.mkdir(mode=0o700)
for name in ('capture-audit.json','bridge_health.json','maintenance_pause.json'):
    shutil.copy2(ROOT/name,backup/name)
shutil.copy2(dropin,backup/'acceptance.conf')
shutil.copy2(BASE/'native_client.py',backup/'native_client.before.py')
shutil.copy2('/tmp/yuanbao_native_client.py',BASE/'native_client.py')
dropin.unlink()
subprocess.run(['systemctl','daemon-reload'],check=True)
session=requests.Session();session.trust_env=False
panel=session.get('http://127.0.0.1:8803/api/panel',timeout=15).json()
model=next(m for m in panel['models'] if m['id']=='yuanbao')
assert model['current']['batch']==ROOT.name
response=session.post('http://127.0.0.1:8803/api/control/yuanbao/resume',json={},headers={
    'Origin':'http://127.0.0.1:8803','X-CSRF-Token':panel['csrf'],'X-Action-Id':uuid.uuid4().hex},timeout=30)
response.raise_for_status()
assert response.json()['batch']==ROOT.name
record={'resumed_at':time.time(),'batch':ROOT.name,'completed_preserved':3,'backup':str(backup),
        'limit_removed':True,'same_batch_resumed':True,'projection_opened':False}
(BASE/'capture_release.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record))
