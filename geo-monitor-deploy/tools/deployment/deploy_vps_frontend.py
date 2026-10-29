"""Publish prefix-aware frontend only; keep collectors, tunnel and API intact."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request

BASE=Path('/opt/monitor/geo-capture')
SOURCE=Path('/opt/monitor/yuanbao_monitor/dashboard')
STAGE=Path('/home/user/redroid-doubao/dashboard-vps-prefix-20261015')
POINTER=BASE/'vps_frontend_release.json'
IMAGE='monitor-dashboard:vps-prefix-20261015'
PREVIEW='monitor-dashboard-vps-preview'


def command(*args):
    return subprocess.run(args,capture_output=True,text=True,check=True,timeout=50).stdout.strip()


def get(url):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url,timeout=20) as stream:return json.load(stream)


def write(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2))
def read(path):return json.loads(path.read_text())


def ready(port):
    for _ in range(25):
        try:
            if len(get(f'http://127.0.0.1:{port}/api/geo-capture/panel')['models'])==5:return
        except Exception:time.sleep(1)
    raise RuntimeError('Frontend readiness failed')


parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['preview','publish','verify']);args=parser.parse_args()
if args.mode=='preview':
    assert not POINTER.exists(),'Inspect existing prefix deployment before retrying'
    backup=BASE/'backups'/('vps-prefix-'+str(int(time.time())))
    backup.mkdir(mode=0o700)
    originals=[];created=[]
    for path in (STAGE/'app').rglob('*'):
        if not path.is_file():continue
        relative=path.relative_to(STAGE)
        target=SOURCE/relative
        if target.exists():
            destination=backup/relative;destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(target,destination);originals.append(str(relative))
        else:created.append(str(relative))
    assert hashlib.sha256((SOURCE/'app/globals.css').read_bytes()).hexdigest()==hashlib.sha256((STAGE/'app/globals.css').read_bytes()).hexdigest()
    old=command('docker','inspect','monitor-dashboard','--format','{{.Image}}')
    tag='monitor-dashboard:before-vps-prefix-'+str(int(time.time()))
    command('docker','tag',old,tag)
    fleet=get('http://127.0.0.1:8803/api/status')
    units=[m['service'] for m in fleet['collectors']]+['geo-editorial-scheduler.service','geo-editorial-api-worker.service','geo-editorial-coordinator.service','geo-editorial-session-watch.service','monitor-vps2-tunnel.service']
    value={'created_at':time.time(),'backup':str(backup),'original_image':old,'original_tag':tag,'new_image':IMAGE,
           'original_files':originals,'created_files':created,'containers_before':fleet['containers'],'units':units,
           'services_before':command('systemctl','show',*units,'-p','Id','-p','MainPID','-p','ExecMainStartTimestamp'),
           'batches_before':{m['name']:{'batch':m['batch'],'captured':m['captured'],'processed':m['processed']} for m in fleet['collectors']},'status':'preview'}
    write(POINTER,value);write(backup/'release.json',value)
    command('docker','run','-d','--name',PREVIEW,'--network','host','--label','com.docker.compose.project=geo-vps-preview',
            '--label','com.docker.compose.service=preview',IMAGE,'npm','run','start','--','-H','0.0.0.0','-p','3001')
    ready(3001);print(json.dumps({'status':'preview_ready','backup':str(backup),'original_tag':tag}))
elif args.mode=='publish':
    value=read(POINTER);assert value['status']=='preview'
    qa=read(BASE/'panel-qa/dashboard-integration-preview.json')
    assert qa['passed'] and qa['port']==3001 and qa['finished_at']>value['created_at']
    command('docker','tag',IMAGE,'monitor-dashboard:local')
    compose=['docker','compose','-p','local-server','-f','/opt/monitor/deploy/local-server/docker-compose.yml','up','-d','--no-deps','--no-build','--force-recreate','dashboard']
    try:command(*compose);ready(3000)
    except Exception:
        command('docker','tag',value['original_tag'],'monitor-dashboard:local');command(*compose)
        value['status']='rolled_back';write(POINTER,value);raise
    for path in (STAGE/'app').rglob('*'):
        if path.is_file():
            target=SOURCE/path.relative_to(STAGE);target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(path,target);shutil.chown(target,user='user',group='user');target.chmod(0o644)
    shutil.copy2(STAGE/'tests/capture-gateway.test.mjs',SOURCE/'tests/capture-gateway.test.mjs')
    command('docker','rm','-f',PREVIEW)
    value.update(status='deployed',deployed_at=time.time());write(POINTER,value)
    print(json.dumps({'status':'deployed','backup':value['backup'],'rollback_image':value['original_tag']}))
else:
    value=read(POINTER);fleet=get('http://127.0.0.1:8803/api/status')
    before={c['name']:c for c in value['containers_before'] if c['name']!='monitor-dashboard'}
    after={c['name']:c for c in fleet['containers'] if c['name']!='monitor-dashboard'}
    assert before==after,'A non-frontend container changed'
    services=command('systemctl','show',*value['units'],'-p','Id','-p','MainPID','-p','ExecMainStartTimestamp')
    assert services==value['services_before'],'A collector, editorial service or tunnel restarted'
    for m in fleet['collectors']:
        old=value['batches_before'][m['name']]
        assert old['batch']==m['batch'] and m['captured']>=old['captured'] and m['processed']>=old['processed']
    result={'checked_at':time.time(),'non_frontend_containers_unchanged':True,'collectors_editorial_and_tunnel_unchanged':True,'same_batches_progress_preserved':True,'collectors':fleet['collectors']}
    write(BASE/'panel-qa/vps-access-continuity.json',result);print(json.dumps(result,ensure_ascii=False))
