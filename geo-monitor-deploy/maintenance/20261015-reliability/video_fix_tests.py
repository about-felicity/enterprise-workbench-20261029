import json,os,subprocess,time
from pathlib import Path
root=Path('/opt/monitor/geo-capture/maintenance/20261015-reliability/yuanbao-video-fix')
env={**os.environ,'PYTHONPATH':'/tmp/geo-yuanbao-video-stage:/opt/monitor/geo-capture:/home/user/redroid-doubao/geo-batch-code:/home/user/redroid-yuanbao',
     'GEO_TEST_WORKER':'/tmp/geo-yuanbao-video-stage/question_only_worker.py'}
names=['test_runtime_reliability','test_capture_bridge','test_control_panel','test_native_core','test_question_only','test_reliability','test_completion_states','test_send_position_recheck','test_round_cycle','test_completion_fence','test_all_channel_soak']
report={'at':time.time(),'suites':[]}
for python,suites in [('/opt/monitor/geo-capture/venv/bin/python',names),('/home/user/redroid-doubao/worker-venv/bin/python',['test_native_worker_reliability'])]:
    r=subprocess.run([python,'-B','-m','unittest',*suites,'-q'],cwd='/tmp/geo-yuanbao-video-stage/tests',env=env,text=True,capture_output=True,timeout=120)
    report['suites'].append({'tests':suites,'exit_code':r.returncode,'output':r.stdout+r.stderr})
report['passed']=all(s['exit_code']==0 for s in report['suites'])
(root/'tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
out=Path('/tmp/geo-video-fix-export/tests.json');out.write_bytes((root/'tests.json').read_bytes());out.chmod(0o644)
print(json.dumps(report,ensure_ascii=False))
