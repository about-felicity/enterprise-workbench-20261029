"""Isolated headless Chromium + MV3 extension. No automatic question on startup."""
import asyncio,json,os,threading,time,signal
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parent
STATE={'status':'opening','headless':True,'auto_start':False,'port':8820}
LOOP=PAGE=CONTEXT=WORKER=None
STOP=None

def publish(**values):
    STATE.update(values,updated_at=time.time())
    tmp=ROOT/'state.tmp';tmp.write_text(json.dumps(STATE,ensure_ascii=False));tmp.replace(ROOT/'state.json')

async def call(kind,value):
    if kind=='frame':return await PAGE.screenshot(type='jpeg',quality=70)
    if kind=='click':
        x,y=value['x'],value['y']
        if type(x) not in (int,float) or type(y) not in (int,float) or not(0<=x<1100 and 0<=y<780):raise ValueError('Invalid position')
        await PAGE.mouse.click(x,y)
    elif kind=='text':
        text=value.get('text','')
        if not isinstance(text,str) or not 0<len(text)<=4096:raise ValueError('Invalid text')
        await PAGE.keyboard.insert_text(text)
    elif kind=='key':
        key=value.get('key')
        if key not in ('Enter','Tab','Backspace','Escape','ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Control+A','Delete'):raise ValueError('Invalid key')
        await PAGE.keyboard.press(key)
    elif kind=='scroll':
        delta=value.get('delta',0)
        if type(delta) not in (int,float) or abs(delta)>1000:raise ValueError('Invalid scroll')
        await PAGE.mouse.wheel(0,delta)
    else:raise ValueError('Unknown operation')
    return {'ok':True}

async def plugin_state():
    return await WORKER.evaluate('async()=>{await initialization;return await storageGet(["settings","job","geoAssignment","nextAllowedSendAt","pendingSync"]) }')

async def controls():
    folder=ROOT/'control';(folder/'requests').mkdir(parents=True,exist_ok=True);(folder/'responses').mkdir(exist_ok=True)
    for path in sorted((folder/'requests').glob('*.json')):
        response=folder/'responses'/path.name
        if response.exists():continue
        try:
            request=json.loads(path.read_text());action=request['action'];args=request.get('args',{})
            if action=='inspect':
                data={'state':await plugin_state(),'modes':await PAGE.locator('button,[role=button],.ds-toggle-button').evaluate_all('els=>els.map(e=>({text:e.innerText,pressed:e.getAttribute("aria-pressed"),classes:e.className})).filter(x=>/搜索|思考|Search|Think/i.test(x.text||""))')}
            elif action=='start':
                data=await plugin_state();job=data.get('job') or {}
                if job.get('state') in ('running','paused'):
                    if data.get('geoAssignment',{}).get('batch')!=args['batch']:
                        if job.get('state')!='paused' or (job.get('inFlight') or {}).get('phase') in ('submitted','send_intent'):raise ValueError('another_browser_job_exists')
                        await WORKER.evaluate('async()=>{const d=await storageGet(["geoPreviousJobs","job","geoAssignment"]);await storageSet({geoPreviousJobs:[...(d.geoPreviousJobs||[]),{job:d.job,assignment:d.geoAssignment}].slice(-200)});await mutateJob(j=>({...j,state:"stopped"}))}')
                        job={}
                    else:data={'ok':True,'job':job,'existing':True}
                if not job or job.get('state') not in ('running','paused'):
                    await PAGE.reload(wait_until='domcontentloaded',timeout=45000)
                    await PAGE.wait_for_selector('textarea,[contenteditable=true]',timeout=20000)
                    await WORKER.evaluate('async a=>{await storageSet({geoAssignment:a})}',args)
                    data=await WORKER.evaluate('async a=>await startJob({settings:{...DEFAULT_SETTINGS,questions:a.questions,rounds:a.rounds,dailyEnabled:false,intervalMinSeconds:600,intervalMaxSeconds:900}})',args)
            elif action in ('pause','resume','stop'):
                data=await plugin_state()
                if args.get('batch') and data.get('geoAssignment',{}).get('batch')!=args['batch']:raise ValueError('assignment_changed')
                state={'pause':'paused','resume':'running','stop':'stopped'}[action]
                data=await WORKER.evaluate('async a=>{const job=await mutateJob(j=>j?({...j,state:a}):j);if(a==="running"&&job?.ownerTabId)await sendToTab(job.ownerTabId,{type:"DM_RUN"});return {ok:true,job}}',state)
            elif action=='get':data=await plugin_state()
            else:raise ValueError('unsupported_browser_command')
            value={'ok':True,'result':data,'at':time.time()}
        except Exception as error:value={'ok':False,'error':type(error).__name__,'at':time.time()}
        tmp=response.with_suffix('.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False));tmp.replace(response)

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*_):pass  # Never record user inputs or credentials.
    def reply(self,value,mime='application/json',status=200):
        data=value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False).encode()
        self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def do_GET(self):
        path=urlparse(self.path).path
        try:
            if path=='/':return self.reply((ROOT/'login.html').read_bytes(),'text/html; charset=utf-8')
            if path=='/status':return self.reply(STATE)
            if path=='/frame' and PAGE:return self.reply(asyncio.run_coroutine_threadsafe(call('frame',{}),LOOP).result(12),'image/jpeg')
            return self.reply({'error':'not_ready'},status=503)
        except Exception:return self.reply({'error':'temporary_browser_error'},status=503)
    def do_POST(self):
        # Loopback-only over SSH; reject cross-origin submissions.
        if self.path!='/input':return self.reply({'error':'not_found'},status=404)
        origin=self.headers.get('Origin')
        if origin and urlparse(origin).netloc!=self.headers.get('Host'):return self.reply({'error':'origin_rejected'},status=403)
        try:
            n=int(self.headers.get('Content-Length','0'))
            if not 0<n<=20000:raise ValueError('Invalid size')
            value=json.loads(self.rfile.read(n))
            result=asyncio.run_coroutine_threadsafe(call(value.get('type'),value),LOOP).result(25)
            return self.reply(result)
        except Exception:return self.reply({'error':'input_not_confirmed_do_not_replay'},status=400)

async def run():
    global LOOP,PAGE,CONTEXT,WORKER,STOP
    LOOP=asyncio.get_running_loop()
    STOP=asyncio.Event();LOOP.add_signal_handler(signal.SIGTERM,STOP.set)
    server=ThreadingHTTPServer(('127.0.0.1',8820),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    async with async_playwright() as pw:
        ext=str(ROOT/'project/extension')
        CONTEXT=await pw.chromium.launch_persistent_context(str(ROOT/'profile'),channel='chromium',headless=True,
            executable_path=str(ROOT/'chromium/chrome-linux64/chrome'),
            viewport={'width':1100,'height':780},locale='zh-CN',timezone_id='Asia/Shanghai',
            args=['--disable-extensions-except='+ext,'--load-extension='+ext])
        WORKER=CONTEXT.service_workers[0] if CONTEXT.service_workers else await CONTEXT.wait_for_event('serviceworker',timeout=30000)
        settings=await WORKER.evaluate('async()=>{await initialization;return safeSettings(await settings())}')
        if (settings.get('intervalMinSeconds'),settings.get('intervalMaxSeconds'))!=(600,900):
            # Reload extension assets only; retain its storage, profile and original job.
            next_worker=asyncio.create_task(CONTEXT.wait_for_event('serviceworker',timeout=20000))
            await WORKER.evaluate('()=>{setTimeout(()=>chrome.runtime.reload(),150);return true}')
            WORKER=await next_worker
            settings=await WORKER.evaluate('async()=>{await initialization;return safeSettings(await settings())}')
        await WORKER.evaluate('async()=>{await storageSet({settings:safeSettings(await settings())})}')
        assert settings['intervalMinSeconds']==600 and settings['intervalMaxSeconds']==900
        assert settings['dailyEnabled'] is False
        publish(extension_id=WORKER.url.split('/')[2],browser_version=CONTEXT.browser.version if CONTEXT.browser else 'persistent',
                interval_min=600,interval_max=900,extension_loaded=True)
        # Read the persisted permit. Startup must never reserve an extra send slot.
        saved=await plugin_state()
        publish(next_send_not_before=saved.get('nextAllowedSendAt',0))
        PAGE=CONTEXT.pages[0] if CONTEXT.pages else await CONTEXT.new_page()
        old_job=saved.get('job') or {};flight=old_job.get('inFlight') or {}
        target=flight.get('conversationUrl') if flight.get('phase')=='submitted' else 'https://chat.deepseek.com/'
        if not str(target).startswith('https://chat.deepseek.com/'):target='https://chat.deepseek.com/'
        try:await PAGE.goto(target,wait_until='domcontentloaded',timeout=60000)
        except Exception:publish(status='page_loading',message='DeepSeek页面仍在加载，可通过登录画面查看')
        if old_job.get('state') in ('running','paused'):
            await WORKER.evaluate('async()=>{const tab=await findTargetTab();if(tab?.id){const j=await mutateJob(j=>({...j,ownerTabId:tab.id,state:j.inFlight?.phase==="send_intent"?"paused":j.state}));if(j?.state==="running")await sendToTab(tab.id,{type:"DM_RUN"});}}')
        while not STOP.is_set():
            try:
                await controls()
                info=await PAGE.evaluate((ROOT/'auth_probe.js').read_text())
                status='risk_or_verification' if info['risk'] else 'login_required' if info['login'] else 'ready_to_verify' if info['composer'] else 'page_loading'
                publish(status=status,message={'login_required':'请在下方真实浏览器画面中手动登录','risk_or_verification':'页面提示验证或账号限制，尚未判定可采集','ready_to_verify':'已检测到输入框，等待账号与模式复核；尚未发送问题','page_loading':'页面加载中'}[status],page_title=info['title'])
                data=await plugin_state();job=data.get('job') or {}
                publish(plugin_job=job,assignment=data.get('geoAssignment'),next_send_not_before=data.get('nextAllowedSendAt',0),
                        auth='ready' if status=='ready_to_verify' else 'risk_blocked' if status=='risk_or_verification' else 'login_required' if status=='login_required' else 'unknown')
                if status=='ready_to_verify' and job.get('state')=='running':publish(status='running',message='任务运行中：'+str(job.get('cursor',0))+'/'+str(len(job.get('schedule',[])))+'，按10–15分钟发送间隔执行')
            except Exception:publish(status='temporarily_unavailable',message='浏览器页面暂不可读，保留原会话')
            await asyncio.sleep(3)
        await CONTEXT.close()

if __name__=='__main__':
    os.umask(0o077)
    asyncio.run(run())
