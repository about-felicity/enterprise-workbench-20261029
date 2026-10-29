import json,sys,time,zipfile
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import studio,runtime
R=Path('/opt/monitor/geo-capture/maintenance/20261021-product-richness');t=runtime.read(R/'task.json');day=runtime.read(studio.day_path(t['plan_id'],t['date']));rows=[]
for jid in day.get('jobs',{}).values():
 root=runtime.job_root(jid)
 for a in runtime.articles(root):
  folder=root/'approved'/a['id'];m=runtime.read(folder/'product_detail_review.json')
  rows.append({'job':jid,'article':a['id'],'title':a['title'],'detail':m,'draft':str(folder/'draft.md'),'word_bytes':(folder/'article.docx').stat().st_size if (folder/'article.docx').exists() else None,'semantic':runtime.read(folder/'semantic_review.json')})
out={'at':time.time(),'articles':rows,'count':len(rows)}
(R/'output-audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
