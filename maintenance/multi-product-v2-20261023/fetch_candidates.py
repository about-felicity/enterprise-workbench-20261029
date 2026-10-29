"""Fetch actual links from captured answers; preserve both successful and rejected sources."""
import argparse,hashlib,json,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path[:0]=[str(BASE/'engine'),str(BASE)]
from geo_source_cards.article_fetch import ScraplingArticleFetcher,check_article_relevance
from geo_source_cards.runtime import atomic_json,atomic_write
from geo_source_cards.rewrite_v2.integration import classify
from geo_source_cards.article_quality import normalize
p=argparse.ArgumentParser();p.add_argument('--key',required=True);p.add_argument('--limit',type=int,default=8);p.add_argument('--browser-key');p.add_argument('--only-url');a=p.parse_args()
out=BASE/'multi-results'/a.key
records=[json.loads(line) for line in (out/'captured.jsonl').read_text().splitlines() if line.strip()]
reader=ScraplingArticleFetcher(timeout=25,backends=('dynamic',) if a.browser_key else ('http',))
seen=set();reports=[]
for row in records:
    for source in row.get('sources',[]):
        url=source.get('url','')
        if a.only_url and url!=a.only_url:continue
        if not url or url in seen:continue
        seen.add(url)
        if len(seen)>a.limit:break
        key=hashlib.sha256(url.encode()).hexdigest()[:16];path=out/'candidates'/(key+'.json')
        if a.browser_key and key!=a.browser_key:continue
        if path.exists() and not a.browser_key:record=json.loads(path.read_text())
        else:
            if path.exists():atomic_json(path.with_suffix('.http.json'),json.loads(path.read_text()))
            article=normalize(check_article_relevance(reader(url),source.get('title','')))
            record={'question':row.get('question'),'model':row.get('model'),'source':{**source,'article':article}}
            if article.get('status')=='fetched':
                record['category']=classify([record['source']],1)['categories'][0]['label']
                atomic_write(path.with_suffix('.md'),article['text'])
            atomic_json(path,record)
        article=record['source']['article']
        report={'key':key,'title':article.get('title') or source.get('title'),'url':url,
                'chars':len(article.get('text','')),'status':article.get('status'),'category':record.get('category'),
                'error':article.get('error'),'preview':article.get('text','')[:400]}
        reports.append(report);print(json.dumps(report,ensure_ascii=False),flush=True)
atomic_json(out/'candidates.json',reports)
