import json,os,hashlib,shutil,subprocess,tarfile,tempfile,time
from pathlib import Path
base=Path('/opt/monitor/geo-content/maintenance/token-efficiency-20261029');base.mkdir(parents=True,exist_ok=True)
engine=Path('/opt/monitor/geo-content/engine');target=engine/'geo_source_cards/rewrite_v2/full_writer.py';stage=base/'stage';stage.mkdir(exist_ok=True)
shutil.copytree(engine/'geo_source_cards',stage/'geo_source_cards',dirs_exist_ok=True)
with tarfile.open('/tmp/token-efficiency-20261029.tar.gz') as t:
 for n in ['full_writer.py','test_prompt_efficiency.py','test_rewrite_v2.py']:
  (stage/('geo_source_cards/rewrite_v2/full_writer.py' if n=='full_writer.py' else n)).write_bytes(t.extractfile(n).read())
env={**os.environ,'PYTHONPATH':str(stage)+':/opt/monitor/geo-content'}
for name in ['test_prompt_efficiency.py','test_rewrite_v2.py']:
 cmd=['/home/user/geo-editorial/venv/bin/python','-B','-m','unittest','discover','-s',str(stage),'-p',name]
 r=subprocess.run(cmd,capture_output=True,text=True,env=env,timeout=180);print(r.stdout+r.stderr,flush=True);assert r.returncode==0
assert hashlib.sha256(target.read_bytes()).hexdigest()=='6ef0868948377426f07fe8bfb397431caee83e0ab4f2ee771e99af42349ed6e5'
backup=base/'full_writer.before.py';assert not backup.exists();shutil.copy2(target,backup)
tmp=target.with_suffix('.installing');shutil.copy2(stage/'geo_source_cards/rewrite_v2/full_writer.py',tmp);tmp.chmod(0o644);os.replace(tmp,target)
# Creation worker launches a fresh Python process per execution quantum: no restart or paid replay.
release={'at':time.time(),'tests':45,'restarted_services':[],'new_paid_calls':0,'files':[{'source':'geo-source-card-collectors/geo_source_cards/rewrite_v2/full_writer.py','server':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}]}
(base/'release.json').write_text(json.dumps(release,indent=2));print(json.dumps(release),flush=True)
