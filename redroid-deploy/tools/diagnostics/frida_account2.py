"""Run sanitized Java diagnostics on account2 only, detached on exit."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import frida,subprocess,time,json,sys
from pathlib import Path
pid=int(subprocess.check_output(['docker','exec','doubao-hpe14-account2','pidof','com.larus.nova'],text=True))
device=frida.get_device_manager().add_remote_device('127.0.0.1:27043')
realm='emulated' if '--emulated' in sys.argv else 'native'
session=device.attach(pid,realm=realm)
bridge=Path('/home/user/redroid-doubao/worker-venv/lib/python3.10/site-packages/frida_tools/bridges/java.js').read_text()
code=Path('/home/user/redroid-doubao/'+sys.argv[1]).read_text()
script=session.create_script((bridge+'\nconst Java=bridge;\n' if realm=='native' else '')+code)
script.on('message',lambda message,data:print(json.dumps(message,ensure_ascii=False),flush=True))
try:
    script.load()
    time.sleep(int(sys.argv[2]) if len(sys.argv)>2 else 15)
finally:session.detach()
