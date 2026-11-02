import subprocess,concurrent.futures
def run(n):return subprocess.run(['/home/user/redroid-doubao/worker-venv/bin/python','-u','-B','/tmp/doubao-ref-sample.py',str(n)],capture_output=True,text=True,timeout=180)
with concurrent.futures.ThreadPoolExecutor(2) as pool:
 for f in concurrent.futures.as_completed([pool.submit(run,n) for n in (3,4)]):
  r=f.result();print(r.stdout,r.stderr,flush=True)
