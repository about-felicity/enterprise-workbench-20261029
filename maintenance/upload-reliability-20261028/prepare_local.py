import tarfile,json,hashlib,re
from pathlib import Path
root=Path(__file__).resolve().parents[2];d=Path(__file__).parent
files=['runtime.py','product_images.py','knowledge_library.py','service.py','panel.html','library.js','uploads.js','test_upload_reliability.py','test_knowledge_library.py','test_product_images.py']
with tarfile.open(d/'candidate.tar.gz','w:gz') as tar:
 for name in files:
  p=root/'geo-monitor-deploy/creation'/name
  if name.endswith('.py'):compile(p.read_text('utf-8'),name,'exec')
  tar.add(p,arcname='creation/'+name)
 tar.add(root/'geo-monitor-deploy/dashboard-integration/app/api/geo-creation/[...path]/route.ts',arcname='route.ts')
 tar.add(root/'geo-monitor-deploy/dashboard-integration/tests/creation-gateway.test.mjs',arcname='creation-gateway.test.mjs')
text=(root/'geo-monitor-deploy/creation/panel.html').read_text('utf-8');scripts=re.findall(r'<script[^>]*>(.*?)</script>',text,re.S)
(d/'panel-check.js').write_text('\n'.join(scripts),encoding='utf-8')
print('Candidate compiled and packaged',files)
