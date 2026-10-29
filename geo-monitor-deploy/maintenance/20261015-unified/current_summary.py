import json
import urllib.request
def get(url):
    with urllib.request.urlopen(url,timeout=20) as stream:return json.load(stream)
panel=get('http://127.0.0.1:8803/api/panel');creation=get('http://127.0.0.1:8804/api/status')
print(json.dumps({'capture':[{**{k:m['current'].get(k) for k in ('batch','state','service_state','captured','processed','unique_processed','duplicates','needs_review')},'model':m['id']} for m in panel['models']],
    'creation':[{'job_id':j['job_id'],'control':j['control'],'queue':j['queue'],'approved':len(j['articles']),'worker':j['worker']} for j in creation['jobs']]},ensure_ascii=False))
