import sys,json,requests
sys.path.insert(0,'/tmp')
from vps_geo_access import browser_cookie
s=requests.Session();s.trust_env=False;s.cookies.set('geo_monitor_session',browser_cookie(),domain='1any.top',path='/geo_monitor/')
for base in ['http://127.0.0.1:3000/api/geo-capture/','https://1any.top/geo_monitor/api/geo-capture/']:
 for path in ['login/deepseek2/ui','login/deepseek2/state','login/deepseek2/frame']:
  try:
   r=s.get(base+path,timeout=15);x={'entry':'lan' if '127.0.0.1' in base else 'public','path':path,'status':r.status_code,'bytes':len(r.content)}
   if path.endswith('/state') and r.ok:x.update(auth=r.json().get('auth'),csrf_present=len(r.json().get('csrf',''))==64)
   if not r.ok:x['message']=r.text[:160]
   print(json.dumps(x,ensure_ascii=False),flush=True)
  except requests.RequestException as e:print(type(e).__name__,str(e)[:230],flush=True)
