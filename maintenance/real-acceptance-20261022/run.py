"""Two authorized real versions, same billing scope, isolated from batch workers."""
import hashlib,json,shutil,sqlite3,sys,time,traceback
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from creation.client import CreationClient
from geo_source_cards.runtime import atomic_json,process_lock
from geo_source_cards.daily_editorial import publish_ticket
from geo_source_cards.api_worker import Worker
from geo_source_cards.pipeline_control import pause

ROOT=runtime.BASE/'acceptance/20261022-three-agent'
ORIGINAL=runtime.job_root('creation-1792575159-0a8f9221')
DAY='2026-10-21'
INPUTS=['writing_prompt.md','writing_job.json','knowledge.json','product.json','writing_task.txt','category.json','batch_rules.md']
SELECTED=[('测评类',2),('排行类',1)]

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def originals():
    paths=[ORIGINAL/'job.json',ORIGINAL/'control.json']
    for c,n in SELECTED:paths+=list((ORIGINAL/f'days/{DAY}/compiler-pilots/{c}/{n:02d}').rglob('*'))
    return {str(p):sha(p) for p in paths if p.is_file()}
def ledger():
    con=sqlite3.connect('file:'+str(runtime.SHARED/'api/costs.sqlite')+'?mode=ro',uri=True)
    con.row_factory=sqlite3.Row
    rows=[dict(r) for r in con.execute('select * from costs')]
    con.close()
    return {'count':len(rows),'used':sum(r['charged'] if r['charged'] is not None else r['reserved'] for r in rows),'unknown':[r for r in rows if r['state']!='settled']}
def log(value):
    value={'at':time.time(),**value}
    print(json.dumps(value,ensure_ascii=False),flush=True)
    atomic_json(ROOT/'status.json',value)

def main():
    ROOT.mkdir(parents=True,exist_ok=True)
    with process_lock(ROOT/'runner.lock',blocking=False):
        assert not (ROOT/'authorization.json').exists(),'Do not rerun; inspect durable execution first'
        assert runtime.read(ORIGINAL/'api/active.json').get('state') in (None,'SUBMITTED')
        assert not any(runtime.read(p).get('state') in {'pending','claimed'} for p in (ORIGINAL/'queue').glob('*/ticket.json'))
        old=runtime.read(runtime.SHARED/'settings.json')
        changed={**old,'article_budget_cny':2.0,'daily_budget_cny':12.0}
        baseline=originals()
        atomic_json(ROOT/'authorization.json',{'at':time.time(),'user_authorization':'那你上调预算不就行了，先跑通再说，继续','selected':SELECTED,'same_original_billing_scope':True,'article_cumulative_cap':2.0,'task_cumulative_cap':8.0,'daily_cap':12.0,'original_settings':old,'leased_settings':changed,'ledger_before':ledger(),'original_hashes':baseline})
        # New acceptance version only; original batch/job budgets remain frozen.
        job=runtime.read(ORIGINAL/'job.json');job['budget_limits']={'article_budget_cny':2.0,'task_budget_cny':8.0}
        atomic_json(ROOT/'job.json',job)
        atomic_json(ROOT/'settings.json',changed)
        atomic_json(ROOT/'control.json',{'paused':False,'revision':1,'reason':'authorized_two_sample_acceptance'})
        atomic_json(ROOT/f'days/{DAY}/day.json',{'date':DAY,'status':'isolated_acceptance'})
        tickets=[]
        for c,n in SELECTED:
            src=ORIGINAL/f'days/{DAY}/compiler-pilots/{c}/{n:02d}'
            base=ROOT/f'days/{DAY}/articles/{c}/{n:02d}'
            (base/'writer').mkdir(parents=True);(base/'review').mkdir()
            for name in INPUTS:shutil.copy2(src/'writer'/name,base/'writer'/name)
            shutil.copytree(src/'research',base/'research')
            meta={'date':DAY,'category':c,'number':n,'revision':1,'consumer_rewrite':True,'paragraph_repair':False,'known_response_replay':False,'acceptance_version':'three-agent-20261022-v1'}
            tid=publish_ticket(ROOT,'writer',base/'writer',INPUTS,['draft.md','article.docx','claim_map.json','knowledge_to_sections.json','writer_done.json'],meta)
            tickets.append({'category':c,'number':n,'ticket':tid})
        atomic_json(ROOT/'selected.json',tickets)
        with process_lock(runtime.SHARED/'settings.lock',blocking=True):
            assert runtime.read(runtime.SHARED/'settings.json')==old,'Settings changed before lease'
            atomic_json(runtime.SHARED/'settings.json',changed)
        results=[]
        budget=runtime.SharedBudget(ROOT);client=CreationClient(runtime.KEY,budget=budget)
        try:
            with process_lock(ROOT/'api/worker.lock',blocking=False):
                for c,n in SELECTED:
                    worker=Worker(ROOT,client,target_article=(DAY,c,n))
                    for step in range(12):
                        log({'state':'running','category':c,'number':n,'step':step})
                        result=worker.once(DAY)
                        log({'state':'stage_result','category':c,'number':n,'step':step,'result':result})
                        output=ROOT/f'approved/{DAY}/{c}/{n:02d}/receipt.json'
                        if output.exists():
                            results.append({'category':c,'number':n,'state':'accepted','receipt':runtime.read(output)})
                            # Archive only completed active state before selecting the next article.
                            active=runtime.read(ROOT/'api/active.json')
                            if active.get('state')=='SUBMITTED':
                                target=ROOT/'api/history'/(active['run_id']+'.json');target.parent.mkdir(exist_ok=True);(ROOT/'api/active.json').replace(target)
                            break
                        if result['status'] in {'idle','completed_with_failures','needs_attention'} or result['status'].startswith('blocked'):
                            results.append({'category':c,'number':n,'state':'not_accepted','result':result});break
                    else:raise RuntimeError('Bounded stage count exhausted')
                    if any(r.get('state')!='accepted' for r in results):
                        # Stop at the first real quality failure, preserving later sample budget.
                        break
        except BaseException as error:
            pause(ROOT,'acceptance_stopped','验收停止；保留请求状态，不自动重发')
            results.append({'state':'stopped','type':type(error).__name__,'code':getattr(error,'code',None),'error':str(error)[:1600]})
            log({'state':'stopped','results':results,'traceback':traceback.format_exc()[-4000:]})
        finally:
            client.close();budget.close()
            with process_lock(runtime.SHARED/'settings.lock',blocking=True):
                now=runtime.read(runtime.SHARED/'settings.json')
                # Restore only the two leased keys if still ours; preserve unrelated changes.
                restored=dict(now)
                for key in ('article_budget_cny','daily_budget_cny'):
                    if now.get(key)==changed[key]:restored[key]=old[key]
                atomic_json(runtime.SHARED/'settings.json',restored)
            final={'at':time.time(),'results':results,'ledger_after':ledger(),'originals_unchanged':originals()==baseline,'settings_after':runtime.read(runtime.SHARED/'settings.json')}
            atomic_json(ROOT/'summary.json',final)
            log({'state':'finished','results':results,'originals_unchanged':final['originals_unchanged']})

if __name__=='__main__':main()
