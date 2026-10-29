
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
from remote import connect
import shlex
c,p=connect(); cmd='docker exec doubao-hpe14-test logcat -d | grep -E "FATAL EXCEPTION|Fatal signal|houdini|UnsatisfiedLinkError|dlopen failed|cannot locate|Process.*nova|Abort message|SIGSEGV|SIGABRT" | tail -70'
i,o,e=c.exec_command('sudo -S -p "" bash -lc '+shlex.quote(cmd));i.write(p+'\n');i.flush();i.channel.shutdown_write();print(o.read().decode('utf8','replace'));c.close()
