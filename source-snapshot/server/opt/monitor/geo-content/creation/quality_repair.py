"""One-shot, evidence-bound revisions of saved articles; no capture/task resume."""
import argparse,concurrent.futures,hashlib,json,shutil,threading,time
from pathlib import Path
from geo_source_cards.runtime import atomic_json,atomic_write,process_lock
from geo_source_cards.consumer_voice import issues
from geo_source_cards.api_prompts import build_prompt
from geo_source_cards.api_worker import materialize
from geo_source_cards.staged_editorial import check,research_for_writer
from geo_source_cards.daily_editorial import finalize,file_hash
from geo_source_cards.deepseek_api import APIError
from geo_source_cards.pipeline_control import event
from . import runtime
from .client import CreationClient

ROOT=runtime.BASE/'quality-repair/20261021-consumer-voice'
STOP=threading.Event()
STOP_ON_UNKNOWN=True
REASON='用户要求修复来源解读式正文。独立重写为消费文章，内部溯源移到附件；原始来源、历史日期、费用、预算和用户暂停保持。'

def writer_for(root,day,category,number):
    candidates=[]
    for p in (root/'queue').glob('*/ticket.json'):
        t=runtime.read(p);m=t.get('meta',{})
        if t.get('stage')=='review' and (m.get('date'),m.get('category'),m.get('number'))==(day,category,number):
            candidates.append((t.get('accepted_at',t.get('created_at','')),root/t['location']))
    if not candidates:raise ValueError('没有对应的原研究与写作执行记录，不能无依据重写')
    return max(candidates,key=lambda x:x[0])[1].parent/'writer'

def scan():
    ROOT.mkdir(parents=True,exist_ok=True);out=ROOT/'inventory.json'
    if out.exists():return runtime.read(out)['articles']
    items=[]
    for root in [runtime.SHARED]+[p.parent for p in sorted((runtime.BASE/'runs').glob('*/job.json'),reverse=True)]:
        for a in runtime.articles(root):
            if a.get('receipt',{}).get('workflow')=='rewrite-v2':continue
            if a.get('quality_status')!='needs_revision':continue
            day,category,num=a['id'].split('/');key=hashlib.sha256((str(root)+'/'+a['id']).encode()).hexdigest()[:24]
            try:writer=writer_for(root,day,category,int(num));research=research_for_writer(writer);error=None
            except ValueError as e:writer=research=None;error=str(e)
            items.append({'key':key,'root':str(root),'id':a['id'],'date':day,'category':category,'number':int(num),'title':a['title'],'original_word_sha256':a['receipt']['word_sha256'],'writer':str(writer) if writer else None,'research':str(research) if research else None,'preflight_error':error})
    atomic_json(out,{'at':time.time(),'reason':REASON,'articles':items})
    return items

def prepare(item,side):
    root=Path(item['root']);folder=root/'approved'/item['id']
    if runtime.read(folder/'receipt.json').get('workflow')=='rewrite-v2':
        raise ValueError('V2文章不能进入旧版段落补丁返修')
    if item.get('preflight_error'):raise ValueError(item['preflight_error'])
    with process_lock(root/'coordinator.lock',blocking=True):
        assert runtime.read(folder/'receipt.json').get('word_sha256')==item['original_word_sha256'],'文章版本已变化'
        active=runtime.read(root/'api/active.json')
        if active.get('state') not in (None,'SUBMITTED'):
            ticket=runtime.read(root/'queue'/active.get('ticket','')/'ticket.json');m=ticket.get('meta',{})
            if (m.get('date'),m.get('category'),m.get('number'))==(item['date'],item['category'],item['number']):raise ValueError('原文章仍有执行请求，保留现场等待')
        writer=Path(item['writer']);research=Path(item['research'])
        base=side/'days'/item['date']/'articles'/item['category']/f"{item['number']:02d}"
        base.mkdir(parents=True,exist_ok=True)
        if not (base/'writer').exists():shutil.copytree(writer,base/'writer')
        if not (base/'research').exists():shutil.copytree(research,base/'research')
        atomic_json(side/'days'/item['date']/'day.json',{'date':item['date'],'status':'isolated_quality_revision'})
        job=runtime.read(root/'job.json') or {'job_id':root.name,'date':item['date']}
        atomic_json(side/'job.json',job)
        if (runtime.SHARED/'settings.json').exists():shutil.copy2(runtime.SHARED/'settings.json',side/'settings.json')
        atomic_write(base/'writer/revision_note.txt',REASON)
        backup=side/'original-approved'
        if not backup.exists():shutil.copytree(folder,backup)
    return base

def reuse_verified_delivery(entry, side, base):
    """Reuse the complete delivered draft, including paid append/revision work."""
    writer=base/'writer'
    candidates=sorted(entry.glob('attempt-*/days/*/articles/*/*/writer'),key=lambda p:p.stat().st_mtime,reverse=True)
    for previous in candidates:
        if side in previous.parents:continue
        if any(not (previous/name).is_file() or file_hash(previous/name)!=file_hash(writer/name) for name in ('knowledge.json','product.json')):continue
        try:
            if check(base/'research',previous)['failures']:continue
        except (ValueError,KeyError,TypeError,FileNotFoundError):continue
        shutil.copytree(previous,writer,dirs_exist_ok=True)
        if check(base/'research',writer)['failures']:raise ValueError('Copied delivery failed verification; no new writer request sent')
        return str(previous/'writer_done.json')
    return None

def revise(item,retry_known=False):
    entry=ROOT/item['key'];entry.mkdir(exist_ok=True);status=entry/'status.json'
    old=runtime.read(status)
    if old.get('state') in {'complete','budget_blocked','unknown_request'}:return old
    if old.get('state')=='needs_attention' and not retry_known:return old
    attempt=old.get('attempt',1)+(1 if old.get('state')=='needs_attention' else 0)
    if any(runtime.read(p).get('state') in {'REQUEST_UNKNOWN','REQUESTING'} and not (p.parent/'response.json').exists() for p in entry.rglob('api_state.json')):
        if STOP_ON_UNKNOWN:STOP.set()
        result={'state':'unknown_request','article':item['id'],'reason':'存在未知API请求，不能重发'}
        atomic_json(status,result);return result
    side=entry/f'attempt-{attempt}';side.mkdir(exist_ok=True)
    budget=None
    try:
        base=prepare(item,side);writer=base/'writer';review=base/'review';review.mkdir(exist_ok=True)
        meta={k:item[k] for k in ('date','category','number')};meta.update(consumer_rewrite=True)
        budget=runtime.SharedBudget(side);client=CreationClient(runtime.KEY,budget=budget)
        def request(stage,location,call,limit):
            atomic_json(status,{'state':stage,'article':item['id'],'at':time.time()})
            if stage=='writer':
                from geo_source_cards.consumer_prompts import require_writer_material,evidence_units
                require_writer_material(runtime.read(location/'knowledge.json'),runtime.read(location/'product.json'),evidence_units(location))
            job={'stage':stage,'meta':meta};prompt=build_prompt(job,location)
            answer=client.complete(prompt,call,max_tokens=limit,stage=stage,meta=meta)
            if stage=='review' and not answer.get('failures') and len(answer.get('checks',{}))==7 and all(answer['checks'].values()):
                answer['logic_review']=client.review_logic(location,call/'logic-call',meta)
            materialize(job,location,answer)
        reused=reuse_verified_delivery(entry,side,base)
        # A known delivered draft may only need canonical heading/count repair.
        # Re-materialize it locally before paying for a fresh writer request.
        candidates=sorted(entry.glob('attempt-*/calls/writer/response.json'),key=lambda p:p.stat().st_mtime,reverse=True)
        candidates += list(entry.glob('calls/writer/response.json'))
        for cached in candidates:
            if reused:break
            previous=cached.parent.parent.parent
            if previous==side:continue
            earlier=list(previous.glob('days/*/articles/*/*/writer/knowledge.json'))
            if len(earlier)!=1 or file_hash(earlier[0])!=file_hash(writer/'knowledge.json') or file_hash(earlier[0].with_name('product.json'))!=file_hash(writer/'product.json'):continue
            try:
                materialize({'stage':'writer','meta':meta},writer,runtime.read(cached))
                report=check(base/'research',writer)
                if not report['failures']:reused=str(cached);break
            except (ValueError,KeyError,TypeError):continue
        if not reused:request('writer',writer,side/'calls/writer',6000)
        report=check(base/'research',writer)
        if report['failures']:
            from geo_source_cards.append_repair import eligible_error,MARKER
            reason='; '.join(report['failures'])
            if not eligible_error(reason):raise ValueError(reason)
            atomic_write(writer/'revision_note.txt',MARKER+'\n'+reason)
            request('writer',writer,side/'calls/length-addition',2400)
            report=check(base/'research',writer)
            if report['failures']:raise ValueError('; '.join(report['failures']))
        for cycle in range(2):
            for name in ('draft.md','knowledge.json','product.json','category.json'):shutil.copy2(writer/name,review/name)
            request('review',review,side/'calls'/('review' if cycle==0 else 'revision-review'),1800)
            try:
                finalize(side,review);break
            except ValueError as error:
                if cycle or not str(error).startswith('Semantic review'):raise
                atomic_write(writer/'revision_note.txt','只修订下列独立审稿指出的真实问题，保留正确内容，不引用旧错误作为事实：\n'+str(error))
                request('writer',writer,side/'calls/semantic-writer',6000)
                report=check(base/'research',writer)
                if report['failures']:raise ValueError('; '.join(report['failures']))
        output=side/'approved'/item['id'];root=Path(item['root']);destination=root/'approved'/item['id']
        with process_lock(root/'coordinator.lock',blocking=True):
            assert runtime.read(destination/'receipt.json').get('word_sha256')==item['original_word_sha256'],'文章在修订期间已变化，修订版保留待核对'
            note={'at':time.time(),'reason':REASON,'original_word_sha256':item['original_word_sha256'],'new_word_sha256':file_hash(output/'article.docx'),'repair_id':item['key'],'evidence_source':'same original research and product evidence; original inputs retained','original_approved_backup':str(side/'original-approved'),'review_draft_sha256':runtime.read(output/'semantic_review.json').get('draft_sha256'),'reused_delivered_writer_response':reused,'paid_requests_recorded':[{ 'stage':p.parent.name,**{k:v for k,v in runtime.read(p).items() if k in {'state','payload_sha256','reservation','started_epoch'}}} for p in (side/'calls').glob('*/api_state.json')],'publication_approved':False}
            atomic_json(output/'content_revision.json',note)
            receipt=runtime.read(output/'receipt.json');receipt['files']['content_revision.json']=file_hash(output/'content_revision.json');receipt['content_revision']='consumer-voice-v1';atomic_json(output/'receipt.json',receipt)
            replacement=destination.with_name(destination.name+'.quality-new');assert not replacement.exists()
            shutil.copytree(output,replacement)
            retired=side/'replaced-approved';assert not retired.exists()
            shutil.move(str(destination),retired);replacement.rename(destination)
            event(root,'content_revision','正文已独立重写并重新审稿，溯源单独保留，预算未提高',category=item['category'],number=item['number'],repair_id=item['key'])
        result={'state':'complete','article':item['id'],'at':time.time(),'new_word_sha256':note['new_word_sha256']}
    except APIError as error:
        result={'state':'unknown_request' if error.uncertain else 'budget_blocked' if error.code=='budget_exceeded' else 'needs_attention','article':item['id'],'at':time.time(),'reason':error.code}
        if error.uncertain and STOP_ON_UNKNOWN:STOP.set()
    except Exception as error:
        result={'state':'needs_attention','article':item['id'],'at':time.time(),'reason':str(error)[:1600]}
    finally:
        if budget:budget.db.close()
    result['attempt']=attempt
    atomic_json(status,result);return result

def main():
    global STOP_ON_UNKNOWN
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true');parser.add_argument('--limit',type=int,default=0);parser.add_argument('--retry-known-failures',action='store_true')
    parser.add_argument('--continue-pending',action='store_true',help='Only untouched or maintenance-held articles; quarantine unresolved requests without replay')
    parser.add_argument('--workers',type=int,choices=(1,2),default=2);args=parser.parse_args()
    with process_lock(ROOT/'process.lock',blocking=False):
        items=scan()
        items.sort(key=lambda x:(x['date'],x['root']!=str(runtime.SHARED),x['category']=='科普类'),reverse=True)
        if args.continue_pending:
            assert not args.retry_known_failures,'Pending continuation must not retry failed API work'
            STOP_ON_UNKNOWN=False
            items=[i for i in items if not runtime.read(ROOT/i['key']/'status.json') or runtime.read(ROOT/i['key']/'status.json').get('reason')=='consumer_contract_maintenance']
        if args.limit:items=items[:args.limit]
        if args.run:
            # Independent article calls share the transactional original ledger.
            with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
                def process(item):
                    if STOP.is_set():return {'state':'waiting_unknown_reconciliation'}
                    return revise(item,args.retry_known_failures or args.continue_pending)
                for result in pool.map(process,items):print(json.dumps(result,ensure_ascii=False),flush=True)
        states={}
        for item in scan():
            state=runtime.read(ROOT/item['key']/'status.json').get('state','pending');states[state]=states.get(state,0)+1
        atomic_json(ROOT/'summary.json',{'at':time.time(),'total':len(scan()),'states':states,'unknown_requests_never_replayed':True,'user_task_controls_unchanged':True})
        print(json.dumps(states,ensure_ascii=False))

if __name__=='__main__':main()
