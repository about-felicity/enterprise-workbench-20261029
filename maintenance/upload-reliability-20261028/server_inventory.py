import sys,json,hashlib,time,urllib.request,subprocess
from pathlib import Path
root=Path('/opt/monitor/geo-content'); st=root/'studio'
read=lambda p:json.loads(p.read_text())
out={'at':time.time(),'products':[],'library':[],'hashes':{}}
for p in (st/'products').glob('*.json'):
 d=read(p);out['products'].append({'id':d['product_id'],'name':d['product']['name'],'brand':d['product'].get('brand'),'updated_at':d['updated_at'],'source':d.get('word_source',{}).get('sha256'),'file':d.get('word_source',{}).get('filename'),'facts':len(d['product'].get('facts',[]))})
for p in (st/'library').glob('library-*.json'):
 d=read(p);out['library'].append({k:d.get(k) for k in ['library_id','product_id','name','updated_at','uploads']})
for f in ['runtime.py','product_images.py','library.js','knowledge_library.py','studio.py','panel.html','service.py']:
 out['hashes'][f]=hashlib.sha256((root/'creation'/f).read_bytes()).hexdigest()
out['gateway_sha']=hashlib.sha256(Path('/opt/monitor/yuanbao_monitor/dashboard/app/api/geo-creation/[...path]/route.ts').read_bytes()).hexdigest()
out['processes']=subprocess.run(['systemctl','show','geo-content-api','geo-content-worker','geo-creation-studio','-p','Id','-p','MainPID'],capture_output=True,text=True).stdout
for endpoint in ['http://127.0.0.1:8804/api/panel','http://127.0.0.1:3000/api/geo-creation/panel']:
 begin=time.monotonic()
 try:
  with urllib.request.urlopen(endpoint,timeout=65) as r:body=r.read();out[endpoint]={'seconds':round(time.monotonic()-begin,2),'bytes':len(body),'http':r.status}
 except Exception as e:out[endpoint]={'seconds':round(time.monotonic()-begin,2),'error':str(e)}
sys.path.insert(0,'/opt/monitor/geo-capture')
try:
 from vps_geo_access import vps_python
 out['public']=json.loads(vps_python("""import json,re
from pathlib import Path
t=Path('/etc/nginx/nginx.conf').read_text();start=t.find('location ^~ /geo_monitor/api/geo-creation/')
print(json.dumps({'creation_block':t[start:t.find('}',start)+1] if start>=0 else 'missing','body_limits':re.findall(r'client_max_body_size[^;]*;',t),'oversize_errors':[s for s in Path('/var/log/nginx/error.log').read_text().splitlines() if 'too large body' in s and 'geo-creation' in s][-5:]}))"""))
except Exception as e:out['public_error']=str(e)
print(json.dumps(out,ensure_ascii=False,indent=2))
