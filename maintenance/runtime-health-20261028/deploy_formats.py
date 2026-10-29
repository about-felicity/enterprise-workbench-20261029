import hashlib,json,shutil,os,sys,time
from pathlib import Path
D=Path('/opt/monitor/maintenance/creation-formats-20261028');D.mkdir(parents=True,exist_ok=True)
files=[('structure_parser.py','d2f765e8bb823c0a64806038155c7942f29091a6159b7ea5639c7fa17f7bc775'),('full_writer.py','d7db7f317024f119553e592c1c8644a5dce3410132e90ae81bc9ec853af27018')]
release=[]
for name,expected in files:
 target=Path('/opt/monitor/geo-content/engine/geo_source_cards/rewrite_v2')/name
 candidate=Path('/tmp/formats28-'+name)
 assert hashlib.sha256(target.read_bytes()).hexdigest()==expected,name
 compile(candidate.read_text(),str(target),'exec')
 shutil.copy2(target,D/(name+'.before'))
 tmp=target.with_suffix('.new');shutil.copyfile(candidate,tmp);os.chmod(tmp,target.stat().st_mode);os.chown(tmp,target.stat().st_uid,target.stat().st_gid);os.replace(tmp,target)
 release.append({'source':'geo-source-card-collectors/geo_source_cards/rewrite_v2/'+name,'server':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
(D/'release.json').write_text(json.dumps({'files':release},indent=2))
print('DEPLOYED',json.dumps(release))
