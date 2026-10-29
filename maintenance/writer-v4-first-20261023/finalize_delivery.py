import hashlib,json,shutil,sys,zipfile
from pathlib import Path
def deny(event,args):
 if event in ('socket.connect','socket.getaddrinfo','socket.sendto'):raise RuntimeError('Offline finalization only')
sys.addaudithook(deny)
root=Path(sys.argv[1]);sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();read=lambda p:json.loads(Path(p).read_text('utf8'))
assert root==Path('/opt/monitor/geo-content/runtime/acceptance/20261023-writer-v4-first/rank01-writer-v4-20261023T150914-d4beec2f')
assert read(root/'summary.json')['real_model_calls']==3 and not (root/'fact_review.json').exists() and not (root/'logic_review.json').exists()
auth=read(root/'preflight.json');assert all(sha(p)==v for p,v in auth['protected_before'].items())
shutil.copy2(root/'output_manifest.json',root/'output_manifest_before_word.json')
for source,target in [('/tmp/writer-v4-partial-draft.docx','draft.docx'),('/tmp/writer-v4-word-render.json','word_render_validation.json'),
 ('/tmp/writer-v4-acceptance-final.json','writer_acceptance.json'),('/tmp/writer-v4-summary-final.md','acceptance_summary.md')]:shutil.copy2(source,root/target)
assert sha(root/'draft.docx')=='8192c1c72a566f36414d52f4b2551d18069e09d3137747bfac26bc781d2f05ac'
assert read(root/'writer_acceptance.json')['complete'] is False
files={str(p.relative_to(root)):{'sha256':sha(p),'bytes':p.stat().st_size,'server_path':str(p)} for p in sorted(root.rglob('*')) if p.is_file() and p!=root/'output_manifest.json'}
(root/'output_manifest.json').write_text(json.dumps({'status':'writer_failed_partial_intro_only','files':files},ensure_ascii=False,indent=2),encoding='utf8')
zpath=Path('/tmp')/(root.name+'-delivery.zip')
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
 for p in root.rglob('*'):
  if p.is_file():z.write(p,str(p.relative_to(root)))
names=('draft.md','draft.docx','writer_manifest.json','writer_calls.json','writer_cost_ledger.json','writer_acceptance.json','review_status.json','acceptance_summary.md')
print(json.dumps({'archive':str(zpath),'archive_sha256':sha(zpath),'manifest_sha256':sha(root/'output_manifest.json'),
 'files':{n:files[n] for n in names},'file_count':len(files)},ensure_ascii=False))
