import json,subprocess,time
from pathlib import Path
root=Path('/opt/monitor/geo-capture/manual-login/deepseek_test')
r=json.loads((root/'request.json').read_text());assert r['model']=='deepseek_test'
unit='geo-deepseek-manual-login-'+r['id'][:12]+'.service'
p=subprocess.run(['systemctl','is-active',unit],capture_output=True,text=True)
assert p.stdout.strip()!='active','Do not interrupt an active manual test'
s=json.loads((root/'state.json').read_text());assert s['id']==r['id']
s.update(status='failed',message='测试机已完成重连，请点击重开投屏',updated_at=time.time())
(root/'state.json').write_text(json.dumps(s,ensure_ascii=False))
print('only inactive sandbox flow released')
