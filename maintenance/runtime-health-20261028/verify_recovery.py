import sys,json,hashlib,time,urllib.request,urllib.parse,zipfile,io
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
D=Path('/opt/monitor/maintenance/creation-formats-20261028');results=[]
for backup in D.iterdir():
 if not backup.is_dir() or not backup.name.startswith('creation-'):continue
 jid=backup.name.removesuffix('-materials');root=runtime.BASE/'runs'/jid;j=runtime.read(root/'job.json')
 articles=runtime.articles(root);original=runtime.read(backup/'ticket.json');target=original.get('meta',{})
 selected=[a for a in articles if not target or a['id']==target['date']+'/'+target['category']+'/'+str(target['number']).zfill(2)]
 downloads=[]
 for a in selected:
  url='http://127.0.0.1:8804/api/download?'+urllib.parse.urlencode({'job':jid,'article':a['id'],'kind':'word'})
  with urllib.request.urlopen(url,timeout=30) as response:raw=response.read();status=response.status
  with zipfile.ZipFile(io.BytesIO(raw)) as z:assert 'word/document.xml' in z.namelist()
  downloads.append({'id':a['id'],'http':status,'bytes':len(raw)})
 result={'job':jid,'day':runtime.read(root/'days'/j['date']/'day.json'),'articles':len(articles),'verified_downloads':downloads}
 if target:result['original_ticket_state']=runtime.read(root/'queue'/original['id']/'ticket.json').get('state')
 results.append(result)
print(json.dumps(results,ensure_ascii=False))
(D/'creation-verification.json').write_text(json.dumps({'at':time.time(),'jobs':results},ensure_ascii=False,indent=2))
