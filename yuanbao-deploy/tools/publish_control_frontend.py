"""Publish only Yuanbao's dashboard controls, with preview and rollback."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request

BASE = Path('/opt/monitor/geo-capture')
SOURCE = Path('/opt/monitor/yuanbao_monitor/dashboard')
STAGE = BASE / 'releases/yuanbao-control-20261015'
POINTER = BASE / 'yuanbao_control_frontend.json'
IMAGE = 'monitor-dashboard:yuanbao-control-20261015'
PREVIEW = 'monitor-dashboard-yuanbao-preview'
FILES = ['app/CaptureControl.tsx', 'app/api/geo-capture/[...path]/route.ts',
         'tests/capture-gateway.test.mjs']
EXPECTED = ['1a16c967609a09e52f07f93d8d9a0806cb29f8afe0e41b5bb938a0a28dc24f10',
            '88c22cff60f4a60f226a04c7f96d90c2a7ba022137361ec84b545ba6adf85120']


def command(*args):
    return subprocess.run(args, capture_output=True, text=True, check=True, timeout=55).stdout.strip()


def get(url):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url, timeout=15) as stream:
        return json.load(stream)


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2))


def ready(port):
    for _ in range(25):
        try:
            value = get(f'http://127.0.0.1:{port}/api/geo-capture/panel')
            if len(value['models']) == 6 and any(m['id'] == 'yuanbao' for m in value['models']):
                return
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError('Six-channel dashboard readiness failed')


def main(mode):
    if mode == 'preview':
        assert not POINTER.exists(), 'Inspect previous deployment before retrying'
        for name, digest in zip(FILES, EXPECTED):
            assert hashlib.sha256((SOURCE / name).read_bytes()).hexdigest() == digest
        backup = BASE / 'backups' / ('yuanbao-frontend-' + str(int(time.time())))
        backup.mkdir(mode=0o700)
        for name in FILES:
            target = backup / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(SOURCE / name, target)
        old = command('docker', 'inspect', 'monitor-dashboard', '--format', '{{.Image}}')
        tag = 'monitor-dashboard:before-yuanbao-control-' + str(int(time.time()))
        command('docker', 'tag', old, tag)
        fleet = get('http://127.0.0.1:8803/api/status')
        units = [m['service'] for m in fleet['collectors']] + [
            'geo-editorial-scheduler.service', 'geo-editorial-api-worker.service',
            'geo-editorial-coordinator.service', 'geo-editorial-session-watch.service',
            'monitor-vps2-tunnel.service']
        value = {'created_at': time.time(), 'backup': str(backup), 'original_image': old,
                 'original_tag': tag, 'new_image': IMAGE, 'containers_before': fleet['containers'],
                 'units': units, 'services_before': command('systemctl', 'show', *units,
                 '-p', 'Id', '-p', 'MainPID', '-p', 'ExecMainStartTimestamp'),
                 'batches_before': {m['name']: {'batch': m['batch'], 'captured': m['captured'],
                 'processed': m['processed']} for m in fleet['collectors']}, 'status': 'preview'}
        write(POINTER, value)
        write(backup / 'release.json', value)
        command('docker', 'run', '-d', '--name', PREVIEW, '--network', 'host',
                '--label', 'com.docker.compose.project=geo-yuanbao-preview', IMAGE,
                'npm', 'run', 'start', '--', '-H', '0.0.0.0', '-p', '3001')
        ready(3001)
        print(json.dumps({'status': 'preview_ready', 'backup': str(backup)}))
    elif mode == 'publish':
        value = json.loads(POINTER.read_text())
        assert value['status'] == 'preview'
        qa = json.loads((BASE / 'panel-qa/yuanbao-preview.json').read_text())
        assert qa['passed'] and qa['port'] == 3001 and qa['finished_at'] > value['created_at']
        command('docker', 'tag', IMAGE, 'monitor-dashboard:local')
        compose = ['docker', 'compose', '-p', 'local-server', '-f',
                   '/opt/monitor/deploy/local-server/docker-compose.yml',
                   'up', '-d', '--no-deps', '--no-build', '--force-recreate', 'dashboard']
        try:
            command(*compose)
            ready(3000)
        except Exception:
            command('docker', 'tag', value['original_tag'], 'monitor-dashboard:local')
            command(*compose)
            value['status'] = 'rolled_back'
            write(POINTER, value)
            raise
        for name in FILES:
            target = SOURCE / name
            shutil.copy2(STAGE / name, target)
            shutil.chown(target, user='user', group='user')
            target.chmod(0o644)
        command('docker', 'rm', '-f', PREVIEW)
        value.update(status='deployed', deployed_at=time.time())
        write(POINTER, value)
        print(json.dumps({'status': 'deployed', 'backup': value['backup'],
                          'rollback_image': value['original_tag']}))
    else:
        value = json.loads(POINTER.read_text())
        fleet = get('http://127.0.0.1:8803/api/status')
        before = {c['name']: c for c in value['containers_before'] if c['name'] != 'monitor-dashboard'}
        after = {c['name']: c for c in fleet['containers'] if c['name'] != 'monitor-dashboard'}
        assert before == after, 'A non-frontend container changed'
        assert command('systemctl', 'show', *value['units'], '-p', 'Id', '-p', 'MainPID',
                       '-p', 'ExecMainStartTimestamp') == value['services_before']
        for model in fleet['collectors']:
            old = value['batches_before'][model['name']]
            assert old['batch'] == model['batch'] and model['captured'] >= old['captured']
            assert model['processed'] >= old['processed']
        result = {'checked_at': time.time(), 'non_frontend_containers_unchanged': True,
                  'collectors_editorial_and_tunnel_unchanged': True,
                  'same_batches_progress_preserved': True}
        write(BASE / 'panel-qa/yuanbao-continuity.json', result)
        print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['preview', 'publish', 'verify'])
    main(parser.parse_args().mode)
