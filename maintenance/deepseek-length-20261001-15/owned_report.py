import json,csv,collections,sys,importlib.util
from pathlib import Path
D=Path(__file__).parent;raw=json.loads((D/'owned_dataset.json').read_text('utf8'))
allrows={r['canonical_url']:r for r in csv.DictReader((D/'DeepSeek全部信源字数及地域.csv').open(encoding='utf-8-sig'))};strict={r['canonical_url']:r for r in csv.DictReader((D/'DeepSeek文章样本明细.csv').open(encoding='utf-8-sig'))}
sys.path.insert(0,str(D.parents[1]/'geo-monitor-deploy/server-source'))
spec=importlib.util.spec_from_file_location('owned_rules',D.parents[1]/'geo-monitor-deploy/server-source/monitor_core/owned_products.py');rules=importlib.util.module_from_spec(spec);spec.loader.exec_module(rules)
articles=[];events=[];by=collections.defaultdict(lambda:{'urls':set(),'citations':0})
for a in raw['articles']:
 r=allrows.get(a['canonical_url'],{});es=[e for e in a['events'] if e['source_complete'] is True]
 if not a.get('own_products') or not es or r.get('region') not in {'mainland','hk_macao_taiwan'} or r.get('content_kind')!='文章候选':continue
 captured_products=rules.own_product_mentions('\n'.join(a.get('source_titles',[])))
 row={'url':a['url'],'canonical_url':a['canonical_url'],'title':a.get('article_title') or a['title'],'products':'；'.join(a['own_products']),'citations':len(es),'days':len({e['day'] for e in es}),'questions':'；'.join(sorted({e['question'] for e in es})),'first_seen':min(e['day'] for e in es),'last_seen':max(e['day'] for e in es),'chars':a.get('alnum_chars'),'status':a['status'],'quality':a.get('quality'),'usable_for_length':a['canonical_url'] in strict,'captured_title_products':'；'.join(captured_products),'title_products_including_cached_title':'；'.join(a['title_products']),'body_products':'；'.join(a['body_products']),'evidence':json.dumps(a.get('product_evidence',{}),ensure_ascii=False),'region':r['region'],'fetched_at':a.get('fetched_at')}
 articles.append(row)
 for e in es:events.append({'run_id':e['run_id'],'captured_at':e['captured_at'],'day':e['day'],'question':e['question'],'url':a['url'],'canonical_url':a['canonical_url'],'products':row['products'],'title':row['title']})
 for product in a['own_products']:by[product]['urls'].add(a['canonical_url']);by[product]['citations']+=len(es)
assert len({(e['run_id'],e['canonical_url']) for e in events})==len(events)
articles.sort(key=lambda x:x['citations'],reverse=True)
for filename,rs in [('自有产品文章引用汇总.csv',articles),('自有产品逐次引用证据.csv',events)]:
 with (D/filename).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
products=[{'product':p,'article_urls':len(v['urls']),'citations':v['citations']} for p,v in sorted(by.items(),key=lambda x:x[1]['citations'],reverse=True)]
result={'date_start':'2026-10-01','date_end':'2026-10-15','model':'DeepSeek','article_urls':len(articles),'citation_events':len(events),'distinct_answers':len({e['run_id'] for e in events}),'usable_articles_for_length':sum(r['usable_for_length'] for r in articles),'usable_article_citations':sum(r['citations'] for r in articles if r['usable_for_length']),'captured_title_confirmed_urls':sum(bool(r['captured_title_products']) for r in articles),'captured_title_confirmed_citations':sum(r['citations'] for r in articles if r['captured_title_products']),'products':products}
(D/'owned_summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
lines=['# DeepSeek：自有产品文章的引用次数核对','', '**此前1,018篇是所有品牌的文章样本，并非仅自有产品文章。此前字数结论不能直接当作自有产品结论。**','', '范围：2026年10月1—15日，DeepSeek主GEO成功记录，剔除国外站点，归属未知单列；明显商品、百科、问答、专利等非文章页面排除。10月5日无成功记录。','', f"- 识别到自有产品的文章链接：{result['article_urls']}个。",f"- 累计引用事件：{result['citation_events']}次；来自{result['distinct_answers']}次独立成功答复。",f"- 其中合格正文可用于字数分析：{result['usable_articles_for_length']}篇，累计{result['usable_article_citations']}次引用。",f"- 历史采集到的来源卡片标题文本中可直接识别产品的链接：{result['captured_title_confirmed_urls']}个，累计{result['captured_title_confirmed_citations']}次；其余依赖现存正文或当前缓存标题识别。",'', '| 产品 | 涉及文章链接数 | 累计引用次数 |','|---|---:|---:|']
for p in products:lines.append(f"| {p['product']} | {p['article_urls']} | {p['citations']} |")
lines+=['', '**计数规则**：一次答复中同一规范化URL只算一次，不同答复再次引用则再算一次。逐次证据CSV保留run_id、采集时间、问题和URL。不同产品可能在同一文章出现，产品分项不能相加作为总引用数。','', '**归属含义**：按照配置的自有品牌与产品描述近邻匹配标题/清洗后的正文。表示文章包含自有产品，并不证明由用户本人发布，也不等同于DeepSeek答复直接推荐该产品。若要确认“自己发布的文章”，还需与发布URL/账号清单交叉比对。','', '**时间限制**：引用事件发生于10月1—15日；产品识别部分依赖当前正文缓存，其抓取时间可能晚于引用日期，页面可能发生修改。因此引用URL次数可追溯，但不能保证正文在引用当日已包含同样产品。','', '**正文与识别完整性**：正文不可访问且来源标题没有产品名称的文章，可能漏识别，以上不是全部自有文章的保证总数。未把访问失败文章算作零引用。','', '明细文件：自有产品文章引用汇总.csv、自有产品逐次引用证据.csv、owned_summary.json。']
(D/'自有产品引用核对.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
print(json.dumps(result,ensure_ascii=False,indent=2))

