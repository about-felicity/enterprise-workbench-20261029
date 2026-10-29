"""Read-only operational audit; only counts, comparisons and public build facts leave the host."""
import collections,hashlib,hmac,json,os,secrets,sqlite3,statistics,subprocess,time
from datetime import datetime,timezone,timedelta
from pathlib import Path
ROOT=Path('/opt/monitor/geo-capture/maintenance/20261017-ban-audit');ROOT.mkdir(parents=True,exist_ok=True)
salt=secrets.token_bytes(32)
def tag(value):return hmac.new(salt,str(value).encode(),hashlib.sha256).hexdigest()
def stamp(value):return datetime.fromtimestamp(float(value),timezone(timedelta(hours=8))).isoformat() if value else None
def run(*args,timeout=20):return subprocess.check_output(args,stderr=subprocess.DEVNULL,timeout=timeout,text=True).strip()
def connect(path):
 db=sqlite3.connect(Path(path).as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row;db.execute('pragma query_only=on');return db
result={'at':stamp(time.time()),'containers':{},'queues':[],'private_sources_scanned':0,'account_overlap':{},'manual_flows':{}}
names=['deepseek-hpe14-android13','deepseek-hpe14-account2','deepseek-manual-test','doubao-hpe14-13-test','doubao-hpe14-account2','yuanbao-hpe14-android13']
identities={};accounts={};images={}
for name in names:
 v=json.loads(run('docker','inspect',name))[0]
 props={key:run('docker','exec',name,'getprop',key) for key in ['ro.product.model','ro.build.type','ro.build.tags','ro.debuggable','ro.secure','ro.product.cpu.abi','ro.dalvik.vm.native.bridge','ro.build.version.release']}
 identities[name]=tag(run('docker','exec',name,'settings','get','secure','android_id'))
 images[name]=v['Image']
 result['containers'][name]={'image_id':v['Image'],'privileged':v['HostConfig']['Privileged'],'persistent_data':any(m['Destination']=='/data' and m['Type']=='volume' for m in v['Mounts']),'started_at':v['State']['StartedAt'],'restart_count':v['RestartCount'],'oom_killed':v['State']['OOMKilled'],'properties':props}
 if name.startswith('deepseek'):
  path=Path('/var/lib/docker/volumes/'+name+'-data/_data/data/com.deepseek.chat/databases/deepseek_chat.db')
  if path.exists():
   with connect(path) as db:
    rows=db.execute('select id,length(token)>0 as has_token from app_user_info').fetchall()
    accounts[name]={tag(row['id']) for row in rows if row['id']}
    result['containers'][name]['account_rows']=len(rows)
    result['containers'][name]['rows_with_token']=sum(bool(row['has_token']) for row in rows)
result['android_id_distinct_count']=len(set(identities.values()))
result['image_distinct_count']=len(set(images.values()))
for a in accounts:
 for b in accounts:
  if a<b:result['account_overlap'][a+' / '+b]=bool(accounts[a]&accounts[b])
roots=[Path('/home/user/redroid-deepseek/batches'),Path('/home/user/redroid-deepseek-account2/batches')]
all_events=collections.defaultdict(list)
for root in roots:
 for path in sorted(root.glob('*/tasks.sqlite')):
  if '20261017' not in path.parent.name:continue
  with connect(path) as db:
   tables={r['name'] for r in db.execute("select name from sqlite_master where type='table'")}
   columns={r['name'] for r in db.execute('pragma table_info(events)')}
   assert {'time','event','task_id'}<=columns
   rows=db.execute("select time,event,task_id from events order by time").fetchall()
   clicks=[r for r in rows if r['event']=='send_click_intent_committed']
   sends=[r['time'] for r in clicks];gaps=[b-a for a,b in zip(sends,sends[1:])]
   counts=collections.Counter(r['task_id'] for r in clicks)
   states=dict(db.execute('select state,count(*) from tasks group by state'))
   model='deepseek2' if 'account2' in str(root) else 'deepseek'
   all_events[model].extend(sends)
   record={'model':model,'batch':path.parent.name,'states':states,'send_click_intents':len(sends),'unique_clicked_tasks':len(counts),'tasks_with_multiple_intents':sum(v>1 for v in counts.values()),'first_send':stamp(sends[0]) if sends else None,'last_send':stamp(sends[-1]) if sends else None,'min_gap_seconds':round(min(gaps),2) if gaps else None,'max_gap_seconds':round(max(gaps),2) if gaps else None,'median_gap_seconds':round(statistics.median(gaps),2) if gaps else None,'gaps_below_600':sum(g<600 for g in gaps),'gaps_below_660':sum(g<660 for g in gaps),'uncertain_events':sum(r['event']=='send_uncertain' for r in rows),'retry_events':dict(collections.Counter(r['event'] for r in rows if 'retry' in r['event'] or 'recovery' in r['event']))}
   manifest=path.parent/'capture_manifest.json'
   if manifest.exists():
    cfg=json.loads(manifest.read_text());record['config']={k:cfg.get(k) for k in ['rounds','interval','prompt_mode']};record['question_count']=len(cfg.get('questions',[]))
   result['queues'].append(record)
combined=sorted((v,k) for k,values in all_events.items() for v in values)
result['combined_two_account_gaps']={'send_intents':len(combined),'min_seconds':round(min(b[0]-a[0] for a,b in zip(combined,combined[1:])),2) if len(combined)>1 else None,'different_account_pairs_under_600':sum(a[1]!=b[1] and b[0]-a[0]<600 for a,b in zip(combined,combined[1:]))}
for model in ['deepseek','deepseek2','deepseek_test']:
 path=Path('/opt/monitor/geo-capture/manual-login')/model
 request=json.loads((path/'request.json').read_text()) if (path/'request.json').exists() else {}
 state=json.loads((path/'state.json').read_text()) if (path/'state.json').exists() else {}
 result['manual_flows'][model]={'created_at':stamp(request.get('created_at')),'status':state.get('status'),'message':state.get('message'),'collector_send_intents_since_flow_open':sum(t>=request.get('created_at',1e99) for t in all_events.get(model,[]))}
# Read App-native user turn timestamps; do not export the questions, ids, tokens or DB filenames.
for name in ['deepseek-hpe14-android13','deepseek-hpe14-account2','deepseek-manual-test']:
 base=Path('/var/lib/docker/volumes/'+name+'-data/_data/data/com.deepseek.chat/databases')
 count=0;timestamps=[];per_question=collections.Counter()
 for path in base.rglob('*.db'):
  try:
   with connect(path) as db:
    for row in db.execute("select name from sqlite_master where type='table' and name like 'chat_session_messages_%'"):
     table='"'+row['name'].replace('"','""')+'"'
     cols={r['name'] for r in db.execute('pragma table_info('+table+')')}
     if not {'role','inserted_at','fragments'}<=cols:continue
     for m in db.execute('select inserted_at,fragments from '+table+" where role='USER'"):
      count+=1;t=float(m['inserted_at']);timestamps.append(t/1000 if t>1e11 else t)
      try:
       fragment=json.loads(m['fragments']);q=''.join(str(v.get('content','')) for v in fragment if v.get('type')=='REQUEST');per_question[tag(q)]+=1
      except Exception:pass
  except sqlite3.DatabaseError:continue
  result['private_sources_scanned']+=1
 today=[v for v in timestamps if datetime.fromtimestamp(v,timezone(timedelta(hours=8))).strftime('%Y-%m-%d')=='2026-10-17']
 result['containers'][name]['native_user_turns']={'all_local':count,'today':len(today),'first_today':stamp(min(today)) if today else None,'last_today':stamp(max(today)) if today else None,'repeated_prompt_groups_all_history':sum(v>1 for v in per_question.values())}
(ROOT/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
