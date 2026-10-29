
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import sys,json,sqlite3
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from unattended_worker import databases
results=[]
for container,batch in [('doubao-hpe14-13-test','geo-products-21x5-20261013'),('doubao-hpe14-account2','geo-products-21x5-account2-20261013')]:
    p=Path('/home/user/redroid-doubao/batches')/batch/'tasks.sqlite'
    q=sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True)
    task=q.execute("select task_id from tasks where prepared_at is not null order by prepared_at desc limit 1").fetchone()[0]
    matches=[]
    for dbpath in databases(container):
        c=sqlite3.connect(dbpath.resolve().as_uri()+'?mode=ro',uri=True)
        for row in c.execute('select sender_id,local_message_id,status from im_message where user_type=1 and (instr(fts_content,?)>0 or instr(content,?)>0)',(task,task)):
            matches.append({'uid':str(row[0]),'database':dbpath.name,'message':str(row[1]),'state':row[2]})
    if len(matches)!=1:raise RuntimeError('Expected exactly one actual sent request per account')
    r=matches[0]
    results.append(r)
    print(json.dumps({'container':container,'sender_uid_masked':'***'+r['uid'][-6:],
                      'database_uid_masked':'***'+r['database'][-6:],'message_state':r['state']},ensure_ascii=False))
print(json.dumps({'same_sender_uid':results[0]['uid']==results[1]['uid'],
                  'same_account_database':results[0]['database']==results[1]['database']}))
