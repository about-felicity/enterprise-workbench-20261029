import json,sqlite3
from pathlib import Path
base=Path('/opt/monitor/geo-capture');pointer=json.loads((base/'soak12h_current.json').read_text());manifest=json.loads((Path(pointer['root'])/'manifest.json').read_text())
job=manifest['jobs']['baidu_ai'];root=base/'batches'/job['batch']
with sqlite3.connect((root/'collector/tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
    db.row_factory=sqlite3.Row
    rows=db.execute("select task_id,ordinal,round,state,error,result from captures where json_extract(result,'$.availability') in ('no_card','supplement_unavailable')").fetchall()
    result=[]
    for row in rows:
        record=json.loads(row['result'])
        result.append({'task':row['task_id'],'ordinal':row['ordinal'],'round':row['round'],'state':row['state'],
            'availability':record.get('availability'),'reason':record.get('unavailable_reason',record.get('availability_reason',record.get('error'))),
            'record_keys':list(record),'error':row['error']})
print(json.dumps(result,ensure_ascii=False))
