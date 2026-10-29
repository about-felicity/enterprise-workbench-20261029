import json,os,sys,xml.etree.ElementTree as ET
from pathlib import Path
os.environ['ADBUTILS_ADB_PATH']='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
import uiautomator2 as u2
sys.path.insert(0,'/home/user/redroid-deepseek/code')
from auth_policy import classify_ui
d=u2.connect('127.0.0.1:5562')
assert d.app_current().get('package')=='com.deepseek.chat'
xml=d.dump_hierarchy()
root=Path('/opt/monitor/geo-capture/maintenance/20261017-deepseek-risk');root.mkdir(exist_ok=True)
p=root/'test-ui-private.xml';p.write_text(xml);p.chmod(0o600)
tree=ET.fromstring(xml)
texts=[{k:n.get(k,'') for k in ['text','class','resource-id','bounds','clickable','enabled']} for n in tree.iter('node') if n.get('package')=='com.deepseek.chat' and n.get('text')]
print(json.dumps({'before':classify_ui(xml,True),'visible_nodes':texts},ensure_ascii=False))
