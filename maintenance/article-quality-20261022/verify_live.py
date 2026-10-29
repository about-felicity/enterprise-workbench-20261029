import sys,json,time,sqlite3,subprocess,hashlib,urllib.request
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261022-article-quality');B=Path('/opt/monitor/geo-content')
read=lambda p:json.loads(p.read_text()) if p.is_file() else {}
services={n:subprocess.check_output(['systemctl','is-active',n],text=True).strip() for n in ('geo-content-api','geo-content-worker','geo-creation-studio')}
with urllib.request.urlopen('http://127.0.0.1:8804/api/status',timeout=25) as response:status=json.loads(response.read());http_status=response.status
with urllib.request.urlopen('http://127.0.0.1:8804/',timeout=15) as response:html=response.read();html_status=response.status
assert hashlib.sha256(html).hexdigest()==hashlib.sha256((B/'creation/panel.html').read_bytes()).hexdigest()
assert status['ok'] and all(v=='active' for v in services.values())
assert time.time()-read(B/'runtime/worker_health.json').get('at',0)<60
baseline=read(D/'before.json');costs=[]
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 costs=db.execute("select c.date,sum(c.charged),sum(case when c.charged is null then c.reserved else 0 end) from costs c join studio_cost_scopes s on c.id=s.id where s.scope=? group by c.date",('plan-33e7bfca8bb6497da10b28f0444a693b',)).fetchall()
 unknown=sorted(r[0] for r in db.execute('select id from costs where charged is null'))
assert unknown==baseline['unknown_ids']
assert [list(r) for r in costs]==baseline['costs']
deploy=read(D/'deployment.json');assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in deploy['source_files'].items())
controls={j['id']:read(B/'runtime/runs'/j['id']/'control.json')==j['control'] for j in baseline['jobs']}
drain=read(D/'deployment-drain.json');drain_restored=all(read(B/'runtime/runs'/r['job']/'control.json')==r['before'] for r in drain.get('paused',[]));assert drain_restored
actual=[]
for j in status['jobs']:
 actual.append({'id':j['job_id'],'health':j['health']['status'],'active':j['health'].get('active_execution'),'paused':j['control']['paused'],'queue':j['queue'],'approved_articles':len(j['articles'])})
result={'at':time.time(),'services':services,'api_http_status':http_status,'frontend_http_status':html_status,'frontend_matches_deployed_source':True,'browser_acceptance':False,
 'source_sha_verified':len(deploy['source_files']),'deployment_drain_controls_restored':drain_restored,'worker_heartbeat_recent':True,'costs':costs,'new_cost_cny':0,'unknown_ids_unchanged':True,'unknown_count':len(unknown),'original_controls_match_initial_snapshot':controls,'jobs':actual}
(D/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in {'jobs','original_controls_match_initial_snapshot'}},ensure_ascii=False))
