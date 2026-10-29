"""One execution quantum per process; original API engine owns send-intent and recovery gates."""
import time
from geo_source_cards.api_worker import Worker
from geo_source_cards.deepseek_api import APIError, DeepSeekClient
from geo_source_cards.pipeline_control import PipelinePaused, pause, state
from geo_source_cards.runtime import atomic_json, process_lock
from .runtime import BASE,KEY,SharedBudget,read
from .client import CreationClient
from . import recovery

def execute_once(root):
    from .parallel import eligible
    with process_lock(root/'api/worker.lock',blocking=False):
        if not eligible(root) or not recovery.ready(root) or state(root).get('paused'):return
        execute(root,read(root/'job.json'),read(root/'preparation_retry.json'))

def execute(root,job,retry):
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
            return
        pause(root,'api_unknown' if error.uncertain else error.code,
              'API发送结果未知，保留现场等待核对' if error.uncertain else 'API阶段受保护暂停：'+error.code)
        atomic_json(root/'geo_worker.json',{'at':time.time(),'error':error.code,'uncertain':error.uncertain})
    except ValueError as error:
        from .materials import InsufficientMaterials
        if isinstance(error,InsufficientMaterials):
            result={'status':'blocked_insufficient_sources','message':str(error)}
            atomic_json(root/'days'/job['date']/'day.json',result)
            atomic_json(root/'geo_worker.json',{'at':time.time(),'result':result})
            job.update(preparation='insufficient',material_shortfall=str(error));atomic_json(root/'job.json',job)
            return
        if job.get('preparation')=='pending' and str(error).startswith('专用素材仅有'):
            attempt=retry.get('attempts',0)+1
            if attempt<=3:
                atomic_json(root/'preparation_retry.json',{'attempts':attempt,'next_at':time.time()+min(900,60*2**attempt),'reason':'incomplete_public_source_fetch'})
                atomic_json(root/'geo_worker.json',{'at':time.time(),'phase':'preparation_backoff','attempt':attempt,'message':str(error)[:300]})
                return
        pause(root,'material_or_quality_check',str(error)[:300])
        atomic_json(root/'geo_worker.json',{'at':time.time(),'message':str(error)[:300]})
    except Exception as error:
        if (isinstance(error,RuntimeError) and isinstance(error.__cause__,OSError)
                and str(error)=='Another collector uses this runtime; do not share browser profiles concurrently'
                and recovery.safe_original(root)):
            # A shared material/skeleton cache has another producer. Re-enter the
            # same durable execution later; completed model responses are reused.
            atomic_json(root/'concurrency_retry.json',{'next_at':time.time()+2})
            atomic_json(root/'geo_worker.json',{'at':time.time(),'phase':'waiting_shared_analysis'})
            return
        # Never clear an active execution or retry unknown delivery here.
        pause(root,'execution_error','执行校验失败，保留现场：'+type(error).__name__)
        atomic_json(root/'geo_worker.json',{'at':time.time(),'error_type':type(error).__name__,'message':str(error)[:600]})
    finally:
        if client is not None:client.close()
        budget.db.close()
def run():
    from .parallel import run as supervise
    supervise()

if __name__=='__main__':
    import argparse
    from .runtime import job_root
    parser=argparse.ArgumentParser();parser.add_argument('--job');args=parser.parse_args()
    if args.job:
        try:execute_once(job_root(args.job))
        except RuntimeError as error:
            if isinstance(error.__cause__,OSError) and str(error)=='Another collector uses this runtime; do not share browser profiles concurrently':
                raise SystemExit(75)
            raise
    else:run()
