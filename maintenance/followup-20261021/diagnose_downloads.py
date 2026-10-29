"""Inspect existing GEO downloads and narrowly filtered browser download metadata."""
import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

home = Path.home()
out = []
for path in (home / 'Downloads').glob('*.zip'):
    if path.name not in {'article.zip'} and '创作' not in path.name and 'creation' not in path.name.lower():
        continue
    row = {'path': str(path), 'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'zip': zipfile.is_zipfile(path)}
    if row['zip']:
        with zipfile.ZipFile(path) as z:
            row.update(entries=z.namelist(), crc_error=z.testzip())
            for name in ('导出清单.json', 'manifest.json'):
                if name in z.namelist() and z.getinfo(name).file_size < 100000:
                    row['manifest'] = json.loads(z.read(name))
    else:
        row['magic_hex'] = path.read_bytes()[:16].hex()
    out.append(row)

history = []
for vendor in ('Google/Chrome', 'Microsoft/Edge'):
    base = Path(os.environ['LOCALAPPDATA']) / vendor / 'User Data'
    for profile in [base / 'Default'] + sorted(base.glob('Profile *')):
        source = profile / 'History'
        if not source.exists():
            continue
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / 'History'
            try:
                shutil.copy2(source, copy)
                db = sqlite3.connect('file:' + copy.as_posix() + '?mode=ro', uri=True)
                db.row_factory = sqlite3.Row
                rows = db.execute("select id,target_path,start_time,received_bytes,total_bytes,state,interrupt_reason from downloads where start_time>=?", (int((datetime(2026, 10, 19, tzinfo=timezone.utc) - datetime(1601, 1, 1, tzinfo=timezone.utc)).total_seconds() * 1000000),)).fetchall()
                for row in rows:
                    urls = [v[0] for v in db.execute('select url from downloads_url_chains where id=? order by chain_index', (row['id'],))]
                    if not any('geo-creation' in u or 'geo_monitor' in u for u in urls):
                        continue
                    clean = []
                    for url in urls:
                        u = urlsplit(url)
                        clean.append(u.scheme + '://' + u.netloc + u.path)
                    query = parse_qs(urlsplit(urls[0]).query) if urls else {}
                    filters = {k: v for k, v in query.items() if k in {'job', 'article', 'kind', 'date', 'product', 'source', 'plan'}}
                    started = (datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=row['start_time'])).astimezone(timezone(timedelta(hours=8))).isoformat()
                    history.append({'browser': vendor, 'profile': profile.name, **dict(row), 'started_at_beijing': started, 'url_paths_without_queries': clean, 'download_filters': filters})
                db.close()
            except (OSError, sqlite3.Error) as error:
                history.append({'browser': vendor, 'profile': profile.name, 'inspection_error': type(error).__name__})
report = {'files': out, 'geo_download_history': history, 'original_files_modified': False}
Path(__file__).with_name('download-forensics.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
