"""Select SDK's built-in fallback by disabling the exact incompatible core version."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time

BASE=Path('/home/user/redroid-yuanbao')
NAME='yuanbao-hpe14-android13'
PACKAGE='com.tencent.hunyuan.app.chat'

def run(*a):return subprocess.check_output(a,text=True,stderr=subprocess.STDOUT,timeout=45).strip()

def main():
    info=json.loads(run('docker','inspect',NAME))[0]
    assert info['Config']['Labels'].get('geo.collector')=='yuanbao'
    mount=next(m for m in info['Mounts'] if m['Destination']=='/data')
    assert mount['Name']=='yuanbao-hpe14-android13-data'
    app=Path(mount['Source'])/'data'/PACKAGE
    core=app/'app_tbs_64/core_share/tbs.conf'
    version=int(re.search(r'^tbs_core_version=(\d+)\s*$',core.read_text(),re.M)[1])
    assert version==47803, 'Unexpected core; validate compatibility instead of applying an old exception'
    config=app/'app_tbs_64/core_private/tbs_pv_config'
    assert config.exists()
    backup=BASE/'compat/disabled-core-47803'
    backup.mkdir(parents=True,exist_ok=True,mode=0o700)
    before=backup/'tbs_pv_config.before'
    if not before.exists():shutil.copy2(config,before)
    run('docker','exec',NAME,'am','force-stop',PACKAGE)
    original=config.read_text('ISO-8859-1')
    lines=[line for line in original.splitlines() if not re.match(r'^\s*disabled_core_version\s*[=:]',line)]
    config.write_text('\n'.join(lines)+f'\ndisabled_core_version={version}\n',encoding='ISO-8859-1')
    (backup/'change.json').write_text(json.dumps({'time':time.time(),'path':str(config),
        'version':version,'original_preserved':True,'account_data_untouched':True},indent=2))
    component=run('docker','exec',NAME,'cmd','package','resolve-activity','--brief',PACKAGE).splitlines()[-1]
    assert component.startswith(PACKAGE+'/')
    print(run('docker','exec',NAME,'am','start','-W','-n',component))
    print(json.dumps({'specific_core_disabled':version,'fallback_needs_validation':True}))

if __name__=='__main__':main()
