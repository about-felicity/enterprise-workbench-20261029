import subprocess,shlex,json,time,concurrent.futures
from pathlib import Path
def measure(url):
 r=subprocess.run(['curl','--noproxy','*','-sS','--connect-timeout','5','--max-time','30','-o','/dev/null','-w','%{http_code} dns=%{time_namelookup} connect=%{time_connect} tls=%{time_appconnect} first=%{time_starttransfer} total=%{time_total} bytes=%{size_download} speed=%{speed_download}',url],capture_output=True,text=True,timeout=35)
 return {'url':url,'result':r.stdout,'error':r.stderr[:200]}
out={'lan':list(concurrent.futures.ThreadPoolExecutor(3).map(measure,['http://127.0.0.1:3000/','http://127.0.0.1:3000/api/geo-creation/uploads','https://1any.top/geo_monitor/']))}
print(json.dumps(out),flush=True)
code=r'''
import subprocess,json,concurrent.futures,re
from pathlib import Path
def measure(url):
 r=subprocess.run(['curl','--noproxy','*','-sS','--connect-timeout','5','--max-time','35','-o','/dev/null','-w','%{http_code} first=%{time_starttransfer} total=%{time_total} bytes=%{size_download} speed=%{speed_download}',url],capture_output=True,text=True,timeout=40)
 return {'url':url,'result':r.stdout,'error':r.stderr[:200]}
o={'vps':list(concurrent.futures.ThreadPoolExecutor(3).map(measure,['http://127.0.0.1:13000/','http://127.0.0.1:13000/api/geo-creation/uploads','https://1any.top/geo_monitor/']))}
t=Path('/etc/nginx/nginx.conf').read_text();o['routing']=[s.strip() for s in t.splitlines() if any(x in s for x in ['location ','proxy_pass ','gzip','limit_rate','proxy_read_timeout','sub_filter','proxy_buffer','expires '])]
o['recent_errors']=[s[-700:] for s in Path('/var/log/nginx/error.log').read_text().splitlines() if '2026/10/29' in s and 'geo_monitor' in s][-8:]
o['resources']=subprocess.run(['uptime'],capture_output=True,text=True).stdout
print(json.dumps(o,ensure_ascii=False))
'''
args=['ssh','-i','/etc/monitor-vps2-tunnel/id_ed25519','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/etc/monitor-vps2-tunnel/known_hosts','-o','ConnectTimeout=10','root@117.55.234.72','python3 -c '+shlex.quote(code)]
r=subprocess.run(args,capture_output=True,text=True,timeout=55);print(r.stdout,flush=True);print(r.stderr)
print('TUNNELS',subprocess.run(['systemctl','list-units','--all','--no-pager','*tunnel*'],capture_output=True,text=True).stdout)
Path('/tmp/public-latency-20261029.json').write_text(json.dumps(out)+'\n'+r.stdout)
