import uiautomator2 as u2,json,xml.etree.ElementTree as E
from pathlib import Path
d=u2.connect('127.0.0.1:5558');print('app',d.app_current());x=d.dump_hierarchy();print(json.dumps([{k:e.attrib.get(k) for k in ['text','resource-id','class','bounds','clickable','enabled']} for e in E.fromstring(x).iter('node') if e.attrib.get('resource-id','').startswith('com.larus')],ensure_ascii=False));d.screenshot().save('/tmp/geo-doubao2-retry.png')
