import json,urllib.request,time
from pathlib import Path
r=json.loads(Path('/opt/monitor/geo-capture/manual-login/deepseek_test/request.json').read_text())
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for part in ['state','frame','stream']:
 req=urllib.request.Request('http://127.0.0.1:8817/'+part,headers={'X-Login-Token':r['token']})
 with op.open(req,timeout=10) as response:
  data=response.read(20000) if part=='stream' else response.read()
  if part=='frame':Path('/tmp/deepseek-test-latest.jpg').write_bytes(data)
  print(json.dumps({'part':part,'bytes':len(data),'state':json.loads(data) if part=='state' else None,'prefix':data[:80].decode(errors='replace') if part=='stream' else ''}),flush=True)
