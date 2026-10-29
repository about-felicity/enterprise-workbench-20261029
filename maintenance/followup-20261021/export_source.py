"""Export allowlisted production code, excluding data, credentials and runtimes."""
import ast
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile

roots = [
    (Path('/opt/monitor'), False),
    (Path('/opt/monitor/monitor_core'), True),
    (Path('/opt/monitor/model_plugins'), True),
    (Path('/opt/monitor/geo-content/engine'), True),
    (Path('/opt/monitor/geo-content/creation'), True),
    (Path('/opt/monitor/geo-capture'), False),
    (Path('/opt/monitor/yuanbao_monitor/dashboard/app'), True),
    (Path('/home/user/redroid-doubao/geo-batch-code'), True),
    (Path('/home/user/redroid-yuanbao'), False),
]
for name in ('geo_source_cards', 'web_collectors', 'monitor_core', 'wenxin_monitor'):
    roots.append((Path('/opt/monitor/geo-capture/venv/lib/python3.10/site-packages') / name, True))
for service in ('geo-deepseek-public-ingest',):
    content = subprocess.run(['systemctl', 'cat', service], capture_output=True, text=True, check=True).stdout
    for line in content.splitlines():
        if line.startswith('ExecStart='):
            for value in line.split():
                if value.startswith('/') and value.endswith('.py'):
                    roots.append((Path(value).parent, False))

allowed_suffixes = {'.py', '.js', '.ts', '.tsx', '.jsx', '.css', '.html', '.toml'}
allowed_names = {'requirements.txt', 'package.json', 'package-lock.json', 'pnpm-lock.yaml', 'Dockerfile'}
blocked_parts = {'node_modules', '__pycache__', '.git', '.venv', 'venv', 'profiles', 'runtime', 'data', 'secrets', 'logs', 'outputs', 'test-results', 'build', 'dist', 'backup'}
files = {}
excluded = []
secret_assignment = re.compile(r'(?:^|_)(?:password|passwd|secret|api_key|access_token|registration_token|enrollment_token|upload_key)(?:$|_)', re.I)

def sensitive(path, text):
    if re.search(r'sk-[A-Za-z0-9_-]{20,}', text) or '-----BEGIN OPENSSH PRIVATE KEY-----' in text or '-----BEGIN RSA PRIVATE KEY-----' in text:
        return 'credential_pattern'
    if path.suffix == '.py':
        try:
            tree = ast.parse(text)
        except SyntaxError:
            return 'source_parse_error'
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str) and len(node.value.value) >= 12:
                if any(isinstance(t, ast.Name) and secret_assignment.search(t.id) for t in node.targets):
                    return 'possible_literal_credential'
    return None

for root, recursive in roots:
    if not root.exists():
        excluded.append({'path': str(root), 'reason': 'missing_optional_source_root'})
        continue
    candidates = root.rglob('*') if recursive else root.iterdir()
    for path in candidates:
        relative = path.relative_to(root)
        if any(part in blocked_parts or part.startswith('backup-') for part in relative.parts) or path.is_symlink() or not path.is_file():
            continue
        if path.suffix not in allowed_suffixes and path.name not in allowed_names:
            continue
        if path.stat().st_size > 2_000_000:
            excluded.append({'path': str(path), 'reason': 'source_size_limit'})
            continue
        data = path.read_bytes()
        try:
            reason = sensitive(path, data.decode('utf-8-sig'))
        except UnicodeDecodeError:
            reason = 'non_text_file'
        if reason:
            excluded.append({'path': str(path), 'reason': reason})
            continue
        files[str(path)] = data

manifest = []
archive = Path('/tmp/geo-production-source-20261021.tar.gz')
with tarfile.open(archive, 'w:gz') as tar:
    for path, data in sorted(files.items()):
        name = 'server' + path
        item = tarfile.TarInfo(name); item.size = len(data); item.mode = 0o644
        tar.addfile(item, io.BytesIO(data))
        manifest.append({'snapshot': name, 'server': path, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    report = {'files': manifest, 'excluded': excluded, 'scope': 'Allowlisted production text source, complete creation engine where source passes credential checks; excludes private configs, dependencies, databases, queues, profiles and binaries. Not a complete machine restore.', 'production_mutated': False}
    data = json.dumps(report, ensure_ascii=False, indent=2).encode()
    item = tarfile.TarInfo('production-manifest.json'); item.size = len(data); item.mode = 0o644
    tar.addfile(item, io.BytesIO(data))
archive.chmod(0o644)
print(json.dumps({'files': len(manifest), 'bytes': archive.stat().st_size, 'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'excluded': excluded}, ensure_ascii=False))
