import subprocess
from pathlib import Path
for n in (3,4):
 args=['/home/user/redroid-doubao/worker-venv/bin/python','-u','/tmp/doubao-url-panel.py',str(n)]
 for p in Path('/proc').glob('[0-9]*/cmdline'):
  try:
   if p.read_bytes().decode().rstrip('\0').split('\0')==args:subprocess.run(['kill','-TERM',p.parent.name])
  except (FileNotFoundError,PermissionError,UnicodeError):pass
 code="""import sys,uiautomator2 as u,xml.etree.ElementTree as E,time
d=u.connect('127.0.0.1:556'+sys.argv[1]);p='com.larus.nova:id/'
for j in range(5):
 ns=list(E.fromstring(d.dump_hierarchy()).iter('node'));print('state',d.app_current(),[(x.get('resource-id','').split('/')[-1],x.get('text','')[:30]) for x in ns if x.get('resource-id','').endswith(('tv_reference_title','tv_reference_index','btn_back','input_text'))][:16])
 if d(resourceId=p+'tv_reference_index').exists:break
 if d(resourceId=p+'tv_reference_title').exists:d(resourceId=p+'tv_reference_title').click();time.sleep(1);continue
 if d(resourceId=p+'input_text').exists:d.swipe(350,340,350,900,.45)
 else:d.press('back')
 time.sleep(.7)
"""
 print(n,subprocess.run([args[0],'-u','-c',code,str(n)],capture_output=True,text=True,timeout=50).stdout,flush=True)
