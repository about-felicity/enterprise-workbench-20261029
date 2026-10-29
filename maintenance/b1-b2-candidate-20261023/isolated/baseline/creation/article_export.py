"""Readable, verifiable article provenance and task/date export packages."""
import hashlib,json,re,threading
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit
from . import runtime


def safe(value):
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',str(value)).strip(' .')[:80] or '未命名'

_metadata_lock=threading.RLock()

def _signature(path):
    try:
        s=path.stat();return s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns
    except FileNotFoundError:return None

@lru_cache(maxsize=64)
def _source_index(path,signature):
    """Cache small source metadata, never retain every captured full article."""
    candidates=runtime.read(path,[])
    if isinstance(candidates,dict):candidates=candidates.get('sources',candidates.get('articles',[]))
    index={}
    for source in candidates:
        article=source.get('article') or {};meta=article.get('metadata') or {}
        item={k:source[k] for k in ('media_registry_name','author') if k in source}
        item['article']={k:article[k] for k in ('site_name','author','published_at','publish_time','official_account_verified') if k in article}
        item['article']['metadata']={k:meta[k] for k in ('publisher','author','published_at') if k in meta}
        for url in (source.get('url'),article.get('final_url')):
            if url:index.setdefault(url,item)
    return index


def info(root,folder):
    root,folder=Path(root),Path(folder)
    relative=folder.relative_to(root/'approved');day,category,number=relative.parts
    provenance=runtime.read(folder/'provenance.json');primary=provenance.get('primary_reference') or {}
    url=primary.get('primary_url','');raw_title=primary.get('primary_title','')
    # Legacy provenance may contain explicit nulls; missing metadata must not
    # take down the entire article library or turn null into a fabricated title.
    url=url if isinstance(url,str) else ''
    title=raw_title if isinstance(raw_title,str) else ''
    if urlsplit(url).scheme not in {'http','https'}:url=''
    source_path=root/'days'/day/'sources.json'
    if not source_path.exists():source_path=root/'days'/day/'media_articles.json'
    with _metadata_lock:source=_source_index(source_path,_signature(source_path)).get(url,{})
    article=source.get('article') or {}
    captured_meta=article.get('metadata') or {}
    title=re.sub(r'(?:icon_voice(?:_on)?)+$','',title).strip()
    host=urlsplit(url).hostname or ''
    from geo_source_cards.daily_editorial import DEFAULT_MEDIA,media_identity
    job=runtime.read(root/'job.json');product=runtime.product_label(root,day)
    question=job.get('question','')
    if job.get('questions'):
        related=[]
        observations=root/'private_observations.jsonl'
        if observations.exists():
            for line in observations.read_text().splitlines():
                if not line.strip():continue
                row=json.loads(line)
                if any(s.get('url')==url or s.get('article',{}).get('final_url')==url for s in row.get('sources',[])) and row.get('question') not in related:related.append(row['question'])
        question='；'.join(related or job['questions'])
    # A platform domain does not prove that an author is an official account.
    return {'task_name':job.get('task_name') or product['name']+'历史创作任务',
            'task_id':job.get('studio_plan_id') or job.get('job_id') or 'legacy-original',
            'job_id':job.get('job_id') or 'legacy-original','task_date':day,
            'question':question,'configured_questions':job.get('questions',[]),'product':product,'category':category,'number':number,
            'primary_reference':{'url':url,'title':title,'raw_title':raw_title,'domain':host,
              'media':source.get('media_registry_name') or article.get('site_name') or captured_meta.get('publisher') or media_identity(url,DEFAULT_MEDIA) or '未标注',
              'author':article.get('author') or source.get('author') or captured_meta.get('author') or '原素材未提供',
              'published_at':article.get('published_at') or article.get('publish_time') or captured_meta.get('published_at') or '原素材未提供',
              'official_account':'已核实' if article.get('official_account_verified') is True else '未核实，不根据域名推断'},
            'reference_urls':runtime.read(folder/'category.json').get('source_urls',[]),
            'review_status':runtime.read(folder/'receipt.json').get('status'),
            'files':runtime.read(folder/'receipt.json').get('files',{})}


def logs(root,metadata):
    events=[]
    for path in sorted((Path(root)/'logs').glob('*.jsonl')):
        for line in path.read_text(encoding='utf8').splitlines():
            try:event=json.loads(line)
            except ValueError:continue
            if event.get('category') not in (None,'',metadata['category']):continue
            if event.get('number') not in (None,0,metadata['number'],int(metadata['number']) if metadata['number'].isdigit() else -1):continue
            events.append({k:v for k,v in event.items() if k in {'at','time','epoch','phase','message','category','number','stage','state','cost_cny','request_id'}})
    tickets=[]
    for path in sorted((Path(root)/'queue').glob('*/ticket.json')):
        ticket=runtime.read(path);meta=ticket.get('meta',{})
        if meta.get('category') not in (None,'',metadata['category']):continue
        if meta.get('number') not in (None,0,int(metadata['number']) if metadata['number'].isdigit() else -1):continue
        tickets.append({k:ticket[k] for k in ('id','stage','state','created_at','updated_at') if k in ticket})
    return {'scope':'本篇各阶段及共享分析的已有日志，不补造历史事件','events':events,'tickets':tickets}


def describe(metadata):
    p=metadata['primary_reference']
    return '\n'.join(['# 文章信息与溯源','',f"任务：{metadata['task_name']}",f"任务日期：{metadata['task_date']}",
      f"文章种类：{metadata['category']}",f"对应问题：{metadata['question'] or '历史任务未标注'}",'',
      '## 仿写参考原文',f"原文标题：{p['title'] or '原记录未提供'}",f"原文链接：{p['url'] or '原记录未提供'}",
      f"发布域名：{p['domain'] or '原记录未提供'}",f"媒体或平台：{p['media']}",f"作者或账号：{p['author']}",
      f"官号认证：{p['official_account']}",f"原文发布时间：{p['published_at']}",'',
      '## 质量与执行记录',f"审稿状态：{metadata['review_status']}",f"任务编号：{metadata['task_id']}",
      '完整执行记录见 执行日志.json；事实映射、原文依据和审核记录见 审核与溯源 目录。',
      '原文作为体裁、主题和证据参考，文章须独立表述；缺失的作者、日期或账号身份不作推断。',''])


def write_article(archive,root,item):
    folder=Path(root)/'approved'/item['id'];m=info(root,folder)
    suffix=hashlib.sha256((str(root)+item['id']).encode()).hexdigest()[:8]
    base=f"{safe(m['task_name'])}_{m['task_date']}/{safe(m['category'])}/{safe(m['number']+'_'+item['title'])}_{suffix}"
    for name,new in [('draft.md',item['title']+'.md'),('article.docx',item['title']+'.docx')]:
        archive.write(folder/name,base+'/'+safe(Path(new).stem)+Path(new).suffix)
    archive.writestr(base+'/文章信息.md',describe(m))
    archive.writestr(base+'/文章信息.json',json.dumps(m,ensure_ascii=False,indent=2))
    archive.writestr(base+'/执行日志.json',json.dumps(logs(root,m),ensure_ascii=False,indent=2))
    for name in ('receipt.json','provenance.json','claim_map.json','knowledge_to_sections.json','semantic_review.json','category.json','formatting_revision.json','content_revision.json','consumer_projection.json','document_projection.json','product_detail_review.json','validation_identity.json','logic_review.json','logic_product.json'):
        file=folder/name
        if file.is_file():archive.write(file,base+'/审核与溯源/'+name)
    for path in (Path(root)/'queue').glob('*/ticket.json'):
        ticket=runtime.read(path);meta=ticket.get('meta',{})
        if ticket.get('stage')!='research' or ticket.get('state')!='accepted' or meta.get('date')!=m['task_date'] or meta.get('category')!=m['category'] or str(meta.get('number','')).zfill(2)!=m['number']:continue
        run_id=ticket.get('execution',{}).get('run_id','')
        if not re.fullmatch(r'[a-f0-9]{24}',run_id):continue
        projection=Path(root)/'api/runs'/run_id/'research_projection.json'
        if projection.is_file():archive.write(projection,base+'/审核与溯源/研究知识投影_'+ticket['id']+'.json')
    return {'directory':base,'task':m['task_name'],'date':m['task_date'],'title':item['title'],'category':m['category'],'primary_reference':m['primary_reference'],'file_hashes':m['files']}
