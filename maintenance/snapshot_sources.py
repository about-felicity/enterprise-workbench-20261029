"""Refresh the reviewed source baseline; never deploy or read private configs."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

WORKSPACE = Path(__file__).resolve().parents[1]
DEST = WORKSPACE / 'source-snapshot'

def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-archive', type=Path)
    parser.add_argument('--refresh-local', action='store_true')
    args = parser.parse_args()
    DEST.mkdir(exist_ok=True)
    if args.server_archive:
        with tarfile.open(args.server_archive, 'r:gz') as tar:
            report = json.load(tar.extractfile('production-manifest.json'))
            allowed = {r['snapshot']: r for r in report['files']}
            for member in tar.getmembers():
                if member.name == 'production-manifest.json':continue
                if member.name not in allowed or not member.isfile():raise ValueError('Unlisted archive member')
                target = (DEST / member.name).resolve()
                if DEST.resolve() not in target.parents:raise ValueError('Archive path escapes source snapshot')
                data = tar.extractfile(member).read()
                if hashlib.sha256(data).hexdigest() != allowed[member.name]['sha256']:raise ValueError('Server source hash mismatch')
                write(target, data)
            write(DEST / 'production-manifest.json', json.dumps(report, ensure_ascii=False, indent=2).encode())
    if args.refresh_local:
        path = WORKSPACE / 'geo-monitor-deploy/releases/20261015/unified-current/manifest.json'
        manifest = json.loads(path.read_text('utf-8'))
        seen = set()
        for item in manifest['files']:
            name = item['source']
            if name in seen:continue
            source = (WORKSPACE / name).resolve()
            if WORKSPACE not in source.parents:raise ValueError('Local source path escapes workspace')
            data = source.read_bytes()
            if hashlib.sha256(data).hexdigest() != item['sha256']:raise ValueError('Regenerate release manifest before snapshotting ' + name)
            if re.search(rb'sk-[A-Za-z0-9_-]{20,}', data) or b'-----BEGIN OPENSSH PRIVATE KEY-----' in data:raise ValueError('Credential pattern in ' + name)
            write(DEST / 'local' / name, data)
            seen.add(name)
        write(DEST / 'local-manifest.json', path.read_bytes())
        clients = []
        client_root = WORKSPACE / 'deepseek-browser-deploy/public_client'
        for source in sorted(client_root.rglob('*')):
            relative = source.relative_to(client_root)
            if not source.is_file() or any(p in {'config', 'data', '__pycache__', 'node_modules'} for p in relative.parts):continue
            if source.suffix not in {'.py', '.js', '.html', '.css', '.cmd', '.ps1', '.md'} and source.name not in {'manifest.json', '.upstream.json', 'questions.txt', '使用说明.txt'}:continue
            data = source.read_bytes()
            if re.search(rb'sk-[A-Za-z0-9_-]{20,}', data):raise ValueError('Credential pattern in client source')
            name = 'client/deepseek-browser-deploy/public_client/' + relative.as_posix()
            write(DEST / name, data)
            clients.append({'snapshot': name, 'source': source.relative_to(WORKSPACE).as_posix(), 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
        write(DEST / 'client-manifest.json', json.dumps({'files': clients, 'excluded': ['config/', 'data/', 'device/upload/enrollment credentials'], 'scope': 'Reviewed local DeepSeek public client source; bootstrap credentials remain private'}, ensure_ascii=False, indent=2).encode())
        # Preserve upstream identity without touching its repository or uncommitted work.
        upstream = {}
        for name in ('geo-source-card-collectors', 'redroid', 'Scrapling', 'doubao-headless-technical-docs'):
            result = subprocess.run(['git', '-C', str(WORKSPACE / name), 'rev-parse', 'HEAD'], capture_output=True, text=True)
            upstream[name] = {'head': result.stdout.strip(), 'source_changes_in_snapshot': name == 'geo-source-card-collectors'}
        write(DEST / 'upstreams.json', json.dumps(upstream, ensure_ascii=False, indent=2).encode())
    if not args.server_archive and not args.refresh_local:parser.error('Choose a source archive or --refresh-local')
    files = [p for p in DEST.rglob('*') if p.is_file()]
    print(json.dumps({'snapshot_files': len(files), 'bytes': sum(p.stat().st_size for p in files), 'server_files': len(json.loads((DEST / 'production-manifest.json').read_text())['files']) if (DEST / 'production-manifest.json').exists() else 0}))

if __name__ == '__main__':main()
