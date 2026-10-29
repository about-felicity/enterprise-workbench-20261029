import sys,json,collections
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,materials
from creation.owned_sources import exclude_owned
from geo_source_cards.source_scope import anchors,evaluate
for root in sorted((runtime.BASE/'runs').glob('creation-*')):
 j=runtime.read(root/'job.json');day=runtime.read(root/'days'/j.get('date','none')/'day.json')
 if j.get('date','')<'2026-10-26':continue
 if j.get('preparation')!='insufficient' and root.name!='creation-1793142584-b167f637':continue
 p=root/'private_source_analysis/articles.jsonl'
 if not p.exists():continue
 rows,excluded=exclude_owned(materials.read_lines(p));terms=anchors([j.get('question','')],runtime.read(root/'product.json'))
 sources=[s for row in rows for s in row.get('sources',[]) if s.get('article',{}).get('status')=='fetched']
 print(json.dumps({'job':root.name,'date':j['date'],'question':j['question'],'state':day.get('status'),'owned':len(excluded),'terms':terms,'sources':[{'url':s['url'],'title':s.get('article',{}).get('title'),'scope':evaluate(s,terms)} for s in sources]},ensure_ascii=False))
