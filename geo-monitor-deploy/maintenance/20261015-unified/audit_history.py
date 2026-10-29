import json,subprocess,hashlib
from pathlib import Path
out=Path('/opt/monitor/geo-capture/maintenance/20261015-unified');out.mkdir(parents=True,exist_ok=True,mode=0o700)
def sql(q):return subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',q],text=True,timeout=45).strip()
q="""select coalesce(json_agg(t),'[]') from (select r.run_id,r.sequence_no,r.day,r.question,r.serial,length(r.answer) body_length,left(r.answer,100) body_start,right(r.answer,100) body_end,r.status,r.payload->>'capture_mode' capture_mode,r.payload->>'round' batch_round,r.payload->>'batch_id' batch_id,(select count(*) from monitor_sources s where s.model_id=r.model_id and s.run_id=r.run_id) sources from monitor_runs r where r.model_id='doubao' and (r.sequence_no in (42810,42941) or (r.day between '2026-10-13' and '2026-10-15' and (r.question like '%眉%' or r.question like '%睫%'))) order by r.day,r.sequence_no desc limit 100) t"""
rows=json.loads(sql(q));(out/'doubao-history-summary.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
print(json.dumps(rows[:18],ensure_ascii=False))
print('GROUPS',sql("""select coalesce(json_agg(t),'[]') from (select day,serial,question,coalesce(payload->>'capture_mode','legacy') mode,count(*) n,min(length(answer)) min_body,max(length(answer)) max_body,round(avg(length(answer))) avg_body from monitor_runs where model_id='doubao' and day between '2026-10-13' and '2026-10-15' and (question like '%眉%' or question like '%睫%') group by day,serial,question,payload->>'capture_mode' order by day,serial,question) t"""))
print('MODULES',[p.name for p in Path('/opt/monitor/monitor_core').glob('*.py')])
print('IMPORTS','\n'.join(Path('/opt/monitor/doubao_dashboard_server.py').read_text().splitlines()[:60]))
