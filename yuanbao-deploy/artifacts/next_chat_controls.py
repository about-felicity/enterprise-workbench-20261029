import os,json,re,xml.etree.ElementTree as E
os.environ['ADBUTILS_ADB_PATH']='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
import uiautomator2 as u2
d=u2.connect('127.0.0.1:5559')
for n in E.fromstring(d.dump_hierarchy()).iter('node'):
 a=n.attrib;b=list(map(int,re.findall(r'\d+',a.get('bounds',''))))
 if (len(b)==4 and 50<b[1]<180) or a.get('class') in ['android.widget.EditText','android.widget.Button']:
  v={k:a.get(k) for k in ['content-desc','resource-id','class','bounds','clickable','enabled']};print(json.dumps(v,ensure_ascii=True))
