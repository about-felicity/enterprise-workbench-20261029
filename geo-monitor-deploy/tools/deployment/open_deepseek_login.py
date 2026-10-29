"""Visible manual DeepSeek login; synchronize only session state over existing SSH."""
import json
import argparse
import os
from pathlib import Path
import shlex
import sys
import time

WORKSPACE=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(WORKSPACE/'geo-source-card-collectors'))
sys.path.insert(0,str(WORKSPACE/'redroid-deploy'))
from remote import connect
from web_collectors.collector import BrowserCollector
from geo_source_cards.runtime import process_lock

RUNTIME=Path.home()/'.geo-editorial/deepseek-geo-manual-login'
STATUS=WORKSPACE/'geo-monitor-deploy/reports/20261015/deepseek-manual-login.json'

def status(state,**extra):
    STATUS.parent.mkdir(parents=True,exist_ok=True)
    temp=STATUS.with_suffix('.tmp')
    temp.write_text(json.dumps({'status':state,'time':time.time(),**extra},ensure_ascii=False,indent=2),encoding='utf8')
    temp.replace(STATUS)

REMOTE_CODE=r'''
import sys,os,json
from pathlib import Path
from geo_source_cards.runtime import process_lock
from web_collectors.collector import BrowserCollector
stage='read_session'
value=json.load(sys.stdin)
os.environ.pop('GEO_PIPELINE_ROOT',None)
os.environ['MONITOR_DEEPSEEK_COOKIES_JSON']=json.dumps(value['cookies'])
os.environ['MONITOR_DEEPSEEK_STORAGE_JSON']=json.dumps(value['storage'])
root=Path('/home/user/geo-editorial/runtime-api/collectors/deepseek')
os.environ.update(GEO_COLLECTOR_RUNTIME=str(root),GEO_DEEPSEEK_PORT='9414')
with process_lock(root/'collector.lock'):
 stage='source_browser'
 collector=BrowserCollector('deepseek',headless=True)
 try:
  collector.page.call('Page.navigate',{'url':'https://chat.deepseek.com/'})
  state=collector.check_ready()
  source_ok=bool(state.get('ok'))
 finally:collector.close()
for key in ['MONITOR_DEEPSEEK_COOKIES_JSON','MONITOR_DEEPSEEK_STORAGE_JSON']:os.environ.pop(key,None)
if not source_ok:
 print(json.dumps({'source_ready':False,'status':state.get('status','unknown')}));sys.exit(2)
sys.path.insert(0,'/opt/monitor/geo-capture')
from login_probe import browser
stage='geo_runtime_lookup'
import requests,re
http=requests.Session();http.trust_env=False
response=http.get('http://127.0.0.1:8803/api/status',timeout=15);response.raise_for_status()
batch=next(lane['batch'] for lane in response.json()['collectors'] if lane['name']=='DeepSeek')
assert re.fullmatch('[a-zA-Z0-9_-]+',batch)
stage='geo_browser_sync'
result=browser(Path('/opt/monitor/geo-capture/batches')/batch/'collector',True)
print(json.dumps({'source_ready':True,'geo_ready':result.get('status')=='ready','status':result.get('status')}))
'''

REMOTE_CODE='import json,traceback,os\ntry:\n'+''.join(' '+line+'\n' for line in REMOTE_CODE.splitlines())+'''except Exception as error:
 print(json.dumps({'source_ready':globals().get('source_ok',False),'geo_ready':False,'status':'sync_failed','error_kind':type(error).__name__,'stage':globals().get('stage','imports'),'frames':[{'file':os.path.basename(f.filename),'line':f.lineno,'function':f.name} for f in traceback.extract_tb(error.__traceback__)[-4:]]}))
'''

REMOTE_GEO_CODE=r'''
import json,os,sys,requests
from pathlib import Path
value=json.load(sys.stdin)
os.environ.pop('GEO_PIPELINE_ROOT',None)
os.environ['MONITOR_DEEPSEEK_COOKIES_JSON']=json.dumps(value['cookies'])
os.environ['MONITOR_DEEPSEEK_STORAGE_JSON']=json.dumps(value['storage'])
http=requests.Session();http.trust_env=False
panel=http.get('http://127.0.0.1:8803/api/panel',timeout=20).json()
model=next(m for m in panel['models'] if m['id']=='deepseek')
assert model['current']['service_state'] not in {'active','activating','reloading','deactivating'}
runtime=Path('/opt/monitor/geo-capture/batches')/model['current']['batch']/'collector'
sys.path.insert(0,'/opt/monitor/geo-capture')
from login_probe import browser
try:
 result=browser(runtime,False)
 print(json.dumps({'scope':'geo_only','geo_ready':result.get('status')=='ready','status':result.get('status')}))
except Exception as error:
 print(json.dumps({'scope':'geo_only','geo_ready':False,'status':'sync_failed','error_kind':type(error).__name__}))
'''

def sync(value):
    client,password=connect()
    try:
        command='sudo -S -p "" -- runuser -u user -- /home/user/geo-editorial/venv/bin/python -B -c '+shlex.quote(REMOTE_CODE)
        stdin,stdout,stderr=client.exec_command(command,timeout=180)
        stdin.write(password+'\n')
        stdin.flush()
        # Send state only through encrypted stdin; never logs, argv or seed files.
        stdin.write(json.dumps(value))
        stdin.flush();stdin.channel.shutdown_write()
        output=stdout.read().decode('utf8','replace')
        error=stderr.read().decode('utf8','replace')
        code=stdout.channel.recv_exit_status()
        # Browser diagnostics may precede the single sanitized result object.
        records=[]
        for line in output.splitlines():
            try:
                parsed=json.loads(line)
                if isinstance(parsed,dict) and ('source_ready' in parsed or 'geo_ready' in parsed):records.append(parsed)
            except ValueError:pass
        if records:return records[-1]
        return {'source_ready':False,'geo_ready':False,'status':'sync_failed',
                'exit_code':code,'error_kind':'remote_check_failed' if error else 'missing_result'}
    finally:client.close()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--reuse-session',action='store_true')
    parser.add_argument('--geo-only',action='store_true')
    args=parser.parse_args()
    if args.geo_only:
        global REMOTE_CODE
        REMOTE_CODE=REMOTE_GEO_CODE
    os.environ.pop('GEO_PIPELINE_ROOT',None)
    os.environ.update(GEO_COLLECTOR_RUNTIME=str(RUNTIME),GEO_DEEPSEEK_PORT='19214')
    RUNTIME.mkdir(parents=True,exist_ok=True)
    collector=None
    try:
        with process_lock(RUNTIME/'collector.lock'):
            status('opening_browser')
            collector=BrowserCollector('deepseek',headless=args.reuse_session)
            status('rechecking_local_session' if args.reuse_session else 'waiting_user_login')
            cookies=collector.wait_for_login_cookies(timeout=900)
            value={'cookies':[c for c in cookies if str(c.get('domain','')).lstrip('.').endswith('deepseek.com')],
                   'storage':collector.page.evaluate('({local_storage:{...localStorage},session_storage:{...sessionStorage}})')}
            status('syncing_server_session')
            result={}
            for attempt in range(3):
                try:result=sync(value)
                except Exception as exc:result={'status':'sync_failed','error_kind':type(exc).__name__}
                if result.get('geo_ready') and (args.geo_only or result.get('source_ready')):break
                if attempt<2:time.sleep(5)
            status('ready' if result.get('geo_ready') else 'sync_needs_attention',verification=result,
                   submitted_questions=0)
    except Exception as exc:
        status('needs_attention',error_kind=type(exc).__name__,submitted_questions=0)
    finally:
        if collector:collector.close()

if __name__=='__main__':main()
