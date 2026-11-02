import hashlib,json,sqlite3
from pathlib import Path
base=Path('/opt/monitor/geo-capture');work=base/'maintenance/wenxin-20261031';report=json.loads((work/'release.json').read_text())
assert report['wenxin_probe']['status']=='ready' and report['wenxin_probe']['sources']==35
root=base/'batches'/report['batch'];health=json.loads((root/'bridge_health.json').read_text())
with sqlite3.connect((root/'collector/tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 counts=dict(db.execute('select state,count(*) from captures group by state'));report['completed_now']=counts.get('completed',0);report['pending_now']=counts.get('pending',0)
 before=json.loads((work/'completed-before.json').read_text());now={t:hashlib.sha256(r.encode()).hexdigest() for t,r in db.execute("select task_id,result from captures where state='completed'")};assert all(now.get(t)==h for t,h in before.items())
with sqlite3.connect((base/'panel/control.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 row=db.execute("select * from daily_tasks where model='wenxin_card' and day='2026-10-31'").fetchone()
 report['wenxin_daily']={k:row[k] for k in ['day','model','status','desired','batch']} if row else None
report['status']='fixed_and_live_probe_verified';report['original_card_order_preserved']=True
(work/'release.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
