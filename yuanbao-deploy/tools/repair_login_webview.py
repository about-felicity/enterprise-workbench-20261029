"""Reversible X5 system-WebView selection for this Yuanbao container only."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

ROOT=Path('/home/user/redroid-yuanbao')
NAME='yuanbao-hpe14-android13'
PACKAGE='com.tencent.hunyuan.app.chat'

def run(*args):
    return subprocess.check_output(args,text=True,stderr=subprocess.STDOUT,timeout=35).strip()

def main():
    info=json.loads(run('docker','inspect',NAME))[0]
    assert info['Config']['Labels'].get('geo.collector')=='yuanbao'
    mount=next(m for m in info['Mounts'] if m['Destination']=='/data')
    assert mount['Name']=='yuanbao-hpe14-android13-data'
    app=Path(mount['Source'])/'data'/PACKAGE
    private=app/'app_tbs_64/core_private'
    assert private.is_dir()
    backup=ROOT/'diagnostics/login-20261015/x5-system-webview'
    backup.mkdir(parents=True,exist_ok=True,mode=0o700)
    path=private/'debug.conf'
    manifest_path=backup/'change.json'
    if not manifest_path.exists():
        existed=path.exists()
        if existed:shutil.copy2(path,backup/'debug.conf.before')
        # Keep the pre-change App preferences privately, never export them.
        if (app/'shared_prefs').exists():
            shutil.copytree(app/'shared_prefs',backup/'shared_prefs.before',dirs_exist_ok=True)
        data={'path':str(path),'existed_before':existed,'changed_at':time.time(),
              'key':'setting_forceUseSystemWebview','value':'true'}
        manifest_path.write_text(json.dumps(data,indent=2),encoding='utf8')
        manifest_path.chmod(0o600)
    run('docker','exec',NAME,'am','force-stop',PACKAGE)
    old=path.read_text('ISO-8859-1') if path.exists() else ''
    lines=[line for line in old.splitlines() if not line.strip().startswith('setting_forceUseSystemWebview')]
    lines.append('setting_forceUseSystemWebview=true')
    path.write_text('\n'.join(lines)+'\n',encoding='ISO-8859-1')
    owner=private.stat()
    os.chown(path,owner.st_uid,owner.st_gid)
    path.chmod(0o600)
    run('docker','exec',NAME,'svc','bluetooth','disable')
    activity=run('docker','exec',NAME,'cmd','package','resolve-activity','--brief',PACKAGE).splitlines()[-1]
    assert activity.startswith(PACKAGE+'/')
    print(run('docker','exec',NAME,'am','start','-W','-n',activity))
    print(json.dumps({'changed_only':NAME,'system_webview_requested':True,
                      'private_backup_saved':True,'data_cleared':False}))

if __name__=='__main__':main()
