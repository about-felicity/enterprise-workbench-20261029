import json,sqlite3,time,urllib.request
from pathlib import Path
root=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261028-090004-02abccba')
with sqlite3.connect((root/'tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 tasks=[dict(r) for r in db.execute('select ordinal,state,request_id,answer_id,capture_retries,error from tasks where ordinal<=2')]
 events=[dict(r) for r in db.execute('select event,detail,time from events order by time desc limit 8')]
with urllib.request.urlopen('http://127.0.0.1:8804/api/status',timeout=60) as response:data=json.load(response)
totals={day:sum(len(j.get('articles',[])) for j in data['jobs'] if j.get('date')==day) for day in ['2026-10-26','2026-10-27','2026-10-28']}
result={'checked_at':time.time(),'yuanbao':json.loads((root/'bridge_health.json').read_text()),'tasks':tasks,'events':events,'all_job_article_totals':totals}
Path('/opt/monitor/maintenance/yuanbao-update-20261028/verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False))
