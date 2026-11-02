import subprocess
code="""import uiautomator2 as u,sys,xml.etree.ElementTree as E;d=u.connect('127.0.0.1:556'+sys.argv[1]); ns=list(E.fromstring(d.dump_hierarchy()).iter('node')); print([(n.get('resource-id','').split('/')[-1],n.get('text','')[:12],n.get('bounds')) for n in ns if 'reference' in n.get('resource-id','') or n.get('scrollable')=='true'][:50])"""
for n in (3,4):print(n,subprocess.run(['/home/user/redroid-doubao/worker-venv/bin/python','-c',code,str(n)],capture_output=True,text=True,timeout=20).stdout)
