"""Install only the new prompt protocol, after old collectors have drained."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

BASE=Path('/opt/monitor/geo-capture')
CODE=Path('/home/user/redroid-doubao/geo-batch-code')
EXPECTED={'control_panel.py','native_entry.py','panel.html','yuanbao-delivery.py',
          'question_only_core.py','question_only_adapters.py','question_only_delivery.py','question_only_worker.py','test_question_only.py'}
sys.path.insert(0,str(BASE))
from native_soak import API
panel=API().panel()
assert all(m['current']['service_state'] not in {'active','activating','deactivating'} for m in panel['models']), 'Wait for drain, do not force stop'
assert all(not m['current']['needs_review'] for m in panel['models']), 'Unresolved native send must be reconciled first'
backup=BASE/'backups'/('question-only-'+str(int(time.time())))
backup.mkdir(mode=0o700)
with zipfile.ZipFile('/tmp/geo-question-only-runtime.zip') as archive:
    assert set(archive.namelist())==EXPECTED
    for name in EXPECTED:
        if name.endswith('.py'):ast.parse(archive.read(name).decode('utf-8-sig'))
    installed=[]
    for name in EXPECTED:
        if name=='test_question_only.py':target=backup/'tests'/name
        elif name=='yuanbao-delivery.py':target=Path('/home/user/redroid-yuanbao/delivery.py')
        elif name.startswith('question_only_'):target=CODE/name
        else:target=BASE/name
        target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():shutil.copy2(target,backup/(name+'.before'))
        target.write_bytes(archive.read(name));target.chmod(0o644 if target.parent==BASE else 0o600)
        installed.append({'path':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
subprocess.run(['/home/user/redroid-doubao/worker-venv/bin/python','-B','-m','unittest','discover','-s',str(backup/'tests'),'-p','test_question_only.py','-q'],
               env={**__import__('os').environ,'PYTHONPATH':str(CODE)},check=True,timeout=40)
subprocess.run(['systemctl','restart','geo-monitor-status.service'],check=True)
record={'installed_at':time.time(),'backup':str(backup),'files':installed,
        'prompt_mode':'question_only','old_jobs_preserved':True,'collectors_or_android_restarted':False}
(BASE/'question_only_release.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record))
