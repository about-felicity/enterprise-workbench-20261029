"""Install a backed-up, hash-checked Keva workaround only in account2."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
from pathlib import Path
import subprocess,json,time,os,hashlib,shutil,sqlite3
from active_database_accounts import current_uid
os.umask(0o077)
c='doubao-hpe14-account2'
base=Path('/home/user/redroid-doubao')
assert current_uid(c).endswith('066524')
assert subprocess.run(['systemctl','is-active','redroid-geo-products-account2.service'],capture_output=True,text=True).stdout.strip() in ('inactive','failed')
info=json.loads(subprocess.check_output(['docker','inspect',c]))[0]
mount=Path(next(m['Source'] for m in info['Mounts'] if m['Destination']=='/data'))
pid=subprocess.check_output(['docker','exec',c,'pidof','com.larus.nova'],text=True).strip()
maps=subprocess.check_output(['docker','exec',c,'cat','/proc/'+pid+'/maps'],text=True)
libs={line.split()[-1] for line in maps.splitlines() if line.endswith('/lib/arm64/libkeva.so')}
assert len(libs)==1
android_lib=libs.pop()
target=mount/android_lib.removeprefix('/data/')
assert target.resolve().is_relative_to(mount.resolve())
report=json.loads((base/'account2/workaround-build.json').read_text())
assert hashlib.sha256(target.read_bytes()).hexdigest()==report['original_sha256']
patched=base/'account2/libkeva-openat.so'
assert hashlib.sha256(patched.read_bytes()).hexdigest()==report['patched_sha256']
backup=base/'account2'/('openat-repair-'+str(int(time.time())))
backup.mkdir(mode=0o700)
batch=base/'batches/geo-products-21x5-account2-relogin-20261013'
with sqlite3.connect(batch/'tasks.sqlite') as source, sqlite3.connect(backup/'tasks-before.sqlite') as dest: source.backup(dest)
shutil.copy2(batch/'bridge_health.json',backup/'bridge_health-before.json')
subprocess.run(['docker','exec',c,'am','force-stop','com.larus.nova'],check=True)
app=mount/'data/com.larus.nova'
for directory in ('files/keva','databases','shared_prefs'):
    src=app/directory
    if src.exists(): shutil.copytree(src,backup/directory,copy_function=shutil.copy2)
shutil.copy2(target,backup/'libkeva-original.so')
st=target.stat()
manifest={'time':time.time(),'container':c,'android_library':android_lib,'host_library':str(target),'original_uid':st.st_uid,'original_gid':st.st_gid,'mode':st.st_mode&0o777,'build':report}
(backup/'manifest.json').write_text(json.dumps(manifest,indent=2))
tmp=target.with_name('libkeva-openat.tmp')
shutil.copyfile(patched,tmp);os.chown(tmp,st.st_uid,st.st_gid);tmp.chmod(st.st_mode&0o777)
os.replace(tmp,target)
assert hashlib.sha256(target.read_bytes()).hexdigest()==report['patched_sha256']
print('Account2 library replaced; cache/database files retained; backup:',backup,flush=True)
subprocess.run(['docker','exec',c,'am','start','-W','-n','com.larus.nova/com.larus.home.impl.alias.AliasActivity1'],check=True)
