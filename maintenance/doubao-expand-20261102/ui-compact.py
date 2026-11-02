import subprocess
code="import uiautomator2 as u,sys,xml.etree.ElementTree as E; d=u.connect(sys.argv[1]); x=d.dump_hierarchy(); print([(n.get('resource-id'),n.get('text'),n.get('content-desc')) for n in E.fromstring(x).iter('node') if n.get('package')=='com.larus.nova' and (n.get('text') or n.get('content-desc') or n.get('resource-id','').endswith(('input_text','back_icon')))])"
for n in (3,4):
 r=subprocess.run(['/home/user/redroid-doubao/worker-venv/bin/python','-c',code,f'127.0.0.1:556{n}'],capture_output=True,text=True,timeout=30);print(n,r.stdout,r.stderr)
