import json,sys,time,xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-yuanbao')
from android_ui import Android
a=Android();d=a.device
out=Path('/opt/monitor/geo-capture/maintenance/20261021-yuanbao-stall')
if '--drawer' in sys.argv:
 selector=d(description='抽屉页入口')
 assert selector.count==1,'Unique existing history entry required'
 a.tap(selector);time.sleep(1)
if '--reopen-current' in sys.argv:
 selector=d(text='消息发送中')
 assert selector.count==1,'Only the observed original history row may be opened'
 a.tap(selector);time.sleep(3)
if '--leave-return' in sys.argv:
 for description,title in [('抽屉页入口','干油敏肌爽肤水推荐'),('抽屉页入口','洗面奶推荐与肤质选择')]:
  drawer=d(description=description);assert drawer.count==1;a.tap(drawer);time.sleep(1)
  item=d(text=title);assert item.count==1,'Observed history row changed; no guessed click'
  a.tap(item);time.sleep(2)
if '--open-title' in sys.argv:
 title=sys.argv[sys.argv.index('--open-title')+1]
 assert title=='洗面奶推荐与肤质选择','This one-off only reopens the observed original conversation'
 item=d(text=title);assert item.count==1;a.tap(item);time.sleep(2)
xml=d.dump_hierarchy();(out/'ui-before.xml').write_text(xml);d.screenshot().save(out/'ui-before.png')
print(json.dumps([{'text':n.get('text','')[:180],'desc':n.get('content-desc',''),'bounds':n.get('bounds'),'id':n.get('resource-id')} for n in ET.fromstring(xml).iter('node') if n.get('text') or n.get('content-desc')],ensure_ascii=False))

