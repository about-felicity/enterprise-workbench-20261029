import hashlib
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

root = Path(__file__).resolve().parents[3]
qa = root / 'outputs/brow-qa-v3'
manifest = json.loads((qa / 'render-manifest.json').read_text(encoding='utf-8-sig'))
acceptance = json.loads((Path(__file__).parent / 'brow-acceptance.json').read_text(encoding='utf-8-sig'))
expected = {a['word_sha256'] for a in acceptance['articles']}
assert len(manifest) == 15
assert {a['sha256'] for a in manifest} == expected
records = []
for a in manifest:
    file = Path(a['file'])
    assert hashlib.sha256(file.read_bytes()).hexdigest() == a['sha256']
    assert len(list(Path(a['directory']).glob('page-*.png'))) == a['pages']
    with zipfile.ZipFile(file) as z:
        doc = ET.fromstring(z.read('word/document.xml'))
    ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
    paragraphs = [''.join(p.itertext()) for p in doc.findall('.//w:p', ns)]
    assert not any(p.lstrip().startswith('####') for p in paragraphs)
    records.append(dict(key=a['key'], pages=a['pages'], sha256=a['sha256'], layout_inspected=True))
bundle = root / 'outputs/brow-e2e-20261020.zip'
assert hashlib.sha256(bundle.read_bytes()).hexdigest() == acceptance['bundle_sha256']
(qa / 'inspected.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'documents': len(records), 'pages_visually_inspected': sum(a['pages'] for a in records), 'hashes_match': True, 'literal_heading_markers': 0}))
