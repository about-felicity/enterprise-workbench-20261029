import subprocess,time
for attempt in range(15):
 r=subprocess.run(['/home/user/geo-editorial/venv/bin/python','/tmp/creation-ui-deploy.py'],capture_output=True,text=True)
 if r.returncode==0:print(r.stdout);break
 if 'Another collector uses this runtime' not in r.stderr and 'Request active; retry' not in r.stderr:print(r.stdout+r.stderr);raise SystemExit(r.returncode)
 if attempt==14:print('Still busy; no release installed.');raise SystemExit(2)
 time.sleep(3)
