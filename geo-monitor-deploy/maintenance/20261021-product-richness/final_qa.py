import json,sys,time,sqlite3,zipfile,hashlib,shutil,io,collections,xml.etree.ElementTree as ET
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from creation.article_export import info
r=runtime.job_root('creation-1792556219-bbc55e13');m=Path('/opt/monitor/geo-capture/maintenance/20261021-product-richness');articles=runtime.articles(r)
if len(articles)!=14:print(json.dumps({'not_complete':len(articles),'target':14}));raise SystemExit(0)
counts=collections.Counter(a['id'].split('/')[1] for a in articles);assert counts=={'排行类':7,'科普类':7},counts
metrics=[]
for a in articles:
 folder=r/'approved'/a['id'];q=runtime.read(folder/'product_detail_review.json');target=q['target']
 assert q['actual_hanzi']>=target['minimum_hanzi'] and len(q['used_fact_ids'])>=target['minimum_distinct_facts'] and len(q['used_report_ids'])>=target['minimum_report_facts']
 md=(folder/'draft.md').read_text();assert '姿生怡鱼子酱胶原塑颜面膜' in md
 with zipfile.ZipFile(folder/'article.docx') as z:
  assert z.testzip() is None;tree=ET.fromstring(z.read('word/document.xml'));text=''.join(t.text or '' for t in tree.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'))
  assert '姿生怡鱼子酱胶原塑颜面膜' in text
  for n in ['143.77%','171.43%','33.71%','6.28']:
   if n in md:assert n in text,(a['id'],n)
 meta=info(r,folder);assert meta['primary_reference']['url'] and meta['primary_reference']['domain'] and meta['primary_reference']['media']
 metrics.append({'article':a['id'],'title':a['title'],'product_hanzi':q['actual_hanzi'],'facts':len(q['used_fact_ids']),'reports':len(q['used_report_ids']),'source':meta['primary_reference']})
p=runtime.download(r.name,'','bundle',{'date':'2026-10-21'});dest=Path('/tmp/mask-final21.zip');shutil.copyfile(p,dest);dest.chmod(0o644)
with zipfile.ZipFile(dest) as z:
 assert z.testzip() is None;manifest=json.loads(z.read('导出清单.json'));assert manifest['count']==14
 infos=[n for n in z.namelist() if n.endswith('/文章信息.json')];logs=[n for n in z.namelist() if n.endswith('/执行日志.json')];assert len(infos)==len(logs)==14
 assert all(n.split('/')[0].endswith('_2026-10-21') and n.split('/')[1] in counts for n in infos)
 entries=len(z.namelist())
db=sqlite3.connect('file:'+str(runtime.SHARED/'api/costs.sqlite')+'?mode=ro',uri=True)
rows=db.execute('select c.category,c.article,sum(coalesce(c.charged,c.reserved)),sum(c.state="reserved") from costs c join studio_cost_scopes s on c.id=s.id where s.job=? group by c.category,c.article',(r.name,)).fetchall();db.close();assert max(v[2] for v in rows)<=.35+1e-9;assert sum(v[2] for v in rows)<=5.25;assert sum(v[3] for v in rows)==0
out={'at':time.time(),'count':14,'categories':dict(counts),'budget_actual_cny':sum(v[2] for v in rows),'maximum_article_cny':max(v[2] for v in rows),'costs':rows,'export_bytes':dest.stat().st_size,'export_entries':entries,'export_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'metrics':metrics,'xml_checked_docs':14,'zip_crc_valid':True}
(m/'final-qa.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in out.items() if k not in ['metrics','costs']},ensure_ascii=False))
