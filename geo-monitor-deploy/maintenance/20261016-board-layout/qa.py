"""Read-only geometry checks for real product tables and model filtering."""
import json
from pathlib import Path
import sys
import time
from playwright.sync_api import sync_playwright

port = int(sys.argv[1])
base = 'http://127.0.0.1:3000'
out = Path('/opt/monitor/geo-capture/maintenance/20261016-board-layout')
out.mkdir(exist_ok=True)
errors = []
report = {'started_at': time.time(), 'port': port, 'passed': False, 'layouts': []}

GEOMETRY = '''() => {
  const errors = [];
  for (const table of document.querySelectorAll('.owned-product-table table')) {
    const headers = [...table.querySelectorAll('thead th')];
    for (const row of table.querySelectorAll('tbody tr')) {
      [...row.cells].forEach((cell, index) => {
        const box = cell.getBoundingClientRect();
        const head = headers[index].getBoundingClientRect();
        if (Math.abs(box.left - head.left) > 1 || Math.abs(box.width - head.width) > 1)
          errors.push('header/body column alignment');
        for (const card of cell.querySelectorAll('.owned-product-model-average, .owned-product-surface, .owned-product-state')) {
          const r = card.getBoundingClientRect();
          if (r.left < box.left - 1 || r.right > box.right + 1)
            errors.push('card exceeds its column: ' + card.innerText.slice(0, 30));
          if (card.scrollWidth > card.clientWidth + 1)
            errors.push('text exceeds its card: ' + card.innerText.slice(0, 30));
        }
      });
    }
    for (const stack of table.querySelectorAll('.wenxin-surface-stack')) {
      const cards = [...stack.children].map(el => el.getBoundingClientRect());
      if (cards.length === 2 && cards[0].right > cards[1].left - 1)
        errors.push('Wenxin/Baidu cards overlap');
    }
  }
  if (document.documentElement.scrollWidth > innerWidth + 1) errors.push('page horizontal overflow');
  return [...new Set(errors)];
}'''

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/google-chrome', headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 1600, 'height': 1000}, permissions=['local-network-access'])
    if port == 3001:
        def preview_route(route):
            route.fulfill(response=page.request.get(route.request.url.replace(':3000/', ':3001/')))
        page.route(base + '/**', preview_route)
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(base, wait_until='domcontentloaded', timeout=60000)
    summary = page.locator('.owned-product-summary-table')
    summary.locator('tbody tr').first.wait_for(timeout=60000)
    for width in [1920, 1600, 1280, 390]:
        page.set_viewport_size({'width': width, 'height': 1000 if width > 400 else 844})
        for position in ['left', 'right']:
            page.locator('.owned-product-table').evaluate_all(
                '(elements, position) => elements.forEach(el => el.scrollLeft = position === "right" ? el.scrollWidth : 0)', position)
            problems = page.evaluate(GEOMETRY)
            assert not problems, {'width': width, 'position': position, 'errors': problems}
            report['layouts'].append({'width': width, 'position': position, 'errors': problems})
        if width in [1600, 390]:
            summary.locator('thead').scroll_into_view_if_needed()
            page.screenshot(path=str(out / f'board-{width}-{port}.png'))
    page.set_viewport_size({'width': 1600, 'height': 1000})
    for model in ['文心', '元宝', '全部模型']:
        page.locator('.scope').get_by_role('button', name=model).click()
        summary.locator('tbody tr').first.wait_for(timeout=60000)
        problems = page.evaluate(GEOMETRY)
        assert not problems, {'model': model, 'errors': problems}
        headers = summary.locator('thead th').all_inner_texts()
        assert not any('夸克' in text for text in headers)
        if model == '文心':
            assert len(headers) == 6 and '文心' in headers[-1], headers
        elif model == '元宝':
            assert len(headers) == 6 and '元宝' in headers[-1], headers
        else:
            assert len(headers) == 9, headers
        report['layouts'].append({'model': model, 'headers': headers, 'errors': problems})
    browser.close()
assert not errors, errors
report.update(passed=True, finished_at=time.time(), page_errors=errors)
(out / f'qa-{port}.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps(report, ensure_ascii=False))
