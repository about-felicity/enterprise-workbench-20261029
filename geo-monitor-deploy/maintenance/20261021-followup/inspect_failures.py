import json
from pathlib import Path
R=Path('/opt/monitor/geo-content/runtime/quality-repair/20261021-consumer-voice')
def read(p):return json.loads(p.read_text()) if p.exists() else {}
out=[]
for p in R.glob('*/status.json'):
 s=read(p)
 if s.get('reason')!='invalid_response' or s.get('attempt')!=3:continue
 calls=[]
 for state in p.parent.glob('attempt-3/calls/*/api_state.json'):
  v=read(state);a=read(state.with_name('answer.json'));content=a.get('content','')
  if v.get('state')=='INVALID_RESPONSE':calls.append({'call':str(state.parent),'state':v,'finish_reason':a.get('finish_reason'),'length':len(content),'head':content[:200],'tail':content[-250:]})
 out.append({'key':p.parent.name,'article':s.get('article'),'calls':calls})
print(json.dumps(out,ensure_ascii=False))
