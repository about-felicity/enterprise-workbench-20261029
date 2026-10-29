"""Run the real studio handoff and original worker without interactive gates."""
import json,os,sys,time,traceback
from pathlib import Path
BASE=Path(__file__).resolve().parent
os.environ['GEO_CREATION_ROOT']=str(BASE/'runtime')
sys.path[:0]=[str(BASE/'release/engine'),str(BASE/'release')]
from creation import runtime,studio,materials
from geo_source_cards.runtime import atomic_json,process_lock
from geo_source_cards.api_worker import Worker
from creation.client import CreationClient
from geo_source_cards.pipeline_control import state as control

def status(**values):
    value={'at':time.time(),**values}
    atomic_json(BASE/'acceptance-status.json',value)
    print(json.dumps(value,ensure_ascii=False),flush=True)

def run():
    data=runtime.read(BASE/'state.json');day=data['date'];plan=studio.plan(data['plan_id'])
    runtime.BASE.mkdir(parents=True,exist_ok=True)
    atomic_json(runtime.BASE/'rewrite_defaults.json',{'skeleton_review':'automatic',
        'authorization':'2026-10-24 user: 文章没啥问题，可以直接用了，把系统完善下，然后用这个测试一下，找七个问题，做到无人值守'})
    with process_lock(BASE/'acceptance.lock',blocking=False):
        deadline=time.time()+10800;root=None
        while time.time()<deadline:
            progress=[x for x in materials.progress(day,store_root=Path(data['capture_root'])) if x['id'] in data['channels']]
            if not all(x['completed']>=len(data['questions']) for x in progress):
                status(phase='capturing',progress=progress)
                time.sleep(30);continue
            studio.ensure_day(plan,day)
            product=studio.product(data['product_id'])['product']
            payload={'material_source':'dedicated','studio_plan_id':data['plan_id'],
                'task_name':plan['name'],'budget_limits':{'article_budget_cny':.35,'task_budget_cny':2.45},
                'date':day,'question':'任务问题汇总','questions':data['questions'],'channels':data['channels'],
                'max_per_category':7,'article_target':7,'product':product}
            job=runtime.action('new',payload,runtime.digest({'acceptance':data['plan_id'],'date':day})[:32])
            root=runtime.job_root(job['job_id']);data['job_id']=job['job_id'];atomic_json(BASE/'state.json',data)
            status(phase='preparing_sources',job_id=job['job_id'],progress=progress)
            current=runtime.read(root/'job.json')
            if current.get('preparation')=='pending':materials.prepare(root,current)
            break
        if root is None:raise RuntimeError('Capture deadline reached')
        budget=runtime.SharedBudget(root);client=CreationClient(runtime.KEY,budget=budget)
        try:
            while time.time()<deadline:
                if control(root).get('paused'):
                    status(phase='paused',job_id=root.name,control=control(root));return
                from recover_unsent_budget import recover
                recover(root)
                result=Worker(root,client).once(day)
                delivered=list((root/'approved'/day).glob('*/*/receipt.json'))
                status(phase='writing',job_id=root.name,delivered=len(delivered),result=result)
                day_state=runtime.read(root/'days'/day/'day.json').get('status')
                if result.get('status')=='idle' and day_state in {'complete','complete_with_shortfall','complete_with_failures'}:
                    status(phase='finished' if len(delivered)>=7 else 'needs_attention',job_id=root.name,
                        delivered=len(delivered),result=result,day_status=day_state);return
                if result.get('status') in {'complete','completed_with_failures','blocked_unknown_execution','complete_with_shortfall'} or (result.get('status')=='needs_attention' and 'failed_tickets' in result):
                    status(phase='finished' if len(delivered)>=7 else 'needs_attention',job_id=root.name,
                        delivered=len(delivered),result=result);return
                time.sleep(2)
            raise RuntimeError('Writing deadline reached')
        finally:client.close();budget.db.close()

if __name__=='__main__':
    try:run()
    except Exception as error:
        status(phase='error',error_type=type(error).__name__,message=str(error)[:700])
        traceback.print_exc();raise
