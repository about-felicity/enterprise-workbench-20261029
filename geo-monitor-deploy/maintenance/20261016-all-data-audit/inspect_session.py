"""Metadata only: never prints authentication values."""
import json,os,sqlite3,subprocess,urllib.request
from pathlib import Path
import websocket
B=Path('/opt/monitor/geo-capture/batches/geo-panel-deepseek-20261016-094039-dc64b7e1/collector')
print('events', (B/'deepseek_session_events.jsonl').read_text()[-6000:])
print('files', [{'name':p.name,'modified':p.stat().st_mtime,'bytes':p.stat().st_size} for p in B.iterdir() if p.is_file() and ('deepseek' in p.name or 'health' in p.name)])
for pid in Path('/proc').iterdir():
 if not pid.name.isdigit():continue
 try:
  args=(pid/'cmdline').read_bytes().decode().split('\0')
  if any('--remote-debugging-port=9514'==a for a in args):print('browser_args',[a for a in args if a.startswith(('--user-data-dir','--incognito','--remote-debugging-port'))])
 except (OSError,UnicodeError):pass
try:
 with urllib.request.urlopen('http://127.0.0.1:9514/json') as response:tabs=json.load(response)
 tab=next(t for t in tabs if t['type']=='page' and 'chat.deepseek.com' in t['url'])
 ws=websocket.create_connection(tab['webSocketDebuggerUrl'],origin='http://127.0.0.1',timeout=10)
 def call(method,params):
  call.id+=1;ws.send(json.dumps({'id':call.id,'method':method,'params':params}))
  while True:
   value=json.loads(ws.recv())
   if value.get('id')==call.id:return value.get('result',{})
 call.id=0
 meta=call('Runtime.evaluate',{'expression':"JSON.stringify({origin:location.origin,path:location.pathname,local:Object.entries(localStorage).map(([k,v])=>({key:k,length:v.length})),session:Object.entries(sessionStorage).map(([k,v])=>({key:k,length:v.length}))})",'returnByValue':True})
 print('storage_metadata',meta.get('result',{}).get('value'))
 print('cookie_metadata',[{k:c.get(k) for k in ('name','domain','expires','session')} for c in call('Network.getAllCookies',{}).get('cookies',[]) if 'deepseek' in c.get('domain','')])
 ws.close()
except Exception as error:print('live_metadata_error',type(error).__name__)
