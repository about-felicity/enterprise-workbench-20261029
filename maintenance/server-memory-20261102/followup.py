import subprocess,json,sqlite3
from pathlib import Path
for name in ['monitor-dashboard-api','monitor-content-worker','monitor-product-worker']:
 r=json.loads(subprocess.check_output(['docker','inspect',name],text=True))[0]
 env={v.split('=',1)[0]:v.split('=',1)[1] for v in r['Config'].get('Env',[]) if '=' in v}
 print('TUNING',name,{k:v for k,v in env.items() if k.startswith(('MONITOR_ANALYTICS','MONITOR_RETAIN','MONITOR_SOURCE_INTERSECTION','MONITOR_CONTENT_','DOUBAO_PRODUCT_AI_BATCH')) and not any(x in k for x in ['KEY','TOKEN','SECRET'])})
 print('MOUNTS',name,[{'source':m['Source'],'dest':m['Destination']} for m in r.get('Mounts',[])])
for p in Path('/opt/monitor/geo-capture').glob('memory/*/samples.sqlite'):
 try:
  with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as db:
   print('SAMPLES',str(p),db.execute('select count(*),min(at),max(at) from samples').fetchone())
   rows=[json.loads(x[0]) for x in db.execute('select metrics from samples where at>strftime("%s","now")-172800')]
   for key in ['container_working_bytes','app_pss_kib','java_fraction']:
    vals=sorted(float(x[key]) for x in rows if key in x)
    if vals:print('DISTRIBUTION',p.parent.name,key,{'n':len(vals),'p50':vals[len(vals)//2],'p95':vals[int(len(vals)*.95)],'max':vals[-1]})
 except Exception as e:print('SAMPLE_ERROR',type(e).__name__)
print('PG_CONFIG',subprocess.run(['docker','exec','monitor-postgres','psql','-U','monitor','-d','monitor','-At','-c',"select name,setting,unit from pg_settings where name in ('shared_buffers','work_mem','maintenance_work_mem','max_connections','max_parallel_workers_per_gather');"],capture_output=True,text=True).stdout)
