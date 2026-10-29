"""Update only the four deployed reader files in the recovery package."""
import hashlib,json,shutil,zipfile
from pathlib import Path
W=Path(__file__).resolve().parents[2];D=Path(__file__).resolve().parent
release=W/'geo-monitor-deploy/releases/20261015/unified-current'
mapping={'yuanbao-deploy/native_core.py':'/home/user/redroid-yuanbao/native_core.py',
 'yuanbao-deploy/native_client.py':'/home/user/redroid-yuanbao/native_client.py',
 'yuanbao-deploy/stored_replacements.py':'/home/user/redroid-yuanbao/stored_replacements.py',
 'yuanbao-deploy/tests/test_stored_replacements.py':'/home/user/redroid-yuanbao/tests/test_stored_replacements.py'}
expected=json.loads((D/'candidate-manifest.json').read_text())
paths=[release/'manifest.json',W/'source-snapshot/local-manifest.json',W/'source-snapshot/production-manifest.json']
backup=D/'mapping-before';backup.mkdir(exist_ok=False)
for p in paths:shutil.copy2(p,backup/(p.parent.name+'-'+p.name))
shutil.copy2(release/'source.zip',backup/'source.zip')
objects=[json.loads(p.read_text('utf8')) for p in paths]
for source,target in mapping.items():
 data=(W/source).read_bytes();digest=hashlib.sha256(data).hexdigest();assert digest==expected[source.removeprefix('yuanbao-deploy/')]
 row={'source':source,'server':target,'sha256':digest,'bytes':len(data)}
 for obj in objects[:2]:
  found=[v for v in obj['files'] if v['server']==target]
  if found:found[0].update(row)
  else:obj['files'].append(row.copy())
 snapshot='server/'+target.lstrip('/');found=[v for v in objects[2]['files'] if v['server']==target]
 row={'snapshot':snapshot,'server':target,'sha256':digest,'bytes':len(data)}
 if found:found[0].update(row)
 else:objects[2]['files'].append(row)
 for dest in (W/'source-snapshot/local'/source,W/'source-snapshot'/snapshot):dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
tmp=release/'source.video23.tmp'
with zipfile.ZipFile(release/'source.zip') as old,zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as out:
 for info in old.infolist():
  if info.filename not in mapping:out.writestr(info,old.read(info.filename))
 for name in mapping:out.writestr(name,(W/name).read_bytes())
tmp.replace(release/'source.zip');digest=hashlib.sha256((release/'source.zip').read_bytes()).hexdigest()
for obj in objects[:2]:obj['zip_sha256']=digest
for path,obj in zip(paths,objects):
 old=path.read_bytes();nl='\r\n' if b'\r\n' in old else '\n';text=json.dumps(obj,ensure_ascii=False,indent=2).replace('\n',nl)+(nl if old.endswith(b'\n') else '')
 path.write_bytes(text.encode('utf8'))
(D/'mapping-to-verify.json').write_text(json.dumps(objects[0],ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'recovery_mapping_files':len(objects[0]['files']),'updated_files':list(mapping),'article_candidates_not_packaged':True}))
