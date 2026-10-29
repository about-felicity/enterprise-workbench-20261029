"""Close the superseded test as interrupted, retaining all raw evidence."""
import json
from pathlib import Path
import subprocess
import time

BASE=Path('/opt/monitor/geo-capture')
root=BASE/'soak/all-channel-soak2h-1792056244'
manifest=json.loads((root/'manifest.json').read_text())
change=json.loads((root/'user_requirement_change.json').read_text())
subprocess.run(['systemctl','disable','--now','geo-all-channel-soak2h-1792056244-deadline.timer'],check=True)
subprocess.run(['systemctl','disable','--now','geo-all-channel-soak2h-1792056244.service'],check=True)
models={}
for model,job in manifest['jobs'].items():
    base=Path('/home/user/redroid-yuanbao') if model=='yuanbao' else Path('/home/user/redroid-doubao') if model.startswith('doubao') else BASE
    health=json.loads((base/'batches'/job['batch']/'bridge_health.json').read_text())
    assert health['captured']==health.get('geo_processed',health.get('processed'))
    models[model]={k:health.get(k) for k in ('batch','captured','geo_processed','processed','status','time')}
report={'test_id':manifest['test_id'],'status':'interrupted_by_changed_requirements','verdict':'not_passed',
        'recorded_at':time.time(),'pause_requested_at':change['at'],'original_deadline':manifest['deadline'],
        'capture_window_seconds_before_pause':change['at']-manifest['started_at'],
        'reason':'User requires question-only prompts. Original marked-prompt test drained; pure-question repeated-prompt acceptance replaces its protocol validation. No duration pass claimed.',
        'models':models,'evidence_retained':True,'original_collection_and_service_failure_notes_retained':True}
(root/'interrupted_report.json').write_text(json.dumps(report,indent=2))
(root/'status.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
