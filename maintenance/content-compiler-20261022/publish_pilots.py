"""Two isolated writing versions, same original jobs/articles/billing scopes."""
import sys,json,time,shutil,sqlite3
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from geo_source_cards.runtime import atomic_json,process_lock
from geo_source_cards.daily_editorial import publish_ticket
from geo_source_cards.staged_editorial import research_for_writer
D=Path('/opt/monitor/geo-capture/maintenance/20261022-content-compiler');marker=D/'pilots-published.json'
assert not marker.exists(),'Already published; never resend'
root=runtime.job_root('creation-1792575159-0a8f9221')
assert runtime.read(root/'control.json').get('reason')=='compiler_small_sample'
assert runtime.read(root/'api/active.json').get('state') in (None,'SUBMITTED')
selected=[('排行类',1),('测评类',2)];published=[]
with process_lock(root/'coordinator.lock',blocking=True):
 jobs=[runtime.read(p) for p in (root/'queue').glob('*/ticket.json')]
 assert not any(j['state'] in {'pending','claimed'} for j in jobs)
 for category,number in selected:
  estimate=next(r for r in runtime.read(D/'pilot-affordability.json')['candidates'] if (r['job'],r['category'],r['number'])==(root.name,category,number))
  assert estimate['affordable_writer']
  old=max([j for j in jobs if (j['meta'].get('category'),j['meta'].get('number'))==(category,number)],key=lambda j:j['created_at'])
  original=root/'days/2026-10-21/jobs'/category/f'{number:02d}'/'writer'
  parent=root/'days/2026-10-21/compiler-pilots'/category/f'{number:02d}';writer=parent/'writer'
  shutil.copytree(original,writer)
  shutil.copytree(research_for_writer(original),parent/'research')
  inputs=['writing_prompt.md','writing_job.json','knowledge.json','product.json','writing_task.txt','category.json','batch_rules.md']
  meta={**old['meta'],'revision':1,'replaces':old['id'],'paragraph_repair':False,'known_response_replay':False,
        'consumer_rewrite':True,'compiler_pilot_release':'practical-v1'}
  tid=publish_ticket(root,'writer',writer,inputs,['draft.md','article.docx','claim_map.json','knowledge_to_sections.json','writer_done.json'],meta)
  published.append({'job':root.name,'category':category,'number':number,'ticket':tid,'location':str(writer.relative_to(root)),
                    'preserved_article_budget_cny':runtime.read(root/'job.json')['budget_limits']['article_budget_cny']})
atomic_json(marker,{'at':time.time(),'articles':published,'new_billing_scopes':0,'budgets_changed':False})
runtime.resume(root)
print(json.dumps(runtime.read(marker),ensure_ascii=False))
