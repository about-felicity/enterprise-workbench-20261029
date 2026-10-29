from pathlib import Path
import sys,json,xml.etree.ElementTree as ET
sys.path[:0]=['/home/user/redroid-yuanbao','/home/user/redroid-doubao']
from android_ui import Android,PACKAGE
a=Android();xml=a.device.dump_hierarchy()
for n in ET.fromstring(xml).iter('node'):
 if n.get('package')==PACKAGE:print(json.dumps({k:n.get(k) for k in ['text','content-desc','class','clickable','bounds']},ensure_ascii=False))
a.device.screenshot('/tmp/yuanbao-update-dialog.png')
