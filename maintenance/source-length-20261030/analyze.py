import collections,csv,json,math,statistics,html
from pathlib import Path
from urllib.parse import urlsplit
import numpy as np
D=Path(__file__).parent;data=json.loads((D/'dataset.json').read_text('utf8'))
LABELS={'wenxin_card':'文心','baidu_ai':'百度'}
BINS=[(0,1000,'不足1000'),(1000,2000,'1000–1999'),(2000,3000,'2000–2999'),(3000,5000,'3000–4999'),(5000,8000,'5000–7999'),(8000,float('inf'),'8000及以上')]
rows=[]
for a in data['articles']:
 for m in LABELS:
  events=[e for e in a['events'] if e['model']==m and e['source_complete'] is True]
  if not events:continue
  qs=collections.Counter(e['question'] for e in events)
  rows.append({'platform':LABELS[m],'model':m,'url':a['url'],'canonical_url':a['canonical_url'],'title':a.get('article_title') or a['title'],'domain':urlsplit(a['canonical_url']).netloc,'status':a['status'],'quality':a.get('quality',''),'chars':a.get('alnum_chars'),'han_chars':a.get('han_chars'),'nonspace_chars':a.get('body_chars'),'raw_chars':a.get('raw_chars'),'recommendations':len(events),'recommended_days':len({e['day'] for e in events}),'question_count':len(qs),'main_question':qs.most_common(1)[0][0],'first_seen':min(e['day'] for e in events),'last_seen':max(e['day'] for e in events),'fetched_at':a.get('fetched_at'),'content_sha256':a.get('content_sha256'),'events':events})
def usable(r):return r['status']=='ok' and r['quality'] in {'high','medium'} and r['chars']>=80
valid=[r for r in rows if usable(r)]
def ranks(v):
 a=np.asarray(v,dtype=float);idx=np.argsort(a,kind='stable');s=a[idx];n=len(a);edges=np.r_[0,np.flatnonzero(s[1:]!=s[:-1])+1,n];out=np.empty(n)
 for l,h in zip(edges[:-1],edges[1:]):out[idx[l:h]]=(l+h-1)/2
 return out
def corr(a,b):
 a=np.asarray(a);b=np.asarray(b);a=a-a.mean();b=b-b.mean();den=np.linalg.norm(a)*np.linalg.norm(b)
 return float(a@b/den) if den else None
def association(rs,seed=46):
 x=ranks([r['chars'] for r in rs]);y=ranks([r['recommendations'] for r in rs]);rho=corr(x,y)
 rng=np.random.default_rng(seed);hits=sum(abs(corr(x,rng.permutation(y)) or 0)>=abs(rho or 0) for _ in range(999))
 # Approximate article bootstrap: shows uncertainty, not independent-search causality.
 boots=[]
 for _ in range(499):
  ids=rng.integers(0,len(rs),len(rs));boots.append(corr(x[ids],y[ids]) or 0)
 return dict(n=len(rs),spearman=rho,permutation_p=(hits+1)/1000,approx_bootstrap_ci=np.quantile(boots,[.025,.975]).tolist())
def adjusted(rs):
 groups=collections.defaultdict(list)
 for r in rs:groups[(r['domain'],r['main_question'])].append(r)
 groups=[g for g in groups.values() if len(g)>=5 and len({r['chars'] for r in g})>1 and len({r['recommendations'] for r in g})>1]
 if not groups:return {}
 xx=[];yy=[];segments=[];pos=0
 for g in groups:
  x=np.log([r['chars'] for r in g]);y=np.log1p([r['recommendations'] for r in g]);xx.extend(x-x.mean());yy.extend(y-y.mean());segments.append((pos,pos+len(g)));pos+=len(g)
 x=np.array(xx);y=np.array(yy);value=corr(x,y);rng=np.random.default_rng(724);hits=0
 for _ in range(499):
  perm=y.copy()
  for lo,hi in segments:perm[lo:hi]=rng.permutation(perm[lo:hi])
  hits+=abs(corr(x,perm) or 0)>=abs(value or 0)
 return dict(n=len(x),groups=len(groups),within_domain_question_log_correlation=value,permutation_p=(hits+1)/500)
def summary(rs,allrows):
 a=np.array([r['chars'] for r in rs]);refs=sum(r['recommendations'] for r in rs)
 bins=[]
 for low,high,label in BINS:
  group=[r for r in rs if low<=r['chars']<high];n=len(group);rec=sum(r['recommendations'] for r in group)
  bins.append(dict(bin=label,unique_articles=n,article_share=n/len(rs),recommendations=rec,recommendation_share=rec/refs,mean_recommendations=rec/n if n else 0,repeat_share=sum(r['recommendations']>=2 for r in group)/n if n else 0,mean_questions=statistics.mean([r['question_count'] for r in group]) if group else 0))
 return dict(unique_links=len(allrows),valid_articles=len(rs),coverage=len(rs)/len(allrows),total_link_recommendations=sum(r['recommendations'] for r in allrows),valid_recommendations=refs,median=float(np.median(a)),mean=float(a.mean()),p25=float(np.quantile(a,.25)),p75=float(np.quantile(a,.75)),p90=float(np.quantile(a,.9)),bins=bins,association=association(rs),adjusted=adjusted(rs),domains=[dict(domain=k,articles=len(g),median=float(np.median([r['chars'] for r in g])),recommendations=sum(r['recommendations'] for r in g)) for k,g in sorted(((k,[r for r in rs if r['domain']==k]) for k in {r['domain'] for r in rs}),key=lambda x:len(x[1]),reverse=True)[:10]])
results={}
for model,name in LABELS.items():
 rs=[r for r in valid if r['model']==model];allrows=[r for r in rows if r['model']==model]
 results[name]=summary(rs,allrows)
 results[name]['sensitivity_high_quality']=association([r for r in rs if r['quality']=='high'])
 filtered=[r for r in rs if r['domain'] not in {'baike.baidu.com','baidu.com','zhidao.baidu.com'}]
 results[name]['sensitivity_article_like']=summary(filtered,[r for r in allrows if r['domain'] not in {'baike.baidu.com','baidu.com','zhidao.baidu.com'}])
 dedup={}
 for r in rs:
  key=r['content_sha256']
  if key not in dedup:dedup[key]=dict(r)
  else:dedup[key]['recommendations']+=r['recommendations']
 results[name]['sensitivity_content_dedup']=association(list(dedup.values()))
 complete=[]
 for r in rs:
  es=[e for e in r['events'] if e['day']!=data['window_end']]
  if es:complete.append({**r,'recommendations':len(es),'question_count':len({e['question'] for e in es})})
 results[name]['sensitivity_exclude_today']=association(complete)
 # Same independent search can repeat an identical answer; assess removing them too.
 nondup=[]
 for r in rs:
  es=[e for e in r['events'] if not e['duplicate_answer']]
  if es:nondup.append({**r,'recommendations':len(es)})
 results[name]['sensitivity_exclude_duplicate_answers']=association(nondup)
# Pooled article count deduplicates articles across platforms.
pooled={}
for r in valid:
 k=r['canonical_url']
 if k not in pooled:pooled[k]={**r,'events':list(r['events'])}
 else:pooled[k]['events']+=r['events'];pooled[k]['recommendations']+=r['recommendations']
pooled=list(pooled.values())
for r in pooled:r['question_count']=len({e['question'] for e in r['events']})
results['合计']=summary(pooled,list({r['canonical_url']:r for r in rows}.values()))
# Don't interpret pooled denominators as per-platform exposure.
results['合计']['total_link_recommendations']=sum(r['recommendations'] for r in rows)
results['window']={k:v for k,v in data.items() if k not in ['captures','articles']}
results['capture_counts']={name:dict(total=sum(c['model']==m for c in data['captures']),complete=sum(c['model']==m and c['source_complete'] is True for c in data['captures']),questions=len({c['question'] for c in data['captures'] if c['model']==m}),days=len({c['date'] for c in data['captures'] if c['model']==m})) for m,name in LABELS.items()}
results['daily_captures']=[dict(date=day,**{name:sum(c['model']==m and c['date']==day for c in data['captures']) for m,name in LABELS.items()}) for day in sorted({c['date'] for c in data['captures']})]
results['duplicate_content_hashes']=len(pooled)-len({r['content_sha256'] for r in pooled})
(D/'summary.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
cols=[k for k in rows[0] if k not in ['model','events']]
with (D/'文章字数与推荐明细.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=cols,extrasaction='ignore');w.writeheader();w.writerows(sorted(rows,key=lambda r:r['recommendations'],reverse=True))
with (D/'字数区间统计.csv').open('w',encoding='utf-8-sig',newline='') as f:
 fields=['platform',*results['文心']['bins'][0]];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
 for name in ['文心','百度','合计']:
  for row in results[name]['bins']:w.writerow(dict(platform=name,**row))
print(json.dumps({k:{key:v for key,v in value.items() if key not in ['domains']} for k,value in results.items() if k in ['文心','百度','合计','capture_counts']},ensure_ascii=False,indent=2))
