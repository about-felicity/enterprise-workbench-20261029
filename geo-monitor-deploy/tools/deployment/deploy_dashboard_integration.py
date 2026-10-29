"""Preview and switch only the GEO frontend; preserve running collectors."""

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
STAGE=Path('/home/user/redroid-doubao/dashboard-integration-20261015-rev3')
POINTER=BASE/'dashboard_integration_release.json'
IMAGE='monitor-dashboard:capture-20261015'
PREVIEW='monitor-dashboard-capture-preview'


def command(*args):
    return subprocess.run(args,capture_output=True,text=True,check=True,timeout=45).stdout.strip()


def read(path):return json.loads(path.read_text())
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2))
def get(url):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url,timeout=20) as response:return json.load(response)


def health(port):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(30):
        try:
            with opener.open(f'http://127.0.0.1:{port}/api/geo-capture/panel',timeout=3) as response:
                if len(json.load(response)['models'])==5:return
        except Exception:time.sleep(1)
    raise RuntimeError('New frontend failed readiness check')


parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['preview','switch','manage','verify']);args=parser.parse_args()
if args.mode=='preview':
    if POINTER.exists():raise RuntimeError('Inspect existing release pointer before creating another preview')
    for relative,expected in [('app/Dashboard.tsx','a1e483b69e1f7656c533ed3c34e91ded652049702ffcb338cc9981aeb250fb74'),('app/globals.css','b66f8f6b3ec347f0cf568cd55970228afaf59a168b47ed2609d2b50eb4baccca')]:
        assert hashlib.sha256((SOURCE/relative).read_bytes()).hexdigest()==expected,'Concurrent source change'
    backup=BASE/'backups'/('dashboard-integration-'+str(int(time.time())))
    backup.mkdir(mode=0o700)
    for relative in ['app/Dashboard.tsx','app/globals.css']:
        path=backup/relative;path.parent.mkdir(exist_ok=True);shutil.copy2(SOURCE/relative,path)
    fleet=get('http://127.0.0.1:8803/api/status')
    units=['geo-editorial-scheduler.service','geo-editorial-api-worker.service','geo-editorial-coordinator.service','geo-editorial-session-watch.service']+[m['service'] for m in fleet['collectors']]
    original=command('docker','inspect','monitor-dashboard','--format','{{.Image}}')
    original_tag='monitor-dashboard:before-capture-'+str(int(time.time()))
    command('docker','tag',original,original_tag)
    manifest={'created_at':time.time(),'backup':str(backup),'original_image':original,'original_tag':original_tag,'new_image':IMAGE,
              'containers_before':fleet['containers'],'units':units,
              'services_before':command('systemctl','show',*units,'-p','Id','-p','MainPID','-p','ExecMainStartTimestamp'),
              'batches_before':{m['name']:{'batch':m['batch'],'captured':m['captured'],'processed':m['processed']} for m in fleet['collectors']},'status':'preview'}
    save(POINTER,manifest);save(backup/'manifest.json',manifest)
    command('docker','run','-d','--name',PREVIEW,'--network','host',IMAGE,'npm','run','start','--','-H','0.0.0.0','-p','3001')
    health(3001)
    print(json.dumps({'status':'preview_ready','url':'http://192.168.31.106:3001/#capture/doubao1','backup':str(backup)}))
elif args.mode=='switch':
    manifest=read(POINTER)
    assert manifest['status']=='preview'
    qa=read(BASE/'panel-qa/dashboard-integration-preview.json');assert qa['passed'] and qa['port']==3001
    old_name='monitor-dashboard-before-capture-'+str(int(manifest['created_at']))
    manifest['old_container']=old_name;manifest['status']='switching';save(POINTER,manifest)
    command('docker','stop','--time','15','monitor-dashboard')
    command('docker','rename','monitor-dashboard',old_name)
    try:
        command('docker','run','-d','--name','monitor-dashboard','--network','host','--restart','unless-stopped',IMAGE)
        health(3000)
    except Exception:
        subprocess.run(['docker','rm','-f','monitor-dashboard'],capture_output=True)
        command('docker','rename',old_name,'monitor-dashboard');command('docker','start','monitor-dashboard')
        manifest['status']='rolled_back';save(POINTER,manifest)
        raise
    for path in (STAGE/'app').rglob('*'):
        if path.is_file():
            relative=path.relative_to(STAGE);destination=SOURCE/relative
            destination.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,destination)
            shutil.chown(destination,user='user',group='user');destination.chmod(0o644)
    shutil.copy2(STAGE/'tests/capture-gateway.test.mjs',SOURCE/'tests/capture-gateway.test.mjs')
    command('docker','tag',IMAGE,'monitor-dashboard:local')
    manifest.update(status='deployed',deployed_at=time.time());save(POINTER,manifest)
    print(json.dumps({'status':'deployed','url':'http://192.168.31.106:3000/#capture/doubao1','rollback_container':old_name,'backup':manifest['backup']}))
elif args.mode=='manage':
    # Rejoin the original compose deployment after the blue/green acceptance.
    # The inherited image has compose labels; do not leave a second dashboard
    # container or a preview eligible for a later compose service discovery.
    manifest=read(POINTER)
    assert manifest['status']=='deployed'
    assert command('docker','inspect','monitor-dashboard','--format','{{.Image}}')==command('docker','image','inspect',IMAGE,'--format','{{.Id}}')
    command('docker','image','inspect',manifest['original_tag'],'--format','{{.Id}}')
    command('docker','rm','-f',PREVIEW)
    command('docker','rm','-f','monitor-dashboard')
    try:
        command('docker','compose','-p','local-server','-f','/opt/monitor/deploy/local-server/docker-compose.yml',
                'up','-d','--no-deps','--no-build','--force-recreate','dashboard')
        health(3000)
    except Exception:
        subprocess.run(['docker','rm','-f','monitor-dashboard'],capture_output=True)
        command('docker','run','-d','--name','monitor-dashboard','--network','host','--restart','unless-stopped',IMAGE)
        health(3000)
        manifest['compose_reconciliation_failed']=True;save(POINTER,manifest)
        raise
    manifest.update(managed_by_original_compose=True,old_container_removed_by_compose=True,preview_removed=True,managed_at=time.time())
    save(POINTER,manifest)
    print(json.dumps({'status':'managed_by_original_compose','rollback_image':manifest['original_tag']}))
else:
    manifest=read(POINTER);fleet=get('http://127.0.0.1:8803/api/status')
    before={c['name']:c for c in manifest['containers_before'] if c['name']!='monitor-dashboard'}
    after={c['name']:c for c in fleet['containers'] if c['name']!='monitor-dashboard'}
    assert before==after,'Non-frontend container changed'
    services=command('systemctl','show',*manifest['units'],'-p','Id','-p','MainPID','-p','ExecMainStartTimestamp')
    assert services==manifest['services_before'],'A running collector or editorial service restarted'
    for item in fleet['collectors']:
        old=manifest['batches_before'][item['name']]
        assert old['batch']==item['batch'] and item['captured']>=old['captured'] and item['processed']>=old['processed']
    report={'at':time.time(),'non_frontend_containers_unchanged':True,'collectors_and_editorial_processes_unchanged':True,
            'same_batches_continued':True,'frontend_image':command('docker','inspect','monitor-dashboard','--format','{{.Image}}'),
            'collectors':fleet['collectors']}
    save(BASE/'panel-qa/dashboard-integration-continuity.json',report);print(json.dumps(report,ensure_ascii=False))
