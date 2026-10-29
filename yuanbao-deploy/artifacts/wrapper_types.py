import json
from pathlib import Path
items=json.loads(Path('/home/user/redroid-yuanbao/batches/geo-yuanbao-21x5-20261015/native-model-first.json').read_text())
for i,item in enumerate(items):
 print(json.dumps({'item':i,'wrappers':{k:{'type':v.get('_type'),'prefix':v.get('text','')[:120]} for k,v in item['value'].items() if isinstance(v,dict)}},ensure_ascii=True))
