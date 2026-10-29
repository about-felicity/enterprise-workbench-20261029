"""Verify scoped public route using an existing frozen record only; no new question."""
import json,urllib.request,urllib.error,uuid,time
from pathlib import Path
class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None
op=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
cfg=json.loads(Path('/tmp/deepseek-public-bootstrap.json').read_text());base=cfg['receiver_url']
def call(path,data=None,token=''):
 req=urllib.request.Request(base+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json',**({'Authorization':'Bearer '+token} if token else {})})
 try:
  with op.open(req,timeout=25) as r:return r.status,json.load(r)
 except urllib.error.HTTPError as e:return e.code,{}
assert call('/api/v1/health')[0]==200
assert call('/api/v1/models/deepseek/results',{})[0]==401
assert call('/api/v1/models/yuanbao/results',{})[0]==404
tokens=[];ids=[]
for _ in range(2):
 identity=uuid.uuid4().hex
 status,a=call('/api/v1/register',{'installation_id':identity},cfg['enrollment_token']);assert status==200
 status,b=call('/api/v1/register',{'installation_id':identity},cfg['enrollment_token']);assert status==200 and a==b
 tokens.append(a['token']);ids.append(a['client_id'])
assert tokens[0]!=tokens[1]
done=Path('/opt/monitor/runtime/lan_result_receiver/deepseek/done')
folder=Path('/home/user/redroid-deepseek-account2/batches/geo-panel-deepseek2-20261019-103338-38eaf48a/outbox')
before=len(list(done.glob('*.json')))
selected=None
for path in folder.glob('*.json'):
 env=json.loads(path.read_text());rid=env['request_id'];rp=done/(rid+'.json')
 if rp.exists():
  receipt=json.loads(rp.read_text())
  if receipt.get('stored_run_id'):selected=(env,receipt);break
assert selected,'No existing processed envelope available; do not synthesize production samples'
env,receipt=selected
status,result=call('/api/v1/models/deepseek/results',env,tokens[0])
assert status==200 and result.get('status')=='processed',(status,result)
after=json.loads((done/(env['request_id']+'.json')).read_text())
assert after['stored_run_id']==receipt['stored_run_id'] and len(list(done.glob('*.json')))==before
# Verification devices must not retain upload access.
p=Path('/opt/monitor/geo-capture/public_ingest/clients.json');reg=json.loads(p.read_text())
for c in reg['clients']:
 if c['id'] in ids:c['enabled']=False
tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(reg));tmp.chmod(0o600);tmp.replace(p)
print(json.dumps({'https_health':True,'unauthorized_rejected':True,'other_models_rejected':True,'distinct_device_keys':True,'idempotent_enrollment':True,'existing_receipt_confirmed':True,'no_added_receipts':True,'qa_devices_revoked':True}))
