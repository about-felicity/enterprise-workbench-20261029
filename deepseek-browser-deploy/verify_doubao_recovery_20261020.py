import json,sqlite3,subprocess,time,urllib.request
from pathlib import Path
batch='geo-panel-doubao2-20261020-090001-6bcafb90';root=Path('/home/user/redroid-doubao/batches')/batch
db=sqlite3.connect(root.joinpath('tasks.sqlite').as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
tasks=[dict(v) for v in db.execute("select * from tasks where state='completed' order by ordinal")]
sql="SELECT record FROM monitor_ingest_events WHERE source_device='doubao-hpe14-account2' AND record->>'batch_id'='"+batch+"';"
rows=[json.loads(v) for v in subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-At','-c',sql],text=True).splitlines() if v.strip()]
records={v['native_request_id']:v for v in rows}
verified=[]
for task in tasks:
 r=json.loads(task['result_json']);p=records.get(r['request_id'])
 if not p:continue
 assert p['answerText']==r['body_markdown'] and p['items']==r['sources'] and p['citations']==r['citations']
 assert r['first_user_turn'] is True and r['body_capture_complete'] is True and r['source_capture_complete'] is True
 with sqlite3.connect(Path(next(v['database'] for v in json.loads((root/(task['task_id']+'-attempt-'+str(task['capture_retries'])+'.pre-send.json')).read_text())['databases'] if '2697541922066524' in v['database'])).as_uri()+'?mode=ro',uri=True) as native:
  assert native.execute('select count(*) from im_message where conversation_id=? and user_type=1',(r['conversation_id'],)).fetchone()[0]==1
 verified.append({'ordinal':task['ordinal'],'body_length':len(r['body_markdown']),'sources':len(r['sources']),'capture_retries':task['capture_retries']})
assert '7e05dd72-9965-4fe5-a365-e3421898365a' not in records
clicks=[dict(v) for v in db.execute("select event,count(*) as n from events where task_id='565e4e38-0407-50f8-8fd0-f295b4419e5c' and event='send_click_intent_committed' group by event")]
assert clicks[0]['n']==2 # one rejected completed context attempt + one explicit repair attempt
with urllib.request.urlopen('http://127.0.0.1:8803/',timeout=10) as r:panel=r.read().decode()
assert 'App已退出，正在唤起补读原请求' in panel
info=json.loads(subprocess.check_output(['docker','inspect','doubao-hpe14-account2'],text=True))[0]
report={'checked_at':time.time(),'batch':batch,'local_completed':len(tasks),'postgres_verified':len(verified),'verified_tail':verified[-5:],'rejected_context_not_in_pg':True,'original_task17_was_not_resent':db.execute("select count(*) from events where task_id='9c69d1ac-dd4c-563f-a299-4ca0519856f7' and event='send_click_intent_committed'").fetchone()[0]==1,'panel_recovery_labels_served':True,'memory_limit':info['HostConfig']['Memory'],'memory_swap_limit':info['HostConfig']['MemorySwap'],'health':json.loads((root/'bridge_health.json').read_text())}
Path('/tmp/doubao-recovery-acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
