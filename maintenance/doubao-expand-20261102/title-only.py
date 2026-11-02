import uiautomator2 as u,sys,time,re,json,xml.etree.ElementTree as E
from pathlib import Path
n=int(sys.argv[1]);d=u.connect('127.0.0.1:556'+str(n));d.settings['wait_timeout']=1
p='com.larus.nova:id/';r=Path(f'/home/user/redroid-doubao/batches/geo-expand-doubao{n}-20261102-strict');pay=json.loads(next((r/'outbox').glob('*.json')).read_text())['payload']
def nodes():return list(E.fromstring(d.dump_hierarchy()).iter('node'))
def named(ns,k):return [v for v in ns if v.get('resource-id')==p+k]
def tap(node):
 x,y,a,b=map(int,re.findall(r'\d+',node.get('bounds')));d.shell(['input','tap',str((x+a)//2),str((y+b)//2)]);time.sleep(.6)
def swipe(x,y,a,b):d.shell(['input','swipe',str(x),str(y),str(a),str(b),'450']);time.sleep(.5)
d.shell(['am','start','-W','-n','com.larus.nova/com.larus.home.impl.alias.AliasActivity1'])
seen={};headers=set();matches=set();first=[]
for j in range(30):
 ns=nodes()
 for h in named(ns,'tv_reference_title'):headers.add(h.get('text'))
 titles=named(ns,'tv_reference_content')
 if titles:
  for t in titles:
   title=t.get('text');seen[title]=1
   for i,v in enumerate(pay['items'],1):
    if v['title']==title:matches.add(i)
   if len(first)<4 and title not in first:first.append(title)
  if len(matches)==len(pay['items']):break
  swipe(300,1090,300,575)
 elif named(ns,'tv_reference_title'):tap(named(ns,'tv_reference_title')[0])
 elif named(ns,'input_text'):swipe(325,285,325,900)
 else:d.press('back');time.sleep(.3)
print(n,'HEAD',headers,'matched',sorted(matches),'sample',first,'expected',pay['items'][0]['title'],flush=True)
if named(nodes(),'tv_reference_content'):d.press('back')
