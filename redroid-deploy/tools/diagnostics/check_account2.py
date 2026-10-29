
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import os, json, subprocess
adb='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
os.environ['ADBUTILS_ADB_PATH']=adb
subprocess.run([adb,'connect','127.0.0.1:5558'],check=True,capture_output=True)
import uiautomator2 as u2
d=u2.connect('127.0.0.1:5558')
print(json.dumps({'app':d.app_current().get('package'),
    'new_chat_available':d(resourceId='com.larus.nova:id/larus_chat_top_left_create_new_cvs').exists,
    'text_input_available':d(resourceId='com.larus.nova:id/input_text').exists,
    'input_entry_available':d(resourceId='com.larus.nova:id/action_input').exists},ensure_ascii=False))
