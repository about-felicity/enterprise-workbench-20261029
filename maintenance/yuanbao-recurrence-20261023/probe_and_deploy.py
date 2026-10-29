"""Test actual original stored video, then replace only verified reader code."""
import ast,hashlib,json,os,shutil,sqlite3,subprocess,sys,time
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261023-yuanbao-recurrence');S=D/'stage-final';BASE=Path('/home/user/redroid-yuanbao')
shutil.copy2(BASE/'native_models.js',S/'native_models.js')
R=BASE/'batches/geo-panel-yuanbao-20261023-090004-d6b66215';UNIT='geo-native@'+R.name+'.service'
sys.path[:0]=[str(S),'/home/user/redroid-doubao/geo-batch-code','/home/user/redroid-yuanbao/tools']
from native_client import NativeClient
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def command(*args):return subprocess.check_output(args,text=True,timeout=30).strip()
def article_guard():
 paths=[Path('/home/user/geo-editorial/runtime-api/settings.json')]
 candidate=Path('/opt/monitor/geo-capture/maintenance/20261023-structure-recovery-v3-final/candidate-source')
 paths += [p for p in candidate.rglob('*') if p.is_file()]
 with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
  rows=db.execute('select * from costs order by id').fetchall();scopes=db.execute('select * from studio_cost_scopes order by id').fetchall()
 return {'files':{str(p):sha(p) for p in paths},'ledger_rows':len(rows),'ledger_sha256':hashlib.sha256(json.dumps([rows,scopes]).encode()).hexdigest()}
assert not (R/'maintenance_pause.json').exists(),'Preserve user pause'
before_article=article_guard();pid=command('docker','exec','yuanbao-hpe14-android13','pidof','com.tencent.hunyuan.app.chat')
with sqlite3.connect(R.joinpath('tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row;t=dict(db.execute('select * from tasks where ordinal=125').fetchone())
assert t['state']=='prepared' and t['capture_retries']==0
assert t['request_id']=='876a3acdca7609a26c7eb286254afba7'
for suffix in ('binding','native','render','pre-send'):
 p=R/(t['task_id']+'.'+suffix+'.json');shutil.copy2(p,D/('before-task125-'+suffix+'.json'))
c=NativeClient(R)
try:
 value=c.lookup(t)
 assert value['status']=='nontext_complete' and not value['sources'] and value['text_body_present'] is False
 assert value['request_id']==t['request_id'] and value['answer_id']=='0RTB4lSYXbs_2'
finally:c.close()
with sqlite3.connect(R.joinpath('tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 assert db.execute("select count(*) from events where task_id=? and event='send_click_intent_committed'",(t['task_id'],)).fetchone()[0]==1
actual={'at':time.time(),'source':'Actual original Yuanbao EOF + exact persisted first pair, no resend','status':value['status'],'request_id':value['request_id'],
 'answer_id':value['answer_id'],'rich_cards':len(value['rich_cards']),'media_items':sum(len(c['multimedias']) for c in value['rich_cards']),
 'text_body_present':False,'sources':0,'body_transcript_invented':False,'native_store_proof':value['native_snapshot']['persisted_replacement_snapshot']['records_sha256'],
 'original_render_cards_still_empty':not value['native_snapshot']['render_snapshot']['i']['replacesJson'],'send_clicks':1,'api_calls':0}
(D/'actual-probe.json').write_text(json.dumps(actual,ensure_ascii=False,indent=2));print(json.dumps(actual),flush=True)
targets=['native_core.py','native_client.py','stored_replacements.py','tests/test_stored_replacements.py']
before={name:sha(BASE/name) if (BASE/name).exists() else None for name in targets}
assert before['native_core.py']=='096263fae25fbb8175c19dedd124181e5ad9220e5e99e49842f2b73b68716e10'
assert before['native_client.py']=='05bb0bc9911ca17940f8207d0b09bd9e28c18355c8887303248f31d29ad937a5'
for name in targets:ast.parse((S/name).read_text())
backup=D/('source-before-'+str(time.time_ns()));backup.mkdir()
subprocess.run(['systemctl','mask','--runtime',UNIT],check=True)
try:
 subprocess.run(['systemctl','stop',UNIT],check=True,timeout=45)
 assert command('systemctl','show',UNIT,'-p','ActiveState','--value') in ('inactive','failed')
 with sqlite3.connect(R/'tasks.sqlite') as db,sqlite3.connect(D/'before-tasks.sqlite') as out:db.backup(out)
 for name in targets:
  target=BASE/name
  assert (sha(target) if target.exists() else None)==before[name]
  if target.exists():
   saved=backup/name;saved.parent.mkdir(exist_ok=True,parents=True);shutil.copy2(target,saved)
  tmp=target.with_name(target.name+'.video-recovery.tmp');shutil.copy2(S/name,tmp);tmp.chmod(0o644);tmp.replace(target)
finally:
 subprocess.run(['systemctl','unmask','--runtime',UNIT],check=True)
 subprocess.run(['systemctl','start',UNIT],check=True)
after_article=article_guard();assert before_article==after_article
assert pid==command('docker','exec','yuanbao-hpe14-android13','pidof','com.tencent.hunyuan.app.chat')
out={'at':time.time(),'backup':str(backup),'files':{str(BASE/n):sha(BASE/n) for n in targets},'before':before,
 'only_reader_restarted':True,'app_pid_unchanged':pid,'queue_reset':False,'question_resent':False,'article_budget_and_candidate_unchanged':before_article==after_article,'article_guard':after_article}
(D/'deployment.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in out.items() if k!='article_guard'}))
