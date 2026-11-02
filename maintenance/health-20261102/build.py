from pathlib import Path
import json
work=Path(__file__).parent
old=Path('maintenance/task-health-20261031/recover_today_http.py').read_text('utf-8')
old=old.split("\nfor p in (runtime.BASE/'runs').glob('*/job.json'):",2)
http=old[0].replace("{'plan-c9017fa6d4684997a3370eaf9fc5a553','plan-47fbabcdee8c4807a4f895016f830dbc'}","{'plan-6c8ef07753894b848847aca2005c99ee'}")+"\nfor p in (runtime.BASE/'runs').glob('*/job.json'):"+old[1]
http=http.replace('2026-10-31','2026-11-02').replace('recovery-20261031','recovery-20261102')
source=Path('maintenance/task-health-20261031/recover_sources.py').read_text('utf-8').replace('2026-10-31','2026-11-01').replace('recovery-20261031','recovery-20261102')
for name,script in [('recover_http',http),('recover_sources',source)]:
 (work/(name+'.py')).write_text(script,encoding='utf-8')
 (work/('run_'+name+'.py')).write_text('import subprocess\nraise SystemExit(subprocess.run(["/home/user/geo-editorial/venv/bin/python","-B","-c",'+repr(script)+'],timeout=360).returncode)\n',encoding='utf-8')
