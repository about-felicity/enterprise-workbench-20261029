import subprocess,shlex,json,time
code=r'''
import subprocess,os,signal,re,shutil,json
from pathlib import Path
listeners=subprocess.check_output(['ss','-lntp']).decode().splitlines()
rows=[s for s in listeners if 'pid=40906,' in s]
assert rows and all(any(':'+str(p)+' ' in s for p in [13000,18765]) for s in rows),rows
assert any(':13000 ' in s for s in rows) and any(':18765 ' in s for s in rows)
cmd=Path('/proc/40906/cmdline').read_bytes().decode().replace('\0',' ');assert 'sshd: root' in cmd,cmd
p=Path('/etc/ssh/sshd_config');original=p.read_text();assert '# geo-monitor dead tunnel recovery' not in original
backup=Path('/root/geo-monitor-access-backups/public-latency-20261029');backup.mkdir(parents=True,exist_ok=False);shutil.copy2(p,backup/'sshd_config')
new=original.rstrip()+'\n\n# geo-monitor dead tunnel recovery\nMatch User root\n    ClientAliveInterval 30\n    ClientAliveCountMax 3\n'
tmp=p.with_suffix('.monitor.tmp');tmp.write_text(new);tmp.chmod(p.stat().st_mode&0o777);os.replace(tmp,p)
check=subprocess.run(['/usr/sbin/sshd','-t'],capture_output=True,text=True)
effective=subprocess.run(['/usr/sbin/sshd','-T','-C','user=root,host=localhost,addr=125.69.115.102'],capture_output=True,text=True)
if check.returncode or 'clientaliveinterval 30' not in effective.stdout:
 shutil.copy2(backup/'sshd_config',p);raise RuntimeError('SSH keepalive validation failed')
subprocess.run(['systemctl','reload','sshd'],check=True)
# Terminate only the verified nonresponsive forwarding session, not sshd or any other session.
os.kill(40906,signal.SIGTERM)
print(json.dumps({'stale_session_terminated':40906,'ports':[13000,18765],'server_keepalive_seconds':30,'missed_keepalive_limit':3,'backup':str(backup)}))
'''
args=['ssh','-i','/etc/monitor-vps2-tunnel/id_ed25519','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/etc/monitor-vps2-tunnel/known_hosts','-o','ConnectTimeout=10','root@117.55.234.72','python3 -c '+shlex.quote(code)]
r=subprocess.run(args,capture_output=True,text=True,timeout=35);print(r.stdout,flush=True);print(r.stderr);assert r.returncode==0
subprocess.run(['systemctl','restart','monitor-vps2-tunnel'],check=True,timeout=20)
time.sleep(5)
print(subprocess.check_output(['systemctl','show','monitor-vps2-tunnel','-p','ActiveState','-p','SubState','-p','MainPID','-p','NRestarts']).decode())
