"""Read-only production embed and runtime acceptance."""
import importlib.util
import json
import sqlite3
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path('/opt/monitor/geo-capture/maintenance/20261016-daily-controls')
spec=importlib.util.spec_from_file_location('release_deploy',ROOT/'deploy.py')
deploy=importlib.util.module_from_spec(spec);spec.loader.exec_module(deploy)
release=json.loads((ROOT/'release.json').read_text())
result={'views':[],'page_errors':[]}
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
    for width in (1600,390):
        page=browser.new_page(viewport={'width':width,'height':1100},permissions=['local-network-access'])
        page.on('pageerror',lambda error:result['page_errors'].append(str(error)))
        page.goto('http://127.0.0.1:3000/#capture/yuanbao',wait_until='domcontentloaded')
        frame=page.frame_locator('iframe[title="GEO 六通道采集控制台"]')
        frame.locator('#saveBtn').wait_for(timeout=45000)
        assert frame.locator('#saveBtn').inner_text()=='保存并立即生效'
        frame.locator('#dailyModels .daily-model').nth(5).wait_for(timeout=45000)
        assert frame.locator('#dailyModels .daily-model').count()==6
        page.wait_for_timeout(1200)
        overflow=page.evaluate('document.documentElement.scrollWidth > innerWidth')
        assert not overflow, f'Parent overflow at {width}'
        page.screenshot(path=str(ROOT/f'dashboard-daily-{width}.png'),full_page=True)
        result['views'].append({'width':width,'six_daily_models':True,'save_control':True,'parent_overflow':overflow})
        page.close()
    browser.close()
result['jobs_before']=release['jobs_before'];result['jobs_after']=deploy.jobs()
result['collectors_unchanged']=result['jobs_before']==result['jobs_after']
result['other_containers_unchanged']=release['containers_before']==deploy.containers()
result['actor']=deploy.run('systemctl','is-active','geo-daily-control.service')
with sqlite3.connect('/opt/monitor/geo-capture/panel/control.sqlite') as db:
    result['daily_rows']=[dict(zip(('model','day','desired','status','revision'),row)) for row in db.execute('select model,day,desired,status,revision from daily_tasks order by day,model')]
    result['launch_count']=db.execute('select count(*) from daily_launches').fetchone()[0]
result['actor_health']=json.loads(Path('/opt/monitor/geo-capture/daily_control_health.json').read_text())
assert not result['page_errors']
assert result['actor']=='active'
(ROOT/'final-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False))
