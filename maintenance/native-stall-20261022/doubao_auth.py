import sys,json,xml.etree.ElementTree as ET,time
from pathlib import Path
sys.path[:0]=['/home/user/redroid-doubao/geo-batch-code','/home/user/redroid-yuanbao']
from question_only_adapters import android
d=android('doubao1','127.0.0.1:5557','/home/user/redroid-doubao/linux-tools/platform-tools/adb').device
out={'at':time.time(),'app':d.app_current(),'ui':[{k:n.get(k) for k in ('text','resource-id','class','content-desc','clickable') if n.get(k)} for n in ET.fromstring(d.dump_hierarchy()).iter('node') if n.get('text') or n.get('content-desc')]}
Path('/opt/monitor/geo-capture/maintenance/20261022-native-stall/doubao-auth.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False)[:6000])
