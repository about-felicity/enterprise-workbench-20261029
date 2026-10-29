"""Run only after the candidate API is installed. Preserve history and all originals."""
import sys,json,shutil,time,hashlib
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import studio,runtime,knowledge_library as lib,product_images
base=Path('/opt/monitor/geo-content/maintenance/upload-reliability-20261028')
aliases={'library-1ec41916a4274125af9ee1b01a694631':'科熙本植萃奢护染发剂','library-3e3a558b9ef4409bbbcd2560fbefc51c':'梵玢FBCY龙胆黑钻护发精油'}
with runtime.process_lock(runtime.BASE/'knowledge-actions.lock',blocking=True):
 records=lib.records();products=studio.products();changes=[];moved=[]
 # Snapshot metadata and immutable task/product references before any merge.
 backup=base/'knowledge-before';assert not backup.exists(),'merge has already run'
 backup.mkdir(parents=True)
 shutil.copytree(studio.ROOT/'library',backup/'library')
 for p in (studio.ROOT/'images').glob('image-*/metadata.json'):
  dst=backup/'images'/p.parent.name/'metadata.json';dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dst)
 stable={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ['products','plans','days'] for p in (studio.ROOT/folder).rglob('*.json')}
 original_images={i['image_id']:hashlib.sha256((studio.ROOT/'images'/i['image_id']/'original').read_bytes()).hexdigest() for i in product_images.images()}
 for old in records:
  if old.get('product_id'):continue
  sources={u.get('sha256') for u in old.get('uploads',[]) if u.get('sha256')}
  matches=[p for p in products if p['product']['name']==aliases.get(old['library_id'],old['name']) or p.get('word_source',{}).get('sha256') in sources]
  if not matches:continue # A genuinely new product remains one pending entry.
  assert len(matches)==1,old['name'];product=matches[0];pid=product['product_id']
  targets=[r for r in records if r.get('product_id')==pid];assert len(targets)==1,old['name']
  current=lib.record(targets[0]['library_id'])
  by_hash={}
  for u in old.get('uploads',[])+current.get('uploads',[]):
   key=u.get('sha256') or u['import_id'];prior=by_hash.get(key)
   if not prior or (u.get('status')=='published',u.get('uploaded_at',0))>(prior.get('status')=='published',prior.get('uploaded_at',0)):by_hash[key]=u
  current['uploads']=sorted(by_hash.values(),key=lambda u:u.get('uploaded_at') or 0)
  for n,u in enumerate(current['uploads'],1):u['revision']=n
  current['aliases']=sorted(set(current.get('aliases',[])+[old['name']]))
  current['merged_library_ids']=sorted(set(current.get('merged_library_ids',[])+[old['library_id']]))
  current['updated_at']=max(current['updated_at'],old['updated_at'])
  runtime.atomic_json(studio.ROOT/'library'/(current['library_id']+'.json'),current)
  with runtime.process_lock(studio.ROOT/'image-locks'/(old['library_id']+'.lock'),blocking=True):
   old.update(merged_into=current['library_id'],product_id=pid,merged_at=time.time())
   runtime.atomic_json(studio.ROOT/'library'/(old['library_id']+'.json'),old)
   for image in product_images.images():
    if image.get('library_id')!=old['library_id']:continue
    image.update(product_id=pid,library_id='',previous_library_id=old['library_id'])
    runtime.atomic_json(studio.ROOT/'images'/image['image_id']/'metadata.json',image);moved.append(image['image_id'])
  changes.append({'from':old['library_id'],'to':current['library_id'],'product':product['product']['name']})
 # Remove repeated identical revisions within each remaining active record.
 dedup=[]
 for r in lib.records():
  unique={}
  for u in r.get('uploads',[]):
   key=u.get('sha256') or u['import_id'];prior=unique.get(key)
   if not prior or (u.get('status')=='published',u.get('uploaded_at',0))>(prior.get('status')=='published',prior.get('uploaded_at',0)):unique[key]=u
  if len(unique)!=len(r.get('uploads',[])):
   r['uploads']=sorted(unique.values(),key=lambda u:u.get('uploaded_at') or 0)
   for n,u in enumerate(r['uploads'],1):u['revision']=n
   runtime.atomic_json(studio.ROOT/'library'/(r['library_id']+'.json'),r);dedup.append(r['name'])
 assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in stable.items())
 assert original_images=={i['image_id']:hashlib.sha256((studio.ROOT/'images'/i['image_id']/'original').read_bytes()).hexdigest() for i in product_images.images()}
 current=lib.records();assert len({r.get('product_id') or r['library_id'] for r in current})==len(current)
 result={'merged':changes,'images_rebound':len(moved),'active_libraries':len(current),'products':len(studio.products()),'duplicate_revisions_removed':dedup,'task_product_json_unchanged':True,'image_originals_unchanged':True}
 (base/'knowledge-merge.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
