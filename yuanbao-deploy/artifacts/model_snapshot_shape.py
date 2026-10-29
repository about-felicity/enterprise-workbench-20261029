import json,re
from pathlib import Path
items=json.loads(Path('/home/user/redroid-yuanbao/batches/geo-yuanbao-21x5-20261015/native-model-first.json').read_text())
def shape(v,d=0):
 if d>5:return type(v).__name__
 if isinstance(v,dict):return {k:shape(x,d+1) for k,x in v.items()}
 if isinstance(v,list):return {'count':len(v),'first':shape(v[0],d+1) if v else None}
 if isinstance(v,str):
  try:return {'json':shape(json.loads(v),d+1)}
  except ValueError:return {'type':'string','length':len(v),'task_marker':'820da1fd-a5d3-5050-ba08-99a650c28cc8' in v}
 return v
for item in items:print(json.dumps({'kind':item['kind'],'fields':{k:shape(v) for k,v in item['value'].items()}},ensure_ascii=True))
