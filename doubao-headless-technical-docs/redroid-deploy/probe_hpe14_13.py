import subprocess,time,os,pathlib,json,xml.etree.ElementTree as ET
c='doubao-hpe14-13-test'; adb='/home/user/redroid-doubao/linux-tools/platform-tools/adb';os.environ['ADBUTILS_ADB_PATH']=adb
for i in range(90):
 s=subprocess.run(['docker','exec',c,'getprop','sys.boot_completed'],capture_output=True,text=True).stdout.strip()
 if s=='1':break
 time.sleep(2)
else:raise RuntimeError('boot timeout')
subprocess.run([adb,'connect','127.0.0.1:5557'],check=True)
subprocess.run([adb,'-s','127.0.0.1:5557','install','-r','/home/user/redroid-doubao/doubao.apk'],check=True)
subprocess.run(['docker','exec',c,'am','start','-W','-n','com.larus.nova/com.larus.home.impl.alias.AliasActivity1'],check=True)
import uiautomator2 as u2
d=u2.connect('127.0.0.1:5557')
for i in range(12):
 time.sleep(10)
 xml=d.dump_hierarchy();ids=[n.get('resource-id') for n in ET.fromstring(xml).iter('node') if n.get('resource-id')]
 p=subprocess.run(['docker','exec',c,'pidof','com.larus.nova'],text=True,capture_output=True).stdout.strip()
 print(json.dumps({'seconds':(i+1)*10,'pid':p,'nodes':len(ids),'input':any('input_text' in s for s in ids)}),flush=True)
 pathlib.Path('/home/user/redroid-doubao/hpe14-13-screen.xml').write_text(xml)
