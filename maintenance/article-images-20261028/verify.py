import urllib.request,urllib.parse,json,io,zipfile,hashlib,http.cookiejar,sys
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
base='http://127.0.0.1:8804';jar=http.cookiejar.CookieJar();opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
opener.open(base+'/api/panel',timeout=60).read()
jid='creation-1792807286-eb504495';article='2026-10-24/排行类/01'
def fetch(kind):
 url=base+'/api/download?'+urllib.parse.urlencode({'job':jid,'article':article,'kind':kind})
 with opener.open(url,timeout=90) as r:
  raw=r.read();assert r.headers['X-Content-SHA256']==hashlib.sha256(raw).hexdigest();return raw
md=fetch('markdown').decode();assert '/api/geo-creation/product_image?id=image-' in md
word=fetch('word')
with zipfile.ZipFile(io.BytesIO(word)) as z:assert any(n.startswith('word/media/') for n in z.namelist())
package=fetch('package')
with zipfile.ZipFile(io.BytesIO(package)) as z:
 assert any(n.endswith('/product.png') for n in z.namelist())
 manifest=json.loads(z.read('导出清单.json'));item=manifest['articles'][0]
 for ext,name in [('.docx','article.docx'),('.md','draft.md')]:
  path=next(n for n in z.namelist() if n.startswith(item['directory']+'/') and n.endswith(ext) and n.count('/')==item['directory'].count('/')+1 and not n.endswith('文章信息.md'))
  raw=z.read(path);assert hashlib.sha256(raw).hexdigest()==item['file_hashes'][name]
  if ext=='.md':assert b'(product.png)' in raw
imageid=md.split('product_image?id=')[1].split(')')[0]
with opener.open(base+'/api/product_image?id='+imageid) as r:assert r.status==200 and r.headers['Content-Type'].startswith('image/')
result={'job':jid,'article':article,'word_bytes':len(word),'package_bytes':len(package),'embedded_image':True,'package_image':True,'hashes_verified':True,'image_endpoint':200}
Path('/opt/monitor/maintenance/article-images-20261028/verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
