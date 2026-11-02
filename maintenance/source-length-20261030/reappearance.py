exec((__import__('pathlib').Path(__file__).parent/'analyze.py').read_text('utf-8-sig').split('results={}')[0])
exposures=collections.Counter((c['model'],c['question'],c['date']) for c in data['captures'] if c['source_complete'] is True)
output={}
for model,name in LABELS.items():
 rs=[]
 for r in valid:
  if r['model']!=model:continue
  first={q:min(e['day'] for e in r['events'] if e['question']==q) for q in {e['question'] for e in r['events']}}
  denom=sum(n for (m,q,d),n in exposures.items() if m==model and q in first and d>first[q])
  numer=sum(e['day']>first[e['question']] for e in r['events'])
  if denom:rs.append({**r,'recommendations':numer/denom,'later_opportunities':denom,'later_citations':numer})
 output[name]={'association':association(rs),'adjusted':adjusted(rs),'bins':[]}
 print('REAPPEARANCE',name,output[name]['association'],output[name]['adjusted'])
 for lo,hi,label in BINS:
  g=[r for r in rs if lo<=r['chars']<hi];output[name]['bins'].append(dict(bin=label,n=len(g),mean_rate=statistics.mean([r['recommendations'] for r in g]) if g else None,later_citations=sum(r['later_citations'] for r in g),later_opportunities=sum(r['later_opportunities'] for r in g)));print(label,len(g),round(statistics.mean([r['recommendations'] for r in g]),4) if g else None,sum(r['later_citations'] for r in g),sum(r['later_opportunities'] for r in g))
 with (D/(name+'后续再入选率.csv')).open('w',encoding='utf-8-sig',newline='') as f:
  fields=['url','title','chars','main_question','first_seen','later_opportunities','later_citations','recommendations'];w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(rs)

(D/'reappearance.json').write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf8')
