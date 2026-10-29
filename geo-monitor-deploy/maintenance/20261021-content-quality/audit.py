import json,re,sqlite3,sys,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
rows=[]
for root in [runtime.SHARED]+[p.parent for p in (runtime.BASE/'runs').glob('*/job.json')]:
 for a in runtime.articles(root):
  text=(root/'approved'/a['id']/'draft.md').read_text()
  matches=list(re.finditer('原文|主参考|知识库|未独立|编排|参考文章|参考文|资料列有|资料列明|资料所列|待核验',text))
  rows.append({'job':root.name,'id':a['id'],'title':a['title'],'modern':runtime.read(root/'approved'/a['id']/'category.json').get('reference_design',{}).get('version'),'hits':len(matches),'samples':[text[max(0,m.start()-12):m.end()+30] for m in matches[:3]],'control':runtime.read(root/'control.json')})
ledger=sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True)
report={'at':time.time(),'articles':rows,'counts':{'total':len(rows),'affected':sum(bool(r['hits']) for r in rows)},'daily_costs':ledger.execute('select date,sum(charged) from costs group by date order by date desc limit 3').fetchall(),'unsettled':ledger.execute('select count(*) from costs where charged is null').fetchone()[0]}
out=Path('/tmp/creation-quality-probe');out.mkdir(exist_ok=True);(out/'content-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='articles'},ensure_ascii=False));print(json.dumps(rows[-3:],ensure_ascii=False))
