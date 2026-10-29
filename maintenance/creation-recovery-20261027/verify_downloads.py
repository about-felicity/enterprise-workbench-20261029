import json,urllib.request,urllib.parse,zipfile,io,hashlib
from pathlib import Path
base='http://192.168.31.106:3000/api/geo-creation/'
folder=Path(__file__).resolve().parent
panel=json.load(urllib.request.urlopen(base+'panel',timeout=90))
(folder/'panel-current.json').write_text(json.dumps(panel,ensure_ascii=False),encoding='utf8')
results=[]
for date in ['2026-10-26','2026-10-27']:
 url=base+'download?'+urllib.parse.urlencode({'job':'all-approved','kind':'bundle','date':date})
 raw=urllib.request.urlopen(url,timeout=120).read()
 with zipfile.ZipFile(io.BytesIO(raw)) as archive:
  assert archive.testzip() is None
  docs=[n for n in archive.namelist() if n.endswith('.docx')]
  for n in docs:
   with zipfile.ZipFile(io.BytesIO(archive.read(n))) as doc:
    assert doc.testzip() is None and 'word/document.xml' in doc.namelist()
  results.append({'date':date,'downloaded_word_files':len(docs),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()})
print(json.dumps({'downloads':results,'active_jobs':len(panel['worker'].get('active_jobs',[])),'queued_jobs':panel['worker'].get('queued_jobs'),'tasks':[{k:t.get(k) for k in ['name','date','status','articles','questions','writing_complete','error']} for t in panel['studio']['daily_tasks']]},ensure_ascii=True))
(folder/'verification/downloads.json').write_text(json.dumps(results,indent=2))
