import json
from pathlib import Path
import zipfile
out=Path(__file__).parent
names=['control_panel.py','daily_tasks.py','daily_dispatch.py','fleet_status.py','panel.html','capture_bridge.py','baidu_body_delivery.py']
with zipfile.ZipFile(out/'stage.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name in names:z.write(Path('geo-monitor-deploy')/name,name)
    for name in ['test_control_panel.py','test_daily_dispatch.py','test_daily_tasks.py','test_capture_bridge.py','test_baidu_body_delivery.py']:
        z.write(Path('geo-monitor-deploy/tests')/name,'tests/'+name)
    z.write(Path('geo-monitor-deploy/dashboard-integration/app/api/geo-capture/[...path]/route.ts'),'capture-route.ts')
    z.write(Path('geo-monitor-deploy/dashboard-integration/tests/capture-gateway.test.mjs'),'capture-gateway.test.mjs')
print(json.dumps({'zip':str(out/'stage.zip'),'runtime':len(names)}))
