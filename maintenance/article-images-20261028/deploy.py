import json,hashlib,os,shutil,subprocess
from pathlib import Path
D=Path('/opt/monitor/maintenance/article-images-20261028');D.mkdir(parents=True,exist_ok=True)
expected={'runtime.py':'7c523249c1f41a4512a66967f1feb19129ad5ff27748f77fafb2804eae30d0c4','article_export.py':'90193a70ddaef4bc9e55be446bacb0c97f36007e2f4157a5dad45f4cab881963','panel.html':'2d830ea435cf31123a4b612c90210e7f72c36c0a38955753a3c7ac52b82d6176','article_images.py':None}
root=Path('/opt/monitor/geo-content/creation')
for name,sha in expected.items():
 p=root/name
 assert (not p.exists()) if sha is None else hashlib.sha256(p.read_bytes()).hexdigest()==sha,name
 if name.endswith('.py'):compile((Path('/tmp')/('image28-'+name)).read_text('utf-8-sig'),name,'exec')
release=[]
for name in expected:
 p=root/name;candidate=Path('/tmp')/('image28-'+name)
 if p.exists():shutil.copy2(p,D/(name+'.before'))
 temp=p.with_suffix('.new');shutil.copyfile(candidate,temp);os.chmod(temp,0o644);os.replace(temp,p)
 release.append({'source':'geo-monitor-deploy/creation/'+name,'server':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(D/'release.json').write_text(json.dumps({'files':release},indent=2))
subprocess.run(['systemctl','restart','geo-content-api'],check=True)
print('deployed')
