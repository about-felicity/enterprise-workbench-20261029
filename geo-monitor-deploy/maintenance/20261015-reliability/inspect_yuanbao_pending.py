import hashlib,json,sqlite3,time
from pathlib import Path
base=Path('/opt/monitor/geo-capture');p=json.loads((base/'soak12h_current.json').read_text())
m=json.loads((Path(p['root'])/'manifest.json').read_text());root=Path('/home/user/redroid-yuanbao/batches')/m['jobs']['yuanbao']['batch']
with sqlite3.connect((root/'tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
    db.row_factory=sqlite3.Row
    row=db.execute("select task_id,ordinal,question,state,prepared_at,error from tasks where state in ('prepared','needs_attention') order by ordinal limit 1").fetchone()
    if not row:print(json.dumps({'pending':False}));raise SystemExit(0)
    task=dict(row);raw=json.loads((root/(task['task_id']+'.native.json')).read_text())
    enum=lambda v:v.get('text') if isinstance(v,dict) else v
    entities=raw.get('entities',[])
    text='\n\n'.join(e.get('textEntity',{}).get('text','') for e in entities if enum(e.get('type'))=='TEXT')
    result={'at':time.time(),'task':task,'message_state':enum(raw['message'].get('state')),
        'content_state':enum(raw['content'].get('state')),'isEof':raw['content'].get('isEof'),
        'isBusy':raw['conversation'].get('isBusy'),'expected_entities':raw['content'].get('entityCount'),
        'entity_types':[enum(e.get('type')) for e in entities],
        'body_length':len(text),'body':text[:1800],'raw_sha256':hashlib.sha256(json.dumps(raw,sort_keys=True).encode()).hexdigest(),
        'render_keys':list(raw.get('render_snapshot',{})),
        'search_headers':[e['searchEntity'].get('title') for e in entities if enum(e.get('type'))=='SEARCH_GUIDE']}
    out=base/'maintenance/20261015-reliability/yuanbao-pending-diagnostic.json'
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False))
