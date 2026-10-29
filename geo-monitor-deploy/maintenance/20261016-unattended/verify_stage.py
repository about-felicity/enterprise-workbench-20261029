import json
import os
from pathlib import Path
import re
import subprocess

root=Path('/opt/monitor/geo-capture/maintenance/20261016-unattended')
stage=root/'stage'
env={**os.environ,'PYTHONPATH':str(stage)+':/opt/monitor/geo-capture:/home/user/redroid-doubao/geo-batch-code:/home/user/redroid-yuanbao',
     'GEO_TEST_WORKER':str(stage/'question_only_worker.py')}
report=[]
for path in sorted((stage/'tests').glob('test_*.py')):
    python='/home/user/redroid-doubao/worker-venv/bin/python' if path.name in {'test_unattended.py','test_native_worker_reliability.py','test_question_only.py'} else '/opt/monitor/geo-capture/venv/bin/python'
    result=subprocess.run([python,'-B','-m','unittest','discover','-s','tests','-p',path.name,'-q'],
                          cwd=stage,env=env,capture_output=True,text=True,timeout=45)
    output=result.stdout+result.stderr
    (root/(path.stem+'.log')).write_text(output)
    match=re.search(r'Ran (\d+) tests?',output)
    value={'suite':path.name,'passed':result.returncode==0,'tests':int(match[1]) if match else 0}
    report.append(value);print(json.dumps(value),flush=True)
    if result.returncode:print(output,flush=True)
summary={'passed':all(r['passed'] for r in report),'tests':sum(r['tests'] for r in report),'suites':report}
(root/'tests.json').write_text(json.dumps(summary,indent=2))
assert summary['passed'],'Fix failed suites before deployment'
