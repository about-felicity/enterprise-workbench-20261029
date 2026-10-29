
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
from remote import connect
import shlex,pathlib
c,p=connect()
cmd='docker exec doubao-redroid-redroid-1 logcat -b all -d | grep -E "berberis|crash_dump|Fatal signal|debuggerd" | tail -70'
i,o,e=c.exec_command('sudo -S -p "" bash -lc '+shlex.quote(cmd));i.write(p+'\n');i.flush();i.channel.shutdown_write();s=o.read().decode('utf8','replace');print(s); pathlib.Path('redroid-deploy/artifacts/translation-debugger.log').write_text(s,encoding='utf8');c.close()
