import subprocess
r=subprocess.run(['/home/user/geo-editorial/venv/bin/python','-B','/tmp/eye-budget040-recover.py'],timeout=480)
raise SystemExit(r.returncode)
