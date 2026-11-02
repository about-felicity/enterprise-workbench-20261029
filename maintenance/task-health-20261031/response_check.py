import hashlib,json
from pathlib import Path
base=Path('/opt/monitor/geo-content')
p=base/'engine/geo_source_cards/source_analysis.py';print('SOURCE_HASH',hashlib.sha256(p.read_bytes()).hexdigest())
for jid,rid in [('creation-1793397144-33d4e53e','c06ff7ed0ce26c6097e4fb97'),('creation-1793400211-f3855aab','e6154840a210bc391de15473')]:
 for p in (base/'runtime/runs'/jid/'api/runs'/rid).rglob('answer.json'):
  answer=json.loads(p.read_text());content=answer['content'];info={'path':str(p),'finish_reason':answer.get('finish_reason'),'length':len(content),'tail':content[-220:]}
  try:obj=json.loads(content);info['parsed_keys']=list(obj)
  except json.JSONDecodeError as e:
   info.update(error=str(e),near=content[max(0,e.pos-140):e.pos+140])
   try:info['relaxed_keys']=list(json.loads(content,strict=False))
   except ValueError:pass
  print('ANSWER',json.dumps(info,ensure_ascii=False))
