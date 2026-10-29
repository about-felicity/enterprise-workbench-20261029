import json,os,secrets,hashlib,subprocess,pwd
from pathlib import Path
root=Path('/opt/monitor/geo-capture/public_ingest');root.mkdir(mode=0o700,exist_ok=True)
registry=root/'clients.json';export=Path('/tmp/deepseek-public-bootstrap.json')
if not registry.exists():
 token=secrets.token_urlsafe(36)
 registry.write_text(json.dumps({'enrollment_enabled':True,'enrollment_sha256':hashlib.sha256(token.encode()).hexdigest(),'derive_secret':secrets.token_hex(32),'clients':[]}));registry.chmod(0o600)
 export.write_text(json.dumps({'receiver_url':'https://1any.top/geo_monitor/collector/deepseek','enrollment_token':token},indent=2));export.chmod(0o600)
assert export.exists(),'Existing enrollment key must be recovered, never implicitly rotate'
u=pwd.getpwnam('user');os.chown(export,u.pw_uid,u.pw_gid)
unit='''[Unit]
Description=Scoped DeepSeek public upload gateway
After=network-online.target
[Service]
Type=simple
ExecStart=/usr/bin/python3 -B /opt/monitor/geo-capture/public_ingest/gateway.py
Restart=on-failure
RestartSec=5
MemoryMax=256M
NoNewPrivileges=true
PrivateTmp=true
UMask=0077
[Install]
WantedBy=multi-user.target
'''
Path('/etc/systemd/system/geo-deepseek-public-ingest.service').write_text(unit)
tunnel='''[Unit]
Description=DeepSeek upload reverse tunnel
After=network-online.target geo-deepseek-public-ingest.service
[Service]
Type=simple
ExecStart=/usr/bin/ssh -N -T -i /etc/monitor-vps2-tunnel/id_ed25519 -o BatchMode=yes -o StrictHostKeyChecking=yes -o UserKnownHostsFile=/etc/monitor-vps2-tunnel/known_hosts -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -R 127.0.0.1:18811:127.0.0.1:8811 root@117.55.234.72
Restart=always
RestartSec=10
MemoryMax=64M
NoNewPrivileges=true
[Install]
WantedBy=multi-user.target
'''
Path('/etc/systemd/system/geo-deepseek-upload-tunnel.service').write_text(tunnel)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','--now','geo-deepseek-public-ingest.service','geo-deepseek-upload-tunnel.service'],check=True,capture_output=True)
print(json.dumps({'installed':True,'scope':'deepseek_upload_only','per_device_tokens':True,'other_collectors_unchanged':True}))
