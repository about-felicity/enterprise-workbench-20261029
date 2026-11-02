import json,subprocess
from pathlib import Path
from urllib.parse import urlsplit,parse_qsl,unquote
for n in (3,4):
 p=Path(f'/tmp/doubao-panel-url-{n}.log');print(n,p.read_text()[-600:] if p.exists() else 'waiting')
 r=Path(f'/home/user/redroid-doubao/batches/geo-expand-doubao{n}-20261102-strict');items=json.loads(next((r/'outbox').glob('*.json')).read_text())['payload']['items']
 print('saved',[(i+1,urlsplit(x['url']).netloc,urlsplit(x['url']).path[:80]) for i,x in enumerate(items)])
 code="import uiautomator2 as u;print(u.connect('127.0.0.1:556"+str(n)+"').clipboard)"
 raw=subprocess.run(['/home/user/redroid-doubao/worker-venv/bin/python','-c',code],capture_output=True,text=True,timeout=10).stdout.strip()
 if raw.startswith('http'):
  x=urlsplit(raw);y=urlsplit(dict(parse_qsl(x.query)).get('target',raw));print('clipboard',x.netloc,x.path[:90],y.netloc,y.path[:90],list(dict(parse_qsl(y.query))))
 else:print('clipboard non-url',len(raw))
