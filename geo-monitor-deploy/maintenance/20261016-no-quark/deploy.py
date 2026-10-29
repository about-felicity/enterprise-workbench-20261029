"""Frontend-only release; never restart collectors, APIs, or databases."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
import urllib.request

ROOT = Path('/opt/monitor/geo-capture/maintenance/20261016-no-quark')
SOURCE = Path('/opt/monitor/yuanbao_monitor/dashboard/app/Dashboard.tsx')
POINTER = ROOT / 'release.json'
IMAGE = 'monitor-dashboard:no-quark-20261016'
PREVIEW = 'monitor-dashboard-no-quark-preview'
EXPECTED = 'd356016f9f0c3e3ff09bc5f02f26770910034165988839f55451ff9e9d384a1d'

def run(*args, timeout=60):
    return subprocess.check_output(args, text=True, timeout=timeout).strip()

def save(value):
    POINTER.write_text(json.dumps(value, ensure_ascii=False, indent=2))

def containers():
    names = run('docker', 'ps', '--format', '{{.Names}}').splitlines()
    names = [name for name in names if name not in {'monitor-dashboard', PREVIEW}]
    return {item['Name']: {'image': item['Image'], 'started_at': item['State']['StartedAt']}
            for item in json.loads(run('docker', 'inspect', *names))}

def ready(port):
    for _ in range(25):
        try:
            for path in ['geo-capture', 'geo-creation']:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/{path}/panel', timeout=5) as response:
                    payload = json.load(response)
                if path == 'geo-capture':
                    assert len(payload['models']) == 6
                else:
                    assert payload['ok']
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError('Frontend readiness check failed')

def main(mode):
    ROOT.mkdir(parents=True, exist_ok=True)
    if mode == 'preview':
        assert not POINTER.exists(), 'Inspect the existing release before repeating'
        assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED, 'Production source changed'
        backup = ROOT / 'Dashboard.before.tsx'
        shutil.copy2(SOURCE, backup)
        old = run('docker', 'inspect', 'monitor-dashboard', '--format', '{{.Image}}')
        rollback = 'monitor-dashboard:before-no-quark-' + str(int(time.time()))
        run('docker', 'tag', old, rollback)
        value = {'at': time.time(), 'status': 'building', 'original_image': old,
                 'rollback_tag': rollback, 'new_image': IMAGE, 'backup': str(backup),
                 'non_frontend_before': containers(), 'source_sha_before': EXPECTED}
        save(value)
        (ROOT / 'Dockerfile').write_text(
            f'FROM {rollback}\nCOPY Dashboard.tsx /dashboard/app/Dashboard.tsx\n'
            'WORKDIR /dashboard\n'
            'RUN node --experimental-strip-types --test tests/capture-gateway.test.mjs tests/creation-gateway.test.mjs\n'
            'RUN node --test --test-skip-pattern="总览提供每日自有产品跨模型上榜看板并区分缺数与负样本" tests/rendered-html.test.mjs\n'
            'RUN npm run build\n')
        subprocess.run(['docker', 'build', '-t', IMAGE, str(ROOT)], check=True, timeout=600)
        run('docker', 'run', '-d', '--name', PREVIEW, '--network', 'host', IMAGE,
            'npm', 'run', 'start', '--', '-H', '0.0.0.0', '-p', '3001')
        ready(3001)
        value['status'] = 'preview'
        save(value)
        print(json.dumps({'status': 'preview', 'port': 3001}))
    elif mode == 'publish':
        value = json.loads(POINTER.read_text())
        assert value['status'] == 'preview'
        assert json.loads((ROOT / 'qa-3001.json').read_text())['passed']
        assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == EXPECTED
        assert run('docker', 'inspect', 'monitor-dashboard', '--format', '{{.Image}}') == value['original_image']
        compose = ['docker', 'compose', '-p', 'local-server', '-f',
                   '/opt/monitor/deploy/local-server/docker-compose.yml',
                   'up', '-d', '--no-deps', '--no-build', '--force-recreate', 'dashboard']
        run('docker', 'tag', IMAGE, 'monitor-dashboard:local')
        try:
            run(*compose)
            ready(3000)
            shutil.copyfile(ROOT / 'Dashboard.tsx', SOURCE)
        except Exception:
            run('docker', 'tag', value['rollback_tag'], 'monitor-dashboard:local')
            run(*compose)
            ready(3000)
            value['status'] = 'rolled_back'
            save(value)
            raise
        value.update(status='published', published_at=time.time(),
                     source_sha=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                     non_frontend_after=containers())
        value['non_frontend_containers_unchanged'] = value['non_frontend_before'] == value['non_frontend_after']
        save(value)
        assert value['non_frontend_containers_unchanged']
        print(json.dumps({'status': 'published', 'non_frontend_containers_unchanged': True,
                          'source_sha': value['source_sha']}))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['preview', 'publish'])
    main(parser.parse_args().mode)
