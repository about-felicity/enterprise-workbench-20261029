import subprocess,concurrent.futures
def capture(n):
 r=subprocess.run(['/home/user/redroid-doubao/worker-venv/bin/python','-u','/tmp/doubao-screenshot-refs.py',str(n)],capture_output=True,text=True,timeout=110);return n,r.returncode,r.stdout,r.stderr
with concurrent.futures.ThreadPoolExecutor(2) as pool:
 for f in concurrent.futures.as_completed([pool.submit(capture,n) for n in (3,4)]):print(f.result(),flush=True)
