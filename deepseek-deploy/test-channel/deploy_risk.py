import hashlib,json,shutil,subprocess
from pathlib import Path
ROOT=Path('/opt/monitor/geo-capture/maintenance/20261017-deepseek-risk');BASE=Path('/opt/monitor/geo-capture')
baseline={i['server']:i['sha256'] for i in json.loads((BASE/'maintenance/20261015-unified/current-manifest.json').read_text())['files']}
targets={'auth_policy.py':['/home/user/redroid-deepseek/code/auth_policy.py','/home/user/redroid-deepseek-account2/code/auth_policy.py'],'manual_login.py':[str(BASE/'manual_login.py')],'deepseek_test_auth.py':[str(BASE/'deepseek_test_auth.py')]}
for name,paths in targets.items():
 for value in paths:
  target=Path(value)
  if target.exists():
   assert hashlib.sha256(target.read_bytes()).hexdigest()==baseline[str(target)]
   backup=ROOT/'backup'/value.lstrip('/');backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup)
  shutil.copy2(ROOT/'workspace'/name,target)
  target.chmod(0o644)
subprocess.run(['systemctl','restart','geo-monitor-status.service'],check=True)
print('risk policy deployed to both production runtimes; workers and sandbox session preserved')
