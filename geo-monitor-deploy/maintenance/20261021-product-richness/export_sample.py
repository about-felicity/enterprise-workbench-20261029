import json,sys,shutil,hashlib,zipfile
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
root=runtime.job_root('creation-1792556219-bbc55e13');items=runtime.articles(root)
for a in items:
 d=runtime.read(root/'approved'/a['id']/'product_detail_review.json');print(json.dumps({'id':a['id'],'title':a['title'],'product_hanzi':d.get('actual_hanzi'),'facts':len(d.get('used_fact_ids',[])),'reports':len(d.get('used_report_ids',[]))},ensure_ascii=False))
if items:
 a=items[0];p=runtime.download(root.name,a['id'],'package');dst=Path('/tmp/mask-sample21.zip');shutil.copyfile(p,dst);dst.chmod(0o644)
 with zipfile.ZipFile(dst) as z:assert z.testzip() is None;count=len(z.namelist())
 print(json.dumps({'export':str(dst),'bytes':dst.stat().st_size,'entries':count,'sha256':hashlib.sha256(dst.read_bytes()).hexdigest()}))
