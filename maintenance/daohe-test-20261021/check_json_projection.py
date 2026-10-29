import sys,json,re
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,studio
M=Path('/opt/monitor/geo-capture/maintenance/20261021-daohe-test');s=runtime.read(M/'task.json');t=runtime.read(studio.day_path(s['plan_id'],s['date']));rows=[]
for jid in t['jobs'].values():
 for p in (runtime.job_root(jid)/'api/runs').glob('*/call/api_state.json'):
  if runtime.read(p).get('state')!='INVALID_RESPONSE':continue
  a=runtime.read(p.parent/'answer.json');content=a.get('content','');candidates=[]
  for m in re.finditer(r',\s*"conclusion"\s*:',content):candidates.append(('close_sections_array',content[:m.start()]+']'+content[m.start():]))
  candidates.extend(('close_root_object',content+x) for x in ('}',']'))
  if content.rstrip().endswith('}'):candidates.append(('remove_redundant_final_brace',content.rstrip()[:-1]))
  recovered=[]
  for reason,c in candidates:
   try:
    v=json.loads(c)
    if isinstance(v,dict) and (set(v)=={'document'} and set(v['document'])=={'title','introduction','sections','conclusion'} or set(v)=={'units','angle','sections','gate'}):recovered.append(reason)
   except (ValueError,TypeError,KeyError):pass
  rows.append({'job':jid,'run':p.parent.parent.name,'finish_reason':a.get('finish_reason'),'recovery_candidates':recovered})
print(json.dumps(rows))
