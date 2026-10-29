import sys,json,traceback,sqlite3
from pathlib import Path
sys.path[:0]=['/home/user/redroid-yuanbao','/home/user/redroid-doubao','/home/user/redroid-doubao/geo-batch-code']
from android_ui import Android,PACKAGE
import xml.etree.ElementTree as ET
a=Android();print('APP',a.device.app_current());print('VERSION',a.device.app_info(PACKAGE).get('versionCode'))
xml=a.device.dump_hierarchy();Path('/tmp/yuanbao28-ui.xml').write_text(xml)
print('UI',json.dumps([{k:n.get(k) for k in ['text','content-desc','class','clickable','bounds']} for n in ET.fromstring(xml).iter('node') if n.get('text') or n.get('content-desc')],ensure_ascii=False))
try:
 from native_client import NativeClient
 root=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261028-090004-02abccba')
 client=NativeClient(root);client.connect();print('NATIVE_CONNECTED');client.close()
except Exception as error:print('NATIVE_ERROR',type(error).__name__,str(error));traceback.print_exc()
