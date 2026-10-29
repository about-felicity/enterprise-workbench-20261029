"""Normal App navigation to read existing history only. No retry/send control."""
import os,sys,json,time,xml.etree.ElementTree as ET
from pathlib import Path
os.environ['ADBUTILS_ADB_PATH']='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
import uiautomator2 as u2
d=u2.connect('127.0.0.1:5558');mode=sys.argv[1]
out=Path('/opt/monitor/geo-capture/maintenance/20261015-reliability/pending-doubao2')
if mode=='back':
 s=d(resourceId='com.larus.nova:id/back_icon')
 if s.count!=1:raise RuntimeError('Unique observed back control required')
 s.click();time.sleep(1)
elif mode in ('previous','original'):
 s=d(resourceId='com.larus.nova:id/tv_title',text='推荐卸妆油' if mode=='previous' else '爽肤水推荐')
 if s.count!=1:raise RuntimeError('Unique observed history title required')
 s.click();time.sleep(3)
elif mode!='read':raise RuntimeError('Unsupported mode')
xml=d.dump_hierarchy();(out/('history-'+mode+'.xml')).write_text(xml)
print(json.dumps({'at':time.time(),'mode':mode,'nodes':[{'text':n.get('text','')[:100],'description':n.get('content-desc','')[:100],'resource_id':n.get('resource-id'),'bounds':n.get('bounds'),'clickable':n.get('clickable')} for n in ET.fromstring(xml).iter('node') if (n.get('text') or n.get('content-desc') or n.get('clickable')=='true') and ('com.larus.nova' in n.get('resource-id','') or not n.get('resource-id'))][:65] if mode in ('read','back') else []},ensure_ascii=False))
