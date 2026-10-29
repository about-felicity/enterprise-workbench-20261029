import json, urllib.request, http.cookiejar, hashlib
from pathlib import Path

base='http://127.0.0.1:8804/api/'
opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def panel():
    return json.load(opener.open(base+'panel',timeout=60))
def action(name,payload,key):
    state=panel()
    request=urllib.request.Request(base+'control/'+name,data=json.dumps(payload,ensure_ascii=False).encode(),headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8804','X-CSRF-Token':state['csrf'],'X-Action-Id':hashlib.sha256(('knowledge-batch-20261026-'+key).encode()).hexdigest()[:32]})
    try:
        result=json.load(opener.open(request,timeout=90))
    except urllib.error.HTTPError as e:
        raise RuntimeError(e.read().decode()) from e
    assert result['ok'],result
    return result['result']

folder=Path('/opt/monitor/maintenance/knowledge-import-20261026')
folder.mkdir(parents=True,exist_ok=True)
before=folder/'panel-before.json'
if not before.exists():before.write_text(json.dumps(panel(),ensure_ascii=False))
results=[]
for row in json.loads(Path('/tmp/knowledge-import-bundle.json').read_text()):
    products=panel()['studio']['products']
    matching=[p for p in products if p['product']['name']==row['name']]
    assert len(matching)<=1,row['name']
    old=matching[0] if matching else None
    if old and old.get('word_source',{}).get('sha256')==row['sha256']:
        result={'product_id':old['product_id'],'version':old['version']};status='already_present'
    else:
        upload=action('kb_upload',{k:row[k] for k in ('name','filename','content_base64')}|{'product_id':old['product_id'] if old else '', 'notes':'用户于2026-10-26提供的产品文档；按原文归档，同产品保留一个当前知识库。'},row['sha256']+'-upload')
        result=action('kb_publish',{'library_id':upload['library_id'],'import_id':upload['import_id'],'reviewer':'Codex：产品归属及原文整理（非独立功效核验）','expected_version':old['version'] if old else '', 'product':{'name':row['name'],'brand':row['brand'],'audience':'','facts':row['facts']}},row['sha256']+'-publish')
        status='updated' if old else 'created'
    current=next(p for p in panel()['studio']['products'] if p['product_id']==result['product_id'])
    assert current['word_source']['sha256']==row['sha256']
    assert current['product']['raw_source_text']=='\n'.join(json.loads(Path('/tmp/knowledge-import-extracted.json').read_text())[len(results)]['lines'])
    results.append({'name':row['name'],'status':status,'product_id':result['product_id'],'sha256':row['sha256'],'facts':len(current['product']['facts'])})
    (folder/'result.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
    print(json.dumps(results[-1],ensure_ascii=False),flush=True)
after=panel();assert len(after['studio']['products'])==16
assert len({p['product']['name'] for p in after['studio']['products']})==16
(folder/'panel-after.json').write_text(json.dumps(after,ensure_ascii=False))
print('VERIFIED: 16 unique selectable products, all 8 source hashes match.')
