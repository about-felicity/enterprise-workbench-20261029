"""Retire only specifically proven obsolete observation jobs, preserving evidence."""
from datetime import datetime,timezone,timedelta
import json
from pathlib import Path
import shutil
import subprocess

BASE=Path('/opt/monitor/geo-capture/maintenance/20261015')
EXPORT=Path('/home/user/redroid-doubao/maintenance-20261015')
ARCHIVE=BASE/'retired-observers'
UNIT='geo-editorial-acceptance-current.service'
SOAK='geo-doubao-soak2h-1792030883.service'
TIMER='geo-doubao-soak2h-1792030883-deadline.timer'
STATUS=Path('/home/user/geo-editorial/runtime-api/soak6h/status.json')

def command(*args,check=True):
    r=subprocess.run(args,capture_output=True,text=True,check=check,timeout=30)
    return r.stdout.strip()

def prop(unit,key):return command('systemctl','show',unit,'-p',key,'--value')

assert not (BASE/'retired-observers-applied.json').exists(),'Retirement already recorded'
old=json.loads(STATUS.read_text())
assert old['date']=='2026-10-09' and old['status']=='waiting_prerequisites'
assert old['elapsed_seconds']==0 and not old.get('started_epoch')
assert prop(UNIT,'Transient')=='yes' and prop(UNIT,'ActiveState')=='active'
execution=prop(UNIT,'ExecStart')
assert '-m geo_source_cards.acceptance' in execution
assert '--root /home/user/geo-editorial/runtime-api --date 2026-10-09' in execution
report=json.loads(Path('/opt/monitor/geo-capture/soak/doubao-soak2h-1792030883/report.json').read_text())
assert report['status']=='complete' and report['verdict']=='passed'
assert prop(SOAK,'ActiveState')=='inactive'
for value in report['models'].values():
    assert value['state']=='paused'
    assert prop('geo-native@'+value['batch']+'.service','ActiveState')=='inactive'
assert prop(TIMER,'ActiveState')=='active' and prop(TIMER,'UnitFileState')=='enabled'
reverse=command('systemctl','list-dependencies','--reverse',UNIT,'--plain','--no-pager')
assert not any(name in reverse for name in ('geo-editorial-scheduler.service','geo-editorial-api-worker.service','geo-editorial-coordinator.service'))
ARCHIVE.mkdir(mode=0o700)
for unit in (UNIT,SOAK,TIMER,'geo-doubao-soak2h-1792030883-deadline.service'):
    (ARCHIVE/(unit+'.definition.txt')).write_text(command('systemctl','cat',unit),encoding='utf8')
    (ARCHIVE/(unit+'.status.txt')).write_text(command('systemctl','show',unit,'-p','ActiveState','-p','SubState','-p','MainPID','-p','ExecMainStartTimestamp','-p','ExecMainExitTimestamp','-p','UnitFileState'),encoding='utf8')
shutil.copyfile(STATUS,ARCHIVE/'editorial-status-before.json')
shutil.copyfile(STATUS.with_name('events.jsonl'),ARCHIVE/'editorial-events.jsonl')
(ARCHIVE/'editorial-journal.txt').write_text(command('journalctl','-u',UNIT,'--no-pager'),encoding='utf8')
intent={'at_beijing':datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
    'observer_unit':UNIT,'observer_date':'2026-10-09','observer_verdict':'Not passed; prerequisites never met; observation retired',
    'stop_observer':True,'disable_only_completed_soak_units':[SOAK,TIMER],
    'preserve_business_services':True}
(ARCHIVE/'intent.json').write_text(json.dumps(intent,ensure_ascii=False,indent=2),encoding='utf8')
command('systemctl','stop',UNIT)
command('systemctl','stop',TIMER)
command('systemctl','disable',SOAK,TIMER)
# Do not rewrite the old acceptance result or turn its waiting status into pass.
assert json.loads(STATUS.read_text())['status']=='waiting_prerequisites'
assert prop(UNIT,'ActiveState') in ('inactive','')
assert prop(TIMER,'ActiveState')=='inactive'
assert prop(SOAK,'UnitFileState')=='disabled' and prop(TIMER,'UnitFileState')=='disabled'
result={**intent,'completed_at_beijing':datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
    'observer_active':False,'completed_soak_autostart_disabled':True,'evidence_preserved':True,
    'private_archive':str(ARCHIVE)}
text=json.dumps(result,ensure_ascii=False,indent=2)
(BASE/'retired-observers-applied.json').write_text(text,encoding='utf8')
(EXPORT/'retired-observers-applied.json').write_text(text,encoding='utf8')
(EXPORT/'retired-observers-applied.json').chmod(0o644)
print(text)
