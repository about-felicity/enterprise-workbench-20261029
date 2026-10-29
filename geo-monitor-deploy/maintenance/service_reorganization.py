"""Bounded production code organization and dependency-ordered service restart."""
import ast
from collections import defaultdict
from contextlib import closing
from datetime import datetime,timezone,timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import time
import urllib.request

STATE=Path('/opt/monitor/geo-capture/maintenance/20261015-reorganize')
STATE.mkdir(parents=True,exist_ok=True,mode=0o700)
EXPORT=Path('/home/user/redroid-doubao/reorganization-20261015')
EXPORT.mkdir(exist_ok=True,mode=0o755)
CORE=('monitor-postgres','monitor-redis','monitor-doubao-receiver','monitor-result-receiver',
    'monitor-dashboard-api','monitor-product-worker','monitor-content-worker','monitor-dashboard')
ANDROID=('doubao-hpe14-13-test','doubao-hpe14-account2')
EDITORIAL=('geo-editorial-scheduler.service','geo-editorial-api-worker.service','geo-editorial-coordinator.service','geo-editorial-session-watch.service')
OTHER=('geo-monitor-status.service','redroid-doubao-native-log.service','monitor-live-display.service','monitor-vps2-tunnel.service')
BASE=Path('/opt/monitor/geo-capture')

def now():return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')
def read(path):return json.loads(Path(path).read_text('utf-8-sig'))
def write(name,value,export=True):
    data=json.dumps(value,ensure_ascii=False,indent=2)
    p=STATE/name;p.write_text(data,encoding='utf8');p.chmod(0o600)
    if export:
        p=EXPORT/name;p.write_text(data,encoding='utf8');p.chmod(0o644)
def command(*args,timeout=40,check=True):
    return subprocess.run(args,capture_output=True,text=True,check=check,timeout=timeout).stdout.strip()
def event(step,**value):
    row={'at':now(),'step':step,**value}
    with (STATE/'operations.jsonl').open('a',encoding='utf8') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
    print(json.dumps(row,ensure_ascii=False),flush=True)
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fleet():return json.load(urllib.request.urlopen('http://127.0.0.1:8803/api/status',timeout=20))
def service(unit):
    raw=command('systemctl','show',unit,'-p','ActiveState','-p','MainPID','-p','NRestarts','-p','ExecMainStartTimestampMonotonic',check=False)
    return dict(v.split('=',1) for v in raw.splitlines() if '=' in v)
def snapshot():
    details=json.loads(command('docker','inspect',*CORE,*ANDROID))
    return {'at':now(),'containers':[{'name':v['Name'].lstrip('/'),'id':v['Id'],'image':v['Image'],
        'started_at':v['State']['StartedAt'],'status':v['State']['Status'],'health':v['State'].get('Health',{}).get('Status'),
        'mounts':v['Mounts']} for v in details], 'services':{u:service(u) for u in EDITORIAL+OTHER},
        'collectors':fleet()['collectors'],'editorial_control':read('/home/user/geo-editorial/runtime-api/control.json')}

def organize():
    assert not (STATE/'server-organization-applied.json').exists()
    roots=(Path('/opt/monitor'),Path('/home/user/redroid-doubao'))
    protect={'save_doubao_refs.py','extract_doubao_refs.py','doubao_dashboard_server.py','doubao_source_content_worker.py',
        'remote_product_ai_worker.py','doubao_env_loader.py','remote_model_worker.py','remote_model_control_panel.py',
        'doubao_brand_settings.py','doubao_question_aliases.py','monitor_db_sync.py','process_monitor.py',
        'unattended_core.py','unattended_worker.py','runtime_preflight.py','geo_batch_bridge.py','maintenance_control.py',
        'active_database_accounts.py','soak_sequence.py','soak_monitor.py','hpe14_report.py',
        'vps_geo_access_verified.py','deploy_dashboard_integration_managed.py'}
    units=command('systemctl','show',*EDITORIAL,*OTHER,'redroid-doubao-hpe14-worker.service','redroid-doubao-soak24h.service','redroid-geo-products.service','redroid-geo-products-account2.service','-p','ExecStart')
    protect.update(re.findall(r'/([^/\s;]+\.py)\b',units))
    # Keep helpers invoked dynamically by stable entrypoints at their old paths.
    for root in roots:
        changed=True
        while changed:
            before=set(protect)
            for p in root.glob('*.py'):
                if p.name in protect:protect.update(re.findall(r'[A-Za-z_][A-Za-z0-9_]*\.py',p.read_text('utf-8-sig')))
            changed=before!=protect
    moves=[]
    for root in roots:
        files=list(root.glob('*.py'));inbound=defaultdict(set)
        for p in files+list((root/'monitor_core').glob('*.py')):
            try:tree=ast.parse(p.read_text('utf-8-sig'))
            except (SyntaxError,UnicodeError):continue
            for n in ast.walk(tree):
                names=([n.module.split('.')[0]] if isinstance(n,ast.ImportFrom) and n.module else [a.name.split('.')[0] for a in n.names] if isinstance(n,ast.Import) else [])
                for name in names:inbound[name].add(p.name)
        for p in files:
            text=p.read_text('utf-8-sig')
            if p.name in protect or p.resolve()==Path(__file__).resolve() or inbound[p.stem] or '__file__' in text:continue
            if p.name.startswith(('before-','pause-fix-','maintenance-safe-')) or re.search(r'\.(new\d*|locks-closed|both-keva)\.py$',p.name):category='archive/code_snapshots/20261015'
            elif p.name.startswith('test_'):category='tests/legacy'
            elif p.name.startswith(('inspect_','check_','diagnose_','read_','compare_','probe_','audit_','verify_','frida_','disassemble_','account2_','watch_')):category='tools/diagnostics'
            elif p.name.startswith(('repair_','rebuild_','recover_','reset_','retry_','resume_','reload_','apply_','isolate_','reconcile_','fix_','start_account','create_account','normalize_','backfill_','dedupe_','refresh_')):category='archive/one_off'
            elif p.name.startswith(('export_','package_')):category='tools/exports'
            elif p.name.startswith(('build_','install_','deploy_','backup_','migrate_','finalize_')):category='tools/deployment'
            else:continue
            dest=root/category/p.name
            assert not dest.exists() and p.resolve()==p and not p.is_symlink()
            moves.append({'source':str(p),'target':str(dest),'sha256':digest(p),'root':str(root),'category':category})
    with tarfile.open(STATE/'server-code-before.tar.gz','w:gz') as backup:
        for row in moves:backup.add(row['source'],arcname=row['source'].lstrip('/'))
    write('server-organization-plan.json',{'files':moves})
    for row in moves:
        source,dest=Path(row['source']),Path(row['target']);assert digest(source)==row['sha256']
        text=source.read_text('utf-8-sig');tree=ast.parse(text)
        future=[n.end_lineno for n in tree.body if isinstance(n,ast.ImportFrom) and n.module=='__future__']
        line=max(future) if future else tree.body[0].end_lineno if tree.body and isinstance(tree.body[0],ast.Expr) and isinstance(tree.body[0].value,ast.Constant) and isinstance(tree.body[0].value.value,str) else 0
        root=Path(row['root']);depth=len(dest.relative_to(root).parts)-1
        boot=f'\n# Stable imports for classified maintenance scripts.\nimport sys as _geo_sys\nfrom pathlib import Path as _GeoPath\n_geo_sys.path.insert(0, str(_GeoPath(__file__).resolve().parents[{depth}]))\n'
        lines=text.splitlines(keepends=True);updated=''.join(lines[:line])+boot+''.join(lines[line:]);ast.parse(updated)
        dest.parent.mkdir(parents=True,exist_ok=True);source.rename(dest);dest.write_text(updated,encoding='utf8')
        row['new_sha256']=digest(dest)
    for root in roots:
        subset=[r for r in moves if r['root']==str(root)]
        doc='# 代码分类索引\n\n正式运行入口保持原路径；以下为已分类的历史工具与测试。历史一次性脚本不得作为常规重启命令。\n\n| 原文件 | 当前路径 |\n|---|---|\n'+''.join(f"| {Path(r['source']).name} | {Path(r['target']).relative_to(root)} |\n" for r in subset)
        (root/'CODE_LAYOUT_20261015.md').write_text(doc,encoding='utf8')
    write('server-organization-applied.json',{'at':now(),'moved_files':len(moves),'files':moves})
    event('server-code-organized',files=len(moves))

def readonly_backup(source,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    with closing(sqlite3.connect(Path(source).as_uri()+'?mode=ro',uri=True)) as original:
        with closing(sqlite3.connect(target)) as copy:original.backup(copy)
    target.chmod(0o600)

def gate_and_backup():
    value=snapshot()
    assert value['editorial_control']['paused'] is True,'Editorial work is active; drain it first'
    assert all(c['service_state'] not in ('active','activating','deactivating') for c in value['collectors']),'Collector still active'
    if not (STATE/'restart-before.json').exists():write('restart-before.json',value)
    with closing(sqlite3.connect((BASE/'panel/control.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
        jobs=list(db.execute('select s.model,j.batch,j.health from settings s join jobs j on j.batch=s.current_batch'))
    signatures={}
    for model,batch,health in jobs:
        directory=Path(health).parent
        queue=directory/('tasks.sqlite' if model.startswith('doubao') else 'collector/tasks.sqlite')
        readonly_backup(queue,STATE/'data-before'/(model+'-tasks.sqlite'))
        with closing(sqlite3.connect(queue.as_uri()+'?mode=ro',uri=True)) as db:
            table='tasks' if model.startswith('doubao') else 'captures'
            counts=dict(db.execute('select state,count(*) from '+table+' group by state'))
            assert not any(counts.get(k) for k in ('capturing','sending','prepared','needs_attention')),(model,counts)
            if model!='baidu_ai':assert not counts.get('failed_deferred'),(model,counts)
            signatures[model]={'batch':batch,'counts':counts,'queue':str(queue)}
    readonly_backup(BASE/'panel/control.sqlite',STATE/'data-before/control.sqlite')
    for container in ANDROID:
        info=json.loads(command('docker','inspect',container))[0]
        volume=Path(next(m['Source'] for m in info['Mounts'] if m['Destination']=='/data'))
        for db in (volume/'data/com.larus.nova/databases').glob('im_database_*'):
            if db.name.endswith(('-shm','-wal','-journal')):continue
            if db.open('rb').read(16)==b'SQLite format 3\x00':readonly_backup(db,STATE/'android-databases'/container/db.name)
    write('queue-before.json',signatures)
    event('restart-gates-and-sqlite-backups-passed')

def wait_container(name,seconds=120):
    end=time.monotonic()+seconds
    while time.monotonic()<end:
        value=json.loads(command('docker','inspect',name))[0]['State']
        if value['Status']=='running' and value.get('Health',{}).get('Status','healthy')=='healthy':return
        time.sleep(2)
    raise RuntimeError('Container health timeout: '+name)

def android_ready(container,serial):
    adb='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
    end=time.monotonic()+120
    while time.monotonic()<end:
        command(adb,'connect',serial,check=False)
        result=subprocess.run([adb,'-s',serial,'shell','am','start','-n',
            'com.larus.nova/com.larus.home.impl.alias.AliasActivity1'],capture_output=True,text=True,timeout=20)
        if result.returncode==0 and 'Error type' not in result.stdout+result.stderr:break
        time.sleep(3)
    else:raise RuntimeError('ADB/app startup did not become ready: '+container)
    time.sleep(6)
    command('/home/user/redroid-doubao/worker-venv/bin/python','/home/user/redroid-doubao/runtime_preflight.py','--container',container,timeout=170)

def restart():
    assert not (STATE/'restart-complete.json').exists(),'Restart already completed'
    assert not (STATE/'restart-started.json').exists(),'Restart previously started; inspect operations before retrying'
    gate_and_backup()
    # Validate that the staged bridge differs only by the intended race fix.
    live=BASE/'capture_bridge.py';staged=Path('/home/user/redroid-doubao/capture_bridge_exit_order_20261015.py')
    old=live.read_text();new=staged.read_text();ast.parse(new)
    assert 'Observe process exit first' in new and 'Observe process exit first' not in old
    polling='                exited = child is not None and child.poll() is not None\n                if exited:\n                    last_exit, child = child.returncode, None\n'
    old_without_poll=old.replace(polling,'')
    expected=old_without_poll.replace('                rows = read_rows(runtime / "tasks.sqlite", config["batch"])',
        '                # Observe process exit first: CLI may finalize an exhausted\n                # optional card while the previously sampled row still says\n                # failed_deferred. Decisions must use the post-exit journal.\n'+polling+'                rows = read_rows(runtime / "tasks.sqlite", config["batch"])')
    expected=expected.replace('blocked = bool(counts.get("needs_attention") or counts.get("failed_deferred") or last_exit not in (None, 0)',
        'blocked = bool((child is None and (counts.get("needs_attention") or counts.get("failed_deferred") or last_exit not in (None, 0)))')
    assert expected==new,'Unexpected bridge source drift; refuse overwrite'
    write('restart-started.json',{'at':now()})
    shutil.copyfile(live,STATE/'capture_bridge.before.py')
    temp=live.with_suffix('.restart-install');temp.write_text(new,encoding='utf8');temp.chmod(0o644);temp.replace(live)
    event('bridge-race-fix-installed',before_sha256=digest(STATE/'capture_bridge.before.py'),after_sha256=digest(live))
    stopped=[]
    try:
        for unit in ('geo-monitor-status.service',)+EDITORIAL+('redroid-doubao-native-log.service',):
            command('systemctl','stop',unit,timeout=60);event('service-stopped',unit=unit)
        # No running collector is allowed to appear while the control API is down.
        for name in ('monitor-product-worker','monitor-content-worker','monitor-result-receiver','monitor-doubao-receiver','monitor-dashboard-api','monitor-dashboard'):
            command('docker','stop','--time','45',name,timeout=60);stopped.append(name);event('container-stopped',container=name)
        for name in ('monitor-postgres','monitor-redis'):
            command('docker','restart','--time','45',name,timeout=60);wait_container(name);event('container-restarted',container=name)
        assert command('docker','exec','monitor-postgres','pg_isready','-U','monitor_app','-d','monitor')
        assert command('docker','exec','monitor-redis','redis-cli','ping')=='PONG'
        # Backend image healthchecks for receivers also probe API port 8765.
        # Start that dependency before waiting for receiver health.
        for name in ('monitor-dashboard-api','monitor-doubao-receiver','monitor-result-receiver','monitor-product-worker','monitor-content-worker','monitor-dashboard'):
            command('docker','start',name);wait_container(name);event('container-restarted',container=name)
        for container,serial in zip(ANDROID,('127.0.0.1:5557','127.0.0.1:5558')):
            command('docker','restart','--time','45',container,timeout=60)
            end=time.monotonic()+150
            while time.monotonic()<end:
                if command('docker','exec',container,'/system/bin/getprop','sys.boot_completed',check=False)=='1':break
                time.sleep(3)
            else:raise RuntimeError('Android boot timeout: '+container)
            android_ready(container,serial)
            event('android-restarted-and-runtime-verified',container=container)
    finally:
        # Restore all formerly running consumers even if a later preflight fails.
        for name in stopped:command('docker','start',name,check=False)
        for unit in EDITORIAL+('geo-monitor-status.service','redroid-doubao-native-log.service'):
            command('systemctl','start',unit,timeout=60,check=False)
    for unit in ('monitor-live-display.service','monitor-network-watchdog.timer','monitor-vps2-tunnel.service'):
        command('systemctl','restart',unit,timeout=50);event('service-restarted',unit=unit)
    # Reconnect public control after its existing reverse tunnel rebinds.
    time.sleep(3)
    write('restart-complete.json',{'at':now(),'containers':list(CORE+ANDROID),'services':list(EDITORIAL+OTHER),
        'paused_jobs_not_resumed':True,'deepseek_waits_for_user_login':True})
    event('dependency-restart-complete')

def finish_restart():
    assert (STATE/'restart-started.json').exists() and not (STATE/'restart-complete.json').exists()
    before=read(STATE/'restart-before.json')
    originals={x['name']:x for x in before['containers']}
    jobs=read(STATE/'queue-before.json')
    for container,serial,model in zip(ANDROID,('127.0.0.1:5557','127.0.0.1:5558'),('doubao1','doubao2')):
        live=next(c for c in fleet()['collectors'] if c['name']==('豆包 1' if model=='doubao1' else '豆包 2'))
        assert live['batch']==jobs[model]['batch'] and live['service_state']=='inactive'
        with closing(sqlite3.connect(Path(jobs[model]['queue']).as_uri()+'?mode=ro',uri=True)) as db:
            assert dict(db.execute('select state,count(*) from tasks group by state'))==jobs[model]['counts']
        current=json.loads(command('docker','inspect',container))[0]
        if current['State']['StartedAt']==originals[container]['started_at']:
            command('docker','restart','--time','45',container,timeout=60)
            event('android-container-restarted',container=container)
        else:event('android-restart-already-observed-no-repeat',container=container)
        end=time.monotonic()+150
        while time.monotonic()<end:
            if command('docker','exec',container,'/system/bin/getprop','sys.boot_completed',check=False)=='1':break
            time.sleep(3)
        else:raise RuntimeError('Android boot timeout: '+container)
        android_ready(container,serial)
        event('android-runtime-verified-after-readiness-wait',container=container)
    for unit in ('monitor-live-display.service','monitor-network-watchdog.timer','monitor-vps2-tunnel.service'):
        command('systemctl','restart',unit,timeout=50);event('service-restarted',unit=unit)
    time.sleep(3)
    write('restart-complete.json',{'at':now(),'containers':list(CORE+ANDROID),'services':list(EDITORIAL+OTHER),
        'paused_jobs_not_resumed':True,'deepseek_waits_for_user_login':True,
        'startup_check_recovered_without_repeating_completed_restart':True})
    event('dependency-restart-complete')

def verify():
    before=read(STATE/'restart-before.json');after=snapshot()
    old={x['name']:x for x in before['containers']}
    checks={x['name']:{'same_id':old[x['name']]['id']==x['id'],'same_image':old[x['name']]['image']==x['image'],
        'same_mounts':old[x['name']]['mounts']==x['mounts'],'start_changed':old[x['name']]['started_at']!=x['started_at'],
        'running':x['status']=='running','health':x['health']} for x in after['containers']}
    jobs=read(STATE/'queue-before.json');retained={}
    for model,value in jobs.items():
        with closing(sqlite3.connect(Path(value['queue']).as_uri()+'?mode=ro',uri=True)) as db:
            table='tasks' if model.startswith('doubao') else 'captures'
            counts=dict(db.execute('select state,count(*) from '+table+' group by state'))
        retained[model]={'batch':value['batch'],'before':value['counts'],'after':counts,'unchanged':counts==value['counts']}
    native=[]
    for model in ('doubao1','doubao2'):
        reply=command('/opt/monitor/geo-capture/venv/bin/python',str(BASE/'login_probe.py'),'--model',model,'--runtime','/tmp/geo-native-probe',timeout=60)
        parsed=json.loads(reply.splitlines()[-1]);native.append({'model':model,'status':parsed['status']})
    report={'at':now(),'containers':checks,'services':after['services'],'queues':retained,
        'native_login_checks':native,'editorial_control_preserved':before['editorial_control']==after['editorial_control'],
        'collectors':after['collectors']}
    write('restart-verification.json',report);print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':{'organize':organize,'restart':restart,'finish':finish_restart,'verify':verify}[sys.argv[1]]()
