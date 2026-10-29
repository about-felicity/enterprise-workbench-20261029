import json,sys,subprocess
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content/engine','/opt/monitor/geo-content']
from creation import runtime,studio,materials
p=studio.plan('plan-9b827648df6c4bf9b5648db2eaf6079e')
print('plan',json.dumps({k:v for k,v in p.items() if k!='product'},ensure_ascii=False))
print('capture_settings',json.dumps({k:v for k,v in runtime.read(studio.capture_root(p['plan_id'])/'settings.json').items() if k!='studio_plan'},ensure_ascii=False))
print('today',json.dumps({k:v for k,v in runtime.read(studio.day_path(p['plan_id'],'2026-10-24')).items() if k!='plan'},ensure_ascii=False))
print('pending_requests',json.dumps([{'path':str(f),'state':runtime.read(f).get('state')} for f in runtime.BASE.glob('runs/*/api/runs/**/api_state.json') if runtime.read(f).get('state')=='REQUESTING']))
print('services',subprocess.run(['systemctl','show','geo-content-worker','geo-creation-studio','geo-creation-materials','-p','MainPID','-p','ActiveState'],capture_output=True,text=True).stdout)
print('processes','\n'.join(line for line in subprocess.run(['ps','-eo','pid,ppid,args'],capture_output=True,text=True).stdout.splitlines() if 'creation.' in line or 'geo_source_cards.cli' in line))
