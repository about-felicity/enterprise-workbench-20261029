import uiautomator2 as u,sys,time,json,re,xml.etree.ElementTree as E
from pathlib import Path
n=int(sys.argv[1]);r=Path(f'/home/user/redroid-doubao/batches/geo-expand-doubao{n}-20261102-strict')
pay=json.loads(next((r/'outbox').glob('*.json')).read_text())['payload'];items=pay['items'];p='com.larus.nova:id/'
d=u.connect(f'127.0.0.1:556{n}')
def nodes():return list(E.fromstring(d.dump_hierarchy()).iter('node'))
def named(ns,key):return [x for x in ns if x.get('resource-id')==p+key]
def swipe(*coords):d.swipe(*coords,duration=.45);time.sleep(.6)
ns=nodes();print('original answer identity',n,any(''.join(x.get('text','').split())[:24] in ''.join(pay['answerText'].split()) for x in ns if len(x.get('text',''))>=44),flush=True)
assert d.app_current()['package']=='com.larus.nova'
for i in range(12):
 ns=nodes();heads=named(ns,'tv_reference_title')
 if heads:break
 swipe(360,300,360,950)
assert len(heads)==1,'reference header missing'
print('HEADER',n,heads[0].get('text'),flush=True)
d(resourceId=p+'tv_reference_title').click();time.sleep(.8)
seen={};titles=[x['title'] for x in items]
for i in range(22):
 ns=nodes()
 for a,b in zip(named(ns,'tv_reference_index'),named(ns,'tv_reference_content')):
  idx=int(re.search(r'\d+',a.get('text')).group());seen[idx]=b.get('text')
 if len(seen)>=len(items):break
 swipe(350,1090,350,525)
print('COMPARE',n,len(items),len(seen),[(k,v==titles[k-1]) for k,v in sorted(seen.items()) if 1<=k<=len(items)],flush=True)
print('sample',n,list(seen.items())[:1],titles[:1],flush=True)
