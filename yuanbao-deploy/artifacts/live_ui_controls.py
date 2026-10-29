import os,json,xml.etree.ElementTree as E
from pathlib import Path
os.environ['ADBUTILS_ADB_PATH']='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
import uiautomator2 as u2
d=u2.connect('127.0.0.1:5559');xml=d.dump_hierarchy()
Path('/home/user/redroid-yuanbao/diagnostics/native-capture-20261015/current-ui.xml').write_text(xml,encoding='utf8')
for n in E.fromstring(xml).iter('node'):
 a=n.attrib
 if a.get('text') or a.get('content-desc') or a.get('class')=='android.widget.EditText':
  value={k:a.get(k) for k in ['text','content-desc','resource-id','class','bounds','clickable']}
  if value['text'] and value['text'].startswith('Hi'):value['text']='[account label]'
  print(json.dumps(value,ensure_ascii=True))
