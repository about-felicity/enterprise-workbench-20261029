import sys,time,re,subprocess,xml.etree.ElementTree as E
from pathlib import Path
import uiautomator2 as u
n=int(sys.argv[1]);d=u.connect(f'127.0.0.1:556{n}');p='com.larus.nova:id/';out=Path('/home/user/redroid-doubao/expansion-20261102')
def ns():return list(E.fromstring(d.dump_hierarchy()).iter('node'))
def get(x,k):return [v for v in x if v.get('resource-id')==p+k]
def shot(k):
 data=subprocess.check_output(['docker','exec',f'doubao-hpe14-account{n}','screencap','-p']);assert data.startswith(b'\x89PNG');(out/f'account{n}-{k}.png').write_bytes(data)
d.shell(['am','start','-W','-n','com.larus.nova/com.larus.home.impl.alias.AliasActivity1'])
for i in range(15):
 x=ns()
 if get(x,'tv_reference_index'):d.press('back');time.sleep(.6);continue
 h=get(x,'tv_reference_title')
 if h:
  title=h[0].get('text');assert re.search(r'参考\s*'+str({3:12,4:4}[n])+r'\s*篇',title),title
  shot('answer');a,b,c,e=map(int,re.findall(r'\d+',h[0].get('bounds')));d.shell(['input','tap',str((a+c)//2),str((b+e)//2)]);time.sleep(.9)
  x=ns()
  if not get(x,'tv_reference_index'):continue
  if n==3:
   d.shell(['input','swipe','350','760','350','230','450']);time.sleep(.6)
  assert get(ns(),'tv_reference_index');shot('references');print(n,title,flush=True);d.press('back');break
 d.shell(['input','swipe','350','300','350','920','450']);time.sleep(.5)
else:raise RuntimeError('Reference header not visible')
