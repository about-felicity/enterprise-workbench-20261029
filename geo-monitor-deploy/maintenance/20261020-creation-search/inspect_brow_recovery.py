import json,sys,shutil
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,studio
t=runtime.read(Path('/opt/monitor/geo-capture/maintenance/20261020-brow-daily/task.json'))
r=studio.capture_root(t['plan_id'])/'days'/t['start_date']/'wenxin_card'/'collector'
files=sorted((r/'recovery_evidence').glob('*/*/snapshot.json'),key=lambda p:p.stat().st_mtime)
out=[]
for p in files[-2:]:
    j=runtime.read(p);out.append({'title':j.get('title'),'text':j.get('pageText','')[:1200]})
if files and (files[-1].parent/'page.png').exists():
    shutil.copy2(files[-1].parent/'page.png','/tmp/brow-verification.png')
print(json.dumps({'evidence':out,'recovery':runtime.read(r/'search_recovery.json')},ensure_ascii=False))
