import hashlib, io, json, sys, zipfile
from pathlib import Path
import requests
sys.path.insert(0, '/tmp')
from vps_geo_access import browser_cookie
s=requests.Session();s.trust_env=False
s.cookies.set('geo_monitor_session',browser_cookie(),domain='1any.top',path='/geo_monitor/')
base='https://1any.top/geo_monitor/api/geo-creation/'
out=Path('/tmp/geo-followup-public-qa');out.mkdir(exist_ok=True)
report=[]
for name,params in [('all',{'job':'all-approved','kind':'bundle'}),('one',{'job':'creation-1792526406-8f93ccca','article':'2026-10-21/科普类/01','kind':'package'})]:
 r=s.get(base+'download',params=params,timeout=120)
 row={'name':name,'status':r.status_code,'content_type':r.headers.get('Content-Type'),'bytes':len(r.content),'sha256':hashlib.sha256(r.content).hexdigest(),'header_sha256':r.headers.get('X-Content-SHA256'),'redirects':[x.status_code for x in r.history]}
 (out/(name+'.zip')).write_bytes(r.content)
 if zipfile.is_zipfile(io.BytesIO(r.content)):
  with zipfile.ZipFile(io.BytesIO(r.content)) as z:
   row.update(crc_error=z.testzip(),entries=len(z.namelist()),max_path_chars=max(map(len,z.namelist())),max_component_chars=max(len(c) for n in z.namelist() for c in n.split('/')),manifest_count=json.loads(z.read('导出清单.json'))['count'])
 else:row['binary_zip_valid']=False
 report.append(row)
(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
