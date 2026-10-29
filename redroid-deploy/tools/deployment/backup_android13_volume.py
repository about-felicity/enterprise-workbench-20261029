"""Consistent backup of this project's own Android volume after its queue drains."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess

def command(*args):
    return subprocess.run(args,check=True,timeout=300)

root=Path('/home/user/redroid-doubao')
backup=root/'backups/hpe14-20261006'
backup.mkdir(parents=True,exist_ok=True,mode=0o700)
with sqlite3.connect(root/'hpe14-acceptance/tasks.sqlite') as db:
    assert db.execute("select count(*) from tasks where state!='completed'").fetchone()[0]==0, 'Do not interrupt an active queue'
container='doubao-hpe14-13-test'
volume='doubao-hpe14-android13-data'
source=Path(json.loads(subprocess.check_output(['docker','volume','inspect',volume]))[0]['Mountpoint'])
docker_root=Path(json.loads(subprocess.check_output(['docker','info','--format','{{json .DockerRootDir}}'])))
assert source.resolve()==(docker_root/'volumes'/volume/'_data').resolve()
archive=backup/'android13-data.tar'
command('systemctl','stop','redroid-doubao-hpe14-worker.service','redroid-doubao-native-log.service')
try:
    command('docker','stop','-t','20',container)
    partial=archive.with_suffix('.tar.part')
    command('nice','-n','15','ionice','-c','2','-n','7','tar','--xattrs','--acls','--numeric-owner','--sparse','-cpf',str(partial),'-C',str(source),'.')
    os.replace(partial,archive)
    archive.chmod(0o600)
finally:
    command('docker','start',container)
    command('systemctl','reset-failed','redroid-doubao-hpe14-worker.service')
    command('systemctl','start','redroid-doubao-hpe14-worker.service','redroid-doubao-native-log.service')
digest=hashlib.sha256()
with archive.open('rb') as file:
    for block in iter(lambda:file.read(8*1024*1024),b''):
        digest.update(block)
result={'file':str(archive),'bytes':archive.stat().st_size,'sha256':digest.hexdigest(),'includes_android_login_volume':True,'consistent_container_stopped_backup':True}
(backup/'android-volume-manifest.json').write_text(json.dumps(result,indent=2))
(backup/'android-volume-manifest.json').chmod(0o600)
print(json.dumps(result),flush=True)
