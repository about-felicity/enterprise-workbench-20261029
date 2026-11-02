import uiautomator2 as u,sys,time,re,json,xml.etree.ElementTree as E
from urllib.parse import urlsplit,parse_qsl,urlunsplit,urlencode
from pathlib import Path
n=int(sys.argv[1]);p='com.larus.nova:id/';d=u.connect(f'127.0.0.1:556{n}');root=Path(f'/home/user/redroid-doubao/batches/geo-expand-doubao{n}-20261102-strict')
items=json.loads(next((root/'outbox').glob('*.json')).read_text())['payload']['items']
def ns():return list(E.fromstring(d.dump_hierarchy()).iter('node'))
def get(nodes,rid):return [x for x in nodes if x.get('resource-id')==p+rid]
def tap(x):
 a,b,c,e=map(int,re.findall(r'\d+',x.get('bounds')));d.click((a+c)//2,(b+e)//2);time.sleep(.6)
def norm(url):
 a=urlsplit(url);qs=parse_qsl(a.query,keep_blank_values=True)
 if a.hostname=='seclink.bytedance.com' and dict(qs).get('target'):return norm(dict(qs)['target'])
 return urlunsplit((a.scheme,a.netloc,a.path,urlencode([(k,v) for k,v in qs if k not in {'use_xbridge3','loader_name','need_sec_link','sec_link_scene','theme'}]),a.fragment))
def sheet():
 for i in range(6):
  nodes=ns()
  if get(nodes,'tv_reference_index'):return
  h=get(nodes,'tv_reference_title')
  if h:tap(h[0])
  else:d.swipe(350,330,350,850,.45)
 raise RuntimeError('sheet unavailable')
def page():
 nodes=ns();return list(zip(get(nodes,'tv_reference_index'),get(nodes,'tv_reference_content')))
sheet()
seen={};urls={};skips={}
for index,item in enumerate(items,1):
 try:
  sheet()
  for j in range(12):
   rows=page();visible=[(int(re.search(r'\d+',a.get('text')).group()),b) for a,b in rows]
   found=next((b for k,b in visible if k==index and b.get('text')==item['title']),None)
   if found is not None:break
   if visible and index<min(k for k,b in visible):d.swipe(340,620,340,1090,.4)
   else:d.swipe(350,1100,350,530,.4)
  if found is None:raise RuntimeError('index/title not visible')
  seen[index]=True;tap(found)
  share=d(resourceId=p+'btn_share')
  if not share.wait(timeout=4):raise RuntimeError('no share')
  share.click();link=d(text='复制链接')
  if not link.wait(timeout=3):raise RuntimeError('no copy')
  d.set_clipboard('ref-audit');link.click();time.sleep(.45);raw=d.clipboard
  urls[index]=norm(raw)==norm(item['url']);print('url',n,index,urls[index],flush=True)
 except Exception as e:skips[index]=str(e)[:65]
 finally:
  if d(resourceId=p+'btn_back').exists:d(resourceId=p+'btn_back').click()
  elif not d(resourceId=p+'tv_reference_title').exists and not d(resourceId=p+'tv_reference_index').exists:d.press('back')
 print('progress',n,index,len(seen),len(urls),skips.get(index,''),flush=True)
print('FINAL',n,len(seen),urls,skips,flush=True)
if d(resourceId=p+'tv_reference_index').exists:d.press('back')
