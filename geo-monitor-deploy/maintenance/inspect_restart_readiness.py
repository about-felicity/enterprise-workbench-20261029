"""Read-only restart gates and Baidu failure provenance; no credentials."""
from contextlib import closing
from datetime import datetime,timezone,timedelta
import importlib
import json
from pathlib import Path
import sqlite3
import subprocess

OUT=Path('/opt/monitor/geo-capture/maintenance/20261015-reorganize')
OUT.mkdir(parents=True,exist_ok=True,mode=0o700)

def command(*args):return subprocess.run(args,capture_output=True,text=True,check=True,timeout=25).stdout.strip()

root=Path('/opt/monitor/geo-capture/batches/geo-baidu_ai-21x5-20261015')
with closing(sqlite3.connect((root/'collector/tasks.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
    db.row_factory=sqlite3.Row
    bad=[dict(x) for x in db.execute("select task_id,model,state,error,result,finished from captures where state not in ('completed','pending')")]
    for row in bad:
        row['result_present']=bool(row.pop('result'))
        row['attempts']=[dict(x) for x in db.execute('select id,kind,error,epoch,previous_result from search_recovery_attempts where task_id=? order by id',(row['task_id'],))]
        for attempt in row['attempts']:attempt['partial_result_present']=bool(attempt.pop('previous_result'))
    states=dict(db.execute('select state,count(*) from captures group by state'))
    focus=db.execute('select state,finished,result from captures where task_id=?',('dc19f875ed63ae14607ebe1881ebc05e2c7fb25ca45d0cba5ed67f9ce86b3fc6',)).fetchone()
    finalization={'state':focus['state'],'finished':focus['finished'],
        'availability':json.loads(focus['result']).get('availability')} if focus and focus['result'] else None
process_source=command('/opt/monitor/geo-capture/venv/bin/python','-c',
    'import geo_source_cards.cli; print(geo_source_cards.cli.__file__)')
containers=json.loads(command('docker','inspect','monitor-product-worker','monitor-content-worker','monitor-postgres','monitor-redis'))
container_state=[{'name':x['Name'],'state':x['State']['Status'],'pid':x['State']['Pid'],
    'health':x['State'].get('Health',{}).get('Status'),'started_at':x['State']['StartedAt']} for x in containers]
value={'checked_at':datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
    'baidu_failed':bad,'baidu_states':states,'last_failed_task_finalization':finalization,'cli_module_used':process_source,
    'editorial_control':json.loads(Path('/home/user/geo-editorial/runtime-api/control.json').read_text()),
    'editorial_api_health':json.loads(Path('/home/user/geo-editorial/runtime-api/api/health.json').read_text()),
    'containers':container_state}
(OUT/'readiness.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(value,ensure_ascii=False,indent=2))
