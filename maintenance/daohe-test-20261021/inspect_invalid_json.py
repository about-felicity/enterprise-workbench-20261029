import sys,json
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,studio
M=Path('/opt/monitor/geo-capture/maintenance/20261021-daohe-test');s=runtime.read(M/'task.json');t=runtime.read(studio.day_path(s['plan_id'],s['date']));result=[]
for jid in t['jobs'].values():
 root=runtime.job_root(jid)
 for p in (root/'api/runs').glob('*/call/api_state.json'):
  if runtime.read(p).get('state')!='INVALID_RESPONSE':continue
  a=runtime.read(p.parent/'answer.json');content=a.get('content','');row={'job':jid,'run':p.parent.parent.name,'finish_reason':a.get('finish_reason'),'length':len(content)}
  try:json.loads(content);row['strict_valid']=True
  except json.JSONDecodeError as e:
   row.update(error=e.msg,position=e.pos,near=content[max(0,e.pos-55):e.pos+80])
   try:row['control_only_parse']=isinstance(json.loads(content,strict=False),dict)
   except (ValueError,TypeError):row['control_only_parse']=False
  result.append(row)
print(json.dumps(result,ensure_ascii=False))
