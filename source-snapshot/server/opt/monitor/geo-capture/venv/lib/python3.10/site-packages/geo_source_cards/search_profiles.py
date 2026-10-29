"""Persistent per-channel search profiles; immutable daily task journals stay separate."""
import json,os,re,shutil,time
from pathlib import Path
from .runtime import atomic_json,process_lock

def read(path):
 try:return json.loads(Path(path).read_text('utf8'))
 except (FileNotFoundError,ValueError):return {}

def profile_for_search(runtime,model):
 if model not in {'baidu_ai','wenxin_card'}:raise ValueError('Only read-only search channels have search profiles')
 runtime=Path(runtime).resolve();legacy=runtime/'profiles/baidu/scrapling_profile'
 creation=creation_profile(runtime,model)
 if creation is not None:return creation
 # Standalone/fixture collectors keep their own accounts. A daily batch must
 # identify its own channel before sharing any session with later batches.
 if runtime.name!='collector' or runtime.parent.parent.name!='batches':return legacy
 batch=runtime.parent;config=read(batch/'manifest.json')
 if config.get('model')!=model or config.get('batch')!=batch.name:return legacy
 base=runtime.parents[2];folder=base/'profiles/search'/model;target=folder/'scrapling_profile'
 folder.mkdir(parents=True,exist_ok=True)
 with process_lock(folder/'migration.lock',blocking=True):
  marker=folder/'migration.json'
  if target.exists():
   if not marker.exists():raise RuntimeError('Search profile migration incomplete; preserve files for inspection')
   return target
  if marker.exists():raise RuntimeError('Persistent search profile missing; do not silently reset the session')
  candidates=[]
  for manifest in (base/'batches').glob('*/manifest.json'):
   source=manifest.parent
   if source==batch:continue
   cfg=read(manifest);health=read(source/'bridge_health.json');profile=source/'collector/profiles/baidu/scrapling_profile'
   planned=len(cfg.get('questions',[]))*cfg.get('rounds',0)
   if (cfg.get('model')!=model or cfg.get('batch')!=source.name or not planned
       or cfg.get('created_at',0)>config.get('created_at',0) or not profile.is_dir()
       or health.get('batch')!=source.name or health.get('status')!='complete'
       or health.get('worker_pid') or health.get('bridge_pid')
       or health.get('processed',0)<planned or health.get('tasks',{}).get('completed',0)<planned):continue
   candidates.append((cfg.get('created_at',0),source,profile))
  selected=max(candidates,key=lambda v:v[0]) if candidates else None
  source=selected[2] if selected else legacy if legacy.is_dir() else None
  if source and any((source/name).is_symlink() or (source/name).exists() for name in ('SingletonLock','SingletonSocket')):
   raise RuntimeError('Search profile source may be open; refuse unsafe migration')
  staged=folder/'scrapling_profile.migrating'
  if staged.exists():raise RuntimeError('Interrupted search profile migration; preserve staged session')
  def ignore(path,names):
   return [n for n in names if n.startswith('Singleton') or Path(path,n).is_symlink() or n in {'Cache','Code Cache','GPUCache','DawnGraphiteCache','ShaderCache','Crashpad'}]
  if source:shutil.copytree(source,staged,ignore=ignore)
  else:staged.mkdir()
  # Store provenance before promotion. A crash cannot turn partial files into
  # a new empty session or overwrite an existing persistent profile.
  record={'version':'search-profile-v1','model':model,'at':time.time(),'initial_batch':batch.name,
          'source_profile':str(source) if source else None,'source_batch':selected[1].name if selected else batch.name if source else None,
          'source_completed':bool(selected),'original_profile_preserved':True,'task_journal_copied':False}
  atomic_json(marker,record);staged.rename(target)
  if os.name!='nt':target.chmod(0o700)
  return target


def creation_profile(runtime,model):
 """Keep each creation plan/channel login across days without sharing journals."""
 if len(runtime.parents)<4 or runtime.name!='collector' or runtime.parent.name!=model or runtime.parents[2].name!='days':return None
 day=runtime.parents[1];root=runtime.parents[3];config=read(day/'config.json')
 if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',day.name) or config.get('studio_plan',{}).get('plan_id')!=root.name or model not in config.get('channels',[]):return None
 folder=root/'profiles/search'/model;target=folder/'scrapling_profile';marker=folder/'migration.json'
 folder.mkdir(parents=True,exist_ok=True)
 with process_lock(folder/'migration.lock',blocking=True):
  if target.exists():
   saved=read(marker)
   if saved.get('plan_id')!=root.name or saved.get('model')!=model:raise RuntimeError('Creation profile identity mismatch')
   return target
  if marker.exists():raise RuntimeError('Creation profile missing; preserve migration evidence')
  candidates=[]
  for prior in sorted((root/'days').iterdir()):
   if prior.name>=day.name or not re.fullmatch(r'\d{4}-\d{2}-\d{2}',prior.name):continue
   cfg=read(prior/'config.json');path=prior/model/'results.jsonl';profile=prior/model/'collector/profiles/baidu/scrapling_profile'
   if cfg.get('studio_plan',{}).get('plan_id')!=root.name or not path.is_file() or not profile.is_dir():continue
   rows=[json.loads(line) for line in path.read_text().splitlines() if line.strip()]
   expected={(q,round_) for q in cfg.get('questions',[]) for round_ in range(1,cfg.get('rounds',1)+1)}
   completed={(r.get('question'),r.get('round',1)) for r in rows if r.get('model')==model and r.get('body_capture_complete') is not False and r.get('source_capture_complete') is not False}
   if expected and expected<=completed:candidates.append((prior.name,profile))
  legacy=runtime/'profiles/baidu/scrapling_profile'
  source=max(candidates)[1] if candidates else legacy if legacy.is_dir() else None
  if source and any((source/name).exists() or (source/name).is_symlink() for name in ('SingletonLock','SingletonSocket')):raise RuntimeError('Creation profile source may still be open')
  staged=folder/'scrapling_profile.migrating'
  if staged.exists():raise RuntimeError('Interrupted creation profile migration')
  if source:shutil.copytree(source,staged,ignore=lambda path,names:[n for n in names if n.startswith('Singleton') or Path(path,n).is_symlink() or n in {'Cache','Code Cache','GPUCache','Crashpad'}])
  else:staged.mkdir()
  atomic_json(marker,{'version':'creation-search-profile-v1','plan_id':root.name,'model':model,'at':time.time(),'source_profile':str(source) if source else None,'task_journal_copied':False})
  staged.rename(target)
  if os.name!='nt':target.chmod(0o700)
  return target
