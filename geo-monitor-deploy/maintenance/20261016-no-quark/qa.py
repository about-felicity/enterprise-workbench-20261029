"""Read-only browser regression against the LAN frontend in an isolated browser."""
import json
from pathlib import Path
import sys
import time
from playwright.sync_api import sync_playwright

port = int(sys.argv[1])
# Analytics intentionally allows only the production frontend origin (port 3000).
# Preview serves real built frontend responses under that origin in this isolated
# browser, while analytics requests continue to hit the unchanged real API.
base = 'http://127.0.0.1:3000'
out = Path('/opt/monitor/geo-capture/maintenance/20261016-no-quark')
report = {'at': time.time(), 'port': port, 'passed': False}
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 1600, 'height': 1000}, permissions=['local-network-access'])
    if port == 3001:
        def preview_route(route):
            response = page.request.get(route.request.url.replace(':3000/', ':3001/'))
            route.fulfill(response=response)
        page.route(base + '/**', preview_route)
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('requestfailed', lambda request: print('Request failed:', request.url, request.failure, flush=True))
    page.on('console', lambda message: print('Browser:', message.text[:700], flush=True) if message.type == 'error' else None)
    page.goto(base, wait_until='domcontentloaded', timeout=60000)
    scope = page.locator('.scope')
    scope.get_by_role('button', name='元宝').wait_for(timeout=60000)
    page.locator('.owned-product-board table').first.wait_for(timeout=60000)
    for name in ['DeepSeek', '豆包', '文心', '元宝']:
        assert scope.get_by_role('button', name=name).count() == 1
    assert scope.get_by_role('button').count() == 5  # All + four active models.
    assert '夸克' not in page.locator('body').inner_text()
    assert page.locator('.model-card').count() == 4
    assert not page.locator('.owned-product-board th').filter(has_text='夸克').count()
    page.screenshot(path=str(out / f'desktop-{port}.png'), full_page=False)
    report['sidebar_models'] = scope.get_by_role('button').all_inner_texts()
    report['model_cards'] = page.locator('.model-card header b').all_inner_texts()
    page.locator('.sidebar nav').get_by_role('button', name='问题对比').click()
    page.get_by_role('button', name='刷新数据', exact=True).wait_for(timeout=60000)
    assert '夸克' not in page.locator('body').inner_text()
    page.goto(base + '/#capture/doubao1', wait_until='domcontentloaded')
    controls = page.frame_locator('iframe[title="GEO 六通道采集控制台"]')
    controls.locator('#modelTitle').wait_for(timeout=60000)
    controls.locator('#nav .nav-item').nth(5).wait_for(timeout=60000)
    assert controls.locator('#nav .nav-item').count() == 6
    assert '夸克' not in page.locator('body').inner_text()
    page.goto(base + '/#creation', wait_until='domcontentloaded')
    page.frame_locator('iframe[title="GEO 内容创作控制台"]').locator('#product').wait_for(timeout=60000)
    report['capture_and_creation_loaded'] = True
    page.set_viewport_size({'width': 390, 'height': 844})
    page.goto(base, wait_until='domcontentloaded')
    page.locator('.scope').get_by_role('button', name='元宝').wait_for(timeout=60000)
    assert '夸克' not in page.locator('body').inner_text()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    page.screenshot(path=str(out / f'mobile-{port}.png'), full_page=False)
    browser.close()
assert not errors, errors
report.update(passed=True, page_errors=errors, finished_at=time.time())
(out / f'qa-{port}.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps(report, ensure_ascii=False))
