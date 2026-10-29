"""Selectively refresh only the five verified Yuanbao runtime source mappings.

Do not run the full package builder: isolated article candidates are undeployed.
"""
import hashlib,json,shutil,zipfile
from pathlib import Path
W=Path(__file__).resolve().parents[2];D=Path(__file__).resolve().parent
release=W/'geo-monitor-deploy/releases/20261015/unified-current'
mapping={'redroid-deploy/question_only_worker.py':'/home/user/redroid-doubao/geo-batch-code/question_only_worker.py',
 'redroid-deploy/question_only_adapters.py':'/home/user/redroid-doubao/geo-batch-code/question_only_adapters.py',
 'yuanbao-deploy/native_models.js':'/home/user/redroid-yuanbao/native_models.js',
 'yuanbao-deploy/unbound_history.py':'/home/user/redroid-yuanbao/unbound_history.py',
 'yuanbao-deploy/tests/test_unbound_history.py':'/home/user/redroid-yuanbao/tests/test_unbound_history.py'}
def write_json(path,value):
 old=path.read_bytes();newline='\r\n' if b'\r\n' in old else '\n'
 data=json.dumps(value,ensure_ascii=False,indent=2).replace('\n',newline)
 if old.endswith(b'\n'):data+=newline
 path.write_bytes(data.encode('utf-8'))
back=D/'snapshot-before';back.mkdir(exist_ok=True)
paths=[release/'manifest.json',release/'source.zip',W/'source-snapshot/local-manifest.json',W/'source-snapshot/production-manifest.json']
for path in paths:
 dest=back/(path.parent.name+'-'+path.name)
 if not dest.exists():shutil.copy2(path,dest)
manifest=json.loads(paths[0].read_text('utf-8'));local=json.loads(paths[2].read_text('utf-8'));prod=json.loads(paths[3].read_text('utf-8'))
for source,target in mapping.items():
 data=(W/source).read_bytes();digest=hashlib.sha256(data).hexdigest()
 row={'source':source,'server':target,'sha256':digest,'bytes':len(data)}
 for obj,key,val in [(manifest,'source',source),(local,'source',source)]:
  found=[r for r in obj['files'] if r.get(key)==val and r['server']==target]
  if found:found[0].update(row)
  else:obj['files'].append(row.copy())
 snapshot='server/'+target.lstrip('/')
 found=[r for r in prod['files'] if r['server']==target]
 server_row={'snapshot':snapshot,'server':target,'sha256':digest,'bytes':len(data)}
 if found:found[0].update(server_row)
 else:prod['files'].append(server_row)
 for dest in [W/'source-snapshot/local'/source,W/'source-snapshot'/snapshot]:
  dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
tmp=release/'source.yuanbao23.tmp'
with zipfile.ZipFile(paths[1]) as old,zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as out:
 for info in old.infolist():
  if info.filename not in mapping:out.writestr(info,old.read(info.filename))
 for source in mapping:out.writestr(source,(W/source).read_bytes())
tmp.replace(paths[1]);manifest['zip_sha256']=hashlib.sha256(paths[1].read_bytes()).hexdigest()
local['zip_sha256']=manifest['zip_sha256']
write_json(paths[0],manifest);write_json(paths[2],local);write_json(paths[3],prod)
(D/'mapping-to-verify.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'mapping_count':len(manifest['files']),'updated':mapping}))
