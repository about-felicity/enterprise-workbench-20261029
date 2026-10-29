import json
from pathlib import Path
r=Path('/opt/monitor/geo-content/runtime/runs/creation-1792556219-bbc55e13')
for p in sorted((r/'api/runs').glob('*/materialization_error.json'),key=lambda p:p.stat().st_mtime)[-3:]:
 a=json.loads((p.parent/'answer.json').read_text());print('ERROR',p.parent.name,p.read_text());print('META',json.loads((p.parent/'writing_job.json').read_text()).get('job_id'))
 doc=a.get('document',{})
 for para in doc.get('introduction',[])+[p for s in doc.get('sections',[]) for p in s.get('paragraphs',[])]+doc.get('conclusion',[]):
  if not para.get('text','').strip() or '\n' in para.get('text','') or para.get('text','').startswith('#'):print('BAD',json.dumps(para,ensure_ascii=False)[:1200])
