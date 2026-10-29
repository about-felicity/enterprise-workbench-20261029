import hashlib,json,shutil,sys,zipfile
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import studio,runtime,article_export
pid='plan-6334cde812bd49549df6efd87a51e3b3';day='2026-10-20';articles=[]
for file in (runtime.BASE/'runs').glob('*/job.json'):
 job=runtime.read(file)
 if job.get('studio_plan_id')!=pid:continue
 root=file.parent;state=runtime.read(root/'days'/day/'day.json')
 assert state.get('status')=='complete',state
 assert not runtime.read(root/'control.json').get('paused')
 for item in runtime.articles(root):
  folder=root/'approved'/item['id'];body=(folder/'draft.md').read_text()
  assert '焕颜计小白罐美白精华霜' in body and '科熙本' not in body
  metadata=article_export.info(root,folder);logs=article_export.logs(root,metadata)
  assert metadata['primary_reference']['url'].startswith('https://')
  assert metadata['primary_reference']['domain'] and metadata['primary_reference']['title']
  assert logs['tickets'] or logs['events']
  articles.append({'title':item['title'],'category':item['category'],'primary_reference':metadata['primary_reference'],'word_sha256':hashlib.sha256((folder/'article.docx').read_bytes()).hexdigest(),'body_chars':len(body)})
assert len(articles)>=2
bundle=runtime.download('all-approved','','bundle',{'plan':pid,'date':day,'source':'new'})
with zipfile.ZipFile(bundle) as z:
 manifest=json.loads(z.read('导出清单.json'));assert manifest['count']==len(articles)
 for item in manifest['articles']:
  names=[v for v in z.namelist() if v.startswith(item['directory']+'/')]
  assert any(v.endswith('.docx') for v in names)
  assert all(item['directory']+'/'+v in names for v in ('文章信息.md','文章信息.json','执行日志.json'))
output=Path('/tmp/whitening-e2e-20261020.zip');shutil.copy2(bundle,output);output.chmod(0o644)
report={'plan_id':pid,'articles':articles,'count':len(articles),'bundle':str(output),'bundle_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'original_observations_preserved':True,'scope':'creation_only'}
Path('/tmp/whitening-e2e-acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
