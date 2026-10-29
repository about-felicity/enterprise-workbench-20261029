import hashlib,json,shutil,sqlite3,subprocess,time
from pathlib import Path
R=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261028-090004-02abccba')
D=Path('/opt/monitor/maintenance/yuanbao-update-20261028');D.mkdir(parents=True,exist_ok=True)
service='geo-native@'+R.name+'.service'
files=[('android_ui.py','/home/user/redroid-yuanbao/android_ui.py','6bc4a904722c0449b66ba7339bf11d2a659636234ac9c1ab94bcf1812010ff5e','yuanbao-deploy/android_ui.py'),('question_only_worker.py','/home/user/redroid-doubao/geo-batch-code/question_only_worker.py','9c931b493777086b7ebb4136b99d89ab5d60c75de40d87d4e899e25662266a2f','redroid-deploy/question_only_worker.py')]
for name,target,expected,_ in files:
 assert hashlib.sha256(Path(target).read_bytes()).hexdigest()==expected,'Source changed: '+target
 compile((Path('/tmp/yuanbao28-release')/name).read_text(),target,'exec')
with sqlite3.connect(R/'tasks.sqlite') as db:
 assert db.execute("select count(*) from tasks where state!='pending'").fetchone()[0]==0,'Task advanced; review current state first'
 assert db.execute("select count(*) from events where event='send_click_intent_committed'").fetchone()[0]==0,'Sending already occurred'
subprocess.run(['systemctl','stop',service],check=True,timeout=90)
with sqlite3.connect(R/'tasks.sqlite') as db:
 with sqlite3.connect(D/'tasks-before.sqlite') as out:db.backup(out)
release=[]
for name,target,expected,source in files:
 shutil.copy2(target,D/(name+'.before'))
 shutil.copyfile(Path('/tmp/yuanbao28-release')/name,target)
 release.append({'source':source,'server':target,'sha256':hashlib.sha256(Path(target).read_bytes()).hexdigest()})
(D/'release.json').write_text(json.dumps({'files':release},indent=2))
subprocess.run(['systemctl','start',service],check=True)
print('Deployed optional-update dismissal; resumed original unsent batch')
