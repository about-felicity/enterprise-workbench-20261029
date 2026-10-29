import json,xml.etree.ElementTree as ET
from pathlib import Path
import uiautomator2 as u
for n,port in [('doubao1',5557),('doubao2',5558)]:
 d=u.connect('127.0.0.1:'+str(port));raw=d.dump_hierarchy();Path('/home/user/redroid-doubao/batches')
 out=Path('/opt/monitor/geo-capture/soak/all-channel-soak2h-1792056244/diagnostics');out.mkdir(exist_ok=True,mode=0o700)
 (out/(n+'-prepare-failure.xml')).write_text(raw)
 rows=[]
 for e in ET.fromstring(raw).iter('node'):
  a=e.attrib;rid=a.get('resource-id','')
  if a.get('clickable')=='true' or 'input' in rid or 'create_new' in rid:
   rows.append({'id':rid,'class':a.get('class'),'desc':a.get('content-desc'),'clickable':a.get('clickable'),'bounds':a.get('bounds'),'text_length':len(a.get('text',''))})
 print(json.dumps({'model':n,'controls':rows},ensure_ascii=False))
