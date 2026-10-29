"""One evidence-bound recovery of the two diagnosed stopped jobs; never generic reset."""
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import time
from urllib.parse import urlsplit
sys.path.insert(0,'/opt/monitor/geo-capture/venv/lib/python3.10/site-packages')
from geo_source_cards.journal import Journal
from geo_source_cards.search_recovery import SearchRecovery
base=Path('/opt/monitor/geo-capture');out=base/'maintenance/20261015-unified/web-recovery';out.mkdir(mode=0o700,exist_ok=True)
ds=base/'batches/geo-panel-deepseek-20261015-181821-879aca5d';wx=base/'batches/geo-panel-wenxin-card-20261015-181822-d5a69c59'
history_path=Path('/tmp/geo-deepseek-reconciliation-17920612/history.json')
history=json.loads(history_path.read_text())
fetch=next(r['body'] for r in history['responses'] if r['path']=='/api/v0/chat_session/fetch_page' and r['status']==200)
assert fetch['code']==0 and fetch['data']['biz_code']==0
sessions=fetch['data']['biz_data']['chat_sessions'];times=[s['updated_at'] for s in sessions]
assert len(times)>=5 and times==sorted(times,reverse=True)
journal=Journal(ds/'collector/tasks.sqlite');task=journal.db.execute("select * from captures where state='needs_attention'").fetchone()
if task:
    assert task['task_id']=='6c21e83c60b88dd2f6c6b3f909f5aee73dd1a035fcc55ab2d2cf63f0ef0120a8'
    assert task['error']=='未确认 DeepSeek 接收问题；已保存发送状态，禁止自动重发'
    failure=json.loads((ds/'collector/diagnostics/deepseek-1792060755668161088.json').read_text())
    assert failure['snapshot']['url']=='https://chat.deepseek.com/' and failure['snapshot']['text']==task['question']
    assert max(times)<task['started'] and history['at']>task['started']+120
    # Complete first page covers the entire time window after this click; all
    # five latest nonempty chats predate it and match already captured results.
    known=set()
    for batch in base.joinpath('batches').glob('*/collector/tasks.sqlite'):
        with sqlite3.connect(batch.as_uri()+'?mode=ro',uri=True) as conn:
            for row in conn.execute("select result from captures where model='deepseek' and state='completed'"):
                record=json.loads(row[0]);known.add(urlsplit(record.get('url','')).path.rsplit('/',1)[-1])
    assert all(s['id'] in known for s in sessions[:5])
    proof={'at':time.time(),'task_id':task['task_id'],'history_at':history['at'],
           'history_sha256':hashlib.sha256(history_path.read_bytes()).hexdigest(),
           'latest_server_chat_updated_at':max(times),'intent_at':task['started'],
           'latest_five_are_known_completed':True,'failure_home_and_composer_exact_question':True,
           'conclusion':'No server chat/message in authoritative recent-history window after click; exact question remained in home composer. Reconciled as unsubmitted, not a blind resend of unknown delivery.',
           'previous_row':dict(task)}
    (out/'deepseek-unsubmitted-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2))
    with sqlite3.connect(out/'deepseek-tasks-before.sqlite') as backup:journal.db.backup(backup)
    with journal.db:
        journal.db.execute('create table if not exists submission_reconciliations(task_id text primary key,proof text,epoch real)')
        journal.db.execute('insert into submission_reconciliations values(?,?,?)',(task['task_id'],json.dumps(proof,ensure_ascii=False),time.time()))
        journal.db.execute("update captures set state='pending',error=null,result=null where task_id=? and state='needs_attention'",(task['task_id'],))
    print(json.dumps({'deepseek_reconciled_unsubmitted':task['task_id'],'evidence':str(out/'deepseek-unsubmitted-proof.json')}))
journal.close()
journal=Journal(wx/'collector/tasks.sqlite');task=journal.db.execute("select * from captures where state='needs_attention'").fetchone()
if task:
    assert task['task_id']=='aeabb3335d8ba262d303a9c012bddc760cfda266cb567a786e6e931e59b03f75'
    assert task['error'].startswith('Timeout 45000ms exceeded.')
    with sqlite3.connect(out/'wenxin-tasks-before.sqlite') as backup:journal.db.backup(backup)
    recovery=SearchRecovery(journal,wx/'collector')
    result=recovery.failure(task,TimeoutError('Page.goto: Timeout waiting for original document; original nested timeout: '+task['error']))
    assert result['kind']=='read_error' and not result['exhausted']
    (out/'wenxin-read-recovery.json').write_text(json.dumps({'previous_row':dict(task),'result':result},ensure_ascii=False,indent=2))
    print(json.dumps({'wenxin_read_recovery':result['status']}))
journal.close()
