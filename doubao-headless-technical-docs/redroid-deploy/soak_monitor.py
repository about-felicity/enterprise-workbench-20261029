"""Finite unattended acceptance: periodically ask questions and retain evidence."""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import time
import fcntl

from unattended_core import Queue
from unattended_worker import atomic_json

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--duration',type=float,default=86400)
    parser.add_argument('--interval',type=float,default=600)
    parser.add_argument('--report-dir',type=Path,default=Path('/home/user/redroid-doubao/soak24h'))
    args=parser.parse_args()
    if args.duration<=0 or args.interval<=0:
        raise ValueError('Positive duration and interval required')
    root=Path('/home/user/redroid-doubao')
    args.report_dir.mkdir(mode=0o700,parents=True,exist_ok=True)
    os.chmod(args.report_dir,0o700)
    observer_lock=(args.report_dir/'observer.lock').open('a')
    fcntl.flock(observer_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    path=args.report_dir/'status.json'
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    if path.exists():
        state=json.loads(path.read_text())
        if state['status'] in ('passed','failed'):
            return 0
        if state['duration']!=args.duration or state['interval']!=args.interval:
            raise ValueError('Existing acceptance parameters cannot change')
    else:
        state={'status':'running','start_utc_epoch':time.time(),'start_monotonic':time.monotonic(),
               'boot_id':boot,'duration':args.duration,'interval':args.interval,
               'batch':'hpe14-soak-'+str(int(time.time())),'enqueued':0,'planned':math.ceil(args.duration/args.interval)}
        atomic_json(path,state)
    queue=Queue(root/'hpe14-acceptance/tasks.sqlite')
    examples=json.loads((root/'hpe14-questions.json').read_text(encoding='utf-8-sig'))
    while True:
        now=time.monotonic()
        elapsed=now-state['start_monotonic']
        state.update(last_check_utc_epoch=time.time(),observed_seconds=elapsed)
        problem=None
        if boot!=state['boot_id']:
            problem='Host reboot interrupted this acceptance run'
        elif state.get('last_monotonic') and now-state['last_monotonic']>120:
            problem='Acceptance observer missed more than 120 seconds'
        health=json.loads((root/'hpe14-acceptance/health.json').read_text())
        if time.time()-health['time']>120 or health['status'] not in ('working','idle'):
            problem='Worker heartbeat is stale or tasks need attention'
        active=subprocess.run(['systemctl','is-active','--quiet','redroid-doubao-hpe14-worker.service']).returncode==0
        if not active:
            problem='Worker service is not active'
        log=root/'hpe14-acceptance/native-runtime.log'
        if log.exists():
            faults=[line for line in log.read_text(errors='replace').splitlines()
                    if ' F ' in line or 'ANR in com.larus.nova' in line]
            if faults:
                problem='Native fatal/ANR evidence detected'
                state['native_faults']=faults[-10:]
        if problem:
            state.update(status='failed',error=problem)
            atomic_json(path,state)
            print('Acceptance failed:',problem,flush=True)
            return 0
        due=min(state['planned'],int(elapsed//args.interval)+1)
        if due>state['enqueued']:
            # Re-enqueuing a prefix of the same batch is idempotent even if this
            # process dies after the queue commit but before status publication.
            questions=[examples[i%len(examples)] for i in range(due)]
            queue.enqueue(state['batch'],questions,True)
            state['enqueued']=due
        counts=dict(queue.db.execute('select state,count(*) from tasks where batch=? group by state',(state['batch'],)))
        state['tasks']=counts
        if counts.get('needs_attention'):
            state.update(status='failed',error='An acceptance task needs attention')
        elif elapsed>=args.duration and counts.get('completed',0)==state['planned']:
            state['status']='passed'
        elif elapsed>args.duration+300:
            state.update(status='failed',error='Scheduled answers did not finish within grace period')
        state['last_monotonic']=now
        atomic_json(path,state)
        if state['status']!='running':
            print('Acceptance:',state['status'],counts,flush=True)
            return 0
        time.sleep(min(30,args.interval))

if __name__=='__main__':
    raise SystemExit(main())
