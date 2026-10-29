import sys
sys.path.insert(0,'/tmp')
from vps_geo_access import vps_python
print(vps_python(r"""import subprocess,re,json
from pathlib import Path
r=subprocess.run(['ss','-ltnp'],capture_output=True,text=True)
print('\n'.join(l for l in r.stdout.splitlines() if ':18811' in l))
s=Path('/root/.ssh/authorized_keys').read_text()
print(json.dumps({'permitlisten':re.findall(r'permitlisten="[^"]+"',s),'restrict_count':s.count('restrict'),'no_port_forwarding':s.count('no-port-forwarding')}))
"""))

