import json,sys
from pathlib import Path
sys.path[:0]=['/home/user/redroid-doubao/geo-batch-code','/home/user/redroid-yuanbao']
from native_client import NativeClient,BASE
r=NativeClient(BASE/'batches/geo-panel-yuanbao-20261022-090005-705819fb');r.connect()
bridge=Path('/home/user/redroid-doubao/worker-venv/lib/python3.10/site-packages/frida_tools/bridges/java.js').read_text()
schema=(BASE/'tools/chat_model_schema.json').read_text()
s=r.session.create_script(bridge+'\nconst Java=bridge;\nconst MODEL_SCHEMA='+schema+';\n'+Path('/tmp/yuanbao-models22.js').read_text())
try:
 s.load();rows=s.exports_sync.history_entries()
 print(json.dumps({'count':len(rows),'original':[r for r in rows if r['conversation_id']=='0RRIw2HvYau']},ensure_ascii=False))
finally:r.close()
