import os,json,time,gzip,hashlib
from pathlib import Path
from datetime import datetime
ROOT=Path.cwd().resolve();OUT=ROOT/'geo-monitor-deploy/maintenance/20261021-cleanup';OUT.mkdir(exist_ok=True)
assert not (OUT/'applied.json').exists(),'Cleanup already applied'
def safe(p):
 p=Path(p).absolute();assert p.is_relative_to(ROOT) and p!=ROOT
 for q in [p,*p.parents]:
  if q==ROOT:break
  assert not q.is_symlink() and not (getattr(q.lstat(),'st_file_attributes',0)&0x400),str(q)
 return p
rows=[]
for base,dirs,files in os.walk(ROOT):
 dirs[:]=[d for d in dirs if d!='.git' and not (getattr(Path(base,d).lstat(),'st_file_attributes',0)&0x400) and not Path(base,d).is_symlink()]
 for n in list(dirs):
  p=Path(base,n);parts=p.relative_to(ROOT).parts
  remove=n in {'__pycache__','.pytest_cache','.mypy_cache','.ruff_cache'} or (n in {'Cache','Code Cache','GPUCache','GrShaderCache','ShaderCache','DawnCache'} and 'diagnostics' in parts and any(x in parts for x in ['deepseek-login-20261010','deepseek-login-20261012']))
  if not remove:continue
  safe(p);sizes=[]
  for b,ds,fs in os.walk(p):
   for d in ds:safe(Path(b,d))
   for f in fs:sizes.append(safe(Path(b,f)).stat().st_size)
  rows.append({'path':str(p.relative_to(ROOT)),'bytes':sum(sizes),'files':len(sizes),'reason':'Regenerable bytecode/test cache or inactive historical browser cache'})
  dirs.remove(n)
bad=ROOT/'outputs/creation-quality-20261021/eye-pages'
if bad.exists() and (ROOT/'outputs/creation-quality-20261021/eye-pages-final').exists():
 safe(bad);paths=[safe(p) for p in bad.rglob('*') if p.is_file()];rows.append({'path':str(bad.relative_to(ROOT)),'bytes':sum(p.stat().st_size for p in paths),'files':len(paths),'reason':'Superseded failed blank Word rendering; verified final render retained'})
log=safe(ROOT/'yuanbao-deploy/artifacts/tunnel-error.log');before=log.stat();assert time.time()-before.st_mtime>3600
archive=OUT/'yuanbao-tunnel-error-full.log.gz';tail=OUT/'yuanbao-tunnel-error.tail';h=hashlib.sha256()
with log.open('rb') as src,archive.open('wb') as raw:
 with gzip.GzipFile(filename='yuanbao-tunnel-error.log',mode='wb',fileobj=raw,mtime=0,compresslevel=1) as dst:
  while chunk:=src.read(4*1024*1024):h.update(chunk);dst.write(chunk)
with gzip.open(archive,'rb') as src:assert hashlib.file_digest(src,'sha256').hexdigest()==h.hexdigest()
after=log.stat();assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
with log.open('rb') as src:src.seek(max(0,before.st_size-65536));tail.write_bytes(src.read())
plan={'created_at':datetime.now().astimezone().isoformat(),'root':str(ROOT),'directories':rows,'log':{'path':str(log.relative_to(ROOT)),'bytes':before.st_size,'mtime_ns':before.st_mtime_ns,'sha256':h.hexdigest(),'archive':str(archive.relative_to(ROOT)),'archive_bytes':archive.stat().st_size,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'replacement':str(tail.relative_to(ROOT)),'tail_bytes':tail.stat().st_size,'tail_sha256':hashlib.sha256(tail.read_bytes()).hexdigest()},'scope':'Local only; runtime/source/data/login/results/rollback evidence and reparse targets retained'}
(OUT/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'cache_dirs':len(rows),'cache_mb':round(sum(v['bytes'] for v in rows)/1048576,2),'cache_files':sum(v['files'] for v in rows),'original_log_mb':round(before.st_size/1048576,2),'lossless_gzip_mb':round(archive.stat().st_size/1048576,2),'planned_net_reclaimed_mb':round((sum(v['bytes'] for v in rows)+before.st_size-archive.stat().st_size-tail.stat().st_size)/1048576,2)},ensure_ascii=False))
