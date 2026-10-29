"""Update only deployed Baidu files; preserve undeployed login edits outside bundle."""
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

release = Path('geo-monitor-deploy/releases/20261015/unified-current')
backup = Path('geo-monitor-deploy/maintenance/20261016-daily-start/bundle-before-baidu')
backup.mkdir(exist_ok=False)
for name in ('manifest.json', 'source.zip'):
    shutil.copy2(release / name, backup / name)
manifest = json.loads((release / 'manifest.json').read_text('utf8'))
updates = {
    'geo-monitor-deploy/capture_bridge.py': '/opt/monitor/geo-capture/capture_bridge.py',
    'geo-monitor-deploy/baidu_body_delivery.py': '/opt/monitor/geo-capture/baidu_body_delivery.py',
    'geo-source-card-collectors/geo_source_cards/cli.py': '/opt/monitor/geo-capture/venv/lib/python3.10/site-packages/geo_source_cards/cli.py',
    'geo-source-card-collectors/wenxin_monitor/controller.py': '/opt/monitor/geo-capture/venv/lib/python3.10/site-packages/wenxin_monitor/controller.py',
}
with zipfile.ZipFile(release / 'source.zip') as archive:
    files = {name: archive.read(name) for name in archive.namelist()}
for source, target in updates.items():
    data = Path(source).read_bytes()
    files[source] = data
    entry = {'source': source, 'server': target, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
    matches = [i for i, old in enumerate(manifest['files']) if old['server'] == target]
    if matches:
        manifest['files'][matches[0]] = entry
    else:
        manifest['files'].append(entry)
stage = release / 'source.staged.zip'
with zipfile.ZipFile(stage, 'w', zipfile.ZIP_DEFLATED) as archive:
    for name, data in files.items():
        archive.writestr(name, data)
stage.replace(release / 'source.zip')
manifest['zip_sha256'] = hashlib.sha256((release / 'source.zip').read_bytes()).hexdigest()
(release / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf8')
print(json.dumps({'files': len(manifest['files']), 'updated': list(updates)}))
