"""Exact normal UI actions using Compose accessibility snapshots; never replay send."""
from device import device,auth,PACKAGE,shell,LANDING_GREETINGS
import re,sys,time,xml.etree.ElementTree as ET
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from unattended_core import DataError

class Android:
 def __init__(self):
  self.device=device()
  if self.device.app_current().get('package')!=PACKAGE:shell('am','start','-W','-n',PACKAGE+'/.MainActivity')
 def tree(self):return ET.fromstring(self.device.dump_hierarchy())
 def wait_tree(self,predicate,seconds=8):
  until=time.monotonic()+seconds
  while True:
   root=self.tree()
   if predicate(root):return root
   if time.monotonic()>until:raise DataError('App layout did not settle')
   time.sleep(.3)
 def find(self,root,**attrs):
  return [n for n in root.iter('node') if n.get('package')==PACKAGE and all(n.get(k)==v for k,v in attrs.items())]
 def unique(self,root,**attrs):
  found=self.find(root,**attrs)
  if len(found)!=1:raise DataError('Unique App control not proven: '+','.join(attrs))
  return found[0]
 def tap(self,node):
  values=[int(v) for v in re.findall(r'\d+',node.get('bounds',''))]
  if len(values)!=4:raise DataError('App control bounds missing')
  l,t,r,b=values
  if not(0<=l<r<=720 and 0<=t<b<=1280):raise DataError('App control bounds invalid')
  self.device.shell(['input','tap',str((l+r)//2),str((t+b)//2)])
 def mode(self,label):
  root=self.wait_tree(lambda r:len(self.find(r,text=label))==1);node=self.unique(root,text=label);parents={c:p for p in root.iter() for c in p}
  for _ in range(8):
   if node.get('clickable')=='true':return node.get('checked')=='true' or node.get('selected')=='true',node
   node=parents.get(node)
   if node is None:break
  raise DataError('App mode state not exposed')
 def enforce_modes(self):
  for label,wanted in [('智能搜索',True),('深度思考',False)]:
   on,node=self.mode(label)
   if on!=wanted:self.tap(node);time.sleep(.5)
   if self.mode(label)[0]!=wanted:raise DataError('App search/thinking state not proven')
 def fresh_landing(self,root):
  # Welcome copy is randomized by the App; prove layout rather than its wording.
  nodes=[n for n in root.iter('node') if n.get('package')==PACKAGE]
  editors=[n for n in nodes if n.get('class')=='android.widget.EditText']
  labels={n.get('text','') for n in nodes}
  welcome=[n for n in nodes if n.get('class')=='android.widget.TextView' and n.get('text','').strip() and n.get('text') not in {'深度思考','智能搜索'}]
  actions={n.get('content-desc','') for n in nodes}
  return (len(editors)==1 and editors[0].get('text') in {'','发消息'}
          and {'深度思考','智能搜索'}<=labels and len(welcome)==1
          and '开启新对话' in actions
          and not actions.intersection({'复制','重新生成','停止生成','分享'}))
 def ready(self):
  d=self.device
  if auth(d)['status']!='ready':raise DataError('DeepSeek App login or readiness required')
  self.tap(self.unique(self.tree(),**{'content-desc':'开启新对话'}));time.sleep(.6)
  root=self.tree()
  if not self.find(root,**{'class':'android.widget.EditText'}):
   self.tap(self.unique(root,text='发消息或按住说话'));time.sleep(.5)
  fresh=self.fresh_landing
  root=self.wait_tree(lambda r:len(self.find(r,**{'class':'android.widget.EditText'}))==1 and fresh(r));edit=self.unique(root,**{'class':'android.widget.EditText'})
  if edit.get('text') not in {'','发消息'}:raise DataError('New-chat editor is not empty')
  if not fresh(root):raise DataError('Fresh landing page not proven')
  self.enforce_modes();d.set_input_ime()
 def send(self,wire,before_click):
  d=self.device;root=self.tree();edit=self.unique(root,**{'class':'android.widget.EditText'})
  if edit.get('text') not in {'','发消息'}:raise DataError('Editor changed before exact question input')
  self.tap(edit);d.send_keys(wire,clear=True);time.sleep(.4)
  root=self.tree();edit=self.unique(root,**{'class':'android.widget.EditText'})
  if edit.get('text')!=wire:raise DataError('Exact DeepSeek question not present')
  self.enforce_modes()
  root=self.tree();button=self.unique(root,**{'content-desc':'发送'})
  if button.get('enabled')!='true':raise DataError('DeepSeek send control not enabled')
  if self.unique(root,**{'class':'android.widget.EditText'}).get('text')!=wire:raise DataError('Input changed before send')
  before_click();self.tap(button)
 def evidence(self,root,task_id):
  self.device.screenshot().save(root/(task_id+'.png'))
  (root/(task_id+'.xml')).write_text(self.device.dump_hierarchy(),encoding='utf8')

def make_android(*_):return Android()
