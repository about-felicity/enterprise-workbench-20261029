import subprocess
code="import uiautomator2 as u; import sys; d=u.connect(sys.argv[1]); print(d.app_current()); print(d.dump_hierarchy())"
for n in (3,4):
 print('XML',n,subprocess.run(['/home/user/redroid-doubao/worker-venv/bin/python','-c',code,f'127.0.0.1:556{n}'],capture_output=True,text=True,timeout=30).stdout)
