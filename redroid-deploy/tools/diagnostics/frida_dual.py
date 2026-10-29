
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import frida,subprocess,time,json,sys
from pathlib import Path
container=sys.argv[1]
assert container in ('doubao-hpe14-13-test','doubao-hpe14-account2')
port=27044 if container=='doubao-hpe14-13-test' else 27043
pid=int(subprocess.check_output(['docker','exec',container,'pidof','com.larus.nova'],text=True))
device=frida.get_device_manager().add_remote_device('127.0.0.1:'+str(port))
session=device.attach(pid)
bridge=Path('/home/user/redroid-doubao/worker-venv/lib/python3.10/site-packages/frida_tools/bridges/java.js').read_text()
code=Path('/home/user/redroid-doubao/'+sys.argv[2]).read_text()
if container=='doubao-hpe14-13-test':code=code.replace('38436542168665602','38436622044882690')
script=session.create_script(bridge+'\nconst Java=bridge;\n'+code)
script.on('message',lambda m,d:print(json.dumps(m,ensure_ascii=False),flush=True))
try:
 script.load();time.sleep(int(sys.argv[3]) if len(sys.argv)>3 else 10)
finally:session.detach()
