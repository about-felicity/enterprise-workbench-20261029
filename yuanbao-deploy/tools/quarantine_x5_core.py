"""Preserve the incompatible optional X5 core and let SDK choose system fallback."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

BASE=Path('/home/user/redroid-yuanbao')
NAME='yuanbao-hpe14-android13'
PACKAGE='com.tencent.hunyuan.app.chat'

def run(*args):
    return subprocess.check_output(args,text=True,stderr=subprocess.STDOUT,timeout=45).strip()

def main():
    info=json.loads(run('docker','inspect',NAME))[0]
    assert info['Config']['Labels'].get('geo.collector')=='yuanbao'
    mount=next(m for m in info['Mounts'] if m['Destination']=='/data')
    assert mount['Name']=='yuanbao-hpe14-android13-data'
    app=Path(mount['Source'])/'data'/PACKAGE
    source=app/'app_tbs_64/core_share'
    assert source.resolve().parent==app.resolve()/'app_tbs_64'
    destination=BASE/'compat/x5-core-before'
    manifest=BASE/'compat/x5-quarantine.json'
    assert not destination.exists() and not manifest.exists(), 'Already attempted; inspect instead of repeating'
    assert (source/'libmttwebview.so').is_file()
    entries=[]
    for p in source.rglob('*'):
        if p.is_file():
            entries.append({'name':str(p.relative_to(source)),'size':p.stat().st_size,
                            'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
    destination.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    run('docker','exec',NAME,'am','force-stop',PACKAGE)
    shutil.move(str(source),str(destination))
    manifest.write_text(json.dumps({'time':time.time(),'source':str(source),
        'backup':str(destination),'files':entries,'account_data_untouched':True},indent=2))
    manifest.chmod(0o600)
    component=run('docker','exec',NAME,'cmd','package','resolve-activity','--brief',PACKAGE).splitlines()[-1]
    assert component.startswith(PACKAGE+'/')
    print(run('docker','exec',NAME,'am','start','-W','-n',component))
    print(json.dumps({'optional_core_preserved':True,'account_data_untouched':True,'compatibility_still_requires_validation':True}))

if __name__=='__main__':main()
