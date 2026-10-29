"""Check original Word retention, cross-product caches and actual completed captures."""
import hashlib,json,sys,re,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path[:0]=[str(BASE/'engine'),str(BASE)]
from creation import studio,runtime
from geo_source_cards.runtime import atomic_json
from geo_source_cards.rewrite_v2 import material_manager,structure_parser
from geo_source_cards.rewrite_v2.common import digest
from multi_run import STATE,root_for,CACHE
inputs=runtime.read(BASE/'multi-inputs.json')['products']
class NoNetwork:
    def __getattr__(self,key):raise AssertionError('Cache reuse attempted an API call: '+key)
checks=[]
for item in STATE['products']:
    spec=next(v for v in inputs if v['key']==item['key']);root=root_for(item)
    product=runtime.read(root/'product.json');selected=runtime.read(BASE/'multi-results'/item['key']/'selected-source.json')
    raw=product['raw_source_text']
    with zipfile.ZipFile(BASE/'multi-docs'/spec['filename']) as archive:
        document=ET.fromstring(archive.read('word/document.xml'))
    original_text=''.join(node.text or '' for node in document.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'))
    assert re.sub(r'\s','',original_text)==re.sub(r'\s','',raw),'Original Word content changed'
    assert hashlib.sha256((BASE/'multi-docs'/spec['filename']).read_bytes()).hexdigest()==spec['source_sha256']
    material=material_manager.process(NoNetwork(),product,CACHE,root/'cache-check',{})
    assert material['raw_product']==product
    skeleton=structure_parser.parse(NoNetwork(),selected['source']['article']['text'],CACHE,root/'cache-check',{})
    rows=[]
    for model in ('baidu_ai','wenxin_card'):
        path=Path(item['capture_root'])/'days'/item['date']/model/'results.jsonl'
        records=[json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.exists() else []
        for row in records:
            assert row['question'] in item['questions'] and row['model']==model
            assert row.get('body_capture_complete') is True
            assert row.get('source_capture_complete') is True and row['sources']
            assert row.get('verified_question',row['question'])==row['question']
            assert row.get('body','').strip()
            rows.append({'model':model,'question':row['question'],'body_chars':len(row['body']),
                         'source_count':len(row['sources']),'task_id':row['task_id'],'captured_at':row['captured_at']})
    assert len({r['task_id'] for r in rows})==len(rows)
    checks.append({'key':item['key'],'original_word_preserved':True,'raw_chars':len(raw),
       'material_cache_key':material['cache_key'],'skeleton_cache_key':skeleton['cache_key'],
       'cache_reuse_model_calls':0,'approval_recorded':bool(skeleton.get('approval')),
       'captures':rows,'expected_captures':4,'capture_complete':len(rows)==4})
assert len({x['material_cache_key'] for x in checks})==len(checks)
atomic_json(BASE/'multi-results'/'verification.json',checks)
print(json.dumps(checks,ensure_ascii=False))
