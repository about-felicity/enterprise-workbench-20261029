import subprocess,json,pathlib,shutil
c='doubao-hpe14-13-test';root=pathlib.Path('/home/user/redroid-doubao')
subprocess.run(['docker','exec',c,'am','force-stop','com.larus.nova'],check=True)
vol=json.loads(subprocess.check_output(['docker','volume','inspect','doubao-hpe14-android13-data']))[0]['Mountpoint']
src=json.loads(subprocess.check_output(['docker','volume','inspect','doubao-hpe14-android15-data']))[0]['Mountpoint']
dst=pathlib.Path(vol)/'data/com.larus.nova';uid=dst.stat().st_uid
backup=root/'hpe13-app-before-migration'; assert not backup.exists();shutil.copytree(dst,backup,symlinks=True)
# Copy only this requested App's sandbox; no system/account databases from other apps.
subprocess.run(['cp','-a',str(pathlib.Path(src)/'data/com.larus.nova')+'/.',str(dst)+'/'],check=True)
subprocess.run(['chown','-R',f'{uid}:{uid}',str(dst)],check=True)
print('Copied requested App sandbox to separate Android13 test volume, uid',uid)
subprocess.run(['docker','exec',c,'am','start','-W','-n','com.larus.nova/com.larus.home.impl.alias.AliasActivity1'],check=True)
