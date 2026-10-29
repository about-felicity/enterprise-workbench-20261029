from pathlib import Path
import shutil,time,subprocess,json
p=Path('/etc/nginx/nginx.conf');s=p.read_text();marker='# BEGIN GEO_DEEPSEEK_PUBLIC_INGEST'
if marker in s:print(json.dumps({'already_configured':True}));raise SystemExit(0)
anchor='        location ^~ /geo_monitor/api/geo-capture/ {';assert s.count(anchor)==1
assert s.count('http {')==1
new=s.replace('http {','http {\n    limit_req_zone $binary_remote_addr zone=geo_deepseek_upload:1m rate=30r/m;',1)
block=Path('/tmp/deepseek-ingest-location.conf').read_text(encoding='utf-8-sig')
new=new.replace(anchor,block+'\n'+anchor,1)
backup=Path('/root/geo-monitor-access-backups')/('deepseek-ingest-'+str(int(time.time())));backup.mkdir(parents=True,mode=0o700);shutil.copy2(p,backup/'nginx.conf')
p.write_text(new);test=subprocess.run(['nginx','-t'],capture_output=True,text=True)
if test.returncode:shutil.copy2(backup/'nginx.conf',p);raise RuntimeError('Nginx validation failed; restored prior configuration')
subprocess.run(['systemctl','reload','nginx'],check=True)
print(json.dumps({'configured':True,'backup':str(backup),'dashboard_auth_preserved':True,'upload_token_required_by_gateway':True}))
