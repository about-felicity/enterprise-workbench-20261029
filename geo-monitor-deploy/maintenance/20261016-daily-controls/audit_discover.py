import json,sqlite3,subprocess
from pathlib import Path
def query(sql):
 return json.loads(subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',"select coalesce(json_agg(t),'[]') from ("+sql+")t"],text=True))
print(json.dumps(query("select table_name,column_name,data_type from information_schema.columns where table_name in ('monitor_ingest_events','monitor_runs') order by table_name,ordinal_position")))
for root in [Path('/home/user/redroid-doubao/batches/geo-panel-doubao1-20261015-181820-3d82b024'),Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261016-100013-89d43fdd'),Path('/opt/monitor/geo-capture/batches/geo-panel-deepseek-20261016-094039-dc64b7e1/collector')]:
 with sqlite3.connect((root/'tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  db.row_factory=sqlite3.Row
  tables=[r[0] for r in db.execute("select name from sqlite_master where type='table'")]
  print(str(root),tables)
  for table in tables:
   rows=db.execute('select * from '+table+' limit 1').fetchall()
   for row in rows: print(table,{k: (str(v)[:180] if len(str(v))>180 else v) for k,v in dict(row).items()})
for r in query("select distinct on (source_device) source_device,record from monitor_ingest_events where received_at>='2026-10-16T00:00:00+08:00' order by source_device,received_at desc"):
 print(r['source_device'],{k:(str(v)[:170] if len(str(v))>170 else v) for k,v in r['record'].items() if k not in ('web_body','answerText','capture_result','source_entries','sources','items','citations','native_response')})
