import json,os,subprocess,sys
from pathlib import Path
D=Path(sys.argv[1]);os.environ['GEO_V3_CANDIDATE']='/opt/monitor/geo-capture/maintenance/20261023-structure-recovery-v3-final'
results=[]
for mode in ('v4','v3','prior','engine','creation'):
 p=subprocess.run([sys.executable,'-B',str(D/'run.py'),mode],capture_output=True,text=True,timeout=240)
 data=json.loads((D/f'logs/linux-{mode}.json').read_text());data['exit_code']=p.returncode;results.append(data)
 print(json.dumps({k:data[k] for k in ('suite','tests','exit_code','network_attempts')},ensure_ascii=False),flush=True)
(D/'linux-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
