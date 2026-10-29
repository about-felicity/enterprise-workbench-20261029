
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import sys
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from unattended_worker import Android
from unattended_core import DataError
try:
    Android('127.0.0.1:5558','/home/user/redroid-doubao/linux-tools/platform-tools/adb').ready()
except DataError as exc:
    print('BLOCKED_BEFORE_SEND:',exc)
else:
    print('NEW_CHAT_READY; no message submitted')
