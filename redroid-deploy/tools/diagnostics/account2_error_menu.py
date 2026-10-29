
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import sys,json,os,xml.etree.ElementTree as ET
os.environ['ADBUTILS_ADB_PATH']='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
import uiautomator2 as u2
d=u2.connect('127.0.0.1:5558')
if '--open' in sys.argv:d(text='出了点问题，请稍后重试。').long_click(duration=1)
print(json.dumps([{'id':n.get('resource-id'),'text':n.get('text'),'desc':n.get('content-desc'),'bounds':n.get('bounds')} for n in ET.fromstring(d.dump_hierarchy()).iter('node') if n.get('text') or n.get('content-desc')],ensure_ascii=False))
