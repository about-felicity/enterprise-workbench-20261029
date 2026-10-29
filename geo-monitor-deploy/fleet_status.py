"""Read-only status for the GEO Docker stack and its five capture lanes."""
import json
import hmac
import ipaddress
from pathlib import Path
import re
import secrets
import socket
import subprocess
import threading
import time
import tempfile
from http.cookies import SimpleCookie
from urllib.parse import urlsplit,parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE = Path("/opt/monitor/geo-capture")
TERMINAL = {"complete", "complete_with_unavailable", "paused", "maintenance_paused", "needs_attention", "stopped",'waiting_login','waiting_verification'}
CONTROLLER = None
CONTROLLER_LOCK = threading.RLock()
SESSIONS = {}


def controller():
    global CONTROLLER
    with CONTROLLER_LOCK:
        if CONTROLLER is None:
            from control_panel import Controller
            CONTROLLER = Controller(BASE)
        return CONTROLLER


def read(path):
    try:
        return json.loads(path.read_text("utf-8-sig"))
    except FileNotFoundError:
        return {}


def status():
    fleet = read(BASE / "fleet.json")
    lanes = []
    for lane in fleet["collectors"]:
        health = read(Path(lane["health"]))
        if lane['name']=='百度卡片':
            from baidu_body_delivery import merge_health
            health=merge_health(health,Path(lane['health']).parent)
        service = subprocess.run(["systemctl", "is-active", lane["service"]], capture_output=True, text=True).stdout.strip()
        state = health.get("status", "not_started")
        if lane['name'] == 'DeepSeek' and state == 'needs_attention':
            session = read(Path(lane['health']).parent / 'collector/deepseek_session.json')
            if session.get('status') == 'login_required':
                state = 'waiting_login'
        fresh = health.get("heartbeat_expires_at", 0) or 0
        if state.startswith("running") and (service != "active" or fresh < time.time()):
            state = "stopped" if service != "active" else "stale"
        lanes.append({"name": lane["name"], "service": lane["service"], "service_state": service,
                      "status": state, "batch": health.get("batch"), "planned": health.get("planned", lane.get("planned")),
                      "captured": health.get("captured", 0), "processed": health.get("geo_processed", health.get("processed", 0)),
                      "unique_processed": health.get("unique_processed", health.get("geo_processed", 0)),
                      "duplicates": health.get("duplicates", 0), "unavailable": health.get("unavailable", 0),
                      "delivery_errors": len(health.get("errors", health.get("delivery_errors", []))),
                      "updated_at": health.get("time")})
    output = subprocess.run(["docker", "inspect", *fleet["containers"], "--format",
                             "{{.Name}} {{.State.Status}} {{.State.StartedAt}}"], capture_output=True, text=True, timeout=10)
    containers = []
    for line in output.stdout.splitlines():
        name, state, started = line.split(maxsplit=2)
        containers.append({"name": name.lstrip("/"), "status": state, "started_at": started})
    result = {"project": "GEO", "generated_at": time.time(), "containers": containers, "collectors": lanes}
    target = Path("/opt/monitor/runtime/geo_collection_status.json")
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf8', dir=target.parent, delete=False) as stream:
        stream.write(json.dumps(result, ensure_ascii=False, indent=2))
        temporary = Path(stream.name)
    temporary.chmod(0o644)
    temporary.replace(target)
    return result


HTML = '''<!doctype html><meta charset="utf-8"><title>GEO 采集服务</title>
<style>body{font:16px system-ui;margin:35px;background:#f5f7fa;color:#17212c}a{color:#2866c8}table{border-collapse:collapse;background:white;margin-top:25px;width:100%}td,th{padding:14px;border-bottom:1px solid #ddd;text-align:left}small{color:#667}#error{color:#a22}</style>
<h1>GEO 采集服务</h1><a id="panel">打开 GEO 分析面板</a><p>豆包双实例、DeepSeek、文心卡片、百度卡片统一归属 GEO。每 15 秒更新。</p>
<p id="error"></p><table><thead><tr><th>采集通道</th><th>状态</th><th>完整采集</th><th>已确认回传的观测</th><th>唯一回传</th><th>重复 / 无卡片或不可用</th></tr></thead><tbody id="rows"></tbody></table>
<h2>GEO 核心服务与模拟器</h2><div id="core"></div><small>processed 表示正文与信源已经入库，产品分析及信源正文分析继续由原有 GEO 服务执行。百度五轮原始观测均保留，重复正文与完整信源只回传一次。</small>
<script>document.getElementById('panel').href=location.protocol+'//'+location.hostname+':3000';
const labels={complete:'已完成',complete_with_unavailable:'已结束，部分未取得卡片',running:'采集中',running_backoff:'退避等待',needs_attention:'需要处理',waiting_login:'等待 DeepSeek 登录',paused:'已暂停',stopped:'已停止',not_started:'尚未启动',stale:'心跳过期'};
function cell(row,text){let c=document.createElement('td');c.textContent=text;row.append(c)}
async function refresh(){try{let r=await fetch('/api/status',{cache:'no-store'});if(!r.ok)throw Error(r.status);let d=await r.json(),b=document.getElementById('rows');b.replaceChildren();for(let s of d.collectors){let tr=document.createElement('tr');for(let v of [s.name,labels[s.status]||s.status,s.captured+'/'+s.planned,s.processed,s.unique_processed,s.duplicates+' / '+s.unavailable])cell(tr,v);b.append(tr)}document.getElementById('core').textContent=d.containers.map(c=>c.name+': '+c.status).join(' · ');document.getElementById('error').textContent=''}catch(e){document.getElementById('error').textContent='状态读取失败，保留上次显示'}}refresh();setInterval(refresh,15000)</script>'''


class Handler(BaseHTTPRequestHandler):
    disable_nagle_algorithm=True
    def json_response(self, value, code=200, cookie=None):
        body=json.dumps(value,ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(body)))
        if cookie:self.send_header('Set-Cookie','geo_control='+cookie+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=21600')
        self.end_headers()
        self.wfile.write(body)

    def session(self, create=False):
        if not ipaddress.ip_address(self.client_address[0]).is_private:
            raise PermissionError('控制面板仅允许内网访问')
        host=urlsplit('http://'+self.headers.get('Host','')).hostname
        if host not in {'localhost','127.0.0.1','192.168.31.106',socket.gethostname()}:
            raise PermissionError('请通过服务器内网地址访问控制面板')
        cookies=SimpleCookie(self.headers.get('Cookie',''))
        token=cookies.get('geo_control')
        token=token.value if token else ''
        with CONTROLLER_LOCK:
            if SESSIONS.get(token,0)>time.time():return token
            if create:
                token=secrets.token_hex(32)
                for expired in [k for k,v in SESSIONS.items() if v<time.time()]:SESSIONS.pop(expired,None)
                SESSIONS[token]=time.time()+21600
                return token
        raise PermissionError('会话已过期，请刷新面板')

    def do_POST(self):
        from control_panel import Conflict
        try:
            match=re.fullmatch(r'/api/control/(doubao1|doubao2|deepseek|deepseek2|wenxin_card|baidu_ai|yuanbao)/(settings|new|pause|resume|stop|login|login_sync|login_open)',self.path)
            login_match=re.fullmatch(r'/api/login/(?:(deepseek|deepseek2|deepseek_test)/)?input',self.path)
            login_input=bool(login_match)
            test_open=self.path=='/api/login/deepseek_test/open'
            schedule=self.path=='/api/control/schedule'
            if not match and not login_input and not schedule and not test_open:
                self.json_response({'ok':False,'message':'操作不存在'},404)
                return
            token=self.session()
            host=self.headers.get('Host','')
            if self.headers.get('Origin') not in {'http://'+host,'https://'+host} or not hmac.compare_digest(self.headers.get('X-CSRF-Token',''),token):
                raise PermissionError('请求来源校验失败，请从控制面板操作')
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=1_100_000 or self.headers.get('Content-Type','').split(';')[0]!='application/json':
                raise ValueError('请求格式不正确')
            value=json.loads(self.rfile.read(size).decode('utf8'))
            if not isinstance(value,dict):raise ValueError('请求格式不正确')
            if test_open:
                from manual_login import start
                self.json_response(start(BASE,'/home/user/redroid-deepseek-test','manual-test',0,model='deepseek_test'))
                return
            if schedule:
                from schedule_control import save
                self.json_response(save(controller(),value,self.headers.get('X-Action-Id','')))
                return
            if login_input:
                from browser_backend import enabled as browser_enabled
                if browser_enabled(login_match[1] or 'deepseek',BASE):
                    from urllib.request import Request,build_opener,ProxyHandler
                    req=Request('http://127.0.0.1:8820/input',data=json.dumps(value).encode(),headers={'Content-Type':'application/json'})
                    with build_opener(ProxyHandler({})).open(req,timeout=28) as reply:self.login_response(reply.read(),'application/json')
                    return
                from manual_login import relay
                code,mime,data=relay(BASE,'input',value,model=login_match[1] or 'deepseek')
                self.login_response(data,mime,code)
                return
            result=controller().action(*match.groups(),value,self.headers.get('X-Action-Id',''))
            self.json_response(result)
        except PermissionError as error:self.json_response({'ok':False,'message':str(error)},403)
        except Conflict as error:self.json_response({'ok':False,'message':str(error)},409)
        except (ValueError,UnicodeError) as error:self.json_response({'ok':False,'message':str(error)},400)
        except Exception:self.json_response({'ok':False,'message':'操作未完成，请查看当前状态；不会自动重复创建任务'},500)

    def do_GET(self):
        try:
            login_path=urlsplit(self.path)
            login_match=re.fullmatch(r'/api/login/(?:(deepseek|deepseek2|deepseek_test)/)?(ui|state|frame|stream)',login_path.path)
            if login_match:
                model,part=login_match[1] or 'deepseek',login_match[2]
                token=self.session(create=part=='ui')
                from browser_backend import enabled as browser_enabled,ROOT as browser_root,read as browser_read
                if browser_enabled(model,BASE):
                    if part=='ui':self.login_response((browser_root/'login.html').read_bytes(),'text/html; charset=utf-8',cookie=token)
                    elif part=='state':self.login_response(json.dumps({**browser_read(browser_root/'state.json'),'csrf':token}).encode(),'application/json')
                    elif part=='frame':
                        from urllib.request import build_opener,ProxyHandler
                        with build_opener(ProxyHandler({})).open('http://127.0.0.1:8820/frame',timeout=15) as reply:self.login_response(reply.read(),'image/jpeg')
                    else:self.json_response({'error':'unsupported_browser_route'},404)
                    return
                if part=='ui':
                    self.login_response((BASE/'deepseek_login.html').read_bytes(),'text/html; charset=utf-8',cookie=token)
                elif part=='stream':
                    from manual_login import stream
                    flow=parse_qs(login_path.query).get('flow',[''])[0]
                    with stream(BASE,model,flow) as response:
                        self.send_response(200);self.send_header('Content-Type',response.headers['Content-Type']);self.send_header('Cache-Control','no-store');self.send_header('X-Accel-Buffering','no');self.send_header('Connection','close');self.end_headers()
                        try:
                            while True:
                                block=response.read1(65536)
                                if not block:break
                                self.wfile.write(block);self.wfile.flush()
                        except (BrokenPipeError,ConnectionResetError):pass
                else:
                    from manual_login import relay
                    code,mime,data=relay(BASE,part,model=model)
                    if part=='state' and code==200:
                        data=json.dumps({**json.loads(data),'csrf':token},ensure_ascii=False).encode()
                    self.login_response(data,mime,code)
                return
            if self.path.split('?')[0]=='/api/panel':
                token=self.session(create=True)
                day=parse_qs(urlsplit(self.path).query).get('date',[None])[0]
                self.json_response({**controller().all(day),'csrf':token},cookie=token)
                return
            match = re.fullmatch(r"/api/receipts/(deepseek|wenxin|yuanbao)/([a-f0-9]{64})", self.path)
            if match:
                token = read(Path('/opt/monitor/runtime/lan_result_receiver.json'))['token']
                if not hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + token):
                    self.send_error(401)
                    return
                model, rid = match.groups()
                path = Path('/opt/monitor/runtime/lan_result_receiver') / model / 'done' / (rid + '.json')
                result = {'status': 'processed', 'receipt': read(path)} if path.exists() else {'status': 'queued'}
                body, mime = json.dumps(result, ensure_ascii=False).encode(), 'application/json'
            elif self.path.split("?")[0] in {"/api/status", "/health"}:
                body, mime = json.dumps(status(), ensure_ascii=False).encode(), "application/json"
            elif self.path == "/":
                body, mime = (BASE/'panel.html').read_bytes(), "text/html"
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", mime + "; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header('X-Frame-Options','DENY')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except PermissionError as error:
            self.json_response({'ok':False,'message':str(error)},403)
        except ValueError:
            self.json_response({'ok':False,'message':'任务日期格式不正确'},400)
        except Exception:
            self.send_error(503, "Status unavailable")

    def log_message(self, *_):
        pass

    def login_response(self,data,mime,code=200,cookie=None):
        self.send_response(code)
        self.send_header('Content-Type',mime)
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','SAMEORIGIN')
        self.send_header('Content-Security-Policy',"frame-ancestors 'self'")
        self.send_header('Content-Length',str(len(data)))
        if cookie:self.send_header('Set-Cookie','geo_control='+cookie+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=21600')
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8803), Handler).serve_forever()
