
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import os,pathlib,subprocess,hashlib,json,sqlite3,tarfile,time
os.nice(15)
r=pathlib.Path('/home/user/redroid-doubao');b=r/'backups/hpe14-20261006';b.mkdir(parents=True,exist_ok=True,mode=0o700)
image=b/'redroid13-hpe14-image.tar'
if not image.exists():
 partial=image.with_suffix('.tar.part')
 subprocess.run(['docker','save','-o',str(partial),'doubao/redroid:13-hpe14-com1.3'],check=True)
 os.replace(partial,image)
image.chmod(0o600)
with tarfile.open(image) as archive:
 # Docker29's containerd backend identifies this image by OCI manifest digest,
 # which is distinct from the legacy manifest.json Config digest.
 index=json.load(archive.extractfile('index.json'))
 expected='18244ad4ab1c36047438bb9c524d8f8d6f848ee8d7537a98483a26c5dda7601f'
 assert any(e['digest']=='sha256:'+expected for e in index['manifests'])
 assert hashlib.sha256(archive.extractfile('blobs/sha256/'+expected).read()).hexdigest()==expected
digest=hashlib.sha256()
with image.open('rb') as stream:
 for block in iter(lambda:stream.read(8*1024*1024),b''):digest.update(block)
h=digest.hexdigest()
with sqlite3.connect(r/'hpe14-acceptance/tasks.sqlite') as source, sqlite3.connect(b/'tasks-snapshot.sqlite') as dest:source.backup(dest)
(b/'tasks-snapshot.sqlite').chmod(0o600)
files=['unattended_core.py','unattended_worker.py','runtime_preflight.py','compose.hpe14.yaml','redroid-doubao-hpe14-worker.service','redroid-doubao-native-log.service','redroid-doubao-soak24h.service','soak_monitor.py','soak_sequence.py','test_soak_sequence.py','test_unattended.py','HPE14_FIX.md','README.md','UNATTENDED.md','hpe14_report.py','package_hpe14_results.py','backup_hpe14_release.py','backup_android13_volume.py','hpe14-questions.json','hpe14-soak-questions.json','requirements.txt','.gitignore','PROJECT_TREE.md']
with tarfile.open(b/'project-code.tar','w') as t:
 for name in files:t.add(r/name,arcname=name)
(b/'project-code.tar').chmod(0o600)
manifest={'image_file':str(image),'image_bytes':image.stat().st_size,'image_sha256':h,'image_id':subprocess.check_output(['docker','image','inspect','doubao/redroid:13-hpe14-com1.3','--format','{{.Id}}'],text=True).strip(),'queue_snapshot_time':time.time(),'includes_android_login_volume':False,'note':'Live SQLite backup includes WAL safely; full Android volume is separate and preserved.'}
(b/'manifest.json').write_text(json.dumps(manifest,indent=2));(b/'manifest.json').chmod(0o600);print(json.dumps(manifest),flush=True)
