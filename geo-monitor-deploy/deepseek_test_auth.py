"""Passive sandbox-only UI probe. Never starts an App, sends a question or exports tokens."""
import fcntl,json,os,sqlite3,sys,time
from pathlib import Path
BASE=Path('/opt/monitor/geo-capture')

def probe():
 os.environ['ADBUTILS_ADB_PATH']='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
 import uiautomator2 as u2
 sys.path.insert(0,'/home/user/redroid-deepseek/code')
 from auth_policy import classify_ui
 d=u2.connect('127.0.0.1:5562')
 if d.app_current().get('package')!='com.deepseek.chat':return {'status':'unknown','message':'当前未在DeepSeek界面，手动测试投屏保持打开'}
 dbpath=Path('/var/lib/docker/volumes/deepseek-manual-test-data/_data/data/com.deepseek.chat/databases/deepseek_chat.db')
 account=False
 if dbpath.exists():
  with sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True) as db:
   account=bool(db.execute('select count(*) from app_user_info where length(token)>0 and length(id)>0').fetchone()[0])
 return classify_ui(d.dump_hierarchy(),account)

def refresh(base=BASE):
 base=Path(base);root=base/'manual-login/deepseek_test';root.mkdir(parents=True,exist_ok=True)
 cache=root/'account-check.json'
 with (root/'account-check.lock').open('a') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return
  try:old=json.loads(cache.read_text())
  except (FileNotFoundError,ValueError):old={}
  if time.time()-old.get('checked_at',0)<10:return
  try:value=probe()
  except Exception:value={'status':'unknown','message':'本次测试账号状态未确认，不判定登录成功；投屏保持打开'}
  value['checked_at']=time.time();temp=cache.with_suffix('.tmp');temp.write_text(json.dumps(value,ensure_ascii=False));temp.chmod(0o600);temp.replace(cache)

if __name__=='__main__':refresh()
