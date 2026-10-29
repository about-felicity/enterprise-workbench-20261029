"""Operate only account2 UI by explicit selector; print visible controls."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import os, sys, json, xml.etree.ElementTree as ET
os.environ['ADBUTILS_ADB_PATH']='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
import uiautomator2 as u2
d=u2.connect('127.0.0.1:5558')
if len(sys.argv)>1:
    if sys.argv[1]=='back':
        d.press('back')
    elif sys.argv[1].startswith('desc:'):
        d(description=sys.argv[1][5:]).click(timeout=5)
    elif sys.argv[1].startswith('text:'):
        d(text=sys.argv[1][5:]).click(timeout=5)
    else:
        d(resourceId='com.larus.nova:id/'+sys.argv[1]).click(timeout=5)
tree=ET.fromstring(d.dump_hierarchy())
print(json.dumps([{'id':e.get('resource-id'),'text':e.get('text'),'desc':e.get('content-desc'),'bounds':e.get('bounds')} for e in tree.iter('node') if e.get('text') or e.get('content-desc')],ensure_ascii=False))
