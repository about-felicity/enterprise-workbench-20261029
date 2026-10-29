import sys,json,sqlite3,re,hashlib
from pathlib import Path
sys.path[:0]=['/home/user/redroid-doubao/geo-batch-code','/home/user/redroid-yuanbao']
from native_storage import databases,open_readonly
from android_ui import Android
import xml.etree.ElementTree as ET
D=Path('/opt/monitor/geo-capture/maintenance/20261022-yuanbao-stall')
for i,p in enumerate(databases()):
 with open_readonly(p) as db:
  print('store',i,'tables', {t:db.execute('select count(*) from '+t).fetchone()[0] for t in ('ChatMessages','ChatMessagesContecnt','ChatConversationDetail')})
  print('latest',json.dumps([dict(r) for r in db.execute('select conversation_id,title from ChatConversationDetail order by rowid desc limit 8')],ensure_ascii=False))
  print('columns', [r[1] for r in db.execute('pragma table_info(ChatMessagesContecnt)')])
logs=(D/'logcat-before.txt').read_text(errors='replace').splitlines()
for text in ('6679b5f4','0RRIw2Hv','INTERRUPTED','interrupt','timeout','errorCode','failed','network'):
 hits=[s for s in logs if text.lower() in s.lower() and 'com.google' not in s]
 print('log_hits',text,len(hits))
 # Preserve logs privately; show only tags and numeric status codes.
 print([re.sub(r'(https?://\S+)', '[url]',s[:120]) for s in hits[-8:]])
a=Android();d=a.device
entry=d(description='抽屉页入口')
if entry.count!=1:raise RuntimeError('drawer is not unique')
a.tap(entry)
import time;time.sleep(1)
xml=d.dump_hierarchy();(D/'drawer.xml').write_text(xml)
print('drawer',json.dumps([{k:n.get(k) for k in ('text','content-desc','resource-id','clickable','bounds')} for n in ET.fromstring(xml).iter('node') if n.get('text') or n.get('content-desc')],ensure_ascii=False))
d.press('back')
