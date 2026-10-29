import json,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path[:0]=[str(BASE/'engine'),str(BASE)]
from creation import materials,runtime
from geo_source_cards.runtime import atomic_json,atomic_write
state=runtime.read(BASE/'multi-state.json')
report=[]
for item in state['products']:
    root=Path(item['capture_root']);out=BASE/'multi-results'/item['key'];out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for model in ('baidu_ai','wenxin_card'):
        path=root/'days'/item['date']/model/'results.jsonl'
        if path.exists():rows+=materials.read_lines(path)
    atomic_write(out/'captured.jsonl',''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    sources=[{'question':r.get('question'),'model':r.get('model'),'sources':r.get('sources',[])} for r in rows]
    atomic_json(out/'sources.json',sources)
    result={'key':item['key'],'health':runtime.read(root/'health.json'),
        'progress':[p for p in materials.progress(item['date'],store_root=root) if p['id'] in ('baidu_ai','wenxin_card')],
        'records':len(rows),'source_count':sum(len(r.get('sources',[])) for r in rows)}
    report.append(result)
    print(json.dumps(result,ensure_ascii=False),flush=True)
atomic_json(BASE/'multi-capture-status.json',report)
