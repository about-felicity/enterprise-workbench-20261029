import json,time
from pathlib import Path
from monitor_core.cdp_chat import CDPPage
from web_collectors.collector import BrowserCollector
from web_collectors.config import site_config
page=CDPPage(9514)
try:
    collector=BrowserCollector.__new__(BrowserCollector);collector.site=site_config('deepseek');collector.page=page
    snapshot=collector._snapshot()
    controls=page.evaluate("""(()=>{const visible=e=>{const r=e.getBoundingClientRect();return r.width>8&&r.height>8};return [...document.querySelectorAll('[role=button].ds-button--circle,button[aria-label*=停止],[role=button][aria-label*=停止]')].filter(visible).map(e=>({aria:e.getAttribute('aria-label'),title:e.getAttribute('title'),tooltip:e.getAttribute('data-tooltip'),svg:e.querySelector('svg')?.outerHTML})).slice(-8)})()""")
    value={'at':time.time(),'body_length':len(snapshot['body']),'busy_detected':snapshot['busy'],
           'provider_error':bool(snapshot['providerError']),'controls':controls}
    path=Path('/opt/monitor/geo-capture/maintenance/20261015-reliability/deepseek-dom-readonly.json')
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2))
    print(json.dumps(value,ensure_ascii=False))
finally:page.ws.close()
