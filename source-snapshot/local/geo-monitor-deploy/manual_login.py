"""Manage one ephemeral DeepSeek login process; control cookies never reach it."""
import json
from pathlib import Path
import secrets
import shutil
import subprocess
import time
import urllib.error
import urllib.request
import uuid

def read(path):
    try: return json.loads(Path(path).read_text())
    except FileNotFoundError: return {}

def state(base,model='deepseek'):
    from browser_backend import enabled as browser_enabled
    if browser_enabled(model,base):return {'status':'closed','backend':'browser_extension'}
    if model not in {'deepseek','deepseek2','deepseek_test'}:raise ValueError('无效登录通道')
    root = Path(base) / 'manual-login' / model
    request, result = read(root / 'request.json'), read(root / 'state.json')
    if not request: return {'status': 'closed'}
    if result.get('id') != request['id']:
        result = {key: request[key] for key in ('id', 'batch', 'revision', 'created_at', 'expires_at')}
        result.update(status='opening', message='正在打开 DeepSeek 登录页面')
    if time.time() > result['expires_at'] and result['status'] not in {'ready', 'failed'}:
        result = {**result, 'status': 'failed', 'message': '登录页面已过期，请重新打开'}
    if model=='deepseek_test' and result.get('status') in {'waiting_login','risk_blocked','verification_required'}:
        check=root/'account-check.json'
        cached=read(check)
        if time.time()-cached.get('checked_at',0)>10:
            # Detached read-only inspection avoids delaying scrcpy input/state requests.
            process=subprocess.Popen(['/home/user/redroid-doubao/worker-venv/bin/python','-B',str(Path(base)/'deepseek_test_auth.py')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            # Reap asynchronously; never retain credentials or capture App log output.
            import threading
            threading.Thread(target=process.wait,daemon=True).start()
        if cached and time.time()-cached.get('checked_at',0)<30:
            result={**result,'account_check':cached}
            if cached.get('status') in {'risk_blocked','verification_required'}:
                result.update(status=cached['status'],message=cached.get('message','测试账号尚未通过校验'))
    return result

def start(base, runtime, batch, revision, model='deepseek'):
    if model not in {'deepseek','deepseek2','deepseek_test'}:raise ValueError('无效登录通道')
    root = Path(base) / 'manual-login' / model
    current = state(base,model)
    if current.get('status') in {'opening', 'waiting_login', 'verifying','risk_blocked','verification_required'}:
        if current.get('batch') != batch: raise ValueError('另一登录流程尚未结束')
        return current
    root.mkdir(parents=True, exist_ok=True)
    shutil.chown(root, user='user', group='user')
    testing=model=='deepseek_test'
    android=testing or read(Path(base)/'deepseek_backend.json').get('backend')=='android'
    duration=3600 if testing else 900
    value = {'model':model,'port':{'deepseek':8815,'deepseek2':8816,'deepseek_test':8817}[model],'backend':'android' if android else 'web','id': uuid.uuid4().hex, 'token': secrets.token_hex(32), 'batch': batch,
             'runtime': str(runtime), 'revision': revision, 'created_at': time.time(), 'expires_at': time.time() + duration}
    path = root / 'request.json'
    path.write_text(json.dumps(value))
    path.chmod(0o600)
    shutil.chown(path, user='user', group='user')
    subprocess.run(['systemd-run', '--unit=geo-deepseek-manual-login-' + value['id'][:12],
                    '--collect', *([] if android else ['--uid=user']), '--property=MemoryMax=1800M',
                    '--property=TasksMax=512', '--property=RuntimeMaxSec='+str(duration+60),
                    ('/home/user/redroid-doubao/worker-venv/bin/python' if android else str(Path(base)/'venv/bin/python')), '-B', str(Path(base)/('deepseek_android_login.py' if android else 'deepseek_login_ui.py')), str(path)],
                   check=True, capture_output=True, timeout=15)
    return state(base,model)

def relay(base, path, value=None, model='deepseek'):
    if model not in {'deepseek','deepseek2','deepseek_test'}:raise ValueError('无效登录通道')
    root = Path(base) / 'manual-login' / model
    request = read(root / 'request.json')
    current = state(base,model)
    if path == 'state': return 200, 'application/json', json.dumps(current, ensure_ascii=False).encode()
    if not request or current['status'] not in {'waiting_login','risk_blocked','verification_required','verifying'}:
        return 409, 'application/json', b'{"ok":false,"message":"Login page is closed"}'
    if path not in {'frame', 'input'}: raise ValueError('无效登录操作')
    if value is not None:
        if value.pop('flow', None) != request['id']: raise ValueError('登录页面已变化，请重新打开')
        from deepseek_android_login import validate_input as android_input
        from deepseek_login_ui import validate_input as web_input
        validate_input=android_input if request.get('backend')=='android' else web_input
        validate_input(value)
    headers = {'X-Login-Token': request['token'], 'Content-Type': 'application/json'}
    req = urllib.request.Request('http://127.0.0.1:'+str(request.get('port',8805))+'/' + path, headers=headers,
                                 data=json.dumps(value).encode() if value is not None else None)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=12) as response:
            return response.status, response.headers['Content-Type'], response.read()
    except urllib.error.HTTPError as error: return error.code, 'application/json', error.read()

def stream(base,model,flow):
    if model not in {'deepseek','deepseek2','deepseek_test'}:raise ValueError('无效登录通道')
    root=Path(base)/'manual-login'/model
    request=read(root/'request.json');current=state(base,model)
    if not request or request['id']!=flow or current.get('status') not in {'waiting_login','risk_blocked','verification_required','verifying'}:raise ValueError('登录投屏已关闭或失效')
    req=urllib.request.Request('http://127.0.0.1:'+str(request['port'])+'/stream',headers={'X-Login-Token':request['token']})
    return urllib.request.build_opener(urllib.request.ProxyHandler({})).open(req,timeout=15)
