import json,subprocess
from pathlib import Path
root=Path('/home/user/redroid-yuanbao/batches/geo-yuanbao-21x5-20261015')
path=next((root/'outbox').glob('*.json'));item=json.loads(path.read_text());rid=item['request_id']
sql="select record from monitor_ingest_events where request_id='"+rid+"'"
stored=json.loads(subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',sql],text=True))
print(json.dumps({'keys':list(stored),'nested_keys':{k:list(v) for k,v in stored.items() if isinstance(v,dict)},'question_expected':item['record']['question'],'question_actual':stored.get('question'),'nested_question':stored.get('record',{}).get('question')}))
