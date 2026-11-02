import subprocess
code="""import uiautomator2 as u,xml.etree.ElementTree as E
d=u.connect('127.0.0.1:5564');print(d.app_current());x=E.fromstring(d.dump_hierarchy());print([(n.get('resource-id','').split('/')[-1],n.get('text','')[:30],n.get('content-desc','')[:30]) for n in x.iter('node') if n.get('package')=='com.larus.nova' and (n.get('text') or n.get('content-desc'))][-26:])"""
print(subprocess.run(['/home/user/redroid-doubao/worker-venv/bin/python','-c',code],capture_output=True,text=True,timeout=20).stdout)
print(subprocess.run(['journalctl','-u','geo-expand-strict4-20261102','-n','8','--no-pager'],capture_output=True,text=True).stdout)
