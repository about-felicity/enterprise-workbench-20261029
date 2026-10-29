import sys,time,json
from pathlib import Path
sys.path.insert(0,'/opt/monitor/geo-capture')
from native_soak import API,lane,operation,atomic
base=Path('/opt/monitor/geo-capture');pointer=json.loads((base/'all_channel_soak_current.json').read_text());root=Path(pointer['root']);manifest=json.loads((root/'manifest.json').read_text());api=API();results={}
for model,job in manifest['jobs'].items():
    current=lane(api.panel(),model)['current']
    if current['batch']!=job['batch']:results[model]='superseded';continue
    operation(root,api,model+'-user-question-only-pause',model,'pause',{})
    results[model]='drain_requested'
record={'at':time.time(),'reason':'User requires exact question-only prompts, new conversation for every sample, raw/body/source/analysis audit before retest','previous_test':manifest['test_id'],'results':results,'status':'implementation_in_progress','original_test_not_passed':True}
atomic(root/'user_requirement_change.json',record)
atomic(base/'unified_upgrade_current.json',record)
print(json.dumps(record))
