"""Deploy persistence at the next normal worker launch, without stopping collection."""
import hashlib,json,os,shutil,sys,time
from pathlib import Path
BASE=Path('/opt/monitor/geo-capture');ROOT=BASE/'maintenance/20261016-deepseek-session'
SITE=BASE/'venv/lib/python3.10/site-packages/web_collectors';STAGE=ROOT/'stage/web_collectors'
pointer=ROOT/'release.json'
assert not pointer.exists(),'Inspect existing deployment before repeating'
original=BASE/'batches/geo-panel-deepseek-20261016-094039-dc64b7e1/collector/web_profiles/deepseek'
shared=BASE/'profiles/deepseek';shared.parent.mkdir(mode=0o700,exist_ok=True)
owner=original.stat();os.chown(shared.parent,owner.st_uid,owner.st_gid)
if shared.exists():assert shared.resolve()==original.resolve()
else:shared.symlink_to(original,target_is_directory=True)
os.chmod(original,0o700)
sys.path.insert(0,str(ROOT/'stage'))
from web_collectors.browser import SitePage
from web_collectors.config import site_config
from web_collectors.session_store import checkpoint,state_path
os.environ['GEO_DEEPSEEK_PROFILE_DIR']=str(shared)
os.environ['GEO_DEEPSEEK_PORT']='9514'
saved=False
try:
 page=SitePage(site_config('deepseek'))
 try:
  ready=page.evaluate("location.origin==='https://chat.deepseek.com' && !!localStorage.getItem('userToken') && !!document.querySelector('textarea,[contenteditable=true]') && !/\\/(login|sign[-_]?in)(\\/|$)/i.test(location.pathname)")
  if ready:saved=checkpoint(page)
 finally:page.ws.close()
except Exception:
 pass # An already exited browser needs manual login; never manufacture a saved session.
backup=ROOT/'backup';backup.mkdir()
hashes={}
for name in ('browser.py','collector.py','session_store.py'):
 target=SITE/name
 if target.exists():shutil.copy2(target,backup/name)
 staged=target.with_suffix('.session-new');shutil.copy2(STAGE/name,staged);staged.chmod(0o644);staged.replace(target)
 hashes[name]=hashlib.sha256(target.read_bytes()).hexdigest()
data={'at':time.time(),'files':hashes,'shared_profile':str(shared),'existing_profile':str(original),'profile_moved':False,'collectors_restarted':False,'initial_checkpoint':saved,'state_permissions':oct(state_path().stat().st_mode&0o777) if state_path().exists() else None}
pointer.write_text(json.dumps(data,ensure_ascii=False,indent=2));print(json.dumps(data,ensure_ascii=False))
