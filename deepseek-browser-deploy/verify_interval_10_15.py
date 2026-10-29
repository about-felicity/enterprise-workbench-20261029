import sys,json,time
from pathlib import Path
sys.path.insert(0,'/opt/monitor/geo-capture')
from browser_backend import command,read
s=read('/opt/monitor/geo-deepseek-browser-test/state.json');print(json.dumps({'auth':s.get('auth'),'age':time.time()-s.get('updated_at',0),'interval':[s.get('interval_min'),s.get('interval_max')],'state':s.get('plugin_job',{}).get('state'),'cursor':s.get('plugin_job',{}).get('cursor')}))
x=command('get',timeout=12);print(json.dumps({'settings_interval':[x['settings']['intervalMinSeconds'],x['settings']['intervalMaxSeconds']],'job_id':x['job']['id'],'cursor':x['job']['cursor'],'state':x['job']['state'],'permit':x['nextAllowedSendAt']}))
