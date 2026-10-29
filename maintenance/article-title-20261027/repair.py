import hashlib,json,shutil,time
from pathlib import Path
from geo_source_cards.article_title import normalize,display_title
from geo_source_cards.word_export import export_docx
from geo_source_cards.runtime import atomic_json,atomic_write,process_lock
from creation import runtime
D=Path('/opt/monitor/geo-content/maintenance/20261027-article-title');changed=[];busy=[]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for root in runtime.BASE.glob('runs/*'):
 candidates=[]
 for file in root.glob('approved/*/*/*/draft.md'):
  text=file.read_text();context=runtime.read(file.parent/'rewrite_context.json');fixed=normalize(text,context.get('product'),context.get('category'))
  if fixed!=text and (not text.strip().startswith('# ') or len(text.strip().splitlines()[0])>82):candidates.append((file,text,fixed))
 if not candidates:continue
 try:
  with process_lock(root/'api/worker.lock',blocking=False):
   for file,old,fixed in candidates:
    folder=file.parent;receipt=runtime.read(folder/'receipt.json')
    if receipt.get('delivery_mode')!='direct':continue
    assert file.read_text()==old
    for name,digest in receipt['files'].items():assert sha(folder/name)==digest,(folder,name)
    backup=D/'articles-before'/file.parent.relative_to(runtime.BASE)
    if backup.exists():raise ValueError('Unexpected duplicate migration '+str(folder))
    shutil.copytree(folder,backup)
    # Generate first, publish the matching receipt last. Readers reject a mixed generation.
    export_docx(fixed,folder/'article.title-repair.docx')
    atomic_write(file,fixed);(folder/'article.title-repair.docx').replace(folder/'article.docx')
    done=runtime.read(folder/'writer_done.json');done['draft_sha256']=sha(file)
    atomic_json(folder/'writer_done.json',done)
    record={'at':time.time(),'operation':'add_or_normalize_independent_title','old_draft_sha256':hashlib.sha256(old.encode()).hexdigest(),'new_draft_sha256':sha(file),'body_preserved':True,'title':display_title(fixed),'review_performed':False}
    atomic_json(folder/'title_revision.json',record)
    receipt['files']={name:sha(folder/name) for name in receipt['files']}
    receipt['files']['title_revision.json']=sha(folder/'title_revision.json');receipt['word_sha256']=sha(folder/'article.docx')
    atomic_json(folder/'receipt.json',receipt)
    changed.append({'path':str(folder),**record})
 except BlockingIOError:busy.append(str(root))
result={'at':time.time(),'changed':changed,'busy':busy}
out=D/('repair-'+str(int(time.time()))+'.json');atomic_json(out,result)
print(json.dumps({'changed':len(changed),'busy':busy,'report':str(out),'samples':changed[:3]},ensure_ascii=False))
