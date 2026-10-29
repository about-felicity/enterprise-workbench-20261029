import sys,json,hashlib
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine','/opt/monitor/geo-capture']
from creation import studio,knowledge_library as kl,product_images
out={'products':[{'id':p['product_id'],'name':p['product']['name'],'brand':p['product'].get('brand'),'updated_at':p['updated_at'],'source':p.get('word_source',{}).get('sha256')} for p in studio.products()],
'library':[{'id':r['library_id'],'pid':r.get('product_id'),'name':r['name'],'updated_at':r['updated_at'],'uploads':[{'id':u['import_id'],'hash':u.get('sha256'),'at':u.get('uploaded_at'),'status':u['status']} for u in r['uploads']]} for r in kl.records()],
'images':len(product_images.images()),'hashes':{f:hashlib.sha256((Path('/opt/monitor/geo-content/creation')/f).read_bytes()).hexdigest() for f in ['runtime.py','product_images.py','library.js','knowledge_library.py','studio.py','panel.html','service.py']}}
try:
 from vps_geo_access import vps_python
 out['public']=vps_python("""from pathlib import Path
import json,re
t=Path('/etc/nginx/nginx.conf').read_text();start=t.find('location ^~ /geo_monitor/api/geo-creation/')
print(json.dumps({'creation_block':t[start:t.find('}',start)+1] if start>=0 else 'missing','body_limits':re.findall(r'client_max_body_size[^;]*;',t),'oversize_errors':sum('too large body' in s and 'geo-creation' in s for s in Path('/var/log/nginx/error.log').read_text().splitlines())}))""")
except Exception as e:out['public_error']=str(e)
print(json.dumps(out,ensure_ascii=False,indent=2))
