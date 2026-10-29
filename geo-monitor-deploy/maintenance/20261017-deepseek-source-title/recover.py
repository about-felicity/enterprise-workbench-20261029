"""Load reader fix and reread the existing clicked native request, never resend."""
import importlib.util
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time

sys.path.insert(0,'/home/user/redroid-deepseek/code')
spec=importlib.util.spec_from_file_location('title_fixed_reader','/tmp/deepseek-source-title-reader-1017.py')
reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
root=Path('/home/user/redroid-deepseek/batches/geo-panel-deepseek-app-20261017-094524')
unit='geo-native@'+root.name+'.service'
with sqlite3.connect((root/'tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 task=dict(db.execute('select * from tasks where ordinal=8').fetchone())
 assert task['state']=='prepared'
 clicks=db.execute("select count(*) from events where task_id=? and event='send_click_intent_committed'",(task['task_id'],)).fetchone()[0]
 assert clicks==1
 snapshot=reader.Reader(root).lookup(task)
 assert snapshot['status']=='complete' and snapshot['first_user_turn'] is True
 assert snapshot['thinking_enabled'] is False and snapshot['search_enabled'] is True
 assert len(snapshot['sources'])==12 and snapshot['source_title_missing_count']==2
 assert len(snapshot['body_markdown'])==1035
def counts():
 with sqlite3.connect((root/'tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  return dict(db.execute('select state,count(*) from tasks group by state'))
before=counts()
backup=Path('/opt/monitor/geo-capture/backups')/('deepseek-source-title-'+str(int(time.time())))
backup.mkdir(mode=0o700)
(backup/'verified_original_result.json').write_text(json.dumps(snapshot,ensure_ascii=False))
subprocess.run(['systemctl','stop','geo-daily-control.service'],check=True)
try:
 subprocess.run(['systemctl','stop',unit],check=True)
 assert counts()==before
 for name in ['reader','worker']:
  target=Path('/home/user/redroid-deepseek/code')/(name+'.py')
  shutil.copy2(target,backup/target.name)
  shutil.copy2('/tmp/deepseek-source-title-'+name+'-1017.py',target)
 assert counts()==before
finally:
 subprocess.run(['systemctl','start',unit],check=True)
 subprocess.run(['systemctl','start','geo-daily-control.service'],check=True)
print(json.dumps({'before':before,'after':counts(),'backup':str(backup),'existing_clicks':clicks,
 'preserved_body_length':len(snapshot['body_markdown']),'sources':len(snapshot['sources']),
 'missing_original_titles':2,'queue_reset':False}))
