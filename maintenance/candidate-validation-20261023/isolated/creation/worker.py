"""Single serial executor; original API engine owns send-intent and recovery gates."""
import time
from geo_source_cards.api_worker import Worker
from geo_source_cards.deepseek_api import APIError, DeepSeekClient
from geo_source_cards.pipeline_control import PipelinePaused, pause, state
from geo_source_cards.runtime import atomic_json, process_lock
from .runtime import BASE,KEY,SharedBudget,read
from .client import CreationClient
from . import recovery

def run():
    BASE.mkdir(parents=True,exist_ok=True)
    with process_lock(BASE/'worker.lock',blocking=False):
        while True:
            for path in sorted((BASE/'runs').glob('*/job.json')):
                root=path.parent;job=read(path)
                if not recovery.ready(root):continue
                if state(root).get('paused'):continue
                retry=read(root/'preparation_retry.json')
                if job.get('preparation')=='pending' and retry.get('next_at',0)>time.time():continue
                budget=SharedBudget(root);client=None
                try:
                    if job.get('preparation')=='pending':
                        from .materials import prepare
                        job=prepare(root,job)
                    client=CreationClient(KEY,budget=budget)
                    result=Worker(root,client).once(job['date'])
                    if result.get('status')=='blocked_unknown_execution' or (result.get('status')=='needs_attention' and 'failed_tickets' in result):
                        pause(root,result['status'],'执行需要核对，保留请求和质量证据；不会重发未知请求')
                    atomic_json(root/'geo_worker.json',{'at':time.time(),'result':result})
                    recovery.succeeded(root)
                except PipelinePaused:pass
                except APIError as error:
                    if recovery.defer(root,error):
                        atomic_json(root/'geo_worker.json',{'at':time.time(),'phase':'known_preflight_backoff','code':error.code,
                            'next_at':read(root/'known_preflight_retry.json').get('next_at')})
                        continue
                    pause(root,'api_unknown' if error.uncertain else error.code,
                          'API发送结果未知，保留现场等待核对' if error.uncertain else 'API阶段受保护暂停：'+error.code)
                    atomic_json(root/'geo_worker.json',{'at':time.time(),'error':error.code,'uncertain':error.uncertain})
                except ValueError as error:
                    if job.get('preparation')=='pending' and str(error).startswith('专用素材仅有'):
                        attempt=retry.get('attempts',0)+1
                        if attempt<=3:
                            atomic_json(root/'preparation_retry.json',{'attempts':attempt,'next_at':time.time()+min(900,60*2**attempt),'reason':'incomplete_public_source_fetch'})
                            atomic_json(root/'geo_worker.json',{'at':time.time(),'phase':'preparation_backoff','attempt':attempt,'message':str(error)[:300]})
                            continue
                    pause(root,'material_or_quality_check',str(error)[:300])
                    atomic_json(root/'geo_worker.json',{'at':time.time(),'message':str(error)[:300]})
                except Exception as error:
                    # Never clear an active execution or retry unknown delivery here.
                    pause(root,'execution_error','执行校验失败，保留现场：'+type(error).__name__)
                    atomic_json(root/'geo_worker.json',{'at':time.time(),'error_type':type(error).__name__,'message':str(error)[:600]})
                finally:
                    if client is not None:client.close()
                    budget.db.close()
            atomic_json(BASE/'worker_health.json',{'at':time.time(),'status':'running'})
            time.sleep(5)

if __name__=='__main__':run()
