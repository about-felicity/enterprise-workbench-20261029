import hashlib,json,sys,time,subprocess
from pathlib import Path
B=Path(__file__).resolve().parent;LIVE=Path('/opt/monitor/geo-content')
sys.path[:0]=[str(LIVE/'engine'),str(LIVE)]
from creation import runtime,studio
deployed=runtime.read(LIVE/'maintenance/brow-v2-20261024/deployed.json')
assert all(hashlib.sha256(Path(r['server']).read_bytes()).hexdigest()==r['sha256'] for r in deployed['files'])
state=runtime.read(B/'state.json');plan=studio.plan('plan-9b827648df6c4bf9b5648db2eaf6079e')
assert plan['questions']==state['questions'] and plan['product_id']==state['product_id']
assert plan['enabled'] and plan['frequency']=='daily' and plan['article_target']==7
assert plan['channels']==['baidu_ai','wenxin_card']
assert plan['article_budget_cny']==.35 and plan['task_budget_cny']==2.45
profiles=[]
for model in plan['channels']:
 folder=studio.capture_root(plan['plan_id'])/'profiles/search'/model
 marker=runtime.read(folder/'migration.json')
 assert (folder/'scrapling_profile').is_dir() and marker['plan_id']==plan['plan_id'] and marker['model']==model
 assert marker['source_completed'] and marker['task_journal_copied'] is False
 profiles.append({'model':model,'persistent_profile':True,'seed_completed':True})
root=runtime.job_root(state['job_id']);assert len(runtime.articles(root))==7
assert runtime.read(root/'rewrite_policy.json')['review_policy']=='evidence-v3'
assert runtime.read(runtime.BASE/'rewrite_defaults.json')['skeleton_review']=='automatic'
budget=runtime.SharedBudget(root)
try:
 c=budget.db.execute("select count(*),sum(coalesce(c.charged,0)),sum(case when c.state!='settled' then c.reserved else 0 end) from costs c join studio_cost_scopes s on s.id=c.id where s.job=?",(state['job_id'],)).fetchone()
finally:budget.db.close()
assert c[2]==0
services=['geo-content-worker','geo-content-api','geo-creation-studio','geo-creation-materials']
for service in services:assert subprocess.run(['systemctl','is-active','--quiet',service]).returncode==0
report={'at':time.time(),'deployed_hashes_verified':len(deployed['files']),'articles_visible':7,
 'daily_plan':{k:plan[k] for k in ['plan_id','product_id','enabled','frequency','capture_time','writing_time','article_target','channels','article_budget_cny','task_budget_cny']},
 'persistent_profiles':profiles,'services_active':services,'costs':{'calls':c[0],'charged_cny':c[1],'unsettled_cny':c[2]},
 'next_natural_day_observed':False,'ui_changed':False}
(B/'live-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
