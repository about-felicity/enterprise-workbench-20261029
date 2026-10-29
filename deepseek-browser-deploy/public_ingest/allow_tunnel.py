import sys,subprocess
sys.path.insert(0,'/tmp')
from vps_geo_access import vps_python
pub=subprocess.check_output(['ssh-keygen','-y','-f','/etc/monitor-vps2-tunnel/id_ed25519'],text=True).split()[1]
code=r'''
from pathlib import Path
import shutil,time,json
p=Path('/root/.ssh/authorized_keys');s=p.read_text();lines=s.splitlines(keepends=True)
matches=[i for i,l in enumerate(lines) if KEY in l.split()]
assert len(matches)==1
i=matches[0];line=lines[i];rule='permitlisten="127.0.0.1:18811"'
assert 'permitlisten="127.0.0.1:13000"' in line
if rule not in line:
 shutil.copy2(p,p.with_name('authorized_keys.deepseek-'+str(int(time.time()))))
 lines[i]=line.replace('permitlisten="127.0.0.1:13000"','permitlisten="127.0.0.1:13000",'+rule,1)
 p.write_text(''.join(lines));p.chmod(0o600)
print(json.dumps({'upload_port_allowed':True,'other_key_options_preserved':True}))
'''.replace('KEY',repr(pub))
print(vps_python(code))
