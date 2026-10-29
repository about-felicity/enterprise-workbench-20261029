"""One-time safe-boundary deployment; never changes questions or task rows."""
import json,shutil,sqlite3,subprocess,time
from pathlib import Path
root=Path('/home/user/redroid-doubao/batches/geo-panel-doubao2-20261020-090001-6bcafb90')
unit='geo-native@'+root.name+'.service'
target=Path('/home/user/redroid-doubao/geo-batch-code/question_only_adapters.py')
backup=Path('/opt/monitor/geo-capture/maintenance/20261020-doubao-landing-wait')
marker=root/'maintenance_pause.json'
def desired():
    with sqlite3.connect('file:/opt/monitor/geo-capture/panel/control.sqlite?mode=ro',uri=True) as db:
        return db.execute("select desired,batch from daily_tasks where model='doubao2' and day='2026-10-20'").fetchone()
assert desired()==('running',root.name)
assert not marker.exists()
source=Path('/tmp/doubao2-landing-adapters.py');compile(source.read_text(),str(target),'exec')
backup.mkdir(mode=0o700,exist_ok=False)
subprocess.run(['systemctl','mask','--runtime',unit],check=True,capture_output=True)
try:
    temp=root/'landing-pause.tmp';temp.write_text(json.dumps({'source':'landing_wait_deploy','requested_at':time.time(),'action':'pause'}));temp.replace(marker)
    end=time.monotonic()+120
    while True:
        health=json.loads((root/'bridge_health.json').read_text())
        active=subprocess.run(['systemctl','is-active',unit],capture_output=True,text=True).stdout.strip()
        if health['status'] in ('maintenance_paused','complete') and active!='active':break
        if time.monotonic()>end:raise TimeoutError('No safe boundary; leave code unchanged')
        time.sleep(2)
    assert health['captured']==health['geo_processed'] and not health['delivery_errors']
    assert not any(health['tasks'].get(v,0) for v in ('prepared','capturing','needs_attention'))
    shutil.copy2(target,backup/'question_only_adapters.before.py')
    (backup/'before-health.json').write_text(json.dumps(health))
    temp=target.with_suffix('.landing-new');shutil.copy2(source,temp);temp.replace(target)
    print(json.dumps({'deployed':True,'drained':health['captured'],'app_not_restarted':True,'backup':str(backup)}),flush=True)
finally:
    if marker.exists() and json.loads(marker.read_text()).get('source')=='landing_wait_deploy':marker.unlink()
    subprocess.run(['systemctl','unmask','--runtime',unit],check=True,capture_output=True)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    if desired()==('running',root.name):subprocess.run(['systemctl','start',unit],check=True)
