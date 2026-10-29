"""Run the high-frequency short acceptance, then gate the long acceptance."""
import json
from pathlib import Path
import subprocess
import sys
import time

from unattended_worker import atomic_json

ROOT=Path('/home/user/redroid-doubao')
STAGES=[('short',3600,ROOT/'soak1h'),('long',86400,ROOT/'soak24h')]
INTERVAL=180

def accepted(state,duration):
    planned=duration//INTERVAL
    return (state.get('status')=='passed' and state.get('duration')==duration
            and state.get('interval')==INTERVAL and state.get('planned')==planned
            and state.get('enqueued')==planned
            and state.get('observed_seconds',0)>=duration
            and state.get('tasks')=={'completed':planned})

def main():
    folder=ROOT/'soak1h'
    folder.mkdir(mode=0o700,exist_ok=True)
    sequence=folder/'sequence.json'
    for name,duration,report in STAGES:
        path=report/'status.json'
        state=json.loads(path.read_text()) if path.exists() else None
        if state and state.get('status') in ('failed','cancelled'):
            atomic_json(sequence,{'status':'failed','stage':name,'reason':state.get('error',state['status']),
                                  'long_started':name=='long','updated_utc_epoch':time.time()})
            return 0
        if not state or not accepted(state,duration):
            atomic_json(sequence,{'status':'running','stage':name,'interval':INTERVAL,
                                  'long_started':name=='long','updated_utc_epoch':time.time()})
            command=[sys.executable,'-u',str(ROOT/'soak_monitor.py'),'--duration',str(duration),
                     '--interval',str(INTERVAL),'--report-dir',str(report)]
            subprocess.run(command,check=True)
            state=json.loads(path.read_text())
        if not accepted(state,duration):
            atomic_json(sequence,{'status':'failed','stage':name,'reason':state.get('error','Acceptance gate not met'),
                                  'long_started':name=='long','updated_utc_epoch':time.time()})
            print('Stopped at acceptance gate:',name,flush=True)
            return 0
        print('Acceptance gate passed:',name,flush=True)
    atomic_json(sequence,{'status':'passed','stage':'complete','long_started':True,'updated_utc_epoch':time.time()})
    return 0

if __name__=='__main__':
    raise SystemExit(main())
