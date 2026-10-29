import json,sys,shutil,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from geo_source_cards.runtime import atomic_json,process_lock
root=runtime.BASE/'runs/creation-1793142584-b167f637';p=root/'queue/730c24afaf688d7381074bb6/ticket.json'
with process_lock(root/'api/worker.lock',blocking=False),process_lock(root/'coordinator.lock',blocking=False):
 t=runtime.read(p);assert t['state']=='needs_attention'
 d=Path('/opt/monitor/maintenance/creation-formats-20261028/spray-source-diagnosis');d.mkdir(exist_ok=False)
 shutil.copy2(p,d/'ticket.json');shutil.copy2(p.with_name('auto_repair_blocked.json'),d/'auto_repair_blocked.json')
 reason='参考来源为男士面部抗皱喷雾，与头发造型喷雾不符；原API答复另有JSON格式损坏。已保留原答复，需补充对应头发造型的来源后生成，未重复收费重发。'
 atomic_json(p,{**t,'error':reason})
 atomic_json(p.with_name('auto_repair_blocked.json'),{'status':'SOURCE_TOPIC_MISMATCH','reason':reason,'diagnosed_at':time.time()})
print('Spray failure annotated with verified source mismatch; original receipt preserved')
