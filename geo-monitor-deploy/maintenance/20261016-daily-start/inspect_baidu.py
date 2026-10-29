import json,sqlite3,time
from pathlib import Path
root=Path('/opt/monitor/geo-capture/batches/geo-panel-baidu-ai-20261015-181822-d44632b8')
with sqlite3.connect((root/'collector/tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
    db.row_factory=sqlite3.Row
    groups={};bad=[]
    for row in db.execute('select * from captures order by ordinal'):
        result=json.loads(row['result']) if row['result'] else {}
        group=groups.setdefault(row['question'],{'complete':0,'unavailable':0,'pending':0,'reasons':{}})
        kind='pending' if row['state']!='completed' else 'unavailable' if result.get('availability')=='supplement_unavailable' else 'complete'
        group[kind]+=1
        if kind=='unavailable':
            reason=str(result.get('reason') or result.get('unavailable_reason') or result.get('error') or '')
            group['reasons'][reason]=group['reasons'].get(reason,0)+1
            bad.append({'ordinal':row['ordinal'],'question':row['question'],'result':result})
    print(json.dumps({'at':time.time(),'questions':groups,'recent_unavailable':bad[-3:]},ensure_ascii=False))
print(json.dumps({'diagnostic_files':[str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and ('diagnostic' in str(p) or p.suffix=='.log')][-25:]}))
