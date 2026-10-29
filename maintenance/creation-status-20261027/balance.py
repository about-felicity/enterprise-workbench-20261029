import urllib.request,json,datetime
from pathlib import Path
key=Path('/home/user/geo-editorial/secrets/deepseek.key').read_text().strip()
req=urllib.request.Request('https://api.deepseek.com/user/balance',headers={'Authorization':'Bearer '+key})
try:
 with urllib.request.urlopen(req,timeout=30) as r:data=json.load(r)
 print(json.dumps({'checked_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'provider':'DeepSeek',**data},ensure_ascii=False))
except urllib.error.HTTPError as e:print(json.dumps({'error':'HTTP '+str(e.code)}))
