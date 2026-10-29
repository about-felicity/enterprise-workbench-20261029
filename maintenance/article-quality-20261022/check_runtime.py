"""Read current paid execution/ledger state without credentials or writes."""
import json,sqlite3,subprocess,time
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261022-article-quality');D.mkdir(exist_ok=True)
B=Path('/opt/monitor/geo-content');read=lambda p:json.loads(p.read_text()) if p.is_file() else {}
out={'at':time.time(),'services':{},'jobs':[]}
for service in ('geo-content-api','geo-content-worker','geo-creation-studio'):
 out['services'][service]=subprocess.check_output(['systemctl','is-active',service],text=True).strip()
for root in (B/'runtime/runs').iterdir():
 if not root.is_dir():continue
 active=read(root/'api/active.json');control=read(root/'control.json')
 row={'id':root.name,'control':control,'active':active,'health':read(root/'api/health.json')}
 if root.name in ('creation-1792575159-0a8f9221','creation-1792576129-389f575e'):
  row['limits']=read(root/'job.json').get('budget_limits');row['pilots']=[]
  for parent in (root/'days/2026-10-21/compiler-pilots').glob('*/*'):
   writer=parent/'writer';doc=read(writer/'writer_done.json');review=read(parent/'review/result.json')
   row['pilots'].append({'location':str(parent),'writer_done':bool(doc),'review_checks':review.get('checks'),'review_failures':review.get('failures'),'draft_sha256':review.get('draft_sha256')})
 out['jobs'].append(row)
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 out['costs']=db.execute("select c.date,sum(c.charged),sum(case when c.charged is null then c.reserved else 0 end) from costs c join studio_cost_scopes s on c.id=s.id where s.scope=? group by c.date",('plan-33e7bfca8bb6497da10b28f0444a693b',)).fetchall()
 out['unknown_ids']=sorted(r[0] for r in db.execute('select id from costs where charged is null'))
(D/'after-deploy.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False)[:15500])
