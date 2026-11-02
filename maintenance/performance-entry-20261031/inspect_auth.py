import json,shlex,subprocess
code=r'''
import ast,json,re
from pathlib import Path
p=Path('/opt/geo-monitor-auth/server.py');text=p.read_text();tree=ast.parse(text)
print('FUNCTIONS',[(n.name,n.lineno) for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.ClassDef))])
for n in tree.body:
 if isinstance(n,(ast.FunctionDef,ast.ClassDef)):
  source=ast.get_source_segment(text,n)
  if n.name in ['read_token']:
   print('SOURCE',source)
 elif isinstance(n,(ast.Assign,ast.AnnAssign)):
  names=[x.id for x in ast.walk(n) if isinstance(x,ast.Name) and isinstance(x.ctx,ast.Store)]
  if any(k in ' '.join(names).lower() for k in ['cookie']):
   source=ast.get_source_segment(text,n)
   if not any(k in source.lower() for k in ['password=','secret=','token=']):print('CONFIG',source)
names=[line.split(':',1)[0] for line in Path('/etc/nginx/.geo_monitor_htpasswd').read_text().splitlines() if ':' in line]
print('SUPERADMIN_EXISTS','superadmin' in names)
print('NORMAL_USER_AVAILABLE',any(name!='superadmin' for name in names))
'''
ssh=['ssh','-i','/etc/monitor-vps2-tunnel/id_ed25519','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/etc/monitor-vps2-tunnel/known_hosts','-o','ConnectTimeout=10','root@117.55.234.72']
result=subprocess.run(ssh+['python3 -c '+shlex.quote(code)],capture_output=True,text=True,timeout=35)
print(result.stdout);print(result.stderr);raise SystemExit(result.returncode)
