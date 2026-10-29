import json,subprocess,time
from pathlib import Path
NAME='deepseek-manual-test';root=Path('/opt/monitor/geo-capture/manual-login/deepseek_test')
def run(*args):return subprocess.check_output(args,stderr=subprocess.STDOUT,timeout=40,text=True).strip()
assert json.loads(run('docker','inspect',NAME))[0]['Name']=='/'+NAME
request=json.loads((root/'request.json').read_text());assert request['model']=='deepseek_test'
assert len(request['id'])==32 and all(c in '0123456789abcdef' for c in request['id'])
run('systemctl','stop','geo-deepseek-manual-login-'+request['id'][:12])
state=json.loads((root/'state.json').read_text());state.update(status='failed',message='测试机语言已更新，请重开投屏',updated_at=time.time());(root/'state.json').write_text(json.dumps(state,ensure_ascii=False))
run('docker','exec',NAME,'setprop','persist.sys.locale','zh-CN')
run('docker','restart',NAME)
for _ in range(90):
 try:
  if run('docker','exec',NAME,'getprop','sys.boot_completed')=='1':break
 except subprocess.SubprocessError:pass
 time.sleep(2)
else:raise RuntimeError('Test device boot timeout')
config=run('docker','exec',NAME,'am','get-config')
assert 'zh-rCN' in config or 'zh-CN' in config,config
run('docker','exec',NAME,'am','start','-W','-n','com.deepseek.chat/.MainActivity')
print(json.dumps({'test_device_only':True,'system_config_simplified_chinese':True}))
