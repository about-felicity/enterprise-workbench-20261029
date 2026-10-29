
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import subprocess,time,os,pathlib,xml.etree.ElementTree as ET,json
os.environ['ADBUTILS_ADB_PATH']='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
c='doubao-hpe14-test'
def run(*a):return subprocess.check_output(['docker','exec',c,*a],text=True,stderr=subprocess.STDOUT,timeout=20).strip()
for i in range(90):
 if run('/system/bin/getprop','sys.boot_completed')=='1':break
 time.sleep(2)
else:raise RuntimeError('boot timeout')
print('Boot complete',run('/system/bin/getprop','ro.dalvik.vm.native.bridge'),flush=True)
print(run('houdini64','--version'),flush=True)
print(run('am','start','-W','-n','com.larus.nova/com.larus.home.impl.alias.AliasActivity1'),flush=True)
import uiautomator2 as u2
subprocess.run([os.environ['ADBUTILS_ADB_PATH'],'connect','127.0.0.1:5556'],check=True)
d=u2.connect('127.0.0.1:5556')
start=time.time();report=[]
for i in range(18):
 time.sleep(10)
 try:
  xml=d.dump_hierarchy(); nodes=ET.fromstring(xml).iter('node'); ids=[n.get('resource-id') for n in nodes if n.get('resource-id')]
  p=run('pidof','com.larus.nova'); item={'seconds':round(time.time()-start),'pid':p,'input':any('input_text' in s for s in ids),'new_chat':any('create_new_cvs' in s for s in ids),'nodes':len(ids)}
  print(json.dumps(item),flush=True);report.append(item)
  pathlib.Path('/home/user/redroid-doubao/hpe14-screen.xml').write_text(xml)
 except Exception as e:print(type(e).__name__,str(e),flush=True)
pathlib.Path('/home/user/redroid-doubao/hpe14-startup.json').write_text(json.dumps(report))
