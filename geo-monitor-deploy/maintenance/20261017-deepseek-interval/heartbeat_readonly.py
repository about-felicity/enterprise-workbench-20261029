import json,sys
from datetime import datetime
from zoneinfo import ZoneInfo
sys.path.insert(0,'/opt/monitor/geo-capture')
from control_panel import Controller,read
c=Controller()
for m in c.all('2026-10-17')['models']:
 d=m['daily'];print(json.dumps({'model':m['id'],'day':d['date'],'completed_receipts':d['completed'],'target':d['target'],'remaining':d['remaining']},ensure_ascii=False))
a=read(c.base/'auth-monitor/deepseek2.json')
print('deepseek2_login_loss_Beijing='+datetime.fromtimestamp(a['changed_at'],ZoneInfo('Asia/Shanghai')).isoformat())
