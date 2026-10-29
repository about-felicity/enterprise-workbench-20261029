"""Fair, bounded process supervision; one owner per job and no paid-send retry."""
import os,signal,subprocess,sys,time
from collections import Counter
from pathlib import Path
from geo_source_cards.pipeline_control import pause,state
from geo_source_cards.runtime import atomic_json,process_lock
from .runtime import BASE,read

TERMINAL={'complete','complete_with_failures','complete_with_shortfall','blocked_insufficient_sources','blocked_no_media_articles'}

def eligible(root,now=None):
    now=time.time() if now is None else now
    job=read(root/'job.json')
    if not job:return False
    if read(root/'concurrency_retry.json').get('next_at',0)>now:return False
    if read(root/'days'/job['date']/'day.json').get('status') in TERMINAL:return False
    retry=read(root/'known_preflight_retry.json')
    if retry.get('state')=='waiting' and retry.get('next_at',0)>now:return False
    if state(root).get('paused') and not (retry.get('state')=='waiting' and retry.get('budget_pause')):return False
    return not (job.get('preparation')=='pending' and read(root/'preparation_retry.json').get('next_at',0)>now)

class Scheduler:
    def __init__(self,base=BASE,limit=4,launch=None):
        self.base=Path(base);self.limit=max(1,min(8,int(limit)))
        self.active={};self.last={};self.scope_last={};self.next_at={}
        self.launch=launch or self.start

    def start(self,root):
        with (root/'process-worker.log').open('ab') as log:
            return subprocess.Popen([sys.executable,'-B','-m','creation.worker','--job',root.name],stdout=log,stderr=subprocess.STDOUT)

    def tick(self,draining=False):
        now=time.time()
        for name,(process,scope) in list(self.active.items()):
            code=process.poll()
            if code is None:continue
            del self.active[name];root=self.base/'runs'/name
            if code and code!=75:
                pause(root,'worker_process_exit','执行进程异常退出，保留原请求与进度等待核对')
                atomic_json(root/'geo_worker.json',{'at':now,'error':'worker_process_exit','exit_code':code})
            status=read(root/'geo_worker.json').get('result',{}).get('status')
            self.next_at[name]=now+(2 if code==75 else 15 if status in {'idle','blocked_other_article_execution'} else 0)
        waiting=[]
        if not draining:
            for path in (self.base/'runs').glob('*/job.json'):
                root=path.parent
                if root.name in self.active or self.next_at.get(root.name,0)>now:continue
                if eligible(root,now):
                    job=read(path);waiting.append((root,job.get('studio_plan_id') or root.name))
            scopes=Counter(scope for _,scope in self.active.values())
            while waiting and len(self.active)<self.limit:
                root,scope=min(waiting,key=lambda v:(scopes[v[1]],self.scope_last.get(v[1],0),self.last.get(v[0].name,0),v[0].name))
                waiting.remove((root,scope))
                process=self.launch(root);self.active[root.name]=(process,scope)
                self.last[root.name]=self.scope_last[scope]=time.time();scopes[scope]+=1
        health={'at':time.time(),'status':'draining' if draining else 'running','mode':'bounded_processes','max_parallel_jobs':self.limit,
                'active_jobs':[{'job_id':name,'pid':proc.pid,'plan_id':scope} for name,(proc,scope) in self.active.items()],
                'queued_jobs':len(waiting)}
        atomic_json(self.base/'worker_health.json',health)
        return health

def run():
    BASE.mkdir(parents=True,exist_ok=True)
    draining=False
    def stop(signum,frame):
        nonlocal draining
        draining=True
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    with process_lock(BASE/'worker.lock',blocking=False):
        scheduler=Scheduler(limit=os.environ.get('GEO_CREATION_CONCURRENCY','4'))
        while True:
            scheduler.tick(draining=draining or bool(read(BASE/'worker_drain.json').get('enabled')))
            if draining and not scheduler.active:return
            time.sleep(1)
