import hashlib,json,os,shutil,subprocess
from pathlib import Path
D=Path('/opt/monitor/geo-content/maintenance/20261027-article-title');D.mkdir(parents=True,exist_ok=True)
rows=[('runtime.py','/opt/monitor/geo-content/creation/runtime.py','048331b5b4ac97cbdb08bf1ba2b92bcf213104869fbc8bc12a7f9948031d4eab'),('integration.py','/opt/monitor/geo-content/engine/geo_source_cards/rewrite_v2/integration.py','c5ef64f601915584a6365de440e5801d0312106acfe588965137d9299dd2232c'),('full_writer.py','/opt/monitor/geo-content/engine/geo_source_cards/rewrite_v2/full_writer.py','b3fd2109ef1f649b7dcce68891e41de1bb18c52523236647a0acdcdfe38dc365'),('article_title.py','/opt/monitor/geo-content/engine/geo_source_cards/article_title.py',None)]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,target,expected in rows:
 p=Path(target);assert (sha(p) if p.exists() else None)==expected,target
for name,target,_ in reversed(rows):
 p=Path(target)
 if p.exists():shutil.copy2(p,D/(name+'.before'))
 tmp=p.with_suffix('.title.tmp');shutil.copy2(Path('/tmp/article-title-stage')/name,tmp);tmp.chmod(0o644);os.replace(tmp,p)
subprocess.run(['systemctl','restart','geo-content-api'],check=True,timeout=40)
print(json.dumps({'files':[{'server':target,'sha256':sha(Path(target))} for _,target,_ in rows]}))
