"""Disable obsolete completed/test autostarts, never current capture jobs."""
from datetime import datetime,timezone,timedelta
import json
from pathlib import Path
import subprocess

STATE=Path('/opt/monitor/geo-capture/maintenance/20261015-reorganize')
UNITS=('redroid-doubao-hpe14-worker.service','redroid-doubao-soak24h.service',
    'redroid-geo-products.service','redroid-geo-products-account2.service')
def command(*args):return subprocess.run(args,capture_output=True,text=True,check=True,timeout=25).stdout.strip()
assert (STATE/'restart-complete.json').exists()
assert not (STATE/'superseded-units.json').exists()
out=STATE/'superseded-units';out.mkdir(mode=0o700)
for batch in ('geo-products-21x5-account1-20261014','geo-products-21x5-account2-relogin-20261013'):
    value=json.loads((Path('/home/user/redroid-doubao/batches')/batch/'bridge_health.json').read_text())
    assert value['captured']==value['geo_processed']==105
for unit in UNITS:
    raw=command('systemctl','show',unit,'-p','ActiveState','-p','MainPID','-p','UnitFileState')
    fields=dict(line.split('=',1) for line in raw.splitlines() if '=' in line)
    assert fields['MainPID']=='0' and fields['ActiveState'] in ('inactive','failed')
    (out/(unit+'.before.txt')).write_text(raw,encoding='utf8')
    (out/(unit+'.definition.txt')).write_text(command('systemctl','cat',unit),encoding='utf8')
    (out/(unit+'.journal.txt')).write_text(command('journalctl','-u',unit,'-n','100','--no-pager'),encoding='utf8')
command('systemctl','disable',*UNITS)
for unit in UNITS:assert command('systemctl','show',unit,'-p','UnitFileState','--value')=='disabled'
result={'at':datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
    'disabled_autostarts':list(UNITS),'reason':'Old acceptance workers and completed 105/105 jobs replaced by current immutable GEO jobs',
    'current_five_jobs_untouched':True,'historical_failure_status_not_reset':True,'evidence_saved':str(out)}
data=json.dumps(result,ensure_ascii=False,indent=2)
(STATE/'superseded-units.json').write_text(data,encoding='utf8')
p=Path('/home/user/redroid-doubao/reorganization-20261015/superseded-units.json');p.write_text(data,encoding='utf8');p.chmod(0o644)
print(data)
