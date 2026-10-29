"""Validate the second device in a separate process; never send a question."""
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

sys.path.insert(0,'/home/user/redroid-deepseek/code')
import device
# Process-local overrides only. The primary collector's module and process are untouched.
device.CONTAINER='deepseek-hpe14-account2'
device.SERIAL='127.0.0.1:5561'
import android

d=device.device()
login=device.auth(d)
assert login['status']=='ready', login['message']
app=android.Android.__new__(android.Android);app.device=d
app.enforce_modes()
assert app.mode('智能搜索')[0] is True
assert app.mode('深度思考')[0] is False

def account(container):
    path=Path('/var/lib/docker/volumes')/(container+'-data')/'_data/data/com.deepseek.chat/databases/deepseek_chat.db'
    with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
        rows=db.execute('select id,length(token) from app_user_info where length(id)>0 and length(token)>0').fetchall()
    assert len(rows)==1, 'A single persisted authenticated account must be present'
    return rows[0][0]

second=account(device.CONTAINER)
first=account('deepseek-hpe14-android13')
container=json.loads(subprocess.check_output(['docker','inspect',device.CONTAINER]))[0]
assert any(m.get('Name')==device.CONTAINER+'-data' and m['Destination']=='/data' for m in container['Mounts'])
metadata=Path('/home/user/redroid-deepseek-account2/device.json')
value=json.loads(metadata.read_text())
value.update(state='ready',login_checked_at=time.time(),account_token_persisted=True,
             same_account_as_primary=second==first,thinking_enabled=False,search_enabled=True)
metadata.write_text(json.dumps(value,ensure_ascii=False,indent=2))
print(json.dumps({'status':login['status'],'account_token_persisted':True,
                  'same_account_as_primary':second==first,'thinking_enabled':False,
                  'search_enabled':True,'scheduled':value['scheduled'],'questions_sent':0},ensure_ascii=False))
