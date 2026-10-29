import hashlib,json,shutil,sqlite3,sys,time,zipfile
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import studio,runtime,article_export
task=runtime.read(Path('/opt/monitor/geo-capture/maintenance/20261020-eye-daily/task.json'))
pid=task['plan_id'];day=task['start_date'];articles=[];primary_groups=set();jobs=[]
for file in (runtime.BASE/'runs').glob('*/job.json'):
 job=runtime.read(file)
 if job.get('studio_plan_id')!=pid or job.get('date')!=day:continue
 root=file.parent;state=runtime.read(root/'days'/day/'day.json');allocation=runtime.read(root/'days'/day/'article_allocation.json')
 assert state.get('status')=='complete',state
 assert not runtime.read(root/'control.json').get('paused')
 assert allocation['target']==task['article_target'] and not allocation['shortfall']
 groups=runtime.read(root/'days'/day/'source_dedup.json')['representatives']
 jobs.append(job['job_id'])
 for item in runtime.articles(root):
  folder=root/'approved'/item['id'];body=(folder/'draft.md').read_text()
  product=runtime.read(root/'days'/day/'product.json')
  assert product['name'] in body,(item['id'],'Product identity missing')
  metadata=article_export.info(root,folder);logs=article_export.logs(root,metadata);primary=metadata['primary_reference']
  assert primary['url'].startswith(('http://','https://')) and primary['domain'] and primary['title']
  assert logs['tickets'] or logs['events']
  group=groups.get(primary['url'],primary['url']);assert group not in primary_groups,('Duplicate primary',primary['url']);primary_groups.add(group)
  articles.append({'title':item['title'],'category':item['category'],'primary_reference':primary,'word_sha256':hashlib.sha256((folder/'article.docx').read_bytes()).hexdigest(),'body_chars':len(body)})
assert len(jobs)==1 and len(articles)==task['article_target'],(jobs,len(articles))
assert {a['category'] for a in articles}=={'排行类','科普类'}
bundle=runtime.download('all-approved','','bundle',{'plan':pid,'date':day,'source':'new'})
with zipfile.ZipFile(bundle) as z:
 manifest=json.loads(z.read('导出清单.json'));assert manifest['count']==len(articles)
 for item in manifest['articles']:
  names=[v for v in z.namelist() if v.startswith(item['directory']+'/')]
  assert any(v.endswith('.docx') for v in names)
  assert all(item['directory']+'/'+v in names for v in ('文章信息.md','文章信息.json','执行日志.json'))
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 cost=db.execute('select count(*),coalesce(sum(c.charged),0),sum(case when c.charged is null then 1 else 0 end) from costs c join studio_cost_scopes s on s.id=c.id where s.scope=?',(pid,)).fetchone()
 per_article=db.execute('select c.category,c.article,sum(c.charged) from costs c join studio_cost_scopes s on s.id=c.id where s.scope=? group by c.category,c.article',(pid,)).fetchall()
assert not cost[2]
assert max(c[2] for c in per_article)<=.35+1e-9 and cost[1]<=5.25
output=Path('/tmp/eye-e2e-'+day.replace('-','')+'.zip');shutil.copy2(bundle,output);output.chmod(0o644)
report={'at':time.time(),'plan_id':pid,'jobs':jobs,'articles':articles,'count':len(articles),'cost_calls':cost[0],'cost_cny':cost[1],'cost_by_article':per_article,'max_article_cost_cny':max(c[2] for c in per_article),'unsettled_calls':cost[2],'bundle':str(output),'bundle_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'scope':'creation_only'}
Path('/tmp/eye-e2e-acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
