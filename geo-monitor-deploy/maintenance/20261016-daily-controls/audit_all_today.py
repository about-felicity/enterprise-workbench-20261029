"""Read-only, independent whole-day audit. Never sends collector/control writes."""
from collections import Counter,defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
import hashlib,json,sqlite3,subprocess,time,urllib.request
from pathlib import Path

DAY='2026-10-16';ZONE=ZoneInfo('Asia/Shanghai');BASE=Path('/opt/monitor/geo-capture')
ROOT=BASE/'maintenance/20261016-all-data-audit';ROOT.mkdir(exist_ok=True)
DEV={'doubao-hpe14-13-test':'doubao1','doubao-hpe14-account2':'doubao2','geo-headless-deepseek':'deepseek','geo-headless-wenxin_card':'wenxin_card','geo-headless-baidu_ai':'baidu_ai','yuanbao-hpe14-android13':'yuanbao'}
def query(sql):
 return json.loads(subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',"select coalesce(json_agg(t),'[]') from ("+sql+")t"],text=True,timeout=90))
def date(v):
 if not v:return None
 try:
  d=datetime.fromtimestamp(v,ZONE) if isinstance(v,(int,float)) else datetime.fromisoformat(v.replace('Z','+00:00'))
  if not d.tzinfo:d=d.replace(tzinfo=ZONE)
  return d.astimezone(ZONE).date().isoformat()
 except (ValueError,TypeError):return None
def q(r):return r.get('prompt') or r.get('capture_result',{}).get('question') or r.get('question')
def body(r):return r.get('web_body',r.get('answerText',''))
def src(r):return r.get('sources',r.get('items',[]))
def connection(path):
 db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row;return db
def add_issue(kind,e,detail=''):
 issues.append({'kind':kind,'model':DEV.get(e['source_device'],e['source_device']),'request_id':e['request_id'],'question':q(e['record']),'detail':detail})

started=time.time()
with urllib.request.urlopen('http://127.0.0.1:3000/api/geo-capture/panel',timeout=30) as response:panel=json.load(response)
events=query("select e.*,r.day,r.status run_status,r.answer,r.payload,r.question run_question,r.finished_at run_finished from monitor_ingest_events e left join monitor_runs r on e.model_id=r.model_id and e.run_id=r.run_id where r.day='2026-10-16' or (e.received_at at time zone 'Asia/Shanghai')::date='2026-10-16'")
issues=[];today=[];index=defaultdict(list);summaries={};original=[];orphans=[];sqlite_errors=[]
for e in events:
 r=e['record'];captured=date(r.get('captured_at') or r.get('finished_at') or r.get('extractedAt'))
 if e['day']==DAY or captured==DAY:
  today.append(e)
  key=r.get('capture_task_id') or r.get('native_result',{}).get('task_id')
  if key:index[(r.get('batch_id'),key)].append(e)
  if captured and e['day'] and captured!=e['day']:add_issue('wrong_day',e,str((captured,e['day'])))
  if not e['run_id']:
   if r.get('availability')!='nontext_answer':add_issue('no_stored_run',e)
   continue
  if e['run_status']!='success':add_issue('run_not_success',e,e['run_status'])
  if not body(r).strip():add_issue('empty_body',e)
  if body(r).strip()!=str(e['answer'] or '').strip():add_issue('answer_changed',e)
  if r.get('body_capture_complete') is False:add_issue('incomplete_body_in_run',e)
  if r.get('source_capture_complete') is True and not src(r):add_issue('false_full_sources',e)
  expected=r.get('expected_source_count',r.get('expectedCount'))
  if expected is not None and expected!=len(src(r)):add_issue('source_count_mismatch',e,str((expected,len(src(r)))))
  for s in src(r):
   url=s.get('url',s.get('href',''))
   if not url.startswith(('http://','https://')) or not s.get('title','').strip():add_issue('source_metadata_invalid',e,str(s)[:120])
  raw=r.get('capture_result',r.get('native_result',{}))
  rawbody=raw.get('body',raw.get('body_markdown'))
  if rawbody is not None and rawbody!=body(r):add_issue('embedded_raw_body_changed',e)

# Inspect each original SQLite journal; include old batches crossing midnight.
for parent,web in [(BASE/'batches',True),(Path('/home/user/redroid-doubao/batches'),False),(Path('/home/user/redroid-yuanbao/batches'),False)]:
 for lane in parent.glob('*'):
  dbpath=lane/('collector/tasks.sqlite' if web else 'tasks.sqlite')
  if not dbpath.is_file():continue
  try:
   with connection(dbpath) as db:
    integrity=db.execute('pragma quick_check').fetchone()[0]
    if integrity!='ok':sqlite_errors.append({'batch':lane.name,'error':integrity})
    table='captures' if web else 'tasks'
    rows=[dict(r) for r in db.execute('select * from '+table)]
    complete_times={} if web else dict(db.execute("select task_id,max(time) from events where event='completed' group by task_id"))
    for t in rows:
     raw=json.loads(t.get('result' if web else 'result_json') or '{}')
     stamp=raw.get('captured_at') if web else complete_times.get(t['task_id'])
     if date(stamp)!=DAY:continue
     model=t.get('model') if web else ('yuanbao' if 'yuanbao' in str(parent) else ('doubao2' if 'doubao2' in lane.name or 'account2' in lane.name else 'doubao1'))
     item={'model':model,'batch':lane.name,'task_id':t['task_id'],'question':t['question'],'state':t['state'],'availability':raw.get('availability'),'body_complete':raw.get('body_capture_complete'),'source_complete':raw.get('source_capture_complete'),'time':stamp,'prepared_at':t.get('started' if web else 'prepared_at')}
     if t['state']!='completed':continue
     original.append(item)
     matched=index.get((lane.name,t['task_id']),[])
     expected_body=raw.get('body',raw.get('body_markdown',''))
     if not matched:
      orphans.append({**item,'body_length':len(expected_body),'reason':raw.get('availability')})
     else:
      for e in matched:
       if body(e['record'])!=expected_body:add_issue('sqlite_body_mismatch',e)
       if src(e['record'])!=raw.get('sources',[]):
        norm=lambda sources:[(s.get('title','').strip(),s.get('url',s.get('href','')).strip()) for s in sources]
        if norm(src(e['record']))!=norm(raw.get('sources',[])):add_issue('sqlite_sources_mismatch',e)
       if q(e['record'])!=t['question']:add_issue('sqlite_question_mismatch',e)
  except Exception as error:sqlite_errors.append({'batch':lane.name,'error':str(error)})

for m in panel['models']:
 mid=m['id'];ev=[e for e in today if DEV.get(e['source_device'])==mid and e['run_status']=='success'];cfg=m['daily']['config'];counts=Counter(q(e['record']) for e in ev)
 duplicate=Counter((q(e['record']),hashlib.sha256(body(e['record']).encode()).hexdigest()) for e in ev)
 pending=Counter((e['payload'] or {}).get('product_review_status','unspecified') for e in ev)
 native=defaultdict(list)
 for e in ev:
  r=e['record'];key=r.get('native_request_id') or (r.get('url') if mid=='deepseek' else None)
  if key:native[key].append(e['request_id'])
 repeat_native=[v for v in native.values() if len(v)>1]
 summaries[mid]={'success_rows':len(ev),'configured_questions':len(cfg['questions']),'rounds':cfg['rounds'],'interval':cfg['interval'],'coverage':[{'question':question,'actual':counts[question],'target':cfg['rounds'],'missing':max(0,cfg['rounds']-counts[question])} for question in cfg['questions']],
 'unexpected_questions':dict((question,n) for question,n in counts.items() if question not in cfg['questions']),
 'body_only':sum(e['record'].get('source_capture_complete') is False for e in ev),'repeated_body_observations':sum(n-1 for n in duplicate.values()),'distinct_question_bodies':len(duplicate),'product_review':dict(pending),'duplicate_native_identities':repeat_native,
 'panel_count':m['daily']['completed'],'panel_count_matches':m['daily']['completed']==len(ev),'runtime':{k:m['current'].get(k) for k in ('state','service_state','batch','pending_delivery','needs_review')}}

# Verify DeepSeek spacing from durable original queue start times.
ds=sorted([x for x in original if x['model']=='deepseek' and x['prepared_at']],key=lambda x:x['prepared_at'])
gaps=[{'before':a['task_id'],'after':b['task_id'],'seconds':round(b['prepared_at']-a['prepared_at'],3)} for a,b in zip(ds,ds[1:])]
unmatched_ingest=[{'request_id':e['request_id'],'model':DEV.get(e['source_device'],e['source_device'])} for e in today if e['source_device'] not in DEV]
product_evidence=[];pending_review=[];source_gaps=[]
for e in today:
 p=e['payload'] or {};r=e['record']
 if p.get('product_review_status')=='ai_pending':pending_review.append({'model':DEV.get(e['source_device']),'run_id':e['run_id'],'question':q(r),'received_at':e['received_at'],'retry':p.get('product_ai_retry_count'),'error':p.get('product_analysis_error')})
 for product in p.get('products',[]):
  evidence=product.get('evidence','')
  norm=lambda s:''.join(str(s).split()).lower()
  if evidence and norm(evidence) not in norm(body(r)):
   product_evidence.append({'model':DEV.get(e['source_device']),'run_id':e['run_id'],'question':q(r),'product':product})
 if r.get('source_capture_complete') is False:source_gaps.append({'model':DEV.get(e['source_device']),'question':q(r),'run_id':e['run_id'],'availability':r.get('availability')})
unlinked_runs=query("select r.model_id,r.serial,r.status,count(*) n from monitor_runs r left join monitor_ingest_events e on e.model_id=r.model_id and e.run_id=r.run_id where r.day='2026-10-16' and e.request_id is null group by 1,2,3")
review_queue=query("select model_id,coalesce(payload->>'product_review_status','unspecified') review,count(*) n,min(finished_at) earliest,max(product_ai_retry_count) max_retry from monitor_runs where day='2026-10-16' group by 1,2")
report={'day':DAY,'started':started,'finished':time.time(),'event_rows_scanned':len(events),'today_rows':len(today),'models':summaries,'issues':issues,'issue_counts':dict(Counter(x['kind'] for x in issues)),'sqlite_errors':sqlite_errors,'original_completed_today':dict(Counter(x['model'] for x in original)),'original_not_ingested':orphans,'other_devices':unmatched_ingest,'deepseek_gaps':gaps,'deepseek_under_600': [x for x in gaps if x['seconds']<599.5],'product_evidence_not_exact':product_evidence,'pending_product_review':pending_review,'source_incomplete_records':source_gaps,'runs_without_ingest_event':unlinked_runs,'review_queue':review_queue}
(ROOT/'audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
(ROOT/'original-index.json').write_text(json.dumps(original,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in report.items() if k not in ('deepseek_gaps','original_not_ingested','issues','models')},ensure_ascii=False))
print('models',json.dumps({k:{a:b for a,b in v.items() if a!='coverage'} for k,v in summaries.items()},ensure_ascii=False))
print('orphans',len(orphans),'issues',len(issues))
