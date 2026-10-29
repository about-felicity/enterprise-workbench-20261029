"""Create an isolated manual device, with no collector or daily registration."""
import hashlib,json,subprocess,time
from pathlib import Path
NAME='deepseek-manual-test';VOLUME=NAME+'-data';PORT=5562
def run(*args,timeout=45):return subprocess.check_output(args,timeout=timeout).decode().strip()
existing=run('docker','ps','-a','--format','{{.Names}}').splitlines()
assert NAME not in existing,'Existing test device must be inspected, not overwritten'
assert VOLUME not in run('docker','volume','ls','--format','{{.Name}}').splitlines()
original=json.loads(run('docker','inspect','deepseek-hpe14-account2'))[0]
source=run('docker','exec','deepseek-hpe14-account2','pm','path','com.deepseek.chat')
assert source.startswith('package:') and '\n' not in source
apk=Path('/tmp/deepseek-manual-test-signed.apk')
run('docker','cp','deepseek-hpe14-account2:'+source[8:],str(apk))
assert hashlib.sha256(apk.read_bytes()).hexdigest()=='1468cae414245e6bd447b0ae79c277958a6da1c25f4e4798ffc04e42127fa14a'
run('docker','volume','create',VOLUME)
run('docker','run','-d','--name',NAME,'--restart','unless-stopped','--privileged','--memory','2g','--memory-swap','3g','--cpus','2','-p',f'127.0.0.1:{PORT}:5555','-v',VOLUME+':/data',original['Config']['Image'],*original['Config']['Cmd'])
print(json.dumps({'created':NAME,'scheduled':False}),flush=True)
for _ in range(90):
    try:
        if run('docker','exec',NAME,'getprop','sys.boot_completed',timeout=8)=='1':break
    except subprocess.SubprocessError:pass
    time.sleep(2)
else:raise RuntimeError('Preserve test volume; boot not ready')
run('docker','cp',str(apk),NAME+':/data/local/tmp/deepseek.apk')
assert 'Success' in run('docker','exec',NAME,'pm','install','/data/local/tmp/deepseek.apk',timeout=90)
run('docker','exec',NAME,'settings','put','system','system_locales','zh-CN')
run('docker','exec',NAME,'cmd','locale','set-app-locales','com.deepseek.chat','--user','0','--locales','zh-CN')
run('docker','exec',NAME,'am','start','-W','-n','com.deepseek.chat/.MainActivity')
ids=[run('docker','exec',n,'settings','get','secure','android_id') for n in ['deepseek-hpe14-android13','deepseek-hpe14-account2',NAME]]
assert len(set(ids))==3
directory=Path('/home/user/redroid-deepseek-test');directory.mkdir(mode=0o700,exist_ok=True)
metadata={'container':NAME,'volume':VOLUME,'serial':'127.0.0.1:5562','scheduled':False,'manual_only':True,'locale':'zh-CN','identity_isolated':True,'created_at':time.time()}
(directory/'device.json').write_text(json.dumps(metadata,indent=2))
print(json.dumps(metadata),flush=True)
