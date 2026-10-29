"""A second clean Android device. Copy the signed APK only, never account data."""
import hashlib
import json
from pathlib import Path
import subprocess
import time

NAME='deepseek-hpe14-account2'
VOLUME=NAME+'-data'
PORT=5561
def run(*args, **kwargs):
    return subprocess.check_output(args,timeout=kwargs.pop('timeout',45),**kwargs).decode().strip()
original=json.loads(run('docker','inspect','deepseek-hpe14-android13'))[0]
existing=run('docker','ps','-a','--format','{{.Names}}').splitlines()
assert NAME not in existing, 'Device already exists; inspect and reuse it instead of recreating'
assert VOLUME not in run('docker','volume','ls','--format','{{.Name}}').splitlines(), 'Existing account volume must not be overwritten'
apk_path=run('docker','exec','deepseek-hpe14-android13','pm','path','com.deepseek.chat')
assert apk_path.startswith('package:') and '\n' not in apk_path
apk=Path('/tmp/deepseek-account2-verified.apk')
subprocess.run(['docker','cp','deepseek-hpe14-android13:'+apk_path.removeprefix('package:'),str(apk)],check=True,timeout=45)
assert hashlib.sha256(apk.read_bytes()).hexdigest()=='1468cae414245e6bd447b0ae79c277958a6da1c25f4e4798ffc04e42127fa14a'
run('docker','volume','create',VOLUME)
run('docker','run','-d','--name',NAME,'--restart','unless-stopped','--privileged',
    '--memory','2g','--memory-swap','3g','--cpus','2',
    '-p',f'127.0.0.1:{PORT}:5555','-v',VOLUME+':/data',
    original['Config']['Image'],*original['Config']['Cmd'])
print(json.dumps({'created':NAME,'adb_loopback_port':PORT,'clean_volume':True}),flush=True)
deadline=time.monotonic()+150
while time.monotonic()<deadline:
    try:
        if run('docker','exec',NAME,'getprop','sys.boot_completed',timeout=8)=='1':break
    except subprocess.SubprocessError:pass
    time.sleep(2)
else:raise RuntimeError('New emulator still booting; preserve its volume and inspect before retry')
run('docker','cp',str(apk),NAME+':/data/local/tmp/deepseek.apk')
assert 'Success' in run('docker','exec',NAME,'pm','install','/data/local/tmp/deepseek.apk',timeout=90)
run('docker','exec',NAME,'settings','put','system','system_locales','zh-CN')
run('docker','exec',NAME,'cmd','locale','set-app-locales','com.deepseek.chat','--user','0','--locales','zh-CN')
run('docker','exec',NAME,'am','start','-W','-n','com.deepseek.chat/.MainActivity')
first_id=run('docker','exec','deepseek-hpe14-android13','settings','get','secure','android_id')
second_id=run('docker','exec',NAME,'settings','get','secure','android_id')
assert first_id and second_id and first_id!=second_id, 'Android identity must be isolated'
metadata={'container':NAME,'volume':VOLUME,'serial':'127.0.0.1:5561','local_login_port':15561,
          'package':'com.deepseek.chat','version_code':281,'memory_gib':2,'memory_swap_gib':3,
          'cpus':2,'locale':'zh-CN','state':'awaiting_manual_login','scheduled':False,
          'android_identity_isolated':True,'created_epoch':time.time()}
directory=Path('/home/user/redroid-deepseek-account2');directory.mkdir(mode=0o700,exist_ok=True)
(directory/'device.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2))
print(json.dumps(metadata,ensure_ascii=False),flush=True)
