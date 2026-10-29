
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
from remote import connect
import shlex
c,p=connect();cmd="python3 -c \"import xml.etree.ElementTree as E; r=E.parse('/home/user/redroid-doubao/hpe14-13-screen.xml'); print([(n.get('text'),n.get('resource-id')) for n in r.iter('node') if n.get('text')])\""
i,o,e=c.exec_command('sudo -S -p "" bash -lc '+shlex.quote(cmd));i.write(p+'\n');i.flush();i.channel.shutdown_write();print(o.read().decode('utf8','replace'));c.close()
