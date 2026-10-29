"""Allowlisted GEO audit/cleanup. Never change runtime data, images or volumes."""
from datetime import datetime, timezone, timedelta
import hashlib
import json
import lzma
import os
from pathlib import Path
import subprocess
import sys

BASE=Path('/opt/monitor/geo-capture/maintenance/20261015')
EXPORT=Path('/home/user/redroid-doubao/maintenance-20261015')
SERVICES=('geo-monitor-status.service','geo-capture-wenxin-card.service',
    'geo-editorial-scheduler.service','geo-editorial-api-worker.service',
    'geo-editorial-coordinator.service','geo-editorial-session-watch.service',
    'geo-editorial-acceptance-current.service','monitor-vps2-tunnel.service','redroid-doubao-native-log.service')

def command(*args,timeout=30,check=True):
    return subprocess.run(args,capture_output=True,text=True,check=check,timeout=timeout).stdout.strip()

def write(name,value):
    BASE.mkdir(parents=True,exist_ok=True,mode=0o700)
    (BASE/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
    (BASE/name).chmod(0o600)
    EXPORT.mkdir(exist_ok=True,mode=0o755)
    (EXPORT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
    (EXPORT/name).chmod(0o644)

def read(name):return json.loads((BASE/name).read_text())

def snapshot():
    names=command('docker','ps','-a','--format','{{.Names}}').splitlines()
    inspected=json.loads(command('docker','inspect',*names))
    containers=[]
    for x in inspected:
        containers.append({'name':x['Name'].lstrip('/'),'id':x['Id'],'image_id':x['Image'],
            'state':x['State']['Status'],'started_at':x['State']['StartedAt'],
            'health':x['State'].get('Health',{}).get('Status'),
            'mounts':[{'type':v['Type'],'source':v['Source'],'destination':v['Destination']} for v in x['Mounts']]})
    services={}
    for name in SERVICES:
        raw=command('systemctl','show',name,'-p','ActiveState','-p','SubState','-p','MainPID','-p','ExecMainStartTimestampMonotonic','-p','NRestarts',
            check=not (name=='geo-editorial-acceptance-current.service' and (BASE/'retired-observers-applied.json').exists()))
        services[name]=dict(row.split('=',1) for row in raw.splitlines() if '=' in row)
    import urllib.request
    fleet=json.load(urllib.request.urlopen('http://127.0.0.1:8803/api/status',timeout=20))
    stats=os.statvfs('/')
    return {'at_beijing':datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
        'containers':containers,'services':services,'collectors':fleet['collectors'],
        'disk_free_bytes':stats.f_bavail*stats.f_frsize,
        'docker_space':command('docker','system','df'),
        'images':command('docker','image','ls','--no-trunc','--format','{{.ID}} {{.Repository}}:{{.Tag}}'),
        'volumes':command('docker','volume','ls','-q')}

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as src:
        while chunk:=src.read(4*1024*1024):h.update(chunk)
    return h.hexdigest()

def no_build_process():
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():continue
        try:a=(proc/'cmdline').read_bytes().split(b'\0')
        except OSError:continue
        if not a or Path(os.fsdecode(a[0])).name!='docker':continue
        assert not any(word in (b'build',b'buildx') for word in a[1:]),'Active Docker build; postpone pruning'

def clean():
    if (BASE/'server-cleanup-applied.json').exists():
        raise SystemExit('Cleanup already applied; preserve original evidence.')
    before=read('server-before.json')
    no_build_process()
    targets=[]
    package=Path('/home/user/geo-editorial/downloads/chrome.deb')
    if package.exists():
        installed=command('dpkg-query','-W','-f=${Version}','google-chrome-stable')
        downloaded=command('dpkg-deb','-f',str(package),'Version')
        assert installed==downloaded
        targets.append({'path':str(package),'bytes':package.stat().st_size,'sha256':digest(package),
            'reason':'Downloaded installer, exact same version already installed','installed_version':installed})
    raw=Path('/home/user/redroid-doubao/frida-server-account2')
    compressed=raw.with_suffix('.xz')
    if raw.exists() and compressed.exists():
        h=hashlib.sha256()
        with lzma.open(compressed,'rb') as src:
            while chunk:=src.read(4*1024*1024):h.update(chunk)
        if h.hexdigest()==digest(raw):
            targets.append({'path':str(raw),'bytes':raw.stat().st_size,'sha256':digest(raw),
                'reason':'Exact decompressed duplicate; .xz retained'})
    assert all(x['path'] in ('/home/user/geo-editorial/downloads/chrome.deb','/home/user/redroid-doubao/frida-server-account2') for x in targets)
    write('server-cleanup-plan.json',{'files':targets,'docker_operation':'docker builder prune --force; unused build cache only'})
    for row in targets:
        path=Path(row['path'])
        assert path.resolve()==path and path.is_file() and not path.is_symlink()
        # No bind mount or active host executable may reference a removed file.
        assert not any(path==Path(m['source']) for c in before['containers'] for m in c['mounts'])
        for proc in Path('/proc').iterdir():
            if not proc.name.isdigit():continue
            try:assert (proc/'exe').resolve()!=path
            except OSError:pass
        assert digest(path)==row['sha256']
        path.unlink()
    output=command('docker','builder','prune','--force',timeout=180)
    (BASE/'docker-builder-prune.txt').write_text(output,encoding='utf8')
    # Only the final reclaimed-space line is exported; build IDs remain in the
    # private command transcript as historical operational evidence.
    write('server-cleanup-applied.json',{'at_beijing':datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
        'deleted_files':targets,'deleted_file_bytes':sum(x['bytes'] for x in targets),
        'builder_prune_result':output.splitlines()[-1] if output else 'no output'})

mode=sys.argv[1]
if mode=='before':
    if (BASE/'server-before.json').exists():
        raise SystemExit('Original baseline already exists; do not overwrite it.')
    value=snapshot();write('server-before.json',value)
    print(json.dumps({'recorded':'server-before.json','containers':len(value['containers']),'running':sum(x['state']=='running' for x in value['containers']),'services':value['services']},ensure_ascii=False))
elif mode=='clean':
    clean();print(json.dumps(read('server-cleanup-applied.json'),ensure_ascii=False))
elif mode in ('after','final'):
    before=read('server-before.json');after=snapshot();write('server-'+mode+'.json',after)
    identity=lambda x:{k:x[k] for k in ('id','image_id','state','started_at')}
    previous={c['name']:identity(c) for c in before['containers'] if c['state']=='running'}
    current={c['name']:identity(c) for c in after['containers'] if c['state']=='running'}
    changed={n:{'before':v,'after':current.get(n)} for n,v in previous.items() if current.get(n)!=v}
    service_changes={n:{'before':v,'after':after['services'][n]} for n,v in before['services'].items() if v!=after['services'][n]}
    intended={}
    if (BASE/'retired-observers-applied.json').exists():
        retired='geo-editorial-acceptance-current.service'
        assert after['services'][retired].get('ActiveState','inactive')!='active'
        if retired in service_changes:intended[retired]=service_changes.pop(retired)
    comparison={'containers_unchanged':not changed,'container_changes':changed,
        'business_services_unchanged':not service_changes,'service_changes':service_changes,
        'intentionally_retired_observers':intended,
        'docker_images_unchanged':set(before['images'].splitlines())==set(after['images'].splitlines()),
        'docker_volumes_unchanged':set(before['volumes'].splitlines())==set(after['volumes'].splitlines()),
        'disk_free_increase_bytes':after['disk_free_bytes']-before['disk_free_bytes'],
        'at_beijing':after['at_beijing'],'collectors':after['collectors']}
    write('server-final-continuity.json' if mode=='final' else 'server-continuity.json',comparison);print(json.dumps(comparison,ensure_ascii=False,indent=2))
else:raise ValueError('Invalid operation')
