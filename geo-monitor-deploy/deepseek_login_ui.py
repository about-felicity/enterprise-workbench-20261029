"""Temporary loopback-only manual login display. No credential logging or question submission."""
import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import hmac
import json
import os
from pathlib import Path
import sys
import threading
import time

WIDTH, HEIGHT, PORT = 1100, 780, 8805

def validate_input(value):
    kind = value.get('type')
    if kind == 'click':
        x, y = value.get('x'), value.get('y')
        if type(x) not in (int, float) or type(y) not in (int, float) or not (0 <= x < WIDTH and 0 <= y < HEIGHT):
            raise ValueError('无效点击位置')
        return kind, {'x': x, 'y': y}
    if kind == 'text':
        text = value.get('text')
        if not isinstance(text, str) or not 1 <= len(text) <= 4096:
            raise ValueError('无效输入')
        return kind, {'text': text}
    if kind == 'key':
        key = value.get('key')
        keys = {'Enter': 13, 'Tab': 9, 'Backspace': 8, 'Delete': 46, 'Escape': 27,
                'ArrowLeft': 37, 'ArrowUp': 38, 'ArrowRight': 39, 'ArrowDown': 40,
                'Home': 36, 'End': 35, 'a': 65}
        modifiers = value.get('modifiers', 0)
        if key not in keys or type(modifiers) is not int or not 0 <= modifiers <= 15:
            raise ValueError('不支持的按键')
        return kind, {'key': key, 'windowsVirtualKeyCode': keys[key], 'modifiers': modifiers}
    if kind == 'scroll':
        delta = value.get('delta')
        if type(delta) not in (int, float) or not -1000 <= delta <= 1000:
            raise ValueError('无效滚动')
        return kind, {'type': 'mouseWheel', 'x': WIDTH // 2, 'y': HEIGHT // 2, 'deltaX': 0, 'deltaY': delta}
    raise ValueError('不支持的操作')

def main(request_path, *, port=PORT, linger=8, poll_seconds=2):
    from geo_source_cards.runtime import process_lock
    from web_collectors.collector import BrowserCollector
    request_path = Path(request_path)
    request = json.loads(request_path.read_text())
    state_path = request_path.with_name('state.json')
    lock = threading.RLock()
    state = {'id': request['id'], 'batch': request['batch'], 'revision': request['revision'],
             'status': 'opening', 'created_at': time.time(), 'expires_at': time.time() + 900}
    collector = None

    def publish(status, message):
        state.update(status=status, message=message, updated_at=time.time())
        tmp = state_path.with_suffix('.tmp')
        tmp.write_text(json.dumps(state, ensure_ascii=False))
        tmp.replace(state_path)

    class Handler(BaseHTTPRequestHandler):
        def authorized(self):
            return hmac.compare_digest(self.headers.get('X-Login-Token', ''), request['token'])
        def respond(self, data, mime='application/json', code=200):
            if not isinstance(data, bytes): data = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', mime)
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        def do_GET(self):
            if not self.authorized(): self.respond({'ok': False}, code=403); return
            try:
                with lock:
                    if self.path == '/state': self.respond(state); return
                    if self.path != '/frame': self.respond({'ok': False}, code=404); return
                    if state['status'] != 'waiting_login' or collector is None:
                        self.respond({'ok': False, 'message': '登录页面已关闭'}, code=409); return
                    frame = collector.page.call('Page.captureScreenshot', {'format': 'jpeg', 'quality': 75})
                    self.respond(base64.b64decode(frame['data']), 'image/jpeg')
            except Exception: self.respond({'ok': False, 'message': '登录画面暂不可用'}, code=503)
        def do_POST(self):
            if not self.authorized(): self.respond({'ok': False}, code=403); return
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if self.path != '/input' or not 0 < size <= 20000: raise ValueError('无效输入')
                kind, params = validate_input(json.loads(self.rfile.read(size)))
                with lock:
                    if state['status'] != 'waiting_login' or collector is None:
                        self.respond({'ok': False, 'message': '登录页面已关闭'}, code=409); return
                    # Only direct user input is relayed. Never replay input after a lost reply.
                    if kind == 'click': collector.page.click(**params)
                    elif kind == 'text': collector.page.call('Input.insertText', params)
                    elif kind == 'scroll': collector.page.call('Input.dispatchMouseEvent', params)
                    else:
                        collector.page.call('Input.dispatchKeyEvent', {'type': 'rawKeyDown', **params})
                        collector.page.call('Input.dispatchKeyEvent', {'type': 'keyUp', **params})
                    self.respond({'ok': True})
            except ValueError as error: self.respond({'ok': False, 'message': str(error)}, code=400)
            except Exception: self.respond({'ok': False, 'message': '输入结果未确认，请查看画面后再操作'}, code=503)
        def log_message(self, *_): pass

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    runtime = Path(request['runtime'])
    os.environ.pop('GEO_PIPELINE_ROOT', None)
    os.environ.update(GEO_COLLECTOR_RUNTIME=str(runtime), GEO_DEEPSEEK_PORT='9514')
    try:
        publish('opening', '正在打开 DeepSeek 登录页面')
        with process_lock(runtime / 'collector.lock'):
            collector = BrowserCollector('deepseek', headless=True)
            collector.page.call('Emulation.setDeviceMetricsOverride', {'width': WIDTH, 'height': HEIGHT, 'deviceScaleFactor': 1, 'mobile': False})
            collector.navigate_home()
            publish('waiting_login', '请在此页面手动完成 DeepSeek 登录')
            stable = 0
            while time.time() < state['expires_at']:
                with lock:
                    observed = collector.session_status()
                    cookies = collector.page.call('Network.getAllCookies').get('cookies', [])
                    stable = stable + 1 if observed.get('ok') and cookies else 0
                    if stable >= 2:
                        publish('verifying', '已检测到登录，登录页面已关闭；正在复核采集会话')
                        collector.close()
                        collector = None
                        break
                time.sleep(poll_seconds)
            else: raise TimeoutError('login_timeout')
            with lock:
                collector = BrowserCollector('deepseek', headless=True)
                result = collector.check_ready()
                collector.close()
                collector = None
                publish('ready' if result.get('ok') else 'failed',
                        '登录及采集会话复核通过' if result.get('ok') else '采集会话尚未就绪，请重新校验')
            time.sleep(linger)
    except Exception:
        publish('failed', '登录未完成或会话不可用，请重新打开登录页面')
    finally:
        with lock:
            if collector: collector.close()
        server.shutdown()
        server.server_close()

if __name__ == '__main__': main(sys.argv[1])
