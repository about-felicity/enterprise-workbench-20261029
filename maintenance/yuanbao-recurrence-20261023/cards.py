import json,sys
from pathlib import Path
sys.path[:0]=['/home/user/redroid-yuanbao','/home/user/redroid-doubao/geo-batch-code']
from native_client import NativeClient
R=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261023-090004-d6b66215');D=Path('/opt/monitor/geo-capture/maintenance/20261023-yuanbao-recurrence')
o=json.loads((D/'live.json').read_text());print(json.dumps({'observed':o.get('observed'),'ui':o['ui'],'stored_proof':{k:v for k,v in (o.get('stored_proof') or {}).items() if k!='other_titles'}},ensure_ascii=False))
c=NativeClient(R)
try:
 c.connect();rows=c.script.exports_sync.snapshot('推荐一款护手霜');matches=[]
 for i,r in enumerate(rows):
  v=r['value'];h=v.get('h',{})
  if h.get('conversationId')!='0RTB4lSYXbs':continue
  cards=v.get('i',{}).get('replacesJson',[])
  matches.append({'index':i,'h':h,'cards':cards,'fields':list(v)})
 (D/'cards.json').write_text(json.dumps(matches,ensure_ascii=False,indent=2))
 print(json.dumps({'matching_viewmodels':matches},ensure_ascii=False)[:8000])
finally:c.close()
