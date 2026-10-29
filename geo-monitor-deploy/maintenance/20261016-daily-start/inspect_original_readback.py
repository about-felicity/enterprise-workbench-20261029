"""Observe the original DeepSeek page only. No send or login operations."""
import json
import os
from pathlib import Path
import time
from geo_source_cards.runtime import process_lock
from geo_source_cards.journal import Journal
from web_collectors.collector import BrowserCollector

root=Path('/opt/monitor/geo-capture/batches/geo-panel-deepseek-20261016-094039-dc64b7e1/collector')
os.environ['GEO_COLLECTOR_RUNTIME']=str(root)
os.environ['GEO_DEEPSEEK_PORT']='9514'
out=Path('/tmp/deepseek-original-readback-diagnostic.json')
with process_lock(root/'collector.lock'):
    journal=Journal(root/'tasks.sqlite')
    try:
        task=dict(journal.db.execute("select * from captures where state='needs_attention'").fetchone())
        url=journal.original_conversation(task)
        assert url
    finally:journal.close()
    collector=BrowserCollector('deepseek')
    try:
        collector.page.call('Page.navigate',{'url':url},timeout=30)
        states=[]
        for i in range(5):
            time.sleep(5)
            state=collector.page.evaluate("JSON.stringify({url:location.href,title:document.title,readyState:document.readyState,text:String(document.body?.innerText||'').slice(0,1200),textLength:String(document.body?.innerText||'').length,inputs:document.querySelectorAll('textarea,[contenteditable=true]').length})")
            states.append({'at':time.time(),'dom':json.loads(state),'session':collector.session_status()})
            out.write_text(json.dumps(states,ensure_ascii=False,indent=2))
        print(json.dumps(states,ensure_ascii=False))
    finally:collector.close()
