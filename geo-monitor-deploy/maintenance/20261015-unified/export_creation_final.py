"""Export a completed creation soak's existing evidence, never run a job."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import hashlib,json,sys,time,subprocess
sys.path[:0]=['/opt/monitor/geo-capture','/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from creation.soak import audit
base=Path('/opt/monitor/geo-capture');p=runtime.read(base/'creation_soak_current.json');root=Path(p['root'])
m=runtime.read(root/'manifest.json');r=runtime.read(root/'report.json')
assert p['test_id']==m['test_id']==r['test_id']=='creation-soak6h-rosterfix-1792062355'
assert r['status']=='complete' and r['finished_at']>=m['deadline'] and time.time()>=m['deadline']
assert len(m['jobs'])==1 and m['jobs'][0]=='creation-1792060761-3c2baae0'
jobroot=runtime.job_root(m['jobs'][0]);current=audit(jobroot)
cost=runtime.read(base/'maintenance/20261015-unified/creation-cost-audit.json');assert cost['test_id']==p['test_id']
marker=runtime.read(root/'deadline_pause.json')
metrics=[json.loads(line) for line in (root/'metrics.jsonl').read_text().splitlines() if line.strip()]
idle=[s['at'] for s in metrics for j in s['jobs'] if j['job_id']==m['jobs'][0] and len(j['approved'])==10 and j['worker'].get('result',{}).get('status')=='idle']
gaps=[b['at']-a['at'] for a,b in zip(metrics,metrics[1:])]
active=runtime.read(jobroot/'api/active.json')
new=[a for a in current['approved'] if a['id'] not in set(m['approved_before'][m['jobs'][0]])]
units={name:subprocess.run(['systemctl','is-active',name],text=True,capture_output=True).stdout.strip() for name in ['geo-content-api.service','geo-content-worker.service',p['service'],p['deadline_timer']]}
assert current['control']['paused'] and current['control'].get('reason')=='soak_deadline'
assert marker['jobs']==m['jobs'] and len(current['approved'])==10 and len(new)==1 and not current['unknown_calls']
assert active.get('state') not in ('REQUESTING','AUTHORIZING','RESPONDED','REQUEST_UNKNOWN')
def local(t):return datetime.fromtimestamp(t,timezone(timedelta(hours=8))).isoformat(timespec='milliseconds')
report={'exported_at':time.time(),'test_id':p['test_id'],'verdict':r['verdict'],'scope':r['scope'],
 'started_at':m['started_at'],'deadline':m['deadline'],'finished_at':r['finished_at'],
 'started_beijing':local(m['started_at']),'deadline_beijing':local(m['deadline']),'finished_beijing':local(r['finished_at']),
 'planned_seconds':m['duration_seconds'],'actual_elapsed_seconds':r['finished_at']-m['started_at'],'deadline_to_final_report_seconds':r['finished_at']-m['deadline'],
 'anomalies':r['anomalies'],'job_id':m['jobs'][0],'baseline_approved':len(m['approved_before'][m['jobs'][0]]),
 'approved_total':len(current['approved']),'approved_new_in_window':len(new),'approved':current['approved'],'new_article_ids':[a['id'] for a in new],
 'material_counts':current['material_counts'],'material_hashes_verified':current['material_hashes_verified'],'Word_Markdown_receipts_review_verified':True,
 'platform_extra_questions':current['platform_questions_sent'],'unknown_api_calls':current['unknown_calls'],'api_calls':current['api_calls'],
 'metrics':{'samples':len(metrics),'first_at':metrics[0]['at'],'last_at':metrics[-1]['at'],'max_sample_gap_seconds':max(gaps) if gaps else None,
     'first_idle_with_all_ten_sample_at':min(idle) if idle else None,'first_idle_beijing':local(min(idle)) if idle else None,
     'idle_observed_seconds_to_deadline':max(0,m['deadline']-min(idle)) if idle else None,'idle_scope':'Sampled idle after all ten approved; not a claim of continuous paid generation or exact API compute duration'},
 'costs':cost['jobs'],'cost_scope':cost['scope'],'actual_control':current['control'],'actual_api_active_state':active.get('state'),
 'actual_worker_result':current['worker'].get('result'),'units':units,'independent_deadline_marker':marker,
 'original_report_sha256':hashlib.sha256((root/'report.json').read_bytes()).hexdigest(),
 'budget':{'article_cny':0.35,'shared_daily_cny':10,'ledger':'Existing shared original ledger, never reset or raised'},
 'limits':['Nine articles predate this window; only one was newly approved.', 'Separate two-article acceptance job is excluded.', 'Costs are existing conservative ledger estimates, not provider bills.', 'Capture twelve-hour test remains independent and incomplete; its blockers do not disappear when creation passes.']}
out=Path('/tmp/geo-creation-final-export');out.mkdir(exist_ok=True,mode=0o755)
target=out/'CREATION_6H_FINAL_20261015.json';target.write_text(json.dumps(report,ensure_ascii=False,indent=2));target.chmod(0o644)
print(json.dumps(report,ensure_ascii=False))
