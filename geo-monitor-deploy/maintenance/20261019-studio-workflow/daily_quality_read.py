import sys,json
from pathlib import Path
sys.path.insert(0,'/opt/monitor/geo-capture')
from control_panel import Controller
for m in Controller(Path('/opt/monitor/geo-capture')).all()['models']:
 if m['id'] in ['baidu_ai','yuanbao']:
  c=m['current'];print(json.dumps({'model':m['id'],'quality':{k:c.get(k) for k in ['unavailable','duplicates','captured','processed','state']},'daily':{k:m['daily'].get(k) for k in ['rounds','target','completed','status']}},ensure_ascii=False))
