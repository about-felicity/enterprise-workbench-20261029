import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request

BASE=Path('/opt/monitor/geo-capture');SOURCE=Path('/opt/monitor/yuanbao_monitor/dashboard')
STAGE=BASE/'releases/creation-20261015';POINTER=BASE/'creation_frontend.json';IMAGE='monitor-dashboard:creation-20261015'
def command(*args):return subprocess.check_output(args,text=True,timeout=55).strip()
def ready(port):
    for _ in range(30):
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/geo-creation/panel',timeout=8) as s:value=json.load(s)
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/geo-capture/panel',timeout=8) as s:capture=json.load(s)
            if value['ok'] and len(capture['models'])==6:return
        except Exception:pass
        time.sleep(1)
    raise RuntimeError('Unified frontend readiness failed')
def main(mode):
    if mode=='preview':
        assert not POINTER.exists(),'Inspect existing release before repeating'
        backup=BASE/'backups'/('creation-frontend-'+str(int(time.time())));backup.mkdir(mode=0o700)
        old=command('docker','inspect','monitor-dashboard','--format','{{.Image}}')
        tag='monitor-dashboard:before-creation-'+str(int(time.time()));command('docker','tag',old,tag)
        for source in (STAGE/'app').rglob('*'):
            if source.is_file() and (SOURCE/source.relative_to(STAGE)).exists():
                target=backup/source.relative_to(STAGE);target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(SOURCE/source.relative_to(STAGE),target)
        value={'at':time.time(),'backup':str(backup),'original_image':old,'original_tag':tag,'new_image':IMAGE,'status':'preview'}
        POINTER.write_text(json.dumps(value,indent=2))
        command('docker','run','-d','--name','monitor-dashboard-creation-preview','--network','host',IMAGE,'npm','run','start','--','-H','0.0.0.0','-p','3001')
        ready(3001);print(json.dumps(value))
    elif mode=='publish':
        value=json.loads(POINTER.read_text());assert value['status']=='preview'
        qa=json.loads((BASE/'maintenance/20261015-unified/creation-preview-qa.json').read_text())
        assert qa['passed'] and qa['port']==3001 and qa['finished_at']>value['at']
        compose=['docker','compose','-p','local-server','-f','/opt/monitor/deploy/local-server/docker-compose.yml','up','-d','--no-deps','--no-build','--force-recreate','dashboard']
        command('docker','tag',IMAGE,'monitor-dashboard:local')
        try:command(*compose);ready(3000)
        except Exception:
            command('docker','tag',value['original_tag'],'monitor-dashboard:local');command(*compose)
            value['status']='rolled_back';POINTER.write_text(json.dumps(value,indent=2));raise
        for source in STAGE.rglob('*'):
            if source.is_file() and source.parts[len(STAGE.parts)] in {'app','tests'}:
                target=SOURCE/source.relative_to(STAGE);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        value.update(status='published',published_at=time.time());POINTER.write_text(json.dumps(value,indent=2))
        print(json.dumps(value))
    else:raise ValueError(mode)
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['preview','publish']);main(parser.parse_args().mode)
