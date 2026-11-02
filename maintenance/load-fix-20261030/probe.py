import concurrent.futures,time,json,urllib.request,subprocess

def probe(url):
 t=time.monotonic()
 try:
  with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(url,timeout=20) as r:
   b=r.read();return dict(url=url,seconds=round(time.monotonic()-t,3),status=r.status,bytes=len(b))
 except Exception as e:return dict(url=url,seconds=round(time.monotonic()-t,3),error=str(e))
for u in ['http://127.0.0.1:8804/api/status','http://127.0.0.1:3000/api/geo-creation/status','http://127.0.0.1:3000/api/geo-creation/ui','https://1any.top/geo_monitor/']:
 print('SERIAL',json.dumps(probe(u)),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for result in pool.map(probe,['http://127.0.0.1:8804/api/status']*4):print('CONCURRENT',json.dumps(result),flush=True)
for command in [['free','-m'],['uptime'],['systemctl','show','geo-content-api','-p','ExecStart','-p','NRestarts']]:
 print(subprocess.run(command,capture_output=True,text=True).stdout,flush=True)
