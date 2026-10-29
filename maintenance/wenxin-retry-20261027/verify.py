import json,sqlite3,time
from pathlib import Path
G=Path('/opt/monitor/geo-capture');S=Path('/opt/monitor/geo-content/studio/capture')
def read(p):
 try:return json.loads(p.read_text())
 except FileNotFoundError:return {}
rows=[]
for pid in ['plan-195abff2413a421dac589112f24c7596','plan-53eaaebbc537459f81d55a3f8a43f969']:
 root=S/pid;h=read(root/'health.json');day=h.get('day');r=root/'days'/day/'wenxin_card/collector'
 with sqlite3.connect(r/'tasks.sqlite') as db:counts=dict(db.execute('select state,count(*) from captures group by state'))
 rows.append({'plan':pid,'day':day,'status':h.get('status'),'wenxin':counts,'retry':read(root/'profiles/search/wenxin_card/verification_retry.json')})
root=G/'batches/geo-panel-wenxin-card-20261026-112314-9a29529d';h=read(root/'bridge_health.json')
rows.append({'main_geo':True,'status':h.get('status'),'tasks':h.get('tasks'),'captured':h.get('captured'),'processed':h.get('processed'),'retry':read(G/'profiles/search/wenxin_card/verification_retry.json')})
result={'at':time.time(),'channels':rows};out=G/'maintenance/20261027-wenxin-retry/verification.json';out.write_text(json.dumps(result,indent=2));print(json.dumps(result))
