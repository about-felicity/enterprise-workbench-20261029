"""Use the existing studio for three one-time capture-only tests; no legacy writing is enabled."""
import base64,json,os,pwd,shutil,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path[:0]=[str(BASE/'engine'),str(BASE)]
from creation import studio,materials,runtime
from geo_source_cards.runtime import atomic_json,process_lock
from datetime import datetime

inputs=json.loads((BASE/'multi-inputs.json').read_text())
state_path=BASE/'multi-state.json'
state=runtime.read(state_path) or {'products':[],'started_at':time.time()}
owner=pwd.getpwnam('user')
day=datetime.now(studio.ZONE).date().isoformat()
for spec in inputs['products']:
    existing=next((x for x in state['products'] if x['key']==spec['key']),None)
    if existing:
        print('existing',spec['key'],existing['plan_id'],flush=True)
        continue
    previous=next((p for p in studio.plans() if p.get('name')==spec['name']+' V2两渠道单轮测试' and p.get('start_date')==day),None)
    if previous:
        kb=studio.product(previous['product_id'])
    else:
        word=BASE/'multi-docs'/spec['filename']
        imported=studio.import_word({'filename':spec['filename'],'content_base64':base64.b64encode(word.read_bytes()).decode()})
        assert imported['sha256']==spec['source_sha256']
        facts=[line for line in imported['text'].splitlines() if line.strip()]
        kb=studio.save_product({'name':spec['name'],'brand':spec['brand'],'audience':'关注该品类选购及使用方法的成年消费者',
            'facts':facts,'import_id':imported['import_id']})
    payload={'name':spec['name']+' V2两渠道单轮测试','product_id':kb['product_id'],
        'questions':spec['questions'],'channels':['baidu_ai','wenxin_card'],'rounds':1,
        'enabled':False,'frequency':'once','task_type':'capture_only','max_per_category':1,
        'capture_time':'00:00','writing_time':'00:00','start_date':day,
        'article_target':1,'article_budget_cny':.35,'task_budget_cny':.35}
    if previous:payload['plan_id']=previous['plan_id']
    saved=studio.save_plan(payload);pid=saved['plan_id'];root=studio.capture_root(pid)
    # Copy only a closed, successful browser profile under the main channel lock.
    # The original accounts and question journals remain at their original paths.
    with process_lock(materials.GEO/'search_browser.lock',blocking=True):
        for model in ('baidu_ai','wenxin_card'):
            source=materials.GEO/'profiles/search'/model/'scrapling_profile'
            if any((source/n).exists() or (source/n).is_symlink() for n in ('SingletonLock','SingletonSocket')):
                raise RuntimeError('Source browser is still open; preserve the pending test')
            target=root/'days'/day/model/'collector/profiles/baidu/scrapling_profile'
            if not target.exists():
                def ignore(folder,names):
                    return [n for n in names if n.startswith('Singleton') or Path(folder,n).is_symlink() or n in {'Cache','Code Cache','GPUCache','DawnGraphiteCache','ShaderCache','Crashpad'}]
                shutil.copytree(source,target,ignore=ignore)
            for path in [root,*root.rglob('*')]:
                if not path.is_symlink():os.chown(path,owner.pw_uid,owner.pw_gid)
            atomic_json(root/('profile-seed-'+model+'.json'),{'source':str(source),'target':str(target),'at':time.time(),'main_lock_held':True,'task_journal_copied':False})
    cfg=runtime.read(root/'settings.json');atomic_json(root/'settings.json',{**cfg,'search_pool':'creation_only'})
    row={'key':spec['key'],'product_id':kb['product_id'],'plan_id':pid,'capture_root':str(root),'date':day,
         'questions':spec['questions'],'source_sha256':spec['source_sha256']}
    state['products'].append(row);atomic_json(state_path,state)
    studio.save_plan({**payload,'plan_id':pid,'enabled':True})
    print('enabled',json.dumps(row,ensure_ascii=False),flush=True)
print('Three one-time capture plans ready; paid writing remains isolated.')
