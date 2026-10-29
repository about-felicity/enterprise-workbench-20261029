import json,os,subprocess,time
from pathlib import Path
env={**os.environ,'PYTHONPATH':'/tmp/geo-reliability-stage:/opt/monitor/geo-capture:/home/user/redroid-doubao/geo-batch-code:/home/user/redroid-yuanbao'}
root=Path('/opt/monitor/geo-capture/maintenance/20261015-reliability');report={'at':time.time(),'suites':[]}
for python,names in [('/opt/monitor/geo-capture/venv/bin/python',['test_runtime_reliability','test_capture_bridge','test_control_panel','test_native_core','test_question_only','test_reliability','test_completion_states','test_send_position_recheck','test_round_cycle','test_completion_fence','test_all_channel_soak']),
                     ('/home/user/redroid-doubao/worker-venv/bin/python',['test_native_worker_reliability'])]:
    result=subprocess.run([python,'-B','-m','unittest',*names,'-q'],cwd='/tmp/geo-reliability-stage/tests',env=env,text=True,capture_output=True,timeout=120)
    report['suites'].append({'tests':names,'exit_code':result.returncode,'output':result.stdout+result.stderr})
report['passed']=all(s['exit_code']==0 for s in report['suites'])
(root/'tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
target=Path('/tmp/geo-reliability-export/tests.json');target.write_bytes((root/'tests.json').read_bytes());target.chmod(0o644)
print(json.dumps(report,ensure_ascii=False))
