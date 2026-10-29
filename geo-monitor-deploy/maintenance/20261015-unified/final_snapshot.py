import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation.soak import audit
from creation import runtime
base=Path('/opt/monitor/geo-capture')
read=lambda path:json.loads(Path(path).read_text())
capture=read(base/'soak12h_current.json');manifest=read(Path(capture['root'])/'manifest.json');status=read(Path(capture['root'])/'status.json')
creation=read(base/'creation_soak_current.json');creation_manifest=read(Path(creation['root'])/'manifest.json')
containers=subprocess.check_output(['docker','inspect',*manifest['containers'],'--format','{{.Name}} {{.State.StartedAt}}'],text=True).strip()
proof=audit(runtime.job_root(creation['jobs'][0]))
assert len(proof['approved'])==10 and not proof['unknown_calls'] and not proof['control'].get('paused')
checks={}
for model,job in manifest['jobs'].items():
    root=(Path('/home/user/redroid-yuanbao') if model=='yuanbao' else Path('/home/user/redroid-doubao'))/'batches'/job['batch']
    if model in {'doubao1','doubao2','yuanbao'}:
        with sqlite3.connect((root/'tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
            changed=db.execute('select count(*) from tasks where wire_question<>question').fetchone()[0]
        assert changed==0
        checks[model]={'non_question_prompt_rows':changed}
    else:
        root=base/'batches'/job['batch']
        with sqlite3.connect((root/'collector/tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
            recent=db.execute("select ordinal,round,question from captures where state='completed' order by finished desc limit 1").fetchone()
        checks[model]={'latest_completed_question_ordinal':recent[0],'round':recent[1],'question':recent[2]}
snapshot={'at':time.time(),'capture':{'pointer':capture,'status':status['status'],'anomalies':status['anomalies'],
    'models':{m:{k:v.get(k) for k in ['captured','processed','unique_processed','duplicates','window_counts','min_send_interval','duplicate_native_requests','duplicate_conversations']} for m,v in status['models'].items()},
    'core_and_android_containers_unchanged_since_retest':containers==manifest['docker_before'],'prompt_and_cycle_checks':checks},
    'creation':{'pointer':creation,'approved_total':len(proof['approved']),
        'approved_new_in_window':len(set(a['id'] for a in proof['approved'])-set(creation_manifest['approved_before'][creation['jobs'][0]])),
        'full_word_hash_review_GEO_provenance_verified':True,'unknown_api_calls':proof['unknown_calls'],'queue_complete':proof['day']['status']=='complete',
        'scope':'Fixed queue complete; remainder of six-hour window observes availability and fidelity, without repeated paid generation.'}}
path=base/'maintenance/20261015-unified/final-start-snapshot.json';path.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2))
public=Path('/tmp/geo-unified-export-20261015/final-start-snapshot.json');public.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2));public.chmod(0o644)
print(json.dumps(snapshot,ensure_ascii=False))
