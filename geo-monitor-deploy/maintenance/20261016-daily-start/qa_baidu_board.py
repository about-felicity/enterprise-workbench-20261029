"""Read the live product board using a separate regression-test browser."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

out = Path('/opt/monitor/geo-capture/maintenance/20261016-daily-start')
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 1600, 'height': 1000}, permissions=['local-network-access'])
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://127.0.0.1:3000/', wait_until='domcontentloaded', timeout=60000)
    page.locator('.owned-product-daily-table tbody tr').first.wait_for(timeout=60000)
    day = page.locator('.owned-product-day').filter(has=page.locator('h3 time', has_text='2026-10-16')).first
    rows = {}
    for question in ('卸妆油推荐', '防晒霜推荐', '护发精油推荐'):
        row = day.locator('tbody tr').filter(has=page.get_by_role('cell', name=question, exact=True)).first
        row.wait_for(timeout=30000)
        cell = row.locator('.owned-product-surface').filter(has=page.locator('em', has_text='百度卡片'))
        text = cell.inner_text()
        assert '无卡片' not in text and '检测中' not in text and '轮采集' in text, (question, text)
        rows[question] = text
    row.scroll_into_view_if_needed()
    day.locator('.owned-product-table').evaluate('(el)=>el.scrollLeft=el.scrollWidth')
    page.screenshot(path=str(out / 'baidu-board-live.png'))
    browser.close()
assert not errors, errors
report = {'passed': True, 'rows': rows, 'page_errors': errors}
(out / 'baidu-board-qa.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps(report, ensure_ascii=False))
