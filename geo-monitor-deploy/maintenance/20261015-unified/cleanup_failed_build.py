"""Remove only our proven failed frontend test container after preserving its log."""
from datetime import datetime
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import time
root=Path('/opt/monitor/geo-capture/maintenance/20261015-unified')
removed=[]
ids=subprocess.check_output(['docker','ps','-aq','--filter','status=exited'],text=True).split()
for identity in ids:
    value=json.loads(subprocess.check_output(['docker','inspect',identity],text=True))[0]
    command=value['Config'].get('Cmd') or []
    created=datetime.fromisoformat(value['Created'][:26]+'+00:00').timestamp()
    if not (1792060500<=created<=1792060600 and value['State']['ExitCode']==1 and len(command)==3
            and command[:2]==['/bin/sh','-c'] and command[2].startswith('node --test --test-skip-pattern=')
            and command[2].endswith('tests/rendered-html.test.mjs')):continue
    assert not value['Mounts']
    attempt=subprocess.run(['docker','logs',identity],stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if attempt.returncode:
        log=subprocess.check_output(['journalctl','-u','geo-creation-frontend-build-17920605.service','--no-pager','-o','short-iso'])
        assert identity[:12].encode() in log and b'non-zero code: 1' in log
    else:log=attempt.stdout
    target=root/('failed-build-'+identity[:12]+'.log.gz')
    with gzip.open(target,'wb') as stream:stream.write(log)
    assert hashlib.sha256(gzip.decompress(target.read_bytes())).hexdigest()==hashlib.sha256(log).hexdigest()
    record={'id':identity,'name':value['Name'],'command':command,'created':value['Created'],'log_sha256':hashlib.sha256(log).hexdigest(),'log_bytes':len(log),'log_archive':str(target),'no_mounts':True}
    (root/('failed-build-'+identity[:12]+'.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2))
    subprocess.run(['docker','rm',identity],check=True,capture_output=True);removed.append(record)
report={'at':time.time(),'removed':removed,'scope':'Only failed test container from this exact creation frontend build; history logs losslessly retained. No other stopped container or image deleted.'}
(root/'failed-build-cleanup.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({'removed':[r['id'][:12] for r in removed],'preserved_log_bytes':sum(r['log_bytes'] for r in removed)}))
