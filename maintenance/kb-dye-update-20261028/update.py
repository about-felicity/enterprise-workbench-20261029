import sys,json,hashlib,shutil,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,studio,knowledge_library
from geo_source_cards.runtime import atomic_json
payload=json.loads(Path('/tmp/dye28-payload.json').read_text('utf8'))
pid=payload['upload']['product_id'];old=studio.product(pid)
assert old['version']=='323a07e377b6bc7ddc910f42abba2bd9dc3352c4d867521d32251823a248c28f'
D=Path('/opt/monitor/maintenance/kb-dye-update-20261028');D.mkdir(parents=True,exist_ok=True)
atomic_json(D/'product-before.json',old)
atomic_json(D/'library-before.json',[r for r in knowledge_library.records() if r.get('product_id')==pid])
products_before={p['product_id']:p['version'] for p in studio.products()}
plans_before={p['plan_id']:runtime.digest(p) for p in studio.plans()}
u=runtime.action('kb_upload',payload['upload'],hashlib.sha256(('upload'+payload['sha256']).encode()).hexdigest()[:32])
f=studio.ROOT/'imports'/u['import_id'];original=runtime.read(f/'extraction.json')
assert original['sha256']==payload['sha256']
assert original['text'].splitlines()[0].startswith('把这篇链接') and original['text'].splitlines()[-1].startswith('不要出现代码')
assert payload['clean_text'].splitlines()[1:]==original['text'].splitlines()[1:-1]
shutil.copy2(f/'extraction.json',f/'extraction-original.json')
atomic_json(f/'extraction.json',{**original,'text':payload['clean_text'],'paragraphs':len(payload['clean_text'].splitlines()),'normalization':'Product data only; original extraction preserved in extraction-original.json'})
result=runtime.action('kb_publish',{'library_id':u['library_id'],'import_id':u['import_id'],'expected_version':old['version'],'reviewer':'Codex：按用户要求核对产品归属、区分写作指令与产品资料','product':{'name':old['product']['name'],'brand':old['product']['brand'],'audience':old['product'].get('audience',''),'facts':payload['facts']}},hashlib.sha256(('publish'+payload['sha256']).encode()).hexdigest()[:32])
new=studio.product(pid)
assert new['word_source']['sha256']==payload['sha256'] and new['product']['raw_source_text']==payload['clean_text']
assert all(p['version']==products_before[p['product_id']] for p in studio.products() if p['product_id']!=pid)
assert len(studio.products())==len(products_before)
assert all(runtime.digest(p)==plans_before[p['plan_id']] for p in studio.plans())
assert knowledge_library.record(u['library_id'])['uploads'][-1]['status']=='published'
report={'product_id':pid,'name':new['product']['name'],'previous_version':old['version'],'version':new['version'],'facts':len(new['product']['facts']),'source_sha256':payload['sha256'],'product_count':len(studio.products()),'duplicate_created':False,'original_preserved':True,'plans_unchanged':True,'at':time.time()}
atomic_json(D/'result.json',report);print(json.dumps(report,ensure_ascii=False))
