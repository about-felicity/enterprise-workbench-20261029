import hashlib,json,re,sys,zipfile
from pathlib import Path
archive=Path(sys.argv[1]);root=archive.parent;rows=[]
with zipfile.ZipFile(archive) as z:
 manifest=json.loads(z.read('导出清单.json'))
 for item in manifest['articles']:
  prefix=item['directory']+'/'
  word=next(n for n in z.namelist() if n.startswith(prefix) and n.endswith('.docx'))
  data=z.read(word);sha=hashlib.sha256(data).hexdigest();kind='ranking' if item['category']=='排行类' else 'science'
  number=re.match(r'\d+',item['directory'].rsplit('/',1)[-1]).group()
  key=kind+'-'+number+'-'+sha[:8];path=root/(key+'.docx')
  if path.exists():assert hashlib.sha256(path.read_bytes()).hexdigest()==sha
  else:path.write_bytes(data)
  metadata=json.loads(z.read(prefix+'文章信息.json'));md=next(n for n in z.namelist() if n.startswith(prefix) and n.endswith('.md') and not n.endswith('文章信息.md'))
  (root/(key+'.md')).write_bytes(z.read(md))
  rows.append({'key':key,'file':str(path.resolve()),'title':item['title'],'category':item['category'],'sha256':sha,'primary_reference':metadata['primary_reference']})
(root/'manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps({'articles':len(rows),'keys':[r['key'] for r in rows]}))
