import subprocess,shlex
code="""
import time,json
from monitor_core import database,analytics,employee_assessment,performance_store
for month,last in [('2026-10','2026-10-31'),('2026-11','2026-11-02')]:
 t=time.monotonic();runs=database.load_owned_product_runs(day_from=month+'-01',day_to=last);a=time.monotonic()
 rows=analytics.daily_owned_product_recommendations(runs,['deepseek','doubao','wenxin','yuanbao'],day_limit=3660);b=time.monotonic()
 result=employee_assessment.build_assessment(rows,month=month,as_of=last);c=time.monotonic()
 print(json.dumps({'month':month,'query_s':a-t,'matrix_s':b-a,'assessment_s':c-b,'runs':sum(map(len,runs.values())),'run_json_bytes':len(json.dumps(runs,default=str))}),flush=True)
t=time.monotonic();performance_store.editor_data('2026-10','2026-10-30');print('EDITOR',time.monotonic()-t)
"""
r=subprocess.run(['docker','exec','-w','/app','monitor-dashboard-api','python','-B','-c',code],capture_output=True,text=True,timeout=180)
print(r.stdout);print(r.stderr[-1200:]);assert r.returncode==0
ssh=['ssh','-i','/etc/monitor-vps2-tunnel/id_ed25519','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/etc/monitor-vps2-tunnel/known_hosts','root@117.55.234.72']
remote="""
from pathlib import Path
s=Path('/etc/nginx/nginx.conf').read_text().splitlines()
for i,line in enumerate(s):
 if 'location' in line and any(x in line for x in ['performance','/geo_monitor/api/','/geo_monitor/ {']):print('\\n'.join(s[i:i+30]))
"""
r=subprocess.run(ssh+['python3 -c '+shlex.quote(remote)],capture_output=True,text=True,timeout=45);print(r.stdout);assert r.returncode==0
