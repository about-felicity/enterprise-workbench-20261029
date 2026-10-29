"""One-time, guarded recovery of diagnosed home-page navigation failure."""
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
import uuid

BASE=Path('/opt/monitor/geo-capture')
ROOT=BASE/'batches/geo-wenxin_card-21x6-20261015'
sys.path.insert(0,str(BASE))


def command(*args):
    return subprocess.run(args,capture_output=True,text=True,check=True,timeout=30).stdout


def completed(db):
    return list(db.execute("select task_id,result,finished from captures where state='completed' order by task_id"))


if '--recover-only' in sys.argv:
    from geo_source_cards.runtime import process_lock
    from geo_source_cards.journal import Journal
    from geo_source_cards.search_recovery import SearchRecovery
    with process_lock(ROOT/'bridge.lock'),process_lock(ROOT/'collector/collector.lock'):
        journal=Journal(ROOT/'collector/tasks.sqlite')
        try:
            rows=journal.db.execute("select * from captures where state='needs_attention'").fetchall()
            assert len(rows)==1 and not journal.db.execute("select 1 from captures where state='capturing'").fetchone()
            task=dict(rows[0])
            assert task['model']=='wenxin_card' and task['task_id']=='089b054835c2923394f55a560dd2c2de08ba971b4ec5fe8cf242ab3839ea306d'
            assert 'Page.goto: net::ERR_NETWORK_CHANGED at https://www.baidu.com/' in task['error'] and task['result'] is None
            before=completed(journal.db)
            result=SearchRecovery(journal,ROOT/'collector').failure(task,task['error'])
            assert result['kind']=='read_error' and result['attempt']==1 and not result['exhausted']
            assert completed(journal.db)==before
            print(json.dumps({'recovered_task':task['task_id'],'completed_unchanged':len(before),'recovery':result},ensure_ascii=False))
        finally:journal.close()
    raise SystemExit(0)

assert command('systemctl','show','geo-capture-wenxin-card.service','-p','ActiveState','--value').strip()=='failed'
stage=Path(sys.argv[1])
module=BASE/'venv/lib/python3.10/site-packages/geo_source_cards/search_recovery.py'
old=module.read_bytes();new=(stage/'search_recovery.py').read_bytes()
needle=b'            "Page.goto: net::ERR_NAME_NOT_RESOLVED",'
assert old.count(needle)==1 and b'Page.goto: net::ERR_NETWORK_CHANGED' not in old
assert new==old.replace(needle,needle+b'\n            "Page.goto: net::ERR_NETWORK_CHANGED",')
backup=BASE/'backups'/('wenxin-network-change-'+str(int(time.time())))
backup.mkdir(mode=0o700)
for path in (module,ROOT/'capture.log',ROOT/'bridge_health.json',ROOT/'collector/search_recovery.json'):
    shutil.copy2(path,backup/path.name)
with sqlite3.connect((ROOT/'collector/tasks.sqlite').as_uri()+'?mode=ro',uri=True) as source:
    with sqlite3.connect(backup/'tasks-before.sqlite') as target:source.backup(target)
source.close();target.close()
report={'backup':str(backup),'old_module_sha256':hashlib.sha256(old).hexdigest(),'new_module_sha256':hashlib.sha256(new).hexdigest(),
        'diagnosis':'Home Page.navigate at controller.py:833 failed before _navigate_fresh(query): ERR_NETWORK_CHANGED',
        'at':time.time()}
temporary=module.with_suffix('.network-fix.tmp');temporary.write_bytes(new);temporary.chmod(0o644);temporary.replace(module)
print(command(str(BASE/'venv/bin/python'),'-B','-m','unittest','discover','-s',str(stage),'-p','test_search_recovery.py'))
recovered=command('runuser','-u','user','--',str(BASE/'venv/bin/python'),'-B',str(Path(__file__)),'--recover-only')
report['recovery']=json.loads(recovered)
(backup/'recovery-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
from native_soak import API
api=API();action_id=uuid.uuid4().hex
(backup/'resume-intent.json').write_text(json.dumps({'model':'wenxin_card','action':'resume','key':action_id}))
report['resume']=api.action('wenxin_card','resume',{},action_id)
(backup/'recovery-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
