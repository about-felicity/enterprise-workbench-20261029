"""Private DeepSeek session persistence; never logs credential values."""
import json
import os
import time
from pathlib import Path
from geo_source_cards.runtime import runtime_root,atomic_write

ORIGIN='https://chat.deepseek.com'

def profile_path():
    configured=os.environ.get('GEO_DEEPSEEK_PROFILE_DIR')
    if configured:return Path(configured).expanduser().resolve()
    root=runtime_root()
    # GEO tasks and manual login share one account across immutable daily batches.
    if root.name=='collector' and root.parent.parent.name=='batches':
        return root.parents[2]/'profiles/deepseek'
    return root/'web_profiles/deepseek'

def state_path():return profile_path()/'geo-session.json'

def read_state():
    try:
        state=json.loads(state_path().read_text())
        return state if state.get('version')==1 and not state.get('invalidated') else {}
    except (OSError,ValueError):return {}

def write_state(value):
    path=state_path();path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    # atomic_write fsyncs both the file and parent; temporary file is private too.
    temporary=path.with_name(path.name+'.tmp')
    descriptor=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
    with os.fdopen(descriptor,'w') as stream:
        json.dump(value,stream,ensure_ascii=False);stream.flush();os.fsync(stream.fileno())
    if os.name!='nt' and os.geteuid()==0:
        owner=path.parent.stat();os.chown(temporary,owner.st_uid,owner.st_gid)
    os.chmod(temporary,0o600);os.replace(temporary,path)
    if os.name!='nt':
        descriptor=os.open(path.parent,os.O_RDONLY)
        try:os.fsync(descriptor)
        finally:os.close(descriptor)

def provider_cookie(cookie):
    return cookie.get('domain','').lstrip('.') in {'chat.deepseek.com','deepseek.com'}

def health(state,status):
    # Operational evidence only. Tokens/cookie values never enter diagnostic files.
    atomic_write(profile_path()/'geo-session-health.json',json.dumps({
        'status':status,'at':time.time(),'last_checkpoint':state.get('saved_at'),
        'local_storage_keys':len(state.get('local_storage',{})),
        'session_storage_keys':len(state.get('session_storage',{})),
        'cookies':[{'name':c.get('name'),'expires':c.get('expires',-1),'session':c.get('session',False)} for c in state.get('cookies',[])],
    }))

def restore(page):
    state=read_state()
    if not state:return False
    now=time.time()
    existing={(c['name'],c.get('domain'),c.get('path','/')) for c in page.call('Network.getAllCookies').get('cookies',[])}
    cookies=[]
    for cookie in state.get('cookies',[]):
        if not provider_cookie(cookie):continue
        if cookie.get('expires',-1)>0 and cookie['expires']<=now:continue
        if (cookie['name'],cookie.get('domain'),cookie.get('path','/')) in existing:continue
        cookies.append({k:v for k,v in cookie.items() if k in ('name','value','domain','path','secure','httpOnly','expires','sameSite') and not (k=='expires' and v<=0)})
    if cookies:page.call('Network.setCookies',{'cookies':cookies})
    storage={k:state.get(k,{}) for k in ('local_storage','session_storage')}
    script="""(()=>{if(location.origin!==%s)return;const s=%s;
      for(const [k,v] of Object.entries(s.local_storage||{}))if(localStorage.getItem(k)===null)localStorage.setItem(k,v);
      for(const [k,v] of Object.entries(s.session_storage||{}))if(sessionStorage.getItem(k)===null)sessionStorage.setItem(k,v);
    })()"""%(json.dumps(ORIGIN),json.dumps(storage,ensure_ascii=False))
    page.call('Page.addScriptToEvaluateOnNewDocument',{'source':script})
    page.evaluate(script)
    return True

def checkpoint(page):
    storage=page.evaluate("location.origin==='https://chat.deepseek.com'?({local_storage:{...localStorage},session_storage:{...sessionStorage}}):null")
    if not isinstance(storage,dict):return False
    cookies=[c for c in page.call('Network.getAllCookies').get('cookies',[]) if provider_cookie(c)]
    state={'version':1,'saved_at':time.time(),'origin':ORIGIN,'cookies':cookies,**storage}
    write_state(state);health(state,'saved')
    return True

def invalidate():
    # Never restore a session explicitly rejected by the provider.
    previous=read_state();health(previous,'login_required')
    write_state({'version':1,'invalidated':True,'invalidated_at':time.time()})
