"""Queue this authorized test behind the shared browser lock, retaining journals and limits."""
import argparse,json,os,subprocess,time
from pathlib import Path
BASE=Path(__file__).resolve().parent
state=json.loads((BASE/'multi-state.json').read_text())
p=argparse.ArgumentParser();p.add_argument('--key');p.add_argument('--cycles',type=int,default=2);a=p.parse_args()
for cycle in range(a.cycles):
    for item in state['products']:
        if a.key and item['key']!=a.key:continue
        for model in ('baidu_ai','wenxin_card'):
            lane=Path(item['capture_root'])/'days'/item['date']/model
            output=lane/'results.jsonl'
            if output.exists() and len(output.read_text().splitlines())>=2:continue
            env={**os.environ,'PYTHONPATH':'','GEO_COLLECTOR_RUNTIME':str(lane/'collector'),
                 'GEO_SEARCH_RATE_STATE':'/opt/monitor/geo-content/search-pool/last_search.json','GEO_UNATTENDED':'1'}
            env.pop('GEO_PIPELINE_ROOT',None)
            command=['/usr/sbin/runuser','-u','user','--','/usr/bin/flock','-w','240',
              '/opt/monitor/geo-content/search-pool/browser.lock','/opt/monitor/geo-capture/venv/bin/python',
              '-m','geo_source_cards.cli','--model',model,'--runtime-dir',str(lane/'collector'),
              '--batch','creation-material-'+item['date']+'-'+model,'--questions-file',str(lane/'questions.txt'),
              '--rounds','1','--output',str(output),'--require-sources','--require-complete-sources',
              '--min-search-interval','60','--max-new-captures','1','--bounded-search-recovery']
            if model=='baidu_ai':command+=['--optional-baidu']
            print(json.dumps({'start':item['key'],'model':model,'cycle':cycle,'at':time.time()}),flush=True)
            with (lane/'capture.log').open('ab') as log:
                result=subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
            print(json.dumps({'end':item['key'],'model':model,'code':result.returncode,'at':time.time()}),flush=True)
