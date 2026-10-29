import hashlib
import json
from pathlib import Path
import zipfile

root=Path.cwd();out=Path(__file__).parent
mapping={}
for name in ['question_only_worker.py','question_only_core.py','unattended_core.py']:
    mapping['redroid-deploy/'+name]='/home/user/redroid-doubao/geo-batch-code/'+name
for name in ['capture_bridge.py','control_panel.py','fleet_status.py','panel.html','daily_dispatch.py']:
    mapping['geo-monitor-deploy/'+name]='/opt/monitor/geo-capture/'+name
for name in ['geo_source_cards/cli.py','geo_source_cards/journal.py','geo_source_cards/search_recovery.py','web_collectors/collector.py']:
    mapping['geo-source-card-collectors/'+name]='/opt/monitor/geo-capture/venv/lib/python3.10/site-packages/'+name
baseline=json.loads(Path('geo-monitor-deploy/releases/20261015/unified-current/manifest.json').read_text('utf8'))
expected={item['server']:item['sha256'] for item in baseline['files']}
for local,server in [('unattended_core.before.py','/home/user/redroid-doubao/geo-batch-code/unattended_core.py'),
                     ('search_recovery.before.py','/opt/monitor/geo-capture/venv/lib/python3.10/site-packages/geo_source_cards/search_recovery.py')]:
    expected[server]=hashlib.sha256((out/local).read_bytes()).hexdigest()
files=[]
with zipfile.ZipFile(out/'stage.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for source,target in mapping.items():
        name=source.split('geo-source-card-collectors/')[-1] if source.startswith('geo-source-card-collectors/') else Path(source).name
        data=Path(source).read_bytes();archive.writestr(name,data)
        files.append({'source':source,'target':target,'stage':name,'sha256':hashlib.sha256(data).hexdigest(),'before':expected.get(target)})
    for name in ['geo_source_cards','web_collectors']:
        archive.writestr(name+'/__init__.py',f"__path__.append('/opt/monitor/geo-capture/venv/lib/python3.10/site-packages/{name}')\n")
    tests=[Path('geo-monitor-deploy/tests')/name for name in ['test_daily_dispatch.py','test_control_panel.py','test_native_worker_reliability.py','test_capture_bridge.py','test_runtime_reliability.py']]
    tests += [Path('geo-source-card-collectors/tests')/name for name in ['test_unattended_capture.py','test_search_recovery.py','test_send_position_recheck.py','test_round_cycle.py','test_completion_fence.py','test_collectors.py','test_preflight_recovery.py','test_capture_recovery.py','test_session_watch.py']]
    tests += [Path('redroid-deploy/tests')/name for name in ['test_unattended.py','test_question_only.py']]
    for path in tests:archive.write(path,'tests/'+path.name)
    archive.writestr('manifest.json',json.dumps({'files':files},ensure_ascii=False,indent=2))
print(json.dumps({'files':len(files),'tests':len(tests),'zip':str(out/'stage.zip')}))
