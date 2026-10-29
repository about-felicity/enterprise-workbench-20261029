import json, os, subprocess, sys, time
from pathlib import Path
B=Path(__file__).resolve().parent
os.environ['GEO_CREATION_ROOT']=str(B/'runtime');sys.path[:0]=[str(B/'release/engine'),str(B/'release')]
from creation import runtime
from geo_source_cards.pipeline_control import pause
root=runtime.job_root(runtime.read(B/'state.json')['job_id'])
if sys.argv[1]=='pause':
    pause(root,'maintenance_evidence_checks','Finish sent requests before installing deterministic number/count checks')
    print('Paused at next request boundary; sent calls are not interrupted')
elif sys.argv[1]=='resume':
    assert runtime.read(root/'control.json').get('reason')=='maintenance_evidence_checks'
    assert not any(runtime.read(p).get('state') in {'REQUESTING','REQUEST_UNKNOWN'} for p in (root/'api').rglob('api_state.json'))
    assert runtime.read(B/'release/verification.json')['success']
    runtime.resume(root)
    subprocess.run(['systemd-run','--unit=geo-brow-v2-final-20261024','--collect','--property=UMask=0077',
        '/home/user/geo-editorial/venv/bin/python','-u',str(B/'run_acceptance.py')],check=True)
elif sys.argv[1]=='reviews':
    for p in sorted((root/'days').glob('*/jobs/*/*/review/result.json')):
        r=runtime.read(p)
        print(json.dumps({'article':str(p.parent.parent.relative_to(root)), 'pass':r.get('pass'),
            'findings':r.get('evidence_report',{}).get('findings',[])},ensure_ascii=False))
    for p in (root/'queue').glob('*/ticket.json'):
        t=runtime.read(p)
        if t['state']=='needs_attention':print(json.dumps({'ticket':t,'receipt':runtime.read(p.parent/'receipt.json')},ensure_ascii=False))
