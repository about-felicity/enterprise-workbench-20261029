import json
from pathlib import Path
v=json.loads(Path('/home/user/redroid-yuanbao/batches/geo-yuanbao-21x5-20261015/native-getters-first.json').read_text())
def shape(v,d=0):
 if d>6:return type(v).__name__
 if isinstance(v,dict):return {k:shape(x,d+1) for k,x in v.items() if x is not None}
 if isinstance(v,list):return {'count':len(v),'items':[shape(x,d+1) for x in v[:4]]}
 if isinstance(v,str):
  try:return {'json':shape(json.loads(v),d+1)}
  except ValueError:return {'length':len(v),'prefix':v[:100] if len(v)<200 else '[long text]'}
 return v
print(json.dumps({'entities':shape(v['entities']),'question_entities':shape(v['question_entities']),'question_state':v['question'].get('state')},ensure_ascii=True))
