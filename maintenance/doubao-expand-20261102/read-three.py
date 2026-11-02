import subprocess
r=subprocess.run(['/home/user/redroid-doubao/worker-venv/bin/python','-u','/tmp/doubao-title-only.py','3'],timeout=130,capture_output=True,text=True);print(r.stdout,r.stderr)
