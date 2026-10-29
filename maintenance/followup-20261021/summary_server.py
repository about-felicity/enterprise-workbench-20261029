"""Read-only final evidence summary for repair results and DOCX integrity."""
import hashlib,json,sqlite3,sys,time,zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
R=runtime.BASE/'quality-repair/20261021-consumer-voice'
inventory=runtime.read(R/'inventory.json')['articles'];states=Counter();reasons=Counter();docs=[]
for item in inventory:
 status=runtime.read(R/item['key']/'status.json');states[status.get('state','pending')]+=1
 if status.get('reason'):reasons[status['reason']]+=1
 if status.get('state')!='complete':continue
 folder=Path(item['root'])/'approved'/item['id'];word=folder/'article.docx';receipt=runtime.read(folder/'receipt.json')
 data=word.read_bytes();assert hashlib.sha256(data).hexdigest()==receipt['word_sha256']
 with zipfile.ZipFile(word) as z:
  assert z.testzip() is None
  ET.fromstring(z.read('word/document.xml'));ET.fromstring(z.read('[Content_Types].xml'))
 docs.append({'key':item['key'],'article':item['id'],'root':item['root'],'word_sha256':receipt['word_sha256'],'bytes':len(data),'xml_crc_ok':True,'has_identity_projection':(folder/'validation_identity.json').exists()})
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 ledger=db.execute('select date,count(*),sum(charged),sum(case when charged is null then reserved else 0 end),sum(case when charged is null then 1 else 0 end) from costs group by date order by date desc limit 2').fetchall()
reports={name:runtime.read(R/(name+'.json')) for name in ('followup-20261021','followup-paused-20261021','identity-recovery-20261021','delivered-recovery-20261021')}
value={'at':time.time(),'states':dict(states),'reasons':dict(reasons),'ledger':ledger,'verified_complete_docs':docs,
 'passes':{name:{'selected':len(r.get('selected',r.get('results',[]))),'processed':len(r.get('results',[])),'finished':bool(r.get('finished_at')),'results':dict(Counter(i['state'] for i in r.get('results',[]))),'controls_unchanged':all(i.get('original_job_control_unchanged',True) for i in r.get('results',[]))} for name,r in reports.items()},
 'observation':runtime.read(Path('/opt/monitor/geo-content/observations/20261021-22/latest.json')).get('assessment')}
Path('/tmp/geo-followup-summary.json').write_text(json.dumps(value,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in value.items() if k not in ('reasons','verified_complete_docs')},ensure_ascii=False))
