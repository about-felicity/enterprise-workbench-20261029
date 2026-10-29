"""Package only source and fixtures, leaving production untouched."""
import hashlib
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
entries = []
for folder, prefix in [(ROOT / 'geo-source-card-collectors/geo_source_cards', 'engine/geo_source_cards'),
                       (ROOT / 'geo-source-card-collectors/tests', 'engine/tests'),
                       (ROOT / 'geo-monitor-deploy/creation', 'creation')]:
    for path in sorted(folder.rglob('*')):
        if not path.is_file() or '__pycache__' in path.parts:
            continue
        if path.suffix not in {'.py', '.json', '.html', '.md', '.txt'}:
            continue
        entries.append((path, prefix + '/' + path.relative_to(folder).as_posix()))
entries.append((HERE / 'validate.py', 'validate.py'))
with tarfile.open(HERE / 'validation-source.tar.gz', 'w:gz') as archive:
    for path, name in entries:
        archive.add(path, arcname=name, recursive=False)
manifest = [{'path': name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()} for path, name in entries]
(HERE / 'validation-source-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf8')
print(json.dumps({'files': len(entries), 'archive': str(HERE / 'validation-source.tar.gz')}))
