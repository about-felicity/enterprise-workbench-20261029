import sys,json,time,shutil,collections
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,recovery
from geo_source_cards.runtime import atomic_json,process_lock
from geo_source_cards.rewrite_v2 import integration,material_manager
from geo_source_cards.rewrite_v2.common import seal
from geo_source_cards.daily_editorial import tick,publish_ticket,safe_name

base=Path('/opt/monitor/geo-content/maintenance/recovery-20261027');base.mkdir(parents=True,exist_ok=True)
read=runtime.read
assert not read(runtime.BASE/'worker_health.json').get('active_jobs')
results=[]
for root in sorted((runtime.BASE/'runs').iterdir()):
    job=read(root/'job.json');control=read(root/'control.json')
    if job.get('date','')<'2026-10-26' or control.get('reason')=='plan_deleted':continue
    plan=read(Path('/opt/monitor/geo-content/studio/plans')/(job.get('studio_plan_id','')+'.json'))
    if plan.get('deleted_at'):continue
    row={'job':root.name,'recovered':0,'retry_tickets':[],'errors':[]}
    with process_lock(root/'api/worker.lock',blocking=False):
        if not recovery.safe_original(root):
            row['errors'].append('unknown request; not replayed');results.append(row);continue
        backup=base/root.name
        if not backup.exists():shutil.copytree(root,backup)
        policy=read(root/'rewrite_policy.json');policy.update(article_delivery='direct',max_targeted_repairs=0)
        atomic_json(root/'rewrite_policy.json',policy)
        tickets=[read(p) for p in (root/'queue').glob('*/ticket.json')]
        groups=collections.defaultdict(list)
        for t in tickets:
            if t['stage'] in ('research','writer','review'):groups[(t['meta'].get('category'),t['meta'].get('number'))].append(t)
        for key,ts in groups.items():
            if not key[0] or not key[1]:continue
            destination=root/'approved'/job['date']/safe_name(key[0])/f'{key[1]:02d}'
            already=(destination/'receipt.json').exists();delivered=already
            writers=sorted([t for t in ts if t['stage']=='writer'],key=lambda t:t.get('created_at',''),reverse=True)
            if not already:
                for t in writers:
                    writer=root/t['location']
                    try:
                        if not (writer/'writer_done.json').exists():
                            if 'no titled article' not in t.get('error',''):continue
                            run=root/'api/runs'/t.get('execution',{}).get('run_id','')
                            answers=list(run.rglob('answer.json'))
                            valid=[]
                            for ap in answers:
                                raw=read(ap)
                                if raw.get('finish_reason')!='stop':continue
                                try:answer=json.loads(raw.get('content',''))
                                except (ValueError,TypeError):continue
                                if isinstance(answer,dict) and isinstance(answer.get('draft_markdown'),str) and len(answer['draft_markdown'].strip())>100:valid.append(answer)
                            if len(valid)!=1:continue
                            product=read(writer/'rewrite_context.json')['product']
                            material=seal({'raw_product':product,'layers':{k:[] for k in material_manager.LAYERS},'usage_rules':[],'protocol':'original-product-direct-v1'})
                            integration.materialize(t,writer,{**valid[0],'material':material})
                        integration.finalize(root,writer.parent/'review')
                        delivered=True;row['recovered']+=1;break
                    except Exception as e:row['errors'].append(t['id']+': '+str(e)[:160])
            if delivered:
                for t in ts:
                    if t['state'] in ('pending','claimed','needs_attention'):
                        atomic_json(root/'queue'/t['id']/'ticket.json',{**t,'state':'accepted' if t['stage']=='review' else 'revision_requested','recovery_reason':'Existing article delivered under user direct-output instruction','recovered_at':time.time()})
            elif not any(t['state'] in ('pending','claimed') for t in ts):
                candidates=[t for t in ts if t['state']=='needs_attention' and t['stage'] in ('writer','research')]
                if candidates:
                    t=sorted(candidates,key=lambda v:v.get('created_at',''))[-1]
                    meta={k:v for k,v in t['meta'].items() if k not in ('targeted_repair','targeted_repair_round','review_projection_from','review_output_retry')}
                    meta.update(recovery_20261027=True,replaces=t['id'],revision=meta.get('revision',0)+1)
                    replacement=publish_ticket(root,t['stage'],root/t['location'],list(t['inputs']),t['outputs'],meta)
                    for prior in ts:
                        if prior['state']=='needs_attention':atomic_json(root/'queue'/prior['id']/'ticket.json',{**prior,'state':'revision_requested','replaced_by':replacement})
                    row['retry_tickets'].append(replacement)
        daypath=root/'days'/job['date']/'day.json';day=read(daypath)
        if day.get('status')=='complete_with_failures':atomic_json(daypath,{**day,'status':'producing'})
        if day:tick(root)
        current=read(daypath).get('status')
        if current not in {'complete','complete_with_shortfall','blocked_insufficient_sources','blocked_no_media_articles'}:
            try:runtime.resume(root,check_balance=False);row['resumed']=True
            except Exception as e:row['errors'].append(str(e))
        row['status']=read(daypath).get('status')
    results.append(row);atomic_json(base/'result.json',results);print(json.dumps(row,ensure_ascii=False),flush=True)
print(json.dumps({'jobs':len(results),'recovered':sum(x['recovered'] for x in results),'retry_tickets':sum(len(x['retry_tickets']) for x in results)}))
