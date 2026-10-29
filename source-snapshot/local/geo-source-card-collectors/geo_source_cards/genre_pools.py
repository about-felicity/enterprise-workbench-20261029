"""Auditable local genre routing with opt-in comparative reviews; preserve legacy pools."""
import hashlib
import re

from .reference_design import product_blocks

VERSION = "two-genre-v1"
LABELS = ("排行类", "科普类")
RANK = re.compile(r"排行|榜单|热门榜|红榜|TOP\s*\d|盘点|推荐|十大|\d+大|横评|测评|评测|实测|值得买|好物|避雷名单|几款|\d+\s*款|[四五六七八九十]+款", re.I)
PROMOTION = re.compile(r"购买链接|下单链接|(?:立即|点击|扫码|进店|赶紧).{0,8}(?:购买|下单)|旗舰店|代表案例|品牌参考|推荐.{0,20}(?:洗发|眼霜|面霜)|[（(][一二三四五六七八九十]+[）)].{0,50}洗发")
SINGLE_AD_TITLE = re.compile(r'神器|秘密武器|完美选择|必备.{0,10}(?:单品|好物)|我.{0,8}(?:放弃|入手|自用|回购)')
SINGLE_AD_BODY = re.compile(r'(?:今天|这次).{0,15}(?:介绍|推荐).{0,20}(?:一款|这款)|(?:我|本人).{0,12}(?:入手|亲测|回购)|正是一款|绝对是.{0,25}(?:选择|必备)|这款.{0,30}(?:专为|专门为).{0,25}(?:设计|打造)')

def review_form(title, body, products):
    """Recognize declared comparisons; a claimed test is not verified evidence."""
    return len(products)>=2 and bool(re.search(r'横评|测评|评测|横向对比',title) or (
        '实测' in title and re.search(r'(?:本次|此次)测评|(?:比较|对比|筛选|测评).{0,12}(?:维度|标准)|(?:核心|统一)维度',body[:3500])))

def declared_count(title):
    match=re.search(r'(?<!\d)(\d{1,3})\s*(?:款|大)|TOP\s*(\d{1,3})|([一二三四五六七八九十]{1,3})(?:款|大)',title,re.I)
    if not match:return None
    if match.group(1) or match.group(2):return int(match.group(1) or match.group(2))
    token=match.group(3);numbers={s:i for i,s in enumerate('零一二三四五六七八九')}
    if '十' in token:
        left,right=token.split('十',1)
        return numbers.get(left,1)*10+numbers.get(right,0)
    return numbers.get(token)


def describe_form(title, body, products):
    """Explain overlapping writing forms without treating audience as genre."""
    tags = []
    rules = [("选购指南", r"怎么选|怎样挑选|选购|选品策略"),
             ("避坑纠错", r"误区|避坑|避雷|慎选"),
             ("成分解析", r"成分对比|成分逻辑|配方解析|成分表"),
             ("横向测评", r"横评|数据对比|评分|实测"),
             ("体验分享", r"自用|真实感受|用下来|我的.{0,8}体验")]
    evidence = []
    for label, pattern in rules:
        match = re.search(pattern, title)
        if not match and label == "体验分享":
            match = re.search(r"我(?:自己)?.{0,12}(?:用过|用下来|试过)|我的.{0,8}体验", body[:900])
        if not match and label == "横向测评" and len(products) >= 2:
            match = re.search(r"(?:四个|多个|统一|相同)维度.{0,20}(?:对比|比较)|数据对比|横评", body[:1400])
        if match:
            tags.append(label)
            evidence.append({"tag": label, "quote": match.group()})
    main = next((t for t in ("体验分享", "横向测评", "成分解析", "避坑纠错", "选购指南") if t in tags), None)
    promotional = bool(PROMOTION.search(body) or RANK.search(title))
    if len(products) >= 2:
        main = main or "产品盘点"
    elif promotional:
        main = main or "单品解析或推广待核对"
    else:
        main = main or "科普知识"
    return {"article_type": main, "structure_tags": tags, "type_evidence": evidence,
            "classification_method": "local_rules_v2", "product_count": len(products),
            "topic_tags": [t for t in ("去屑", "控油", "止痒", "男士", "儿童", "敏感", "干性") if t in title]}


def missing_product_details(source,products):
    """Check exact, product-bound neutral excerpts before allocating paid work."""
    if not products:return []
    from .genre_prompts import quote_chunks
    from .genre_outline import captured_neutral_details
    from .consumer_prompts import reader_knowledge
    blueprint={'genre':'ranking','products':products};spans={}
    for i,p in enumerate(products,1):
        for j,q in quote_chunks(p['excerpt'],source['article']['text']):spans[f'R{i}_{j}']={'quote':q,'url':source['url']}
    units=captured_neutral_details({'units':[]},blueprint,spans)['units']
    ku=[{'id':u['id'],'type':'source_claim','content':u['text'],'verification':'not_independently_verified','evidence':[{'quote_id':e,**spans[e]} for e in u['evidence']]} for u in units]
    _,_,projection=reader_knowledge({'knowledge_units':ku,'reference_design':blueprint,'outline':{}},{'name':''},ku)
    return projection['products_without_neutral_details']


def classify_source(source, include_review=False):
    article = source.get("article", {})
    title = article.get("title") or source.get("title", "")
    body = article.get("text", "")
    products = product_blocks(article)
    ranking = len(products) >= 2 or bool(RANK.search(title))
    # Promotional/comparison prose is not a pure knowledge article, even when
    # its headline is phrased as a question. Keep an explicit review hold.
    roundup_prose = re.search(r'第[一二三四五六七八九十\d]+个产品[：:]|(?:以下|把|这|介绍|比较).{0,8}(?:[2-9]|[1-9]\d|[二三四五六七八九十]+)款.{0,10}(?:产品|眼霜|面霜|洗发|护发|精华|面膜)',body)
    ambiguous = not ranking and bool(PROMOTION.search(body) or roundup_prose or SINGLE_AD_TITLE.search(title) or SINGLE_AD_BODY.search(body))
    off_topic=source.get('topic_scope',{}).get('status')=='off_topic'
    missing_excerpt = ranking and any(not any(len(re.sub(r'\s','',line))>=12 for line in p['excerpt'].splitlines()) for p in products)
    neutral_missing=missing_product_details(source,products) if ranking else []
    expected=declared_count(title)
    incomplete_roster=ranking and expected is not None and len(products)!=expected
    genre = "测评类" if include_review and review_form(title,body,products) else "排行类" if ranking or ambiguous else "科普类"
    return {"url": source["url"], "title": title, "genre": genre,
            "status": "needs_review" if off_topic or incomplete_roster or ambiguous or missing_excerpt or neutral_missing or (ranking and len(products) < 2) else "ready",
            "reason": "正文主题未匹配任务产品与问题共同锚点" if off_topic else "原文声明款数与可解析独立产品数不符，须核对名单" if incomplete_roster else "产品缺少可用的具体中性资料，不分配收费写作" if neutral_missing else "多产品独立条目" if len(products) >= 2 else "榜单标题，产品条目待核对" if ranking else "含推广或单品体验内容，不能混入纯科普池" if ambiguous else "知识讲解，未发现推荐榜单或推广段落",
            "declared_product_count":expected,"products_without_neutral_details":neutral_missing,
            "topic_scope":source.get('topic_scope',{}),
            "products": products, "audience": "children" if re.search(r"儿童|婴儿|宝宝|新生儿|小孩", title) else "general",
            **describe_form(title, body, products),
            "text_sha256": hashlib.sha256(body.encode()).hexdigest()}


def classify(articles, limit=10, include_review=False):
    assignments = [classify_source(source,include_review) for source in articles]
    categories = []
    for label in LABELS + (("测评类",) if include_review else ()):
        members = [(s, a) for s, a in zip(articles, assignments) if a["genre"] == label]
        if not members:
            continue
        eligible = [a for _, a in members if a["status"] == "ready" and a["audience"] != "children"]
        categories.append({"label": label, "description": "同口径比较产品资料，标明信息缺口，不虚构亲测和评分" if label == "测评类" else "多产品逐项推荐，自有产品第一位" if label == "排行类" else "知识讲解为主，相关段落自然引入自有产品",
                           "sources": [{"url": s["url"], "quote": s["article"]["text"][:180], "duplicate_of": "", "eligible": a in eligible, "classification_status": a["status"]} for s, a in members],
                           "writing_angles": [(a["title"][:100] + "：保留原文体裁重新组织") for a in eligible[:limit]] or ["素材待核对，暂不写作"]})
    return {"version": "three-genre-v1" if include_review else VERSION, "categories": categories, "assignments": assignments,
            "policy": "按本任务请求区分排行、科普及测评；测评只比较可用资料，不冒充亲测。needs_review为质量状态；儿童素材不用于未核实适用性植入。"}
