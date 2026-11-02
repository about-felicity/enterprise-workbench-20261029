from pathlib import Path
import subprocess
b=Path('/home/user/redroid-doubao/worker-venv/bin/python')
code="""import uiautomator2 as u,time,xml.etree.ElementTree as E
d=u.connect('127.0.0.1:5564');d.settings['wait_timeout']=2;p='com.larus.nova:id/'
d(resourceId=p+'back_icon',description='对话列表').click();time.sleep(.8)
ns=list(E.fromstring(d.dump_hierarchy()).iter('node'));print([(x.get('resource-id','').split('/')[-1],x.get('text','')[:70]) for x in ns if x.get('package')=='com.larus.nova' and x.get('text')])
"""
print(subprocess.check_output([str(b),'-c',code],text=True))
