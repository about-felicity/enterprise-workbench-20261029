"""Read original authenticated history only; never submits or starts a chat."""
import json
import os
from pathlib import Path
import time
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
from web_collectors.collector import BrowserCollector
root=Path('/opt/monitor/geo-capture/batches/geo-panel-deepseek-20261015-181821-879aca5d/collector')
os.environ['GEO_COLLECTOR_RUNTIME']=str(root);os.environ['GEO_DEEPSEEK_PORT']='9514'
out=Path('/tmp/geo-deepseek-reconciliation-17920612');out.mkdir(mode=0o700,exist_ok=True)
collector=BrowserCollector('deepseek',headless=True)
try:
    with sync_playwright() as p:
        browser=p.chromium.connect_over_cdp('http://127.0.0.1:9514')
        context=browser.contexts[0];page=context.pages[0];responses=[]
        def observe(response):
            path=urlsplit(response.url).path
            if '/api/' not in path:return
            entry={'path':path,'status':response.status,'method':response.request.method}
            if 'chat_session' in path or '/history' in path:
                try:entry['body']=response.json()
                except Exception:pass
            responses.append(entry)
        page.on('response',observe)
        page.goto('https://chat.deepseek.com/',wait_until='domcontentloaded',timeout=45000)
        page.wait_for_timeout(5000)
        links=page.locator('a[href*="/a/chat/s/"]').evaluate_all('(nodes)=>nodes.map(n=>({url:n.href,title:n.innerText}))')
        (out/'history.json').write_text(json.dumps({'at':time.time(),'responses':responses,'links':links},ensure_ascii=False,indent=2))
        print(json.dumps({'links':len(links),'responses':[{'path':r['path'],'status':r['status'],'body_keys':list(r.get('body',{}))} for r in responses]},ensure_ascii=False))
        browser.close()
finally:collector.close()
