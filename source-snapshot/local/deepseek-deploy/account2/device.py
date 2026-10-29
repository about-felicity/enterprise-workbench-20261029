"""Dedicated official DeepSeek Android App. No web-session import or API sends."""
import os
import sqlite3
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

CONTAINER='deepseek-hpe14-account2'
SERIAL='127.0.0.1:5561'
PACKAGE='com.deepseek.chat'
ADB='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
VERSION=281
LANDING_GREETINGS=frozenset({'嗨！今天想聊些什么？','你好，我能帮什么忙吗？'})

def shell(*args,timeout=20):
 return subprocess.check_output(['docker','exec',CONTAINER,*args],timeout=timeout)

def device():
 os.environ['ADBUTILS_ADB_PATH']=ADB
 subprocess.run([ADB,'connect',SERIAL],capture_output=True,check=True,timeout=12)
 import uiautomator2 as u2
 return u2.connect(SERIAL)

def auth(d=None):
 d=d or device()
 for _ in range(3):
  result=_auth(d)
  if result['status']!='unknown':return result
  time.sleep(.25)
 return result

def _auth(d):
 d=d or device()
 if d.app_info(PACKAGE).get('versionCode')!=VERSION:
  return {'status':'unknown','message':'DeepSeek App版本已变化，需要检查采集兼容性'}
 if d.app_current().get('package')!=PACKAGE:
  return {'status':'unknown','message':'请打开DeepSeek App后校验'}
 xml=d.dump_hierarchy()
 account_path=Path('/var/lib/docker/volumes/'+CONTAINER+'-data/_data/data/'+PACKAGE+'/databases/deepseek_chat.db')
 account=False
 if account_path.exists():
  with sqlite3.connect(account_path.as_uri()+'?mode=ro',uri=True) as db:
   account=bool(db.execute("select count(*) from app_user_info where length(token)>0 and length(id)>0").fetchone()[0])
 from auth_policy import classify_ui
 return classify_ui(xml,account,PACKAGE)

if __name__=='__main__':
 import json
 try:result=auth()
 except Exception:result={'status':'unknown','message':'安卓App暂不可达，稍后自动重试；没有发送问题'}
 print(json.dumps(result,ensure_ascii=False))
