import subprocess,shlex
for args in [['systemctl','cat','monitor-vps2-tunnel'],['systemctl','show','monitor-vps2-tunnel','-p','NRestarts','-p','ExecMainStatus','-p','MainPID'],['journalctl','-u','monitor-vps2-tunnel','-n','45','--no-pager']]:
 print(subprocess.run(args,capture_output=True,text=True).stdout,flush=True)
code="import subprocess; print(subprocess.run(['ss','-lntp'],capture_output=True,text=True).stdout); print(subprocess.run(['journalctl','-u','sshd','-n','15','--no-pager'],capture_output=True,text=True).stdout)"
args=['ssh','-i','/etc/monitor-vps2-tunnel/id_ed25519','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/etc/monitor-vps2-tunnel/known_hosts','-o','ConnectTimeout=10','root@117.55.234.72','python3 -c '+shlex.quote(code)]
r=subprocess.run(args,capture_output=True,text=True,timeout=30);print(r.stdout);print(r.stderr)
