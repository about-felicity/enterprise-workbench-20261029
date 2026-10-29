
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import os,json,xml.etree.ElementTree as ET
os.environ['ADBUTILS_ADB_PATH']='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
import uiautomator2 as u2
d=u2.connect('127.0.0.1:5558')
print(json.dumps([{'id':e.get('resource-id'),'bounds':e.get('bounds'),'clickable':e.get('clickable')} for e in ET.fromstring(d.dump_hierarchy()).iter('node') if e.get('resource-id') and not e.get('text')],ensure_ascii=False))
