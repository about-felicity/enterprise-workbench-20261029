"""Durable GEO creation jobs, reusing the original evidence/review/Word engine."""
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import time
import uuid
from contextlib import closing

from geo_source_cards import daily_editorial, pipeline_control
from geo_source_cards.api_budget import Budget,BudgetExceeded,ArticleBudgetExceeded
from geo_source_cards.deepseek_api import DeepSeekClient
from geo_source_cards.runtime import atomic_json, atomic_write, process_lock
from . import source_adapter
from .client import CreationClient

BASE=Path(os.environ.get('GEO_CREATION_ROOT','/opt/monitor/geo-content/runtime'))
SHARED=Path('/home/user/geo-editorial/runtime-api')
KEY=Path('/home/user/geo-editorial/secrets/deepseek.key')
CONTENT=Path('/opt/monitor/doubao_source_content.db')

def read(path,default=None):
    try:return json.loads(Path(path).read_text('utf-8-sig'))
    except FileNotFoundError:return {} if default is None else default

def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def db():
    BASE.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(BASE/'operations.sqlite',timeout=30)
    conn.execute('pragma journal_mode=WAL')
    conn.execute('pragma synchronous=FULL')
    conn.execute('create table if not exists operations(id text primary key,payload_hash text,result text)')
    return conn

def job_root(identity):
    if not re.fullmatch(r'creation-[0-9]+-[a-f0-9]{8}',identity):raise ValueError('任务编号不正确')
    path=BASE/'runs'/identity
    if not (path/'job.json').is_file():raise ValueError('任务不存在')
    return path

class SharedBudget(Budget):
    def __init__(self,root):
        super().__init__(SHARED)
        self.root=Path(root)  # pause/call logs belong to this job; ledger stays canonical.

    def remaining(self,meta,stage):
        job=read(self.root/'job.json');limits=job.get('budget_limits') or {}
        if not limits:return None
        from datetime import datetime
        from geo_source_cards.api_budget import BEIJING
        config=pipeline_control.settings(SHARED);scope=job.get('studio_plan_id') or job['job_id']
        category=meta.get('category','');article=str(meta.get('number',0))
        try:
            joined='select coalesce(sum(coalesce(c.charged,c.reserved)),0) from costs c join studio_cost_scopes s on s.id=c.id where '
            daily=self.db.execute('select coalesce(sum(coalesce(charged,reserved)),0) from costs where date=?',(datetime.now(BEIJING).date().isoformat(),)).fetchone()[0]
            used=self.db.execute(joined+'s.scope=? and s.task_day=?',(scope,job['date'])).fetchone()[0]
            per=self.db.execute(joined+"s.job=? and (c.category='' or (c.category=? and (c.article='shared' or c.article=?)))",(job['job_id'],category,article)).fetchone()[0]
        except sqlite3.OperationalError:return None
        return max(0,min(config['daily_budget_cny']-daily,limits['task_budget_cny']-used,
                         min(limits['article_budget_cny'],config['article_budget_cny'])-per))

    def reserve(self,payload,directory,meta,stage):
        job=read(self.root/'job.json');limits=job.get('budget_limits') or {}
        if not limits:return super().reserve(payload,directory,meta,stage)
        from datetime import datetime
        from geo_source_cards.api_budget import PRICE_DATE,INPUT_MISS,OUTPUT,BEIJING
        if (datetime.now(BEIJING).date()-datetime.fromisoformat(PRICE_DATE).date()).days>30:
            raise BudgetExceeded('Budget price version requires review')
        upper=(len(json.dumps(payload['messages'],ensure_ascii=False).encode('utf8'))+256)*INPUT_MISS/1000000+payload['max_tokens']*OUTPUT/1000000
        config=pipeline_control.settings(SHARED);identity=hashlib.sha256(str(Path(directory).resolve()).encode()).hexdigest()
        scope=job.get('studio_plan_id') or job['job_id'];category=meta.get('category','')
        article='shared' if stage=='taxonomy' or stage=='research' and meta.get('cost_scope')!='article' else str(meta.get('number',0))
        date=datetime.now(BEIJING).date().isoformat()
        self.db.execute('create table if not exists studio_cost_scopes(id text primary key,scope text,task_day text,job text)')
        self.db.execute('begin immediate')
        try:
            previous=self.db.execute('select state,charged from costs where id=?',(identity,)).fetchone()
            if previous:
                if previous['state']=='settled' and previous['charged']==0:
                    archived=identity+'-rejected-'+str(time.time_ns())
                    self.db.execute('update costs set id=? where id=?',(archived,identity))
                    self.db.execute('update studio_cost_scopes set id=? where id=?',(archived,identity))
                else:raise BudgetExceeded('Existing reservation requires execution review')
            total='select coalesce(sum(coalesce(charged,reserved)),0) from costs where '
            daily=self.db.execute(total+'date=?',(date,)).fetchone()[0]
            joined='select coalesce(sum(coalesce(c.charged,c.reserved)),0) from costs c join studio_cost_scopes s on s.id=c.id where '
            used=self.db.execute(joined+'s.scope=? and s.task_day=?',(scope,job['date'])).fetchone()[0]
            per=self.db.execute(joined+"s.job=? and (c.category='' or (c.category=? and (c.article='shared' or c.article=?)))",(job['job_id'],category,article)).fetchone()[0]
            if daily+upper>config['daily_budget_cny']+1e-9 or used+upper>limits['task_budget_cny']+1e-9:
                raise BudgetExceeded('Creation budget exhausted; request was not sent')
            if per+upper>min(limits['article_budget_cny'],config['article_budget_cny'])+1e-9:
                raise ArticleBudgetExceeded('Article budget exhausted; request was not sent')
            self.db.execute('insert into costs values(?,?,?,?,?,?,?,?,?,?,?,?)',(identity,date,meta['date'],category,article,stage,0,'reserved',upper,None,None,time.time()))
            self.db.execute('insert into studio_cost_scopes values(?,?,?,?)',(identity,scope,job['date'],job['job_id']))
            self.db.commit()
        except BaseException:
            self.db.rollback();raise
        return identity


def balance():return CreationClient(KEY).balance()

def resume(root,*,check_balance=True):
    assert_job_controllable(root)
    if check_balance:
        checked=balance()
        if not checked['is_available']:raise ValueError('DeepSeek API余额不可用')
    with process_lock(root/'control.lock',blocking=True):
        old=pipeline_control.state(root)
        # Do not replay a request with unknown delivery, even after operator resume.
        active=read(root/'api/active.json')
        if active.get('state')=='REQUESTING':
            call=read(root/'api/runs'/active['run_id']/'call/api_state.json')
            if call.get('state') in {'REQUEST_UNKNOWN','REQUESTING'} and not (root/'api/runs'/active['run_id']/'call/response.json').is_file():
                raise ValueError('存在发送结果未知的API请求，须先核对；不会自动重发')
        atomic_json(root/'environment_check.json',{'checked_epoch':time.time(),'ready':True,
            'control_revision':old.get('revision',0),'source':'GEO existing data + DeepSeek API only'})
        atomic_json(root/'control.json',{'paused':False,'revision':old.get('revision',0)+1,
            'resumed_epoch':time.time()})
    return {'resumed':True}

def create(payload):
    day=payload.get('date','');question=payload.get('question','')
    channels=payload.get('channels',['deepseek','wenxin_card','baidu_ai'])
    limit=payload.get('max_per_category',10)
    if type(limit) is not int or not 1<=limit<=10:raise ValueError('每类篇数须为1至10')
    product=payload.get('product') or read(SHARED/'product.json')
    if not isinstance(product,dict) or not product.get('name') or not isinstance(product.get('facts'),list):
        raise ValueError('请填写原有格式的产品事实资料')
    private=payload.get('material_source')=='dedicated'
    studio_plan=payload.get('studio_plan_id')
    if studio_plan:
        from . import studio
        studio.plan(studio_plan) # Reject stale scheduler snapshots after deletion.
        snapshot=read(studio.day_path(studio_plan,day)).get('plan') or studio.plan(studio_plan)
        product=studio.complete_product_source(product,snapshot.get('product_id'),snapshot.get('product_version'))
    pooled_questions=payload.get('questions')
    article_target=payload.get('article_target',0)
    if pooled_questions is not None:
        if not private or not studio_plan or not isinstance(pooled_questions,list) or not pooled_questions or len(pooled_questions)>100 or any(not isinstance(q,str) or not q.strip() for q in pooled_questions) or len(set(pooled_questions))!=len(pooled_questions):raise ValueError('任务汇总问题不正确')
        if type(article_target) is not int or not 1<=article_target<=100:raise ValueError('请设置1至100篇的任务成稿目标')
    if private:
        from . import materials
        if studio_plan:
            from . import studio
            if read(studio.day_path(studio_plan,day)).get('paused'):raise ValueError('当日创作任务已暂停')
            if pooled_questions is not None:
                confirmed=read(studio.day_path(studio_plan,day)).get('plan') or studio.plan(studio_plan)
                if pooled_questions!=confirmed['questions'] or article_target!=confirmed.get('article_target'):raise ValueError('汇总须使用当天已确认的问题和篇数')
                rows=[];seen=set()
                for q in pooled_questions:
                    for row in materials.records(day,q,channels,store_root=studio.capture_root(studio_plan)):
                        key=digest(row)
                        if key not in seen:rows.append(row);seen.add(key)
            else:rows=materials.records(day,question,channels,store_root=studio.capture_root(studio_plan))
        else:rows=materials.records(day,question,channels)
        if not rows:raise ValueError('所选专用问题尚无采集素材，请选择已有素材日期或等待凌晨专用采集')
        material={'observations':rows,'counts':{'private_observations':len(rows),'full_articles':0},'source':'creation_only'}
    else:
        rows=source_adapter.observations(day,question,channels)
        material=source_adapter.snapshot(rows,CONTENT)
        if material['counts']['full_articles']<3:raise ValueError('该日期问题不足3篇已通过完整正文校验的国内媒体素材，请更换日期或等待正文入库')
    inputs={'workflow':'rewrite-v2','date':day,'question':question,'channels':sorted(channels),'max_per_category':limit,
        'product':product,'observations':material['observations']}
    if private:inputs['material_source']='dedicated'
    if studio_plan:inputs['studio_plan_id']=studio_plan
    if pooled_questions is not None:
        from geo_source_cards.article_allocation import validate_quotas
        inputs.update(questions=pooled_questions,article_target=article_target,genre_targets=validate_quotas(payload.get('genre_targets'),article_target))
    if payload.get('budget_limits'):
        import math
        limits=payload['budget_limits'];shared=pipeline_control.settings(SHARED)
        if not isinstance(limits,dict) or set(limits)!={'article_budget_cny','task_budget_cny'} or any(type(v) not in (int,float) or not math.isfinite(v) or v<=0 for v in limits.values()) or limits['article_budget_cny']>shared['article_budget_cny'] or limits['task_budget_cny']>shared['daily_budget_cny']:
            raise ValueError('任务预算设置不正确或超过共享限额')
        inputs['budget_limits']=limits
    fingerprint=digest(inputs)
    for path in sorted((BASE/'runs').glob('*/job.json')):
        previous=read(path)
        if previous.get('input_sha256')==fingerprint:return {'job_id':previous['job_id'],'reused':True}
    identity='creation-'+str(int(time.time()))+'-'+uuid.uuid4().hex[:8]
    root=BASE/'runs'/identity;root.mkdir(parents=True,exist_ok=False)
    defaults=read(BASE/'rewrite_defaults.json')
    automatic=defaults.get('skeleton_review')=='automatic' and isinstance(defaults.get('authorization'),str) and defaults['authorization'].strip()
    atomic_json(root/'rewrite_policy.json',{'workflow':'rewrite-v2','cache_dir':str(BASE/'rewrite_cache'),'max_rewrites':1,
        'review_policy':'evidence-v3','max_targeted_repairs':2,
        **({'skeleton_review':'automatic','authorization':defaults['authorization']} if automatic else {})})
    atomic_json(root/'control.json',{'paused':True,'revision':0,'reason':'preparing','message':'准备GEO素材'})
    atomic_json(root/'settings.json',{**pipeline_control.settings(SHARED),'max_per_category':limit})
    atomic_json(root/'product.json',product)
    atomic_json(root/'geo_material_manifest.json',material)
    atomic_write(root/'geo_articles.jsonl',''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in material['observations']))
    if private:
        atomic_write(root/'private_observations.jsonl',''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
        prepared={'status':'waiting_material_preparation'}
    else:prepared=daily_editorial.prepare_day(root,root/'geo_articles.jsonl',root/'product.json',day,max_per_category=limit)
    atomic_json(root/'job.json',{'workflow':'rewrite-v2','job_id':identity,'created_at':time.time(),'input_sha256':fingerprint,
        'date':day,'question':question,'channels':sorted(channels),'max_per_category':limit,
        'material_counts':material['counts'],'platform_questions_sent':0,'prepared':prepared,
        'material_source':'dedicated' if private else 'geo','studio_plan_id':studio_plan,'task_name':str(payload.get('task_name') or product['name']+'创作任务')[:120],'budget_limits':inputs.get('budget_limits',{}),'preparation':'pending' if private else 'ready',**({'questions':pooled_questions,'article_target':article_target,'genre_targets':inputs['genre_targets']} if pooled_questions is not None else {})})
    from geo_source_cards.article_logic import VERSION
    atomic_json(root/'logic_policy.json',{'required':True,'version':'rewrite-v2'})
    # Paid calls check balance and reserve transactionally in their worker.
    # Keep network waits outside the global creation lock.
    resume(root,check_balance=False)
    return {'job_id':identity,'reused':False}

def action(name,payload,operation_id):
    if not re.fullmatch(r'[a-f0-9]{32}',operation_id):raise ValueError('操作编号不正确')
    signature=digest({'action':name,'payload':payload})
    # One global lock across HTTP mutations avoids duplicate preparation / paid job creation.
    with process_lock(BASE/'actions.lock',blocking=True):
        with closing(db()) as conn, conn:
            old=conn.execute('select payload_hash,result from operations where id=?',(operation_id,)).fetchone()
            if old:
                if old[0]!=signature:raise ValueError('重复操作编号对应不同内容')
                return json.loads(old[1])
            if name=='new':result=create(payload)
            elif name=='balance':result=balance()
            elif name in {'skeleton_inspect','skeleton_approve'}:
                from geo_source_cards.rewrite_v2.common import cache_root
                from geo_source_cards.rewrite_v2 import structure_parser,integration
                root=job_root(payload.get('job_id',''))
                if read(root/'rewrite_policy.json').get('workflow')!='rewrite-v2':raise ValueError('该历史任务不使用V2骨架')
                cache=cache_root(root)
                if name=='skeleton_inspect':
                    keys={t.get('waiting_skeleton') for p in (root/'queue').glob('*/ticket.json') if (t:=read(p)).get('waiting_skeleton')}
                    result=[read(cache/'skeleton'/(key+'.json')) for key in sorted(keys)]
                else:
                    with process_lock(root/'coordinator.lock',blocking=True):
                        result=structure_parser.approve(cache,payload.get('key',''),payload.get('expected_sha256',''),payload.get('reviewer',''),skeleton=payload.get('skeleton'))
                        integration.sync_approvals(root)
            elif name=='product_image_upload':
                from . import product_images
                result=product_images.upload(payload)
            elif name in {'kb_upload','kb_publish','kb_edit'}:
                from . import knowledge_library
                result={'kb_upload':knowledge_library.upload,'kb_publish':knowledge_library.publish,'kb_edit':knowledge_library.edit}[name](payload)
            elif name in {'kb_import','kb_save','plan_save','plan_delete','day_pause','day_resume'}:
                from . import studio
                result={'kb_import':studio.import_word,'kb_save':studio.save_product,'plan_save':studio.save_plan,'plan_delete':studio.delete_plan,'day_pause':lambda v:studio.day_control(v,True),'day_resume':lambda v:studio.day_control(v,False)}[name](payload)
            elif name=='materials_settings':
                from .materials import save
                result=save(payload)
            elif name in {'materials_pause','materials_resume'}:
                from .materials import control
                result=control('pause' if name=='materials_pause' else 'resume')
            elif name in {'pause','resume'}:
                root=job_root(payload.get('job_id',''))
                assert_job_controllable(root)
                result=pipeline_control.pause(root,'operator','用户请求排空暂停；已发送API保留收尾') if name=='pause' else resume(root)
            else:raise ValueError('操作不存在')
            conn.execute('insert into operations values(?,?,?)',(operation_id,signature,json.dumps(result,ensure_ascii=False)))
            return result

def assert_job_controllable(root):
    from . import studio
    job=read(root/'job.json')
    if job.get('studio_plan_id'):studio.plan(job['studio_plan_id'])
    if read(root/'days'/job.get('date','')/'day.json').get('status') in studio.TERMINAL_JOBS:
        raise ValueError('本次执行已结束，不能暂停或继续；请查看已有成稿')

def product_label(root,day):
    """Use the archived daily product, never today's mutable legacy input."""
    path=root/'days'/day/'product.json'
    product=read(path) if path.is_file() else read(root/'product.json') if root!=SHARED else {}
    name=str(product.get('name') or '').strip();brand=str(product.get('brand') or '').strip()
    return {'id':digest({'name':name,'brand':brand}) if name else 'unknown','name':name or '未标注产品','brand':brand}

def articles(root):
    result=[]
    revoked={read(p).get('word_sha256') for p in (root/'revocations').glob('*.json')}
    for path in sorted((root/'approved').glob('*/*/*/receipt.json')):
        receipt=read(path);folder=path.parent
        draft=folder/'draft.md';word=folder/'article.docx'
        if receipt.get('status')!='accepted_for_user_review' or receipt.get('word_sha256') in revoked:continue
        files=receipt.get('files',{})
        if not files.get('draft.md') or not files.get('article.docx'):continue
        valid=True
        for name,expected in files.items():
            file=folder/name
            if Path(name).name!=name or file.is_symlink() or not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=expected:
                valid=False;break
        if not valid:continue
        # Only original approved receipt directories are downloadable.
        from .article_export import info
        metadata=info(root,folder)
        from geo_source_cards.consumer_voice import issues as voice_issues
        quality_issues=[] if receipt.get('workflow')=='rewrite-v2' else voice_issues(draft.read_text('utf8'))
        if receipt.get('workflow')=='rewrite-v2':
            from geo_source_cards.rewrite_v2.quality_reviewer import verify_final
            try:
                verify_final(read(folder/'semantic_review.json'),read(folder/'rewrite_context.json'),read(folder/'rewrite_material.json'),draft.read_text('utf8'))
            except (ValueError,KeyError,TypeError) as error:quality_issues.append('V2审核尚未通过：'+str(error)[:350])
        elif read(root/'logic_policy.json').get('required'):
            from geo_source_cards.article_logic import enforce
            try:
                product=read(folder/'logic_product.json') if (folder/'logic_product.json').exists() else read(root/'days'/folder.parent.parent.name/'product.json')
                semantic=read(folder/'semantic_review.json');arb=None
                if semantic.get('arbitration'):
                    from geo_source_cards.review_arbitration import enforce as enforce_arbitration
                    from geo_source_cards.article_compiler import verify_inputs
                    knowledge=semantic['arbitration']['input']['knowledge']
                    verify_inputs(read(folder/'compilation.json'),knowledge,product)
                    arb=enforce_arbitration(semantic,draft.read_text('utf8'),knowledge,product)
                enforce(read(folder/'logic_review.json'),draft.read_text('utf8'),product,arbitration=arb)
            except (ValueError,KeyError,TypeError) as error:quality_issues.append('全文逻辑尚未通过复核：'+str(error)[:350])
        result.append({'id':folder.relative_to(root/'approved').as_posix(),'date':folder.parent.parent.name,'product':product_label(root,folder.parent.parent.name),'title':draft.read_text('utf8').splitlines()[0].lstrip('# ') if draft.is_file() else folder.name,
            'quality_status':'needs_revision' if quality_issues else 'ready_with_disputes' if receipt.get('quality_status')=='ready_with_disputes' or receipt.get('logic_status')=='needs_revision' else 'ready','quality_issues':quality_issues,
            'review_disputes':receipt.get('review_disputes',[]),
            'markdown':draft.is_file(),'word':word.is_file(),'receipt':receipt,'task_name':metadata['task_name'],'category':metadata['category'],'primary_reference':metadata['primary_reference']})
    return result

def status():
    jobs=[]
    for path in sorted((BASE/'runs').glob('*/job.json'),reverse=True):
        root=path.parent;job=read(path);tickets=[read(p) for p in (root/'queue').glob('*/ticket.json')]
        counts={}
        for ticket in tickets:
            key=ticket.get('stage','')+':'+ticket.get('state','');counts[key]=counts.get(key,0)+1
        day=read(root/'days'/job['date']/'day.json')
        from .editorial_status import blocks,execution_health
        health=execution_health(root,tickets,day)
        jobs.append({**job,'quality_blocks':blocks(root,tickets),'product':product_label(root,job['date']),'control':pipeline_control.state(root),'health':health,
            'worker':read(root/'geo_worker.json'),'queue':counts,'articles':articles(root),
            'day':day})
    legacy=articles(SHARED)
    from . import materials
    from . import studio
    return {'ok':True,'at':time.time(),'jobs':jobs,'settings':pipeline_control.settings(SHARED),
            'legacy_articles':legacy,'materials':materials.status(),'studio':studio.snapshot(jobs),
            'legacy_approved_articles':len(list((SHARED/'approved').glob('*/*/*/receipt.json'))),
            'source':'专用素材独立保存；可选择只读GEO已有素材','worker':read(BASE/'worker_health.json')}

def download(identity,article_id,kind,filters=None):
    root=SHARED if identity=='legacy-original' else None if identity=='all-approved' else job_root(identity)
    if kind in {'bundle','package'}:
        import zipfile
        filters=filters or {};date=filters.get('date','');product=filters.get('product','');source=filters.get('source','all');search=filters.get('search','')
        if date and not re.fullmatch(r'\d{4}-\d{2}-\d{2}',date):raise ValueError('筛选日期不正确')
        if product and product!='unknown' and not re.fullmatch(r'[a-f0-9]{64}',product):raise ValueError('筛选产品不正确')
        if source not in {'all','new','legacy-original'} or not isinstance(search,str) or len(search)>200:raise ValueError('筛选条件不正确')
        plan=filters.get('plan','')
        if plan and not re.fullmatch(r'plan-[a-f0-9]{32}',plan):raise ValueError('任务筛选不正确')
        if kind=='package' and (root is None or article_id not in {a['id'] for a in articles(root)}):raise ValueError('请选择有效成稿')
        suffix='-'+digest({'filters':filters,'article':article_id if kind=='package' else ''})[:24]
        path=BASE/'exports'/(identity+suffix+'.zip');path.parent.mkdir(parents=True,exist_ok=True)
        temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
        roots=[SHARED]+[p.parent for p in (BASE/'runs').glob('*/job.json')] if root is None else [root]
        from .article_export import write_article
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as archive:
            manifest=[]
            for current in roots:
                if source=='new' and current==SHARED or source=='legacy-original' and current!=SHARED:continue
                if plan and read(current/'job.json').get('studio_plan_id')!=plan:continue
                for item in articles(current):
                    if item.get('quality_status')=='needs_revision':continue
                    if kind=='package' and item['id']!=article_id:continue
                    if date and item['date']!=date or product and item['product']['id']!=product or search.strip().lower() not in item['title'].lower():continue
                    folder=current/'approved'/item['id']
                    if current.resolve() not in folder.resolve().parents:raise ValueError('成稿路径不正确')
                    manifest.append(write_article(archive,current,item))
            archive.writestr('导出清单.json',json.dumps({'articles':manifest,'count':len(manifest)},ensure_ascii=False,indent=2))
        temporary.replace(path)
        with zipfile.ZipFile(path) as checked:
            if checked.testzip() is not None:raise ValueError('压缩包完整性检查失败，请重新下载')
            if not json.loads(checked.read('导出清单.json')).get('count'):raise ValueError('当前筛选没有可下载的成稿，请调整筛选后重试')
        return path
    if root is None:raise ValueError('请选择成稿')
    if kind not in {'markdown','word','info'}:raise ValueError('文件类型不正确')
    if not re.fullmatch(r'[^/\\.][^/\\]*/[^/\\.][^/\\]*/[^/\\.][^/\\]*',article_id):raise ValueError('成稿编号不正确')
    folder=(root/'approved'/article_id).resolve()
    if root.resolve() not in folder.parents or not (folder/'receipt.json').is_file():raise ValueError('成稿不存在')
    available={a['id']:a for a in articles(root)}
    if article_id not in available:raise ValueError('成稿已撤回或文件校验未通过，不作为可下载成稿')
    if kind!='info' and available[article_id].get('quality_status')=='needs_revision':raise ValueError('这篇旧稿未通过正文质量复核，已停止下载，修订通过后恢复')
    if kind=='info':
        from .article_export import info,describe,logs
        metadata=info(root,folder);path=BASE/'exports'/('info-'+digest([identity,article_id])[:24]+'.md')
        atomic_write(path,describe(metadata)+'\n## 执行日志\n\n```json\n'+json.dumps(logs(root,metadata),ensure_ascii=False,indent=2)+'\n```\n')
        return path
    path=folder/('draft.md' if kind=='markdown' else 'article.docx')
    if not path.is_file():raise ValueError('文件不存在')
    return path
