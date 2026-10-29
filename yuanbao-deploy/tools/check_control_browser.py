"""Read-only preview/public browser acceptance; action clicks are intercepted."""
import argparse
import json
from pathlib import Path
import sys
import time

import requests
from playwright.sync_api import sync_playwright
from monitor_core.cdp_chat import chrome_executable

parser = argparse.ArgumentParser()
parser.add_argument('--public', action='store_true')
parser.add_argument('--port', type=int, default=3001)
args = parser.parse_args()
BASE = 'https://1any.top/geo_monitor' if args.public else f'http://127.0.0.1:{args.port}'
OUT = Path('/opt/monitor/geo-capture/panel-qa')
OUT.mkdir(exist_ok=True)
session = requests.Session()
session.trust_env = False


def current():
    response = session.get('http://127.0.0.1:8803/api/panel', timeout=15)
    response.raise_for_status()
    return {m['id']: {'batch': m['current']['batch'], 'revision': m['revision'],
                      'service_state': m['current']['service_state']} for m in response.json()['models']}


before = current()
report = {'started_at': time.time(), 'url': BASE, 'port': args.port}
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=str(chrome_executable()), headless=True,
                                        args=['--no-sandbox'])
    context = browser.new_context(viewport={'width': 1440, 'height': 1050})
    if args.public:
        sys.path.insert(0, '/tmp/yuanbao-control-qa')
        from vps_geo_access import browser_cookie
        token = browser_cookie()
        context.add_cookies([{'name': 'geo_monitor_session', 'value': token, 'domain': '1any.top',
                             'path': '/geo_monitor/', 'httpOnly': True, 'secure': True, 'sameSite': 'Lax'}])
        del token
        response = session.get(BASE + '/api/geo-capture/panel', allow_redirects=False, timeout=20)
        assert response.status_code in (302, 401)
        report['public_unauthenticated_gate_preserved'] = True
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(BASE + '/#capture/yuanbao', wait_until='domcontentloaded', timeout=60000)
    ui = page.frame_locator('iframe[title="GEO 六通道采集控制台"]')
    ui.locator('#modelTitle').filter(has_text='元宝').wait_for(timeout=60000)
    frame = next(f for f in page.frames if '/api/geo-capture/ui' in f.url)
    assert ui.locator('#nav .nav-item').count() == 6
    assert len(ui.locator('#questions').input_value().strip().splitlines()) == 21
    assert ui.locator('#loginBox').is_visible()
    report['yuanbao_sixth_lane_with_questions_and_login'] = True
    invalid = frame.evaluate('''async () => {
      const state = await (await fetch('API/panel')).json();
      const model = state.models.find(m=>m.id==='yuanbao');
      const r = await fetch('API/control/yuanbao/settings', {method:'POST',
        headers:{'Content-Type':'application/json','X-CSRF-Token':state.csrf,
                 'X-Action-Id':crypto.randomUUID().replaceAll('-','')},
        body:JSON.stringify({questions:[],rounds:5,interval:45,revision:model.revision})});
      return {status:r.status,body:await r.json()};
    }'''.replace('API', '/geo_monitor/api/geo-capture' if args.public else '/api/geo-capture'))
    assert invalid['status'] == 400 and '问题' in invalid['body'].get('message', ''), invalid
    report['yuanbao_write_reaches_validation_without_mutating_settings'] = True
    calls = []

    def isolate(route):
        calls.append(route.request.url)
        route.fulfill(status=200, content_type='application/json', body=json.dumps(
            {'ok': True, 'message': '元宝按钮隔离验证成功'}))

    page.route('**/api/geo-capture/control/yuanbao/**', isolate)
    ui.locator('#resumeBtn').click()
    ui.locator('#notice').filter(has_text='元宝按钮隔离验证成功').wait_for()
    assert len(calls) == 1 and calls[0].startswith(BASE + '/api/geo-capture/control/yuanbao/')
    page.unroute('**/api/geo-capture/control/yuanbao/**', isolate)
    report['yuanbao_resume_button_path_verified_without_starting_task'] = True
    page.screenshot(path=str(OUT / ('yuanbao-public.png' if args.public else 'yuanbao-preview.png')), full_page=True)
    page.set_viewport_size({'width': 390, 'height': 844})
    page.wait_for_timeout(700)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
    assert frame.evaluate('document.documentElement.scrollWidth <= innerWidth+1')
    report['desktop_mobile_layout_passed'] = True
    assert not errors, errors
    browser.close()
assert current() == before, 'Browser acceptance changed a batch, settings or service state'
report.update(passed=True, production_tasks_unchanged=True, browser_errors=errors, finished_at=time.time())
(OUT / ('yuanbao-public.json' if args.public else 'yuanbao-preview.json')).write_text(
    json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps(report, ensure_ascii=False))
