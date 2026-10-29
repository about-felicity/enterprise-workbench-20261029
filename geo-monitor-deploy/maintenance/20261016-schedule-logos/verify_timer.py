"""Exercise the real save with the SAME existing enabled/time values."""
import json,subprocess,time,uuid
from pathlib import Path
import requests
B=Path('/opt/monitor/geo-capture');R=B/'maintenance/20261016-schedule-logos'
assert not (R/'timer-verified.json').exists(),'Inspect prior same-value save before repeating'
s=requests.Session();s.trust_env=False;base='http://127.0.0.1:3000/api/geo-capture/'
r=s.get(base+'panel',timeout=30);r.raise_for_status();data=r.json();p=data['schedule']
before={k:p[k] for k in ('enabled','time','revision')}
r=s.post(base+'control/schedule',json=before,headers={'Origin':'http://127.0.0.1:3000','X-CSRF-Token':data['csrf'],'X-Action-Id':uuid.uuid4().hex},timeout=45)
r.raise_for_status();result=r.json();assert result['ok']
saved=json.loads((B/'daily_plan.json').read_text());assert saved['enabled']==before['enabled'] and saved['time']==before['time']
timer=subprocess.check_output(['systemctl','show','geo-daily-dispatch.timer','--property=ActiveState,TimersCalendar,NextElapseUSecRealtime'],text=True)
assert ('ActiveState=active' in timer)==before['enabled']
assert before['time']+':00' in timer
release=json.loads((R/'release.json').read_text())
jobs={service:subprocess.check_output(['systemctl','show',service,'--property=MainPID,ActiveEnterTimestampMonotonic'],text=True).strip() for service in release['jobs_before']}
report={'at':time.time(),'same_value_real_save':True,'before':before,'after':result['schedule'],'timer':timer,'collectors_unchanged':jobs==release['jobs_before'],'jobs_after':jobs}
(R/'timer-verified.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='jobs_after'}))
