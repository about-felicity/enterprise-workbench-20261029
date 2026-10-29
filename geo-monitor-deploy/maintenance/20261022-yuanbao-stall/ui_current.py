import sys,json,xml.etree.ElementTree as ET
sys.path.insert(0,'/home/user/redroid-yuanbao')
from android_ui import Android
a=Android();root=ET.fromstring(a.device.dump_hierarchy())
print(json.dumps([{k:n.get(k) for k in ('text','class','scrollable','bounds','resource-id')} for n in root.iter('node') if n.get('text') or n.get('scrollable')=='true'],ensure_ascii=False)[:7000])
