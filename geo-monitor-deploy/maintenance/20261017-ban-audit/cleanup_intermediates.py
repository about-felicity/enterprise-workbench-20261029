"""Explicit plan/apply cleanup of this session's unreferenced temporary files and dangling build images."""
import hashlib,json,os,stat,subprocess,sys,time
from pathlib import Path
ROOT=Path('/opt/monitor/geo-capture/maintenance/20261017-cleanup');ROOT.mkdir(exist_ok=True)
PREFIXES=('geo-input-','geo-risk-','geo-test-channel-','geo-scrcpy-','geo-ban-')
APKS={'deepseek-account2-verified.apk','deepseek-manual-test-signed.apk'}
def run(*args):return subprocess.check_output(args,text=True,stderr=subprocess.STDOUT,timeout=60).strip()
def refs():
 args=[];opened=set();unit_text=''
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:args.append((p/'cmdline').read_bytes().replace(b'\x00',b' ').decode(errors='replace'))
  except OSError:pass
  try:
   for f in (p/'fd').iterdir():
    try:opened.add(os.readlink(f))
    except OSError:pass
  except OSError:pass
 for root in ['/etc/systemd/system','/run/systemd/transient']:
  for p in Path(root).rglob('*'):
   if p.suffix not in {'.service','.timer','.conf'} or p.is_symlink():continue
   try:unit_text+=p.read_text(errors='replace')+'\n'
   except OSError:pass
 return '\n'.join(args),opened,unit_text
def images():
 ids=list(set(run('docker','image','ls','-q','--no-trunc').splitlines()))
 values=json.loads(run('docker','image','inspect',*ids)) if ids else []
 mapping={v['Id']:v for v in values}
 containers=run('docker','ps','-aq').splitlines()
 used={v['Image'] for v in json.loads(run('docker','inspect',*containers))} if containers else set()
 used|={v['Id'] for v in values if v.get('RepoTags') or v.get('RepoDigests')}
 pending=list(used)
 while pending:
  parent=mapping.get(pending.pop(),{}).get('Parent')
  if parent and parent not in used:used.add(parent);pending.append(parent)
 return mapping,used
def eligible(p,args,opened,units):
 if p.is_symlink() or not p.is_file() or p.resolve().parent!=Path('/tmp'):return False
 if not(p.name.startswith(PREFIXES) or p.name in APKS):return False
 if 'evidence' in p.name or 'proof' in p.name:return False
 if time.time()-p.stat().st_mtime<120:return False
 if str(p) in args or str(p) in opened or str(p) in units:return False
 if p.name in APKS:
  if hashlib.sha256(p.read_bytes()).hexdigest()!='1468cae414245e6bd447b0ae79c277958a6da1c25f4e4798ffc04e42127fa14a':return False
  if not Path('/var/lib/docker/volumes/deepseek-manual-test-data/_data').is_dir():return False
 return True
mode=sys.argv[1]
if mode=='plan':
 args,opened,units=refs();files=[]
 for p in Path('/tmp').iterdir():
  if not eligible(p,args,opened,units):continue
  s=p.stat();files.append({'path':str(p),'size':s.st_size,'inode':s.st_ino,'mtime_ns':s.st_mtime_ns,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 mapping,used=images()
 candidates=[{'id':k,'created':v['Created'],'size_including_shared_layers':v['Size']} for k,v in mapping.items() if k not in used and not v.get('RepoTags') and not v.get('RepoDigests')]
 candidates.sort(key=lambda v:v['created'],reverse=True)
 data={'at':time.time(),'files':files,'images':candidates,'protected_images':len(used),'note':'Only explicit regular /tmp files; all containers, volumes, tagged/referenced images, ancestors, maintenance reports and evidence preserved.'}
 (ROOT/'plan.json').write_text(json.dumps(data,indent=2));print(json.dumps({'files':len(files),'file_bytes':sum(f['size'] for f in files),'dangling_unreferenced_images':len(candidates),'protected_images':len(used)}))
elif mode=='apply':
 plan=json.loads((ROOT/'plan.json').read_text());assert time.time()-plan['at']<1800
 args,opened,units=refs();deleted=[];skipped=[]
 for f in plan['files']:
  p=Path(f['path'])
  if not eligible(p,args,opened,units):skipped.append(str(p));continue
  s=p.stat()
  if (s.st_ino,s.st_mtime_ns,s.st_size)!=(f['inode'],f['mtime_ns'],f['size']) or hashlib.sha256(p.read_bytes()).hexdigest()!=f['sha256']:skipped.append(str(p));continue
  p.unlink();deleted.append(f)
 removed=[];image_skips=[]
 for item in plan['images']:
  mapping,used=images();v=mapping.get(item['id'])
  if not v or item['id'] in used or v.get('RepoTags') or v.get('RepoDigests'):image_skips.append(item['id']);continue
  try:run('docker','image','rm',item['id']);removed.append(item['id'])
  except subprocess.CalledProcessError:image_skips.append(item['id'])
 result={'at':time.time(),'deleted_files':deleted,'deleted_file_bytes':sum(f['size'] for f in deleted),'skipped_files':skipped,'removed_dangling_images':removed,'skipped_images':image_skips}
 (ROOT/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps({'deleted_files':len(deleted),'deleted_file_bytes':result['deleted_file_bytes'],'removed_dangling_images':len(removed),'skipped_files':len(skipped),'skipped_images':len(image_skips)}))
else:raise ValueError('plan or apply')
