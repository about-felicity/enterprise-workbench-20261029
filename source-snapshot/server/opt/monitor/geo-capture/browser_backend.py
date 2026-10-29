"""Private local bridge to the single persistent browser; never exposes credentials."""
import json,time,uuid
from pathlib import Path
ROOT=Path('/opt/monitor/geo-deepseek-browser-test')

def read(path):
    try:return json.loads(Path(path).read_text())
    except (FileNotFoundError,ValueError):return {}

def atomic(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False));tmp.chmod(0o600);tmp.replace(path)

def enabled(model,base=None):
    if base is not None and Path(base)!=Path('/opt/monitor/geo-capture'):return False
    return model=='deepseek2' and read(ROOT/'production.json').get('enabled') is True

def probe():
    if 'deepseek2' in read('/opt/monitor/geo-capture/daily_plan.json').get('desktop_collectors',[]):return {'status':'unknown','message':'已切换本机Chrome插件，服务器仅接收回传','backend':'desktop_extension'}
    value=read(ROOT/'state.json');status=value.get('auth','unknown')
    if time.time()-value.get('updated_at',0)>45:status='unknown'
    message={'ready':'DeepSeek持久浏览器登录正常','login_required':'浏览器登录已失效，请打开浏览器登录画面',
             'verification_required':'浏览器需要人工验证，停止新题等待处理','risk_blocked':'浏览器账号出现限制或验证，停止新题等待处理','unknown':'浏览器状态暂不可用，未据此认定掉登录'}[status]
    return {'status':status,'message':message,'backend':'browser_extension'}

def command(action,args=None,key=None,timeout=75):
    if 'deepseek2' in read('/opt/monitor/geo-capture/daily_plan.json').get('desktop_collectors',[]):raise RuntimeError('desktop_extension_manual_control')
    key=key or uuid.uuid4().hex;root=ROOT/'control'
    path=root/'requests'/(key+'.json');response=root/'responses'/path.name
    if not path.exists():atomic(path,{'action':action,'args':args or {}})
    deadline=time.time()+timeout
    while time.time()<deadline:
        value=read(response)
        if value:
            if not value.get('ok'):raise RuntimeError(value.get('error','browser_command_failed'))
            return value['result']
        time.sleep(.25)
    raise TimeoutError('Browser command unconfirmed; inspect existing assignment before retry')
