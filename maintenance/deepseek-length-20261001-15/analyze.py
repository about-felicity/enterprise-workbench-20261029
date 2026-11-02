import collections,csv,json,math,statistics,html
from pathlib import Path
from urllib.parse import urlsplit
import numpy as np
D=Path(__file__).parent;data=json.loads((D/'dataset.json').read_text('utf8'))
LABELS={'deepseek':'DeepSeek'}
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

labels=json.loads((D/'domain_classification.json').read_text('utf8'))
for r in rows:r['region']=labels[r['domain']]['region'];r['region_reason']=labels[r['domain']]['reason']
known=[r for r in rows if r['region'] in {'mainland','hk_macao_taiwan'}]
# Keep HK/Macao/Taiwan separately labeled; these are not foreign sites.
nonarticle={'baike.baidu.com','wapbaike.baidu.com','baidu.com','zhidao.baidu.com'}
def content_kind(r):
 h=r['domain'];path=urlsplit(r['url']).path
 if h in nonarticle:return '百科/搜索'
 if h.endswith('taobao.com') and h!='jianghu.taobao.com':return '商品/电商'
 shop={'hktvmall.com','hktvmerchantevoucher.hktvmall.com','etmall.com.tw','m.etmall.com.tw','mall.iopenmall.tw','smzdm.com','m.smzdm.com','wiki.smzdm.com','wiki.m.smzdm.com','so.m.jd.com','item.jd.com','taobao.com','world.taobao.com','watsons.com.hk','watsons.com.tw','mannings.com.hk','co.51tomi.com','iherb.com','yesstyle.com'}
 if h in shop or ('/product/' in path) or ('/products/' in path):return '商品/电商'
 if h in {'eureka.patsnap.com','synapse.zhihuiya.com','code.nhsa.gov.cn'}:return '专利/目录'
 if h.endswith('zhihu.com') and '/question/' in path:return '问答正文'
 return '文章候选'
for r in rows:r['content_kind']=content_kind(r)
mainrows=[r for r in known if r['content_kind'] in {'文章候选','问答正文'}]
primary=[r for r in mainrows if usable(r)]
allvalid=[r for r in known if usable(r)]
result={'window':{k:v for k,v in data.items() if k not in ['captures','articles']},'captures':len(data['captures']),'complete_captures':sum(c['source_complete'] is True for c in data['captures']),'questions':len({c['question'] for c in data['captures']}),'days':sorted({c['date'] for c in data['captures']}),'region_url_counts':dict(collections.Counter(labels[__import__('urllib.parse',fromlist=['urlsplit']).urlsplit(a['canonical_url']).netloc]['region'] for a in data['articles'])),'raw_status_counts':dict(collections.Counter(a['status'] for a in data['articles'])),'nonforeign_content_kinds':dict(collections.Counter(r['content_kind'] for r in known)),'primary':summary(primary,mainrows),'including_encyclopedia':summary(allvalid,known)}
for region in ['mainland','hk_macao_taiwan']:
 group=[r for r in primary if r['region']==region]
 result[region]=summary(group,[r for r in mainrows if r['region']==region])
strict=[r for r in primary if r['content_kind']=='文章候选']
result['strict_articles']=summary(strict,[r for r in mainrows if r['content_kind']=='文章候选'])
result['strict_mainland_articles']=summary([r for r in strict if r['region']=='mainland'],[r for r in mainrows if r['content_kind']=='文章候选' and r['region']=='mainland'])
result['sensitivity_high_quality']=association([r for r in primary if r['quality']=='high'])
dedup={}
for r in primary:
 key=r['content_sha256']
 if key not in dedup:dedup[key]=dict(r)
 else:dedup[key]['recommendations']+=r['recommendations']
result['sensitivity_content_dedup']=association(list(dedup.values()))
result['region_quality_counts']={region:dict(all_urls=sum(r['region']==region for r in rows),cache_ok=sum(r['region']==region and r['status']=='ok' for r in rows),valid=sum(r['region']==region and usable(r) for r in rows)) for region in {r['region'] for r in rows}}
# Exposure-adjusted reappearance among already cited articles.
exposure=collections.Counter((c['question'],c['date']) for c in data['captures'] if c['source_complete'] is True)
later=[]
for r in primary:
 first={q:min(e['day'] for e in r['events'] if e['question']==q) for q in {e['question'] for e in r['events']}}
 den=sum(n for (q,d),n in exposure.items() if q in first and d>first[q])
 num=sum(e['day']>first[e['question']] for e in r['events'])
 if den:later.append({**r,'recommendations':num/den,'later_citations':num,'later_opportunities':den})
result['reappearance']={'association':association(later),'adjusted':adjusted(later)}
(D/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
columns=[k for k in rows[0] if k not in {'events','model'}]
with (D/'DeepSeek全部信源字数及地域.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=columns,extrasaction='ignore');w.writeheader();w.writerows(sorted(rows,key=lambda r:r['recommendations'],reverse=True))
with (D/'DeepSeek剔除国外后文章明细.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=columns,extrasaction='ignore');w.writeheader();w.writerows(sorted(primary,key=lambda r:r['recommendations'],reverse=True))
with (D/'DeepSeek文章样本明细.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=columns,extrasaction='ignore');w.writeheader();w.writerows(sorted(strict,key=lambda r:r['recommendations'],reverse=True))
with (D/'域名地域核对表.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['domain','region','reason','unique_urls']);w.writeheader();w.writerows(dict(domain=h,**v) for h,v in labels.items())
print(json.dumps(result,ensure_ascii=False,indent=2))
