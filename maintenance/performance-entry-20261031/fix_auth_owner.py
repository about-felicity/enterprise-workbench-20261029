import shlex,subprocess
code="import shutil;from pathlib import Path;p=Path('/opt/geo-monitor-auth/performance-auth.key');shutil.chown(p,user='nginx',group='nginx');p.chmod(0o600);print('Service identity can read signing key; key remains private')"
ssh=['ssh','-i','/etc/monitor-vps2-tunnel/id_ed25519','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/etc/monitor-vps2-tunnel/known_hosts','root@117.55.234.72']
subprocess.run(ssh+['python3 -c '+shlex.quote(code)],check=True)
