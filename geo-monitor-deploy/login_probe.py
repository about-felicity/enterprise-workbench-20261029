"""Readiness checks without submitting questions or printing credentials."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def native(model):
    if model=='yuanbao':
        result=subprocess.run(['/home/user/redroid-doubao/worker-venv/bin/python','-B','/home/user/redroid-yuanbao/login_probe.py'],capture_output=True,text=True,timeout=45,check=True)
        return json.loads(result.stdout.strip().splitlines()[-1])
    container,serial={'doubao1':('doubao-hpe14-13-test','127.0.0.1:5557'),
                      'doubao2':('doubao-hpe14-account2','127.0.0.1:5558')}[model]
    sys.path.insert(0,'/home/user/redroid-doubao')
    from active_database_accounts import current_uid
    uid=current_uid(container)
    # Read the current UI only; don't navigate, create a chat, or send.
    hierarchy=subprocess.check_output(['/home/user/redroid-doubao/worker-venv/bin/python','-c',
        'import uiautomator2 as u; print(u.connect('+repr(serial)+').dump_hierarchy())'],text=True,timeout=30)
    if any(text in hierarchy for text in ('登录即代表','验证码登录','手机号登录')):
        return {'status':'login_required','message':'当前页面需要登录，请在原账号登录入口处理'}
    return {'status':'locally_logged_in','account':'***'+uid[-6:],
            'message':'本机账号已登录；服务端有效性以实际采集为准'}


def browser(runtime,sync):
    from geo_source_cards.runtime import process_lock
    from web_collectors.collector import BrowserCollector
    os.environ.pop('GEO_PIPELINE_ROOT',None)
    runtime.mkdir(parents=True,exist_ok=True)
    storage=cookies=None
    if sync:
        source=Path('/home/user/geo-editorial/runtime-api/collectors/deepseek')
        with process_lock(source/'collector.lock'):
            os.environ.update(GEO_COLLECTOR_RUNTIME=str(source),GEO_DEEPSEEK_PORT='9414')
            collector=BrowserCollector('deepseek',headless=True)
            try:
                state=collector.check_ready()
                if not state.get('ok'):
                    return {'status':state.get('status','unknown'),'message':'原内容工作台会话尚未就绪，请先完成 DeepSeek 登录'}
                cookies=collector.page.call('Network.getAllCookies')['cookies']
                storage=collector.page.evaluate('({local_storage:{...localStorage},session_storage:{...sessionStorage}})')
            finally:collector.close()
    os.environ.update(GEO_COLLECTOR_RUNTIME=str(runtime),GEO_DEEPSEEK_PORT='9514')
    if storage is not None:
        os.environ['MONITOR_DEEPSEEK_STORAGE_JSON']=json.dumps(storage)
        os.environ['MONITOR_DEEPSEEK_COOKIES_JSON']=json.dumps(cookies)
    with process_lock(runtime/'collector.lock'):
        collector=BrowserCollector('deepseek',headless=True)
        try:
            state=collector.check_ready()
            return {'status':state.get('status','unknown'),'message':'GEO DeepSeek 网页已就绪；没有发送问题' if state.get('ok') else 'GEO DeepSeek 会话未就绪，请登录或同步内容工作台登录'}
        finally:
            collector.close()
            for key in ('MONITOR_DEEPSEEK_STORAGE_JSON','MONITOR_DEEPSEEK_COOKIES_JSON'):os.environ.pop(key,None)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',choices=['doubao1','doubao2','deepseek','yuanbao'],required=True)
    parser.add_argument('--runtime',type=Path,required=True)
    parser.add_argument('--sync-source',action='store_true')
    args=parser.parse_args()
    try:
        result=browser(args.runtime,args.sync_source) if args.model=='deepseek' else native(args.model)
    except Exception as error:
        result={'status':'unknown','message':'校验未完成，浏览器可能被占用；没有发送问题','error_kind':type(error).__name__}
    print(json.dumps(result,ensure_ascii=False))
