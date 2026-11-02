import hashlib,shutil,subprocess
from pathlib import Path
unit=subprocess.check_output(['systemctl','show','geo-web@geo-panel-baidu-ai-20261031-090001-88a32968.service','-p','WorkingDirectory','-p','Environment','-p','KillMode','-p','TimeoutStopUSec','-p','ExecStart'],text=True)
for line in unit.splitlines():
 if line.startswith('Environment='):
  import re
  print('python_path',re.findall(r'PYTHONPATH=([^ "]+)',line))
 else:print(line)
print('pyspy',shutil.which('py-spy'))
print('bridge_hash',hashlib.sha256(Path('/opt/monitor/geo-capture/capture_bridge.py').read_bytes()).hexdigest())
for p in [Path('/opt/monitor/geo-content/engine/geo_source_cards/cli.py'),Path('/home/user/geo-source-card-collectors/geo_source_cards/cli.py')]:
 if p.exists():print('candidate',str(p))
for path in Path('/proc').glob('[0-9]*/cmdline'):
 try:
  args=path.read_bytes().split(b'\0')
  if len(args)>2 and b'geo_source_cards.cli' in args:print('cli_cwd',path.parent.name,str((path.parent/'cwd').resolve()))
 except OSError:pass
