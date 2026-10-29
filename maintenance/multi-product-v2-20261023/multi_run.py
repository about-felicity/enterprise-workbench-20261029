"""Serial V2 product tests using the original shared ledger and immutable per-product scopes."""
import argparse,hashlib,json,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path[:0]=[str(BASE/'engine'),str(BASE)]
from creation import studio,runtime,materials
from geo_source_cards.runtime import atomic_json,atomic_write
from geo_source_cards.api_worker import Worker
from geo_source_cards.deepseek_api import DeepSeekClient
from geo_source_cards.daily_editorial import publish_ticket
from geo_source_cards.rewrite_v2 import integration,material_manager
from geo_source_cards.rewrite_v2.common import digest

STATE=runtime.read(BASE/'multi-state.json')
CACHE=BASE/'multi-runtime/cache'

def root_for(item):
    return BASE/'multi-runtime/runs'/('creation-1792749600-'+hashlib.sha256(item['plan_id'].encode()).hexdigest()[:8])

def init(item):
    root=root_for(item);day=item['date']
    product=studio.product(item['product_id'])['product']
    if not (root/'job.json').exists():
        atomic_json(root/'job.json',{'workflow':'rewrite-v2','job_id':root.name,'studio_plan_id':item['plan_id'],
          'date':day,'task_name':product['name']+'V2单篇测试','budget_limits':{'article_budget_cny':.35,'task_budget_cny':.35}})
        atomic_json(root/'rewrite_policy.json',{'workflow':'rewrite-v2','cache_dir':str(CACHE),'max_rewrites':1})
        atomic_json(root/'logic_policy.json',{'required':True,'version':'rewrite-v2'})
        atomic_json(root/'days'/day/'day.json',{'date':day,'status':'producing','planned_articles':1})
        atomic_json(root/'days'/day/'product.json',product)
        atomic_json(root/'product.json',product)
        atomic_json(root/'monitoring_plan.json',item)
    else:assert runtime.read(root/'product.json')==product,'Product snapshot changed'
    return root,product

def main():
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['init','material','parse','continue','status']);p.add_argument('--key');a=p.parse_args()
    reports=[]
    for item in STATE['products']:
        if a.key and a.key!=item['key']:continue
        root,product=init(item)
        selected=runtime.read(BASE/'multi-results'/item['key']/'selected-source.json')
        category=selected.get('category','科普类')
        meta={'date':item['date'],'category':category,'number':1,'workflow':'rewrite-v2'}
        budget=runtime.SharedBudget(root);client=DeepSeekClient(runtime.KEY,budget=budget)
        try:
            if a.phase=='material':
                # All per-article costs use a stable category: allocated when source is chosen.
                if not selected:print('waiting_source',item['key'],flush=True);continue
                material_manager.process(client,product,CACHE,root/'material-call',meta)
            elif a.phase in {'parse','continue'}:
                if not selected:print('waiting_source',item['key'],flush=True);continue
                location=root/'days'/item['date']/'jobs'/category/'01/research'
                if not (location/'research_input.json').exists():
                    observations=[{'question':selected['question'],'model':selected['model'],'sources':[selected['source']]}]
                    integration.prepare_research(location,observations,product)
                    atomic_json(location.parent/'category.json',{'label':category,'number':1,'source_urls':[selected['source']['url']]})
                    atomic_json(root/'days'/item['date']/'sources.json',[selected['source']])
                    publish_ticket(root,'research',location,['research_input.json','research_task.txt'],['research_result.json'],meta)
                worker=Worker(root,client)
                for _ in range(2 if a.phase=='parse' else 8):
                    result=worker.once(item['date']);print(item['key'],json.dumps(result,ensure_ascii=False),flush=True)
                    if result.get('status') in {'needs_attention','complete','blocked_unknown_execution','idle','completed_with_failures'}:break
        except Exception as error:
            atomic_json(root/'test-error.json',{'kind':type(error).__name__,'error':str(error),'at':time.time()})
            print(item['key'],'error',type(error).__name__,str(error),flush=True)
        finally:
            try:costs=[dict(r) for r in budget.db.execute('select c.stage,c.reserved,c.charged,c.state,c.usage from costs c join studio_cost_scopes s on c.id=s.id where s.job=?',(root.name,))]
            except Exception:costs=[]
            report={'key':item['key'],'root':str(root),'category':category,'costs':costs,
                'tickets':[{k:runtime.read(f).get(k) for k in ('stage','state','waiting_skeleton','error')} for f in sorted((root/'queue').glob('*/ticket.json'))]}
            atomic_json(BASE/'multi-results'/item['key']/'runtime-status.json',report);reports.append(report)
            client.close();budget.db.close()
    print(json.dumps(reports,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
