import json,sys
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-yuanbao')
from native_client import NativeClient
root=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261015-175828-60d0d3fc')
client=NativeClient(root)
try:
 client.connect();rows=client.script.exports_sync.snapshot('推荐一款睫毛增长液')
 for row in rows:
  h=row['value'].get('h',{});cid=h.get('conversationId');answer=h.get('msgId')
  if not cid or not answer:continue
  raw=client.script.exports_sync.read_known(cid,answer)
  q=raw.get('question',{});print(json.dumps({'cid':cid,'createTime':q.get('createTime'),'serverIndex':q.get('serverIndex'),'id':q.get('id')},ensure_ascii=False))
finally:client.close()
