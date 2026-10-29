"""Enroll each Windows installation separately; no LAN token in colleague packages."""
import hashlib,json,os,uuid,urllib.request
from pathlib import Path
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None

def atomic(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(path)

def fingerprint():
 machine=''
 if os.name=='nt':
  import winreg
  with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\Microsoft\Cryptography') as k:machine=winreg.QueryValueEx(k,'MachineGuid')[0]
 else:machine=str(uuid.getnode())
 return hashlib.sha256((str(machine)+'\n'+str(Path.home())).encode()).hexdigest()

def prepare(root):
 root=Path(root);config=root/'config';public=json.loads((config/'public_upload.json').read_text(encoding='utf-8-sig'))
 assert public['receiver_url']=='https://1any.top/geo_monitor/collector/deepseek'
 device_path=config/'device.json';fp=fingerprint()
 try:device=json.loads(device_path.read_text(encoding='utf-8'))
 except (OSError,ValueError):device={}
 if device.get('fingerprint')!=fp:
  device={'installation_id':uuid.uuid4().hex,'fingerprint':fp};atomic(device_path,device)
 identity='desktop-'+device['installation_id'];private_path=config/'deepseek_sync.json'
 try:private=json.loads(private_path.read_text(encoding='utf-8'))
 except (OSError,ValueError):private={}
 if private.get('client_id')!=identity:
  private={'enabled':True,'receiver_url':public['receiver_url'],'client_id':identity,'device_id':'deepseek-browser-extension','token':''};atomic(private_path,private)
 if not private.get('token'):
  req=urllib.request.Request(public['receiver_url']+'/api/v1/register',data=json.dumps({'installation_id':device['installation_id']}).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+public['enrollment_token']})
  try:
   opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
   with opener.open(req,timeout=12) as response:reply=json.load(response)
   if not reply.get('ok') or reply.get('client_id')!=identity or len(reply.get('token',''))<24:raise ValueError('registration_unconfirmed')
   private['token']=reply['token'];atomic(private_path,private)
  except Exception:pass
 return private

if __name__=='__main__':
 root=Path(__file__).resolve().parent;p=prepare(root)
 print('Upload device ready' if p.get('token') else 'Offline: captures stay local and registration retries automatically')
