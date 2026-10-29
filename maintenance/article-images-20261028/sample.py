import sys,importlib.util,json,shutil,hashlib
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
spec=importlib.util.spec_from_file_location('creation.article_images','/tmp/image28-article_images.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
from creation import runtime
for root in (runtime.BASE/'runs').glob('creation-*'):
 if '眉毛' not in runtime.read(root/'product.json').get('name',''):continue
 for a in runtime.articles(root):
  folder=root/'approved'/a['id'];before=hashlib.sha256((folder/'article.docx').read_bytes()).hexdigest()
  output=mod.project(root,folder)
  if not output['image']:continue
  assert hashlib.sha256((folder/'article.docx').read_bytes()).hexdigest()==before
  shutil.copy2(output['word'],'/tmp/image28-preview.docx');Path('/tmp/image28-preview.docx').chmod(0o644)
  print(json.dumps({'job':root.name,'article':a['id'],'projection':runtime.read(output['word'].parent/'complete.json')},ensure_ascii=False))
  raise SystemExit(0)
raise SystemExit('No matching eyebrow image found')
