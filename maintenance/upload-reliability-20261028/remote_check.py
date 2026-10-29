"""Run an explicitly selected maintenance script over the existing SSH connection."""
import os, re, shlex, sys
from pathlib import Path

sys.path.insert(0, str(Path(os.environ['TEMP']) / 'codex-ssh-readonly-deps'))
import paramiko

sys.stdout.reconfigure(encoding='utf-8')
root = Path(__file__).resolve().parents[2]
config = (root / 'local_server.txt').read_text('utf-8-sig')
target = re.search(r'ssh\s+([\w.-]+)@([\w.-]+)', config)
password = re.search(r'password\s*:\s*(.+)', config).group(1).strip()
client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(target.group(2), username=target.group(1), password=password,
               timeout=30, banner_timeout=60, auth_timeout=30, look_for_keys=False, allow_agent=False)
try:
    if sys.argv[1] == 'download':
        dest = Path(sys.argv[3]); dest.parent.mkdir(parents=True, exist_ok=True)
        with client.open_sftp() as sftp:
            sftp.get(sys.argv[2], str(dest))
        print('Downloaded', dest.name)
    elif sys.argv[1] == 'upload':
        with client.open_sftp() as sftp:
            sftp.put(sys.argv[2], sys.argv[3])
        print('Uploaded', sys.argv[3])
    else:
        script = Path(sys.argv[1]).read_text('utf-8-sig')
        command = "sudo -S -p '' -- python3 -B -c " + shlex.quote(script)
        stdin, stdout, stderr = client.exec_command(command, timeout=600)
        stdin.write(password + '\n'); stdin.flush(); stdin.channel.shutdown_write()
        for line in stdout: print(line, end='', flush=True)
        print(stderr.read().decode('utf-8', 'replace'), end='')
        sys.exit(stdout.channel.recv_exit_status())
finally:
    client.close()
