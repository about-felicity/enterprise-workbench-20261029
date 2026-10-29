import hashlib,json,shutil,subprocess,sys,time
from pathlib import Path
BASE=Path('/opt/monitor/geo-capture');ROOT=BASE/'maintenance/20261017-input-latency'
old=BASE/'scrcpy_stream.py';prior=ROOT/'workspace/scrcpy_stream.py'
assert hashlib.sha256(old.read_bytes()).digest()==hashlib.sha256(prior.read_bytes()).digest()
shutil.copy2(old,ROOT/'bridge-before-decoder-thread-fix.py')
root=BASE/'manual-login/deepseek_test';r=json.loads((root/'request.json').read_text());assert r['model']=='deepseek_test'
assert len(r['id'])==32 and all(c in '0123456789abcdef' for c in r['id'])
subprocess.run(['systemctl','stop','geo-deepseek-manual-login-'+r['id'][:12]+'.service'],check=True)
s=json.loads((root/'state.json').read_text());s.update(status='failed',message='投屏解码延迟已更新',updated_at=time.time());(root/'state.json').write_text(json.dumps(s))
shutil.copy2('/tmp/geo-input-stream-v2.py',old)
sys.path.insert(0,str(BASE));from manual_login import start
start(BASE,'/home/user/redroid-deepseek-test','manual-test',0,model='deepseek_test')
print('sandbox projection restarted with single-thread low-latency H264 decoder')
