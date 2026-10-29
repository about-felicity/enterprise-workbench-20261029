import sys,json
sys.path.insert(0,'/opt/monitor/geo-capture')
from browser_backend import command
x=command('inspect');s=x['state'];print(json.dumps({'modes':x['modes'],'job':s.get('job'),'rounds':s.get('settings',{}).get('rounds'),'next_send':s.get('nextAllowedSendAt')},ensure_ascii=False))
