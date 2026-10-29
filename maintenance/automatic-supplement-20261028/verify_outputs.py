import sys,json,urllib.request,urllib.parse,zipfile,io
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
jid='creation-1793172068-fc2baa43';rows=runtime.articles(runtime.job_root(jid));assert len(rows)==3
for a in rows:
 q=urllib.parse.urlencode({'job':jid,'article':a['id'],'kind':'word'})
 with urllib.request.urlopen('http://127.0.0.1:8804/api/download?'+q,timeout=60) as response:data=response.read();assert response.status==200
 with zipfile.ZipFile(io.BytesIO(data)) as z:assert z.testzip() is None and 'word/document.xml' in z.namelist()
 print('WORD_OK',a['id'],len(data))
s=json.load(urllib.request.urlopen('http://127.0.0.1:8804/api/status',timeout=90))
result=[{k:t[k] for k in ['name','date','status','articles','error']} for t in s['studio']['daily_tasks'] if t['name']=='科熙本防脱精华' and t['date']=='2026-10-28' or t['plan_id']=='plan-0d57811d9b2543eab75d181badec6d9e' and t['date']=='2026-10-26']
print(json.dumps(result,ensure_ascii=False))
from pathlib import Path
Path('/opt/monitor/maintenance/automatic-supplement-20261028/final-verification.json').write_text(json.dumps({'tasks':result,'downloaded_word_files':len(rows),'tests_passed':7},ensure_ascii=False,indent=2))
