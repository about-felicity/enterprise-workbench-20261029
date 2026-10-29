import xml.etree.ElementTree as E,json
from pathlib import Path
r=E.fromstring(Path('/home/user/redroid-yuanbao/diagnostics/native-capture-20261015/logged-in-ui.xml').read_text())
for n in r.iter('node'):
 a=n.attrib
 if a.get('clickable')=='true' or a.get('class')=='android.widget.EditText':
  value={k:a.get(k) for k in ['text','content-desc','resource-id','class','bounds','clickable']}
  if value['text'] and value['text'].startswith('Hi'):value['text']='[account label]'
  print(json.dumps(value,ensure_ascii=True))
