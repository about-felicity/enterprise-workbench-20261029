import hashlib,io,json,sys,urllib.parse,urllib.request,zipfile
from pathlib import Path
B=Path(__file__).resolve().parent;state=json.loads((B/'state.json').read_text())
BASE='http://127.0.0.1:8804'
with urllib.request.urlopen(BASE+'/api/status',timeout=60) as r:data=json.load(r)
job=next(j for j in data['jobs'] if j['job_id']==state['job_id'])
assert len(job['articles'])==7 and all(a['quality_status']=='ready' for a in job['articles'])
downloaded=[]
for article in job['articles']:
 query=urllib.parse.urlencode({'job':job['job_id'],'article':article['id'],'kind':'word'})
 with urllib.request.urlopen(BASE+'/api/download?'+query,timeout=60) as r:
  raw=r.read();digest=hashlib.sha256(raw).hexdigest()
  assert r.status==200 and r.headers['X-Content-SHA256']==digest
  assert int(r.headers['X-Download-Bytes'])==len(raw) and digest==article['receipt']['word_sha256']
  with zipfile.ZipFile(io.BytesIO(raw)) as z:assert z.testzip() is None and 'word/document.xml' in z.namelist()
 downloaded.append({'title':article['title'],'sha256':digest,'bytes':len(raw)})
plan=next(p for p in data['studio']['plans'] if p['plan_id']=='plan-9b827648df6c4bf9b5648db2eaf6079e')
assert plan['questions']==state['questions'] and plan['enabled'] and plan['frequency']=='daily'
report={'status':'passed','http_word_downloads':downloaded,'article_count':len(downloaded),
 'recurring_plan':{k:plan[k] for k in ['plan_id','enabled','frequency','capture_time','writing_time','article_target','channels']},
 'ui_changed':False,'next_natural_day_test':'not yet observed'}
(B/'smoke-production.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
