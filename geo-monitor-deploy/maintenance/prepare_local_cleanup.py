"""Prepare a bounded local cleanup manifest; never delete or move files."""
from datetime import datetime
import gzip
import hashlib
import json
import lzma
import os
from pathlib import Path
import tarfile
import zipfile

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'geo-monitor-deploy/maintenance/20261015'
OUT.mkdir(parents=True,exist_ok=True)
if (OUT/'local-cleanup-applied.json').exists():
    raise SystemExit('Cleanup already applied; preserve the original manifest and archives.')
ART=ROOT/'redroid-deploy/artifacts'

def safe(path):
    path=path.resolve(strict=True)
    assert path.is_relative_to(ROOT) and path!=ROOT
    for parent in (path,*path.parents):
        if parent==ROOT:break
        assert not parent.is_symlink()
        assert not getattr(parent.lstat(),'st_file_attributes',0)&0x400
    return path

def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def entry(path,reason,action='remove'):
    path=safe(path)
    return {'path':str(path.relative_to(ROOT)),'bytes':path.stat().st_size,
        'sha256':digest(path),'reason':reason,'action':action}

plan={'created_at':datetime.now().astimezone().isoformat(),'root':str(ROOT),'files':[],
      'directories':[],'archive':'historical-build-copies.zip','retained_image_manifests':[]}

# Old Android NDK image downloads are reproducible installer caches. Current
# Android13/Houdini14 images, volumes and rollback copies remain on the server.
for name in ('redroid-image.tar','redroid-15.0.0_ndk_AVD.tar'):
    path=ART/name
    if not path.exists():continue
    with tarfile.open(path,'r:') as stream:
        record={'archive':name,'manifest':json.load(stream.extractfile('manifest.json'))}
        try:record['index']=json.load(stream.extractfile('index.json'))
        except KeyError:pass
        plan['retained_image_manifests'].append(record)
    plan['files'].append(entry(path,'Legacy NDK image download; installed server images and fixed manifests retained'))
image=ART/'image'
if image.exists():
    for path in image.iterdir():
        assert path.is_file() and len(path.name)==64
        assert digest(path)==path.name
        plan['files'].append(entry(path,'Verified duplicate downloaded OCI image blob'))
    plan['directories'].append(str(image.relative_to(ROOT)))

# Full historical tunnel errors are compressed losslessly; retain a small tail
# at the original path so the login scripts keep their expected log locations.
for name in ('tunnel-error.log','tunnel-15558-error.log'):
    source=ART/name
    if not source.exists() or source.stat().st_size<1024*1024:continue
    before=source.stat()
    assert __import__('time').time()-before.st_mtime>3600
    archived=OUT/(name+'.gz')
    tail=OUT/(name+'.tail')
    original_hash=hashlib.sha256()
    with source.open('rb') as src,archived.open('wb') as raw:
        with gzip.GzipFile(filename=name,mode='wb',fileobj=raw,compresslevel=1,mtime=0) as dst:
            while chunk:=src.read(4*1024*1024):original_hash.update(chunk);dst.write(chunk)
    with gzip.open(archived,'rb') as check:
        assert hashlib.file_digest(check,'sha256').hexdigest()==original_hash.hexdigest()
    after=source.stat()
    assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
    with source.open('rb') as src:
        src.seek(max(0,before.st_size-65536));tail.write_bytes(src.read())
    row=entry(source,'Lossless full gzip archive verified; retain original log path with last 64KiB','replace_with_tail')
    row.update(archive=str(archived.relative_to(ROOT)),archive_sha256=digest(archived),
        archive_bytes=archived.stat().st_size,replacement=str(tail.relative_to(ROOT)),replacement_sha256=digest(tail))
    plan['files'].append(row)

source=ART/'frida-server'
compressed=ART/'frida-server.xz'
if source.exists() and compressed.exists():
    with lzma.open(compressed,'rb') as stream:equivalent=hashlib.file_digest(stream,'sha256').hexdigest()==digest(source)
    if equivalent:plan['files'].append(entry(source,'Exact decompressed duplicate; compressed diagnostic binary retained'))

# Archive historical build copies before deleting them; keep actual sources,
# editable-install metadata, all .git directories and packaged desktop files.
builds=[]
for base in (ROOT/'outputs/intermediates',ROOT/'outputs/api-editorial/intermediates'):
    for current,dirs,files in os.walk(base):
        current=Path(current)
        for name in list(dirs):
            if name in ('build','.ruff_cache','.pytest_cache','__pycache__') or name.endswith('.egg-info'):
                builds.append(safe(current/name));dirs.remove(name)
for path in (ROOT/'geo-source-card-collectors/build',ROOT/'Scrapling/build'):
    if path.exists():builds.append(safe(path))
archived_files=[]
with zipfile.ZipFile(OUT/plan['archive'],'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
    for directory in builds:
        for path in directory.rglob('*'):
            if path.is_file():
                path=safe(path);archive.write(path,path.relative_to(ROOT).as_posix())
                row=entry(path,'Historical build copy; verified restorable zip retained')
                plan['files'].append(row);archived_files.append(row)
        plan['directories'].append(str(directory.relative_to(ROOT)))
with zipfile.ZipFile(OUT/plan['archive']) as archive:
    assert archive.testzip() is None
    for row in archived_files:
        with archive.open(Path(row['path']).as_posix()) as src:
            assert hashlib.file_digest(src,'sha256').hexdigest()==row['sha256']

# Only source-side bytecode with a corresponding .py source may be removed.
for current,dirs,files in os.walk(ROOT):
    current=Path(current)
    dirs[:]=[n for n in dirs if n not in ('.git','.venv','venv','_internal','web_profiles')
             and not (current/n).is_symlink()]
    if any(current==p or current.is_relative_to(p) for p in builds):dirs[:]=[];continue
    if current.name not in ('__pycache__','.ruff_cache','.pytest_cache'):continue
    eligible=[]
    for path in current.rglob('*'):
        if not path.is_file():continue
        if current.name=='__pycache__':
            source=current.parent/(path.name.split('.')[0]+'.py')
            if path.suffix!='.pyc' or not source.is_file():continue
        eligible.append(entry(path,'Reproducible source bytecode or lint/test cache'))
    plan['files'].extend(eligible)
    if len(eligible)==sum(1 for p in current.rglob('*') if p.is_file()):
        plan['directories'].append(str(current.relative_to(ROOT)))
    dirs[:]=[]

assert len({r['path'] for r in plan['files']})==len(plan['files'])
plan['archive_sha256']=digest(OUT/plan['archive'])
plan['gross_bytes']=sum(r['bytes'] for r in plan['files'])
plan['net_expected_bytes']=plan['gross_bytes']-(OUT/plan['archive']).stat().st_size-sum(
    r.get('archive_bytes',0)+(ROOT/r['replacement']).stat().st_size if 'replacement' in r else 0 for r in plan['files'])
(OUT/'local-cleanup-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'files':len(plan['files']),'directories':len(plan['directories']),
    'gross_bytes':plan['gross_bytes'],'net_expected_bytes':plan['net_expected_bytes'],
    'plan':str(OUT/'local-cleanup-plan.json')},ensure_ascii=True))
