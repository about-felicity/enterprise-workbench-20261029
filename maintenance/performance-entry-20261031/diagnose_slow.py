import json,subprocess,time,urllib.request,concurrent.futures
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def probe(path):
 start=time.monotonic()
 try:
  with op.open('http://127.0.0.1:8765'+path,timeout=45) as r:body=r.read();return {'path':path,'status':r.status,'seconds':round(time.monotonic()-start,3),'bytes':len(body)}
 except Exception as e:return {'path':path,'seconds':round(time.monotonic()-start,3),'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(3) as pool:
 for item in pool.map(probe,['/api/performance?month=2026-10','/api/performance?month=2026-10&refresh='+str(time.time_ns()),'/api/performance-entry/access']):print(json.dumps(item),flush=True)
print(subprocess.check_output(['docker','stats','--no-stream','--format','{{.Name}} CPU={{.CPUPerc}} MEM={{.MemUsage}}'],text=True))
logs=subprocess.check_output(['docker','logs','--tail','45','monitor-dashboard-api'],stderr=subprocess.STDOUT,text=True)
for line in logs.splitlines():
 if any(s in line for s in ['performance','Traceback','Error','Exception']):print(line[:600])
