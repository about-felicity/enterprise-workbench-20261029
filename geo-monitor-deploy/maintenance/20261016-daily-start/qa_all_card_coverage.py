"""Check every daily owned-product row against today's real observations."""
import json
from pathlib import Path
import time
import requests
from playwright.sync_api import sync_playwright

ROOT=Path('/opt/monitor/geo-capture/maintenance/20261016-daily-observations')
http=requests.Session();http.trust_env=False
url='http://127.0.0.1:8765/api/analytics?view=overview&date=2026-10-16&model=wenxin'
for attempt in range(160):
    response=http.get(url,timeout=60);response.raise_for_status()
    data=response.json();rows=[r for r in data['owned_product_daily'] if r['date']=='2026-10-16']
    missing=[]
    for row in rows:
        surfaces=row['models']['wenxin']['surfaces']
        for name,target in (('wenxin_card',8),('baidu_card',5)):
            surface=surfaces.get(name,{})
            if surface.get('raw_eligible_runs',0)<target or surface.get('eligible_runs',0)<1:
                missing.append({'question':row['question'],'product':row['product'],'surface':name,
                                'raw':surface.get('raw_eligible_runs',0),'effective':surface.get('eligible_runs',0)})
    summary={'at':time.time(),'products':len(rows),'questions':len({r['question'] for r in rows}),'missing':missing}
    (ROOT/'board-progress.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    if len(rows)==24 and summary['questions']==21 and not missing:break
    time.sleep(5)
else:raise AssertionError(summary)
(ROOT/'analytics.json').write_text(json.dumps(data,ensure_ascii=False))
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1600,'height':1000},permissions=['local-network-access'])
    errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto('http://127.0.0.1:3000/',wait_until='domcontentloaded',timeout=60000)
    day=page.locator('.owned-product-day').filter(has=page.locator('h3 time',has_text='2026-10-16')).first
    day.locator('tbody tr').first.wait_for(timeout=60000)
    for refresh in range(12):
        texts=[]
        for row in day.locator('tbody tr').all():
            for label in ('文心卡片','百度卡片'):
                cell=row.locator('.owned-product-surface').filter(has=page.locator('em',has_text=label))
                texts.append(cell.inner_text())
        if len(texts)==48 and all('轮推荐' in text and '检测中' not in text and '未采集' not in text for text in texts):break
        page.wait_for_timeout(3000)
        page.reload(wait_until='domcontentloaded')
        day.locator('tbody tr').first.wait_for(timeout=60000)
    else:raise AssertionError(texts)
    target=day.locator('tbody tr').filter(has=page.get_by_role('cell',name='防脱洗发水推荐',exact=True)).first
    target.scroll_into_view_if_needed()
    day.locator('.owned-product-table').evaluate('(el)=>el.scrollLeft=el.scrollWidth')
    page.screenshot(path=str(ROOT/'all-cards-live.png'))
    browser.close()
assert not errors,errors
report={**summary,'passed':True,'browser_cells_verified':len(texts),'page_errors':errors,'cells':texts}
(ROOT/'board-verified.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='cells'},ensure_ascii=False))
