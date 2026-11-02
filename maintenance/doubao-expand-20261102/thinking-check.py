from pathlib import Path
import json,xml.etree.ElementTree as E,collections,subprocess
fleet=json.loads(Path('/opt/monitor/geo-capture/fleet.json').read_text())['collectors']
code="""import sys,uiautomator2 as u,xml.etree.ElementTree as E
d=u.connect(sys.argv[1]);print(d.app_current());print([(n.get('text','')[:50],n.get('content-desc','')[:50],n.get('selected')) for n in E.fromstring(d.dump_hierarchy()).iter('node') if any(k in (n.get('text','')+' '+n.get('content-desc','')) for k in ('深度思考','快速思考','快速模式')) and len(n.get('text',''))<80])"""
for n,port in [(1,5557),(2,5558),(3,5563),(4,5564)]:
 r=Path(next(v['health'] for v in fleet if v['name']==f'豆包 {n}')).parent
 counter=collections.Counter()
 for p in r.glob('*.xml'):
  desc=[x.get('content-desc','') for x in E.parse(p).iter('node')]
  counter[tuple(sorted(set(x for x in desc if x.startswith(('深度思考','快速思考')) and len(x)<30)))]+=1
 print('EVIDENCE',n,counter,flush=True)
 v=subprocess.run(['/home/user/redroid-doubao/worker-venv/bin/python','-c',code,'127.0.0.1:'+str(port)],capture_output=True,text=True,timeout=40);print('LIVE',n,v.stdout,v.stderr[-250:],flush=True)
