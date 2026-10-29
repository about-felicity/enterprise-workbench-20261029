import json,subprocess,sys
from pathlib import Path
import frida
sys.path.insert(0,'/home/user/redroid-yuanbao/tools')
from wechat_qr_compat import validate
validate()
pid=int(subprocess.check_output(['docker','exec','yuanbao-hpe14-android13','pidof','com.tencent.hunyuan.app.chat']))
session=frida.get_device_manager().add_remote_device('127.0.0.1:27044').attach(pid,realm='native')
bridge=Path('/home/user/redroid-doubao/worker-venv/lib/python3.10/site-packages/frida_tools/bridges/java.js').read_text()
code=Path('/tmp/yuanbao_wcdb_reader.js').read_text()
script=session.create_script(bridge+'\nconst Java=bridge;\n'+code)
script.load()
try:script.exports_sync.discover();print(json.dumps(script.exports_sync.schema()))
finally:session.detach()

