import ast,json,zipfile,hashlib
from pathlib import Path
root=Path.cwd();out=Path(__file__).parent
mapping={
 'geo-monitor-deploy/runtime_reliability.py':['/opt/monitor/geo-capture/runtime_reliability.py','/home/user/redroid-doubao/geo-batch-code/runtime_reliability.py','/home/user/redroid-yuanbao/runtime_reliability.py'],
 'redroid-deploy/question_only_worker.py':['/home/user/redroid-doubao/geo-batch-code/question_only_worker.py'],
 'redroid-deploy/question_only_delivery.py':['/home/user/redroid-doubao/geo-batch-code/question_only_delivery.py'],
 'yuanbao-deploy/delivery.py':['/home/user/redroid-yuanbao/delivery.py'],
 'yuanbao-deploy/native_core.py':['/home/user/redroid-yuanbao/native_core.py'],
 'yuanbao-deploy/native_client.py':['/home/user/redroid-yuanbao/native_client.py'],
 'geo-monitor-deploy/capture_bridge.py':['/opt/monitor/geo-capture/capture_bridge.py'],
 'geo-monitor-deploy/control_panel.py':['/opt/monitor/geo-capture/control_panel.py'],
 'geo-monitor-deploy/panel.html':['/opt/monitor/geo-capture/panel.html'],
 'geo-monitor-deploy/creation/panel.html':['/opt/monitor/geo-content/creation/panel.html'],
 'geo-source-card-collectors/web_collectors/collector.py':['/opt/monitor/geo-capture/venv/lib/python3.10/site-packages/web_collectors/collector.py']}
mapping['geo-source-card-collectors/geo_source_cards/cli.py']=['/opt/monitor/geo-capture/venv/lib/python3.10/site-packages/geo_source_cards/cli.py']
for name in ['question_only_core.py','question_only_adapters.py']:
    mapping['redroid-deploy/'+name]=['/home/user/redroid-doubao/geo-batch-code/'+name]
files=[]
with zipfile.ZipFile(out/'stage.zip','w',zipfile.ZIP_DEFLATED) as z:
    for relative,targets in mapping.items():
        p=root/relative;data=p.read_bytes()
        if p.suffix=='.py':ast.parse(data.decode('utf-8-sig'))
        name='creation-panel.html' if '/creation/' in relative else p.name
        if '/web_collectors/' in relative:name='web_collectors/'+p.name
        if '/geo_source_cards/' in relative:name='geo_source_cards/'+p.name
        z.writestr(name,data);files.append({'source':relative,'stage':name,'targets':targets,'sha256':hashlib.sha256(data).hexdigest()})
    z.write(root/'geo-source-card-collectors/web_collectors/__init__.py','web_collectors/__init__.py')
    z.writestr('geo_source_cards/__init__.py',"__path__.append('/opt/monitor/geo-capture/venv/lib/python3.10/site-packages/geo_source_cards')\n")
    tests=[*root.glob('geo-monitor-deploy/tests/test_*.py'),*root.glob('yuanbao-deploy/tests/test_native_core.py'),
           *root.glob('redroid-deploy/tests/test_question_only.py'),*root.glob('geo-source-card-collectors/tests/test_*reliability.py'),
           *[root/'geo-source-card-collectors/tests'/name for name in ['test_collectors.py','test_completion_states.py','test_send_position_recheck.py','test_round_cycle.py','test_completion_fence.py']]]
    for p in tests:z.write(p,'tests/'+p.name)
    z.writestr('manifest.json',json.dumps({'files':files},ensure_ascii=False,indent=2))
print(json.dumps({'files':len(files),'bytes':(out/'stage.zip').stat().st_size}))
