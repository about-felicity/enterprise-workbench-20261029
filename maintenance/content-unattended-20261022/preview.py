"""Run new local gates on isolated copies of the 14 old samples, no API calls."""
import sys,shutil,tempfile,json,time,sqlite3
from pathlib import Path
S=Path('/opt/monitor/geo-capture/maintenance/20261022-content-unattended/stage-v2')
sys.path[:0]=[str(S),str(S/'engine')]
from geo_source_cards.staged_editorial import check,research_for_writer
from geo_source_cards.paragraph_repair import prepare
B=Path('/opt/monitor/geo-content/runtime/runs');D=S.parent;results=[]
for identity in ('creation-1792575159-0a8f9221','creation-1792576129-389f575e'):
 root=B/identity
 for original in sorted((root/'days/2026-10-21/jobs').glob('*/*/writer')):
  entry={'job':identity,'article':original.parent.relative_to(root).as_posix(),'draft':(original/'draft.md').exists()}
  if entry['draft']:
   with tempfile.TemporaryDirectory(prefix='preview-',dir=D) as tmp:
    article=Path(tmp)/'article';shutil.copytree(original.parent,article)
    writer=article/'writer'
    try:
     entry['checks']=check(research_for_writer(writer),writer)
     files=prepare(writer,'; '.join(entry['checks']['failures']))
     entry['patch_prepared']=bool(files)
    except Exception as e:entry['error']=type(e).__name__+': '+str(e)[:800]
  results.append(entry)
db=sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True)
unknown=sorted(r[0] for r in db.execute('select id from costs where charged is null'))
controls={}
for p in B.glob('*/control.json'):
 import hashlib
 controls[p.parent.name]=hashlib.sha256(p.read_bytes()).hexdigest()
report={'at':time.time(),'articles':results,'unknown_ids':unknown,'control_sha256':controls}
(D/'preview.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({'articles':results,'unknown_count':len(unknown)},ensure_ascii=False))
