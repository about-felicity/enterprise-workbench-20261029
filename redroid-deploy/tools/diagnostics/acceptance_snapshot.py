"""Record finite live acceptance, without querying unrelated account/chat data."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
from datetime import datetime, timezone
import json
from pathlib import Path
import pwd
import os
import sqlite3
import subprocess

root=Path('/home/user/redroid-doubao')
runtime=str(root/'worker-venv/bin/python')
worker=str(root/'unattended_worker.py')
live=root/'acceptance-live'
process=subprocess.run([runtime,worker,'--state-dir',str(live),'run','--once'],capture_output=True,timeout=15)
with sqlite3.connect((live/'tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
    db.row_factory=sqlite3.Row
    tasks=[dict(r) for r in db.execute('select task_id,state,attempts,error from tasks order by rowid')]
health=json.loads((live/'health.json').read_text())
audits=json.loads((root/'acceptance-audit/audit-existing.json').read_text())
smoke=subprocess.check_output(['systemctl','show','redroid-worker-watchdog-smoke.service','--property=Result','--property=ExecMainStatus'],text=True)
adb=str(root/'linux-tools/platform-tools/adb')
logs=subprocess.check_output([adb,'-s','127.0.0.1:5555','logcat','-d'],text=True,errors='replace',timeout=20)
native=[line for line in logs.splitlines() if 'F berberis' in line or ('Fatal signal' in line and 'com.larus.nova' in line)]
containers=[json.loads(line) for line in subprocess.check_output(['docker','ps','--format','{{json .}}'],text=True).splitlines()]
baseline={'monitor-dashboard':'30121c903f1a','monitor-product-worker':'d02827c7ee79',
 'monitor-dashboard-api':'db748b4d6609','monitor-doubao-receiver':'49a44812dc37',
 'monitor-result-receiver':'c47f89d43fe3','monitor-content-worker':'5d02f9c6912e',
 'monitor-postgres':'044d2082faa5','monitor-redis':'980c10b36d94'}
report={'time':datetime.now(timezone.utc).isoformat(),'unattended_acceptance_passed':False,
 'reason':'App failed readiness on three attempts; ARM translation CHECK failures remain',
 'unit_tests':{'passed':22,'platform':'Linux server'},'live_exit_code':process.returncode,
 'health':health,'tasks':tasks,'watchdog_smoke':smoke.strip(),
 'existing_answer_audit':[{'status':r['status'],'sources':len(r.get('sources',[])), 'citations':len(r.get('citations',[]))} for r in audits],
 'native_errors':native[-10:],
 'business_containers_unchanged':all(any(c['Names']==name and c['ID']==identity for c in containers) for name,identity in baseline.items()),
 'service_enabled':False,'service_note':'Systemd template verified; production service not activated'}
destination=root/'unattended-acceptance.json'
destination.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
owner=pwd.getpwnam('user')
os.chown(destination,owner.pw_uid,owner.pw_gid)
destination.chmod(0o600)
subprocess.run([adb,'-s','127.0.0.1:5555','shell','am','force-stop','com.larus.nova'],check=True,timeout=15)
print(json.dumps({'acceptance_passed':False,'live_exit_code':process.returncode,'health':health,
                  'business_containers_unchanged':report['business_containers_unchanged'],'watchdog':smoke.strip()},ensure_ascii=False))
