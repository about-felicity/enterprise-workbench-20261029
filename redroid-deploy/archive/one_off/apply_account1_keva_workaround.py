"""Fix the observed account1 Keva mapping collision while preserving in-flight work."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import subprocess,os,json,time,sqlite3,shutil,hashlib
from pathlib import Path
from active_database_accounts import current_uid
os.umask(0o077)
c='doubao-hpe14-13-test';base=Path('/home/user/redroid-doubao')
assert current_uid(c).endswith('385833')
subprocess.run(['systemctl','stop','redroid-geo-products.service'],check=True)
info=json.loads(subprocess.check_output(['docker','inspect',c]))[0]
mount=Path(next(m['Source'] for m in info['Mounts'] if m['Destination']=='/data'))
pid=subprocess.check_output(['docker','exec',c,'pidof','com.larus.nova'],text=True).strip()
maps=subprocess.check_output(['docker','exec',c,'cat','/proc/'+pid+'/maps'],text=True)
libs={l.split()[-1] for l in maps.splitlines() if l.endswith('/lib/arm64/libkeva.so')}
assert len(libs)==1
target=mount/libs.pop().removeprefix('/data/')
assert target.resolve().is_relative_to(mount.resolve())
report=json.loads((base/'account2/workaround-build.json').read_text())
assert hashlib.sha256(target.read_bytes()).hexdigest()==report['original_sha256']
patched=base/'account2/libkeva-openat.so'
assert hashlib.sha256(patched.read_bytes()).hexdigest()==report['patched_sha256']
backup=base/('account1-keva-repair-'+str(int(time.time())));backup.mkdir(mode=0o700)
root=base/'batches/geo-products-21x5-account1-20261014'
with sqlite3.connect(root/'tasks.sqlite') as source,sqlite3.connect(backup/'queue-before.sqlite') as dest:source.backup(dest)
shutil.copy2(root/'bridge_health.json',backup/'health-before.json')
subprocess.run(['docker','exec',c,'am','force-stop','com.larus.nova'],check=True)
app=mount/'data/com.larus.nova'
for folder in ('files/keva','databases'):shutil.copytree(app/folder,backup/folder,copy_function=shutil.copy2)
shutil.copy2(target,backup/'libkeva-original.so')
st=target.stat();temporary=target.with_name('libkeva-openat.tmp')
(backup/'manifest.json').write_text(json.dumps({'target':str(target),'uid':st.st_uid,'gid':st.st_gid,'mode':st.st_mode&0o777,'build':report},indent=2))
shutil.copyfile(patched,temporary);os.chown(temporary,st.st_uid,st.st_gid);temporary.chmod(st.st_mode&0o777);os.replace(temporary,target)
subprocess.run(['docker','exec',c,'am','start','-W','-n','com.larus.nova/com.larus.home.impl.alias.AliasActivity1'],check=True)
print('Account1 Keva library repaired, all cache/message files retained, in-flight task left intact. Backup:',backup,flush=True)
