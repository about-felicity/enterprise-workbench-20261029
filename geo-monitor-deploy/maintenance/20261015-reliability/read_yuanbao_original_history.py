"""Navigate only to the already submitted conversation; never touch send."""
import sys,os,json,time,sqlite3
from pathlib import Path
import xml.etree.ElementTree as ET
os.environ['ADBUTILS_ADB_PATH']='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
import uiautomator2 as u2
sys.path.insert(0,'/tmp');import yuanbao_native_storage as ns
out=Path('/opt/monitor/geo-capture/maintenance/20261015-reliability/yuanbao-ack')
mode=sys.argv[1] if len(sys.argv)>1 else 'read'
d=u2.connect('127.0.0.1:5559')
if mode=='drawer':
 for i,path in enumerate(ns.databases()):
  target=out/('before-history-'+str(i)+'.sqlite')
  if not target.exists():
   with ns.open_readonly(path) as src,sqlite3.connect(target) as dst:src.backup(dst)
 selector=d(description='抽屉页入口')
 if selector.count!=1:raise RuntimeError('Unique drawer unavailable')
 selector.click();time.sleep(1)
elif mode in ('original','previous'):
 selector=d(text='祛痘精华液推荐指南' if mode=='original' else '眉毛增长液推荐与成分分析')
 if selector.count!=1:raise RuntimeError('Original conversation title not unique')
 selector.click();time.sleep(3)
elif mode!='read':raise RuntimeError('Unsupported read-only mode')
xml=d.dump_hierarchy();(out/('history-ui-'+mode+'.xml')).write_text(xml)
print(json.dumps({'at':time.time(),'mode':mode,'nodes':[{'text':n.get('text','')[:95],'description':n.get('content-desc',''),'class':n.get('class'),'bounds':n.get('bounds')} for n in ET.fromstring(xml).iter('node') if n.get('text') or n.get('content-desc')]},ensure_ascii=False))
