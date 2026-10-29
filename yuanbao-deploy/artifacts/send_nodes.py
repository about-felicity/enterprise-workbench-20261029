import re,xml.etree.ElementTree as E,json
from pathlib import Path
r=E.fromstring(Path('/home/user/redroid-yuanbao/diagnostics/native-capture-20261015/current-ui.xml').read_text())
for n in r.iter('node'):
 a=n.attrib;b=list(map(int,re.findall(r'\d+',a.get('bounds',''))))
 if len(b)==4 and b[0]>=560 and 300<b[1]<650:print(json.dumps({k:a.get(k) for k in ['text','content-desc','resource-id','class','bounds','clickable','enabled']}))
