import subprocess
code="""import uiautomator2 as u,xml.etree.ElementTree as E;d=u.connect('127.0.0.1:5563');print(d.app_current());print([(v.get('resource-id','').split('/')[-1],v.get('text','')[:65]) for v in E.fromstring(d.dump_hierarchy()).iter('node') if v.get('resource-id','').endswith(('tv_reference_title','tv_reference_index','tv_reference_content','input_text','title'))][:32])"""
r=subprocess.run(['/home/user/redroid-doubao/worker-venv/bin/python','-c',code],capture_output=True,text=True,timeout=20);print(r.stdout,r.stderr)
