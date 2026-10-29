import base64,json,os,pwd,shutil,sys,time
from pathlib import Path
from datetime import datetime
BASE=Path(__file__).resolve().parent
sys.path[:0]=[str(BASE/'engine'),str(BASE)]
from creation import studio,runtime,materials
from geo_source_cards.runtime import atomic_json,process_lock
spec=json.loads((BASE/'inputs.json').read_text())['products'][0]
state_path=BASE/'state.json'
if state_path.exists():
    print(state_path.read_text());raise SystemExit(0)
day=datetime.now(studio.ZONE).date().isoformat()
imported=studio.import_word({'filename':'新眉毛产品库信息.docx','content_base64':base64.b64encode((BASE/'knowledge.docx').read_bytes()).decode()})
assert imported['sha256']==spec['source_sha256']
kb=studio.save_product({'name':spec['name'],'brand':spec['brand'],'audience':'关注眉毛日常护理和眉毛精华液选购的成年人','facts':[line for line in imported['text'].splitlines() if line.strip()],'import_id':imported['import_id']})
payload={'name':'梵玢FBCY眉毛精华液 V2七问题无人值守验收','product_id':kb['product_id'],'questions':spec['questions'],'channels':['baidu_ai','wenxin_card'],'rounds':1,'enabled':False,'frequency':'once','task_type':'capture_only','max_per_category':7,'capture_time':'00:00','writing_time':'00:00','start_date':day,'article_target':7,'article_budget_cny':.35,'task_budget_cny':2.45}
saved=studio.save_plan(payload);pid=saved['plan_id'];root=studio.capture_root(pid)
owner=pwd.getpwnam('user')
old=json.loads(Path('/tmp/geo-rewrite-v2-mQfF5Dbd/multi-state.json').read_text())['products'][0]
with process_lock(materials.SEARCH_POOL/'browser.lock',blocking=True):
    for model in payload['channels']:
        source=Path(old['capture_root'])/'days'/old['date']/model/'collector/profiles/baidu/scrapling_profile'
        if any((source/n).exists() or (source/n).is_symlink() for n in ('SingletonLock','SingletonSocket')):raise RuntimeError('Seed profile still open')
        target=root/'days'/day/model/'collector/profiles/baidu/scrapling_profile'
        shutil.copytree(source,target,ignore=lambda folder,names:[n for n in names if n.startswith('Singleton') or Path(folder,n).is_symlink() or n in {'Cache','Code Cache','GPUCache','Crashpad'}])
    for path in [root,*root.rglob('*')]:
        if not path.is_symlink():os.chown(path,owner.pw_uid,owner.pw_gid)
cfg=runtime.read(root/'settings.json');atomic_json(root/'settings.json',{**cfg,'search_pool':'creation_only'})
state={'plan_id':pid,'product_id':kb['product_id'],'date':day,'capture_root':str(root),'questions':spec['questions'],'channels':payload['channels'],'capture_plan':payload,'source_sha256':spec['source_sha256']}
atomic_json(state_path,state)
studio.save_plan({**payload,'plan_id':pid,'enabled':True})
print(json.dumps(state,ensure_ascii=False),flush=True)
