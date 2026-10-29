"""Resume known completed stage into its existing repair ticket; never replay sends."""
import sys,json,time,traceback
from pathlib import Path
ROOT=Path('/opt/monitor/geo-content/runtime/acceptance/20261022-three-agent')
sys.path[:0]=[str(ROOT/'stage'),str(ROOT/'stage/engine')]
from creation import runtime
from creation.client import CreationClient
from geo_source_cards.api_worker import Worker
from geo_source_cards.runtime import process_lock,atomic_json
from geo_source_cards.pipeline_control import pause
from geo_source_cards.deepseek_api import APIError

def main():
 with process_lock(ROOT/'runner.lock',blocking=False):
  auth=runtime.read(ROOT/'authorization.json');old=auth['original_settings'];changed=auth['leased_settings'];results=[]
  history=ROOT/('summary-before-resume-'+str(time.time_ns())+'.json')
  if (ROOT/'summary.json').exists():(ROOT/'summary.json').replace(history)
  with process_lock(runtime.SHARED/'settings.lock',blocking=True):
   now=runtime.read(runtime.SHARED/'settings.json')
   assert all(now[k]==old[k] for k in ('article_budget_cny','daily_budget_cny')),'Budget lease changed'
   atomic_json(runtime.SHARED/'settings.json',{**now,**{k:changed[k] for k in ('article_budget_cny','daily_budget_cny')}})
  budget=runtime.SharedBudget(ROOT);client=CreationClient(runtime.KEY,budget=budget)
  def log(value):
   value={'at':time.time(),**value};atomic_json(ROOT/'status.json',value);print(json.dumps(value,ensure_ascii=False),flush=True)
  try:
   with process_lock(ROOT/'api/worker.lock',blocking=False):
    for c,n in ([('排行类',1)] if '--ranking-only' in sys.argv else [('测评类',2),('排行类',1)]):
     w=Worker(ROOT,client,target_article=('2026-10-21',c,n))
     for step in range(12):
      log({'state':'running','category':c,'number':n,'step':step,'engine':'isolated-blocking-fix'})
      result=w.once('2026-10-21');log({'state':'stage_result','category':c,'number':n,'step':step,'result':result})
      output=ROOT/f'approved/2026-10-21/{c}/{n:02d}/receipt.json'
      if output.exists():
       results.append({'category':c,'number':n,'state':'accepted','receipt':runtime.read(output)})
       active=runtime.read(ROOT/'api/active.json')
       if active.get('state')=='SUBMITTED':
        target=ROOT/'api/history'/(active['run_id']+'.json');target.parent.mkdir(exist_ok=True);(ROOT/'api/active.json').replace(target)
       break
      if result['status'].startswith('blocked') or result['status'] in {'idle','completed_with_failures'} or result['status']=='needs_attention' and not result.get('ticket'):
       results.append({'category':c,'number':n,'state':'not_accepted','result':result});break
     else:raise RuntimeError('Stage bound exhausted')
     if any(r['state']!='accepted' for r in results):break
  except BaseException as e:
   pause(ROOT,'acceptance_stopped','验收停止；保留请求状态，不自动重发')
   results.append({'state':'stopped','type':type(e).__name__,'code':getattr(e,'code',None),'error':str(e)[:1600]})
   log({'state':'stopped','results':results,'traceback':traceback.format_exc()[-4000:]})
  finally:
   client.close();budget.close()
   with process_lock(runtime.SHARED/'settings.lock',blocking=True):
    now=runtime.read(runtime.SHARED/'settings.json');restored=dict(now)
    for k in ('article_budget_cny','daily_budget_cny'):
     if now.get(k)==changed[k]:restored[k]=old[k]
    atomic_json(runtime.SHARED/'settings.json',restored)
   import hashlib
   unchanged=all(Path(p).is_file() and hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in auth['original_hashes'].items())
   atomic_json(ROOT/'summary.json',{'at':time.time(),'results':results,'originals_unchanged':unchanged,'settings_after':runtime.read(runtime.SHARED/'settings.json')})
   log({'state':'finished','results':results,'originals_unchanged':unchanged})

if __name__=='__main__':main()
