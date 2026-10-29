"""Register only the verified resource policy, preserving undeployed candidates."""
import hashlib,json,shutil,zipfile
from pathlib import Path
W=Path(__file__).resolve().parents[2];D=Path(__file__).resolve().parent
source='yuanbao-deploy/config/container_resources.json';target='/home/user/redroid-yuanbao/container_resources.json'
release=W/'geo-monitor-deploy/releases/20261015/unified-current';data=(W/source).read_bytes();sha=hashlib.sha256(data).hexdigest()
assert sha==json.loads((D/'result.json').read_text())['resources_sha256']
paths=[release/'manifest.json',W/'source-snapshot/local-manifest.json',W/'source-snapshot/production-manifest.json']
backup=D/'manifest-before';backup.mkdir(exist_ok=True)
for p in paths:
 dest=backup/(p.parent.name+'-'+p.name)
 assert not dest.exists(),'Do not replace earlier baseline';shutil.copy2(p,dest)
assert not (backup/'source.zip').exists();shutil.copy2(release/'source.zip',backup/'source.zip')
row={'source':source,'server':target,'sha256':sha,'bytes':len(data)};objects=[]
for p in paths[:2]:
 obj=json.loads(p.read_text('utf8'));assert not any(r['server']==target for r in obj['files']);obj['files'].append(row.copy());objects.append(obj)
prod=json.loads(paths[2].read_text('utf8'));snapshot='server/'+target.lstrip('/')
assert not any(r['server']==target for r in prod['files'])
prod['files'].append({'server':target,'snapshot':snapshot,'sha256':sha,'bytes':len(data)});objects.append(prod)
for p in (W/'source-snapshot/local'/source,W/'source-snapshot'/snapshot):p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
tmp=release/'source.memory23.tmp'
with zipfile.ZipFile(release/'source.zip') as old,zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as out:
 for info in old.infolist():out.writestr(info,old.read(info.filename))
 out.writestr(source,data)
tmp.replace(release/'source.zip');digest=hashlib.sha256((release/'source.zip').read_bytes()).hexdigest()
for obj in objects[:2]:obj['zip_sha256']=digest
for p,obj in zip(paths,objects):
 before=p.read_bytes();nl='\r\n' if b'\r\n' in before else '\n'
 text=json.dumps(obj,ensure_ascii=False,indent=2).replace('\n',nl)+(nl if before.endswith(b'\n') else '')
 p.write_bytes(text.encode('utf8'))
print(json.dumps({'resource_sha256':sha,'mapping_count':len(objects[0]['files']),'other_mappings_changed':False}))
