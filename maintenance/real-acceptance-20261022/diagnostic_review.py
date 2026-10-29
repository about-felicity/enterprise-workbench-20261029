"""Independent review of the preserved complete draft; never bypass delivery gates."""
import sys,shutil,time,json,traceback
from pathlib import Path
R=Path('/opt/monitor/geo-content/runtime/acceptance/20261022-three-agent')
sys.path[:0]=[str(R/'stage'),str(R/'stage/engine')]
from creation import runtime
from creation.client import CreationClient
from geo_source_cards.api_worker import Worker
from geo_source_cards.daily_editorial import publish_ticket
from geo_source_cards.runtime import process_lock,atomic_json,atomic_write
from geo_source_cards.pipeline_control import pause

def main():
 with process_lock(R/'runner.lock',blocking=False),process_lock(R/'api/worker.lock',blocking=False):
  assert not (R/'diagnostic-review.json').exists(),'Existing paid diagnostic must not be resent'
  active=runtime.read(R/'api/active.json')
  if active:
   assert active['state']=='SUBMITTED'
   (R/'api/active.json').replace(R/'api/history'/(active['run_id']+'.json'))
  src=R/'days/2026-10-21/articles/测评类/02'
  base=R/'days/2026-10-21/diagnostic/测评类/02'
  shutil.copytree(src/'writer',base/'writer');shutil.copytree(src/'research',base/'research');review=base/'review';review.mkdir()
  for name in ('draft.md','knowledge.json','product.json','category.json','writer_done.json'):shutil.copy2(base/'writer'/name,review/name)
  atomic_write(review/'task.md','对当前完整已保存稿件执行独立事实审稿及全文逻辑审稿。逐条核对真实材料、当前声明与因果范围；指出具体位置、证据、问题和修改要求。一般选择建议不需实验背书，成分或质地不能证明成品功效。此稿尚未通过本地交付门槛，诊断不豁免任何最终验收，也不增加内容修订轮次。')
  meta={'date':'2026-10-21','category':'测评类','number':2,'revision':1,'compiled_repair_round':2,'consumer_rewrite':True,'diagnostic_only':True,'acceptance_version':'complete-saved-draft-independent-diagnostic'}
  tid=publish_ticket(R,'review',review,['task.md','draft.md','knowledge.json','product.json','category.json','writer_done.json'],['result.json'],meta)
  atomic_json(R/'diagnostic-review.json',{'at':time.time(),'ticket':tid,'diagnostic_only':True,'article_not_accepted':True,'writer_version':str(base/'writer')})
  auth=runtime.read(R/'authorization.json');old=auth['original_settings'];changed=auth['leased_settings']
  with process_lock(runtime.SHARED/'settings.lock',blocking=True):
   now=runtime.read(runtime.SHARED/'settings.json');assert all(now[k]==old[k] for k in ('article_budget_cny','daily_budget_cny'))
   atomic_json(runtime.SHARED/'settings.json',{**now,**{k:changed[k] for k in ('article_budget_cny','daily_budget_cny')}})
  budget=runtime.SharedBudget(R);client=CreationClient(runtime.KEY,budget=budget)
  try:
   atomic_json(R/'status.json',{'at':time.time(),'state':'diagnostic_review_running','ticket':tid})
   result=Worker(R,client,target_article=('2026-10-21','测评类',2)).once('2026-10-21')
  except BaseException as e:
   pause(R,'diagnostic_stopped','保留审稿响应和未知保护，不增加内容修订')
   result={'status':'blocked','type':type(e).__name__,'code':getattr(e,'code',None),'detail':str(e)[:800],'traceback':traceback.format_exc()[-2500:]}
  finally:
   client.close();budget.close()
   with process_lock(runtime.SHARED/'settings.lock',blocking=True):
    now=runtime.read(runtime.SHARED/'settings.json')
    for k in ('article_budget_cny','daily_budget_cny'):
     if now[k]==changed[k]:now[k]=old[k]
    atomic_json(runtime.SHARED/'settings.json',now)
  atomic_json(R/'diagnostic-result.json',{'at':time.time(),'result':result,'diagnostic_only':True})
  atomic_json(R/'status.json',{'at':time.time(),'state':'diagnostic_finished','result':result,'diagnostic_only':True})
  print(json.dumps(result,ensure_ascii=False),flush=True)

if __name__=='__main__':main()
